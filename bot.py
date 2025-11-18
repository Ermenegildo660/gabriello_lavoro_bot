import os
import json
from datetime import datetime
from typing import Dict, Any, List

from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # imposta su Railway
OWNER_ID = int(os.environ.get("OWNER_ID", "361555418"))

DATA_FILE = "dati_lavoro.json"
FIXED_JOBS_FILE = "fixed_jobs.json"

# Tastiere principali
MAIN_KEYS = [
    ["Entrata", "Uscita"],
    ["Inizio lavoro", "Fine lavoro"],
    ["Lavori del giorno"],
    ["Esporta Excel", "Reset mese"]
]

CLOSE_KEY = [["Chiudi"]]


# ---------------- UTILITIES FILES ----------------
def load_json_file(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------------- DEFAULT FIXED JOBS (init if missing) ----------------
DEFAULT_FIXED_JOBS = {
    "Lavaggi settimanali": [
        "Lavaggio settimanale di scalette pasticceria",
        "Lavaggio settimanale di rampa acceso panificio",
        "Lavaggio settimanale corridoio e aspirapolvere dietro forni",
        "Lavaggio carelli e sistemazione teglie legno",
        "Lavaggio bandelle cella negativa pasticceria",
        "Lavaggio e pulizia totale di cella negativa pasticceria"
    ],
    "Pulizia forni (Polin/Bongard/Rotor/Platea)": [
        "Pulizia settimanale di forni rotor Polin e Bongard (precotto/cotto/pizzeria)",
        "Pulizia tappeto semi automatico pane forni platea",
        "Pulizia mensile di linea taglio pane ad acqua Beor",
        "Pulizia mensile di frontale forno platea n.11",
        "Pulizia mensile di frontale forno platea n.10",
        "Pulizia mensile frontali forni rotor (gruppi vari)",
        "Pulizia sopra forni rotor e Polin zona cotto (tubi + condensa)",
        "Pulizia sopra forni rotor e Polin zona precotto (tubi + condensa)",
        "Pulizia forni rotor Polin zona cotto internamente (idropulitrice)"
    ],
    "Linee di produzione": [
        "Pulizia di linee taglio pane a fette e imbustaggio pane",
        "Pulizia settimanale di linea tappetti contrapposti zona panetteria",
        "Pulizia di linea impacchettamento pasta pizza",
        "Pulizia di nuova macchina robot scarica carrelli in zona forno area cotto"
    ],
    "Macchinari e altre pulizie": [
        "Pulizia volumetrica spezzatrice pasta pizza",
        "Pulizia volumetrica spezzatrice pagnotte",
        "Pulizia filtri sala farina silos",
        "Pulizia di teglie farina su carrello",
        "Pulizia mensile di pesa linea ingredienti",
        "Pulizia di lavastoviglie Velox e lavastoviglie piccole",
        "Pulizia di lavastoviglie a tunnel Velox zona resi",
        "Manutenzione addolcitori (riempimento sale/cillit)"
    ],
    "Altro (mensili/straordinari)": [
        "Controllo numeri pozzetti di acqua potabile e vigili del fuoco",
        "Manutenzione straordinaria di addolcitori (cicli)",
        "Pulizia mensile di forni rotor Polin e bongard zona precotto internamente (idropulitrice)"
    ]
}


def ensure_fixed_jobs():
    if not os.path.exists(FIXED_JOBS_FILE):
        save_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)


# ---------------- DATA MODEL ----------------
def load_data() -> Dict[str, Any]:
    default = {}
    return load_json_file(DATA_FILE, default)


def save_data(data: Dict[str, Any]):
    save_json_file(DATA_FILE, data)


def date_key(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d")


def get_today_record(data: Dict[str, Any]) -> Dict[str, Any]:
    key = date_key()
    if key not in data:
        # initialize day's record
        data[key] = {
            "data": key,
            "entrata": None,
            "uscita": None,
            "ore_lavorate": None,
            "inizio_lavoro": None,
            "fine_lavoro": None,
            "ore_sessione": None,
            "lavori_fissi": [],
            "lavori_extra": []
        }
    return data[key]


# ---------------- HELPERS TEMPI ----------------
def current_time_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def calculate_hours(start_str: str, end_str: str) -> float:
    fmt = "%Y-%m-%d %H:%M:%S"
    start = datetime.strptime(start_str, fmt)
    end = datetime.strptime(end_str, fmt)
    diff = end - start
    hours = round(diff.total_seconds() / 3600, 2)
    return hours


# ---------------- KEYBOARD BUILDERS ----------------
def main_keyboard():
    return ReplyKeyboardMarkup(MAIN_KEYS, resize_keyboard=True)


def simple_keyboard(options: List[List[str]]):
    return ReplyKeyboardMarkup(options, resize_keyboard=True)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
        return
    ensure_fixed_jobs()
    await update.message.reply_text("Ciao — bot di lavoro attivo ✅", reply_markup=main_keyboard())


# State flags in-memory per flussi (può anche essere persistito, qui user_data basta)
# keys in context.user_data:
#  "expecting_new_fixed" -> True when waiting name to add to fixed list (category expected in payload)
#  "expecting_extra_job" -> True when waiting user to write a free-text extra job
#  "browse_category" -> name of category user is browsing (to show back)
# We'll store also temporary "last_category_for_new" when adding to a specific category.

# ---------------- LAVORI FLOW ----------------
async def lavori_del_giorno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # show options: Lavori fissi, Lavoro extra, Aggiungi nuovo lavoro fisso, Chiudi
    opts = [
        ["Lavori fissi", "Lavoro extra"],
        ["Aggiungi nuovo lavoro fisso", "Chiudi"]
    ]
    await update.message.reply_text("Scegli:", reply_markup=simple_keyboard(opts))


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    categories = list(fixed_jobs.keys())
    # split categories into keyboard rows (2 per row)
    rows = []
    temp = []
    for c in categories:
        temp.append(c)
        if len(temp) == 2:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    rows.append(["Indietro"])
    await update.message.reply_text("Scegli la categoria:", reply_markup=simple_keyboard(rows))
    # set browsing flag
    context.user_data["browse_category"] = None


async def show_jobs_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    jobs = fixed_jobs.get(category, [])
    if not jobs:
        await update.message.reply_text("Nessun lavoro in questa categoria.", reply_markup=simple_keyboard([["Indietro"]]))
        return
    # build rows (2 per row)
    rows = []
    temp = []
    for j in jobs:
        temp.append(j)
        if len(temp) == 2:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    rows.append(["Indietro"])
    context.user_data["browse_category"] = category
    await update.message.reply_text(f"Scegli il lavoro da aggiungere alla giornata ({category}):", reply_markup=simple_keyboard(rows))


async def add_fixed_job_to_today(update: Update, context: ContextTypes.DEFAULT_TYPE, job_name: str):
    data = load_data()
    rec = get_today_record(data)
    rec["lavori_fissi"].append(job_name)
    save_data(data)
    await update.message.reply_text(f"✅ Lavoro aggiunto: {job_name}", reply_markup=main_keyboard())


async def prompt_new_fixed_job_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ask for category where to add new fixed job
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    categories = list(fixed_jobs.keys()) + ["Nuova categoria"]
    # keyboard rows
    rows = []
    temp = []
    for c in categories:
        temp.append(c)
        if len(temp) == 2:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    rows.append(["Indietro"])
    await update.message.reply_text("Scegli la categoria a cui vuoi aggiungere il lavoro (o 'Nuova categoria'):", reply_markup=simple_keyboard(rows))
    context.user_data["expecting_new_fixed_category"] = True


async def handle_new_fixed_job_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Indietro":
        context.user_data.pop("expecting_new_fixed_category", None)
        await update.message.reply_text("Annullato.", reply_markup=main_keyboard())
        return
    if text == "Nuova categoria":
        context.user_data["expecting_new_fixed_newcategory_name"] = True
        await update.message.reply_text("Scrivi il nome della nuova categoria:", reply_markup=simple_keyboard([["Indietro"]]))
        return
    # selected existing category
    context.user_data["last_category_for_new"] = text
    context.user_data["expecting_new_fixed"] = True
    await update.message.reply_text(f"Scrivi il nome del nuovo lavoro da aggiungere alla categoria '{text}':", reply_markup=simple_keyboard([["Indietro"]]))


async def handle_new_fixed_job_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Indietro":
        context.user_data.pop("expecting_new_fixed_newcategory_name", None)
        await update.message.reply_text("Annullato.", reply_markup=main_keyboard())
        return
    # create new category and then ask for job name
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    fixed_jobs[text] = []
    save_json_file(FIXED_JOBS_FILE, fixed_jobs)
    context.user_data["last_category_for_new"] = text
    context.user_data["expecting_new_fixed_newcategory_name"] = False
    context.user_data["expecting_new_fixed"] = True
    await update.message.reply_text(f"Categoria '{text}' creata. Ora scrivi il nome del lavoro da aggiungere a '{text}':", reply_markup=simple_keyboard([["Indietro"]]))


async def handle_new_fixed_job_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Indietro":
        context.user_data.pop("expecting_new_fixed", None)
        context.user_data.pop("last_category_for_new", None)
        await update.message.reply_text("Annullato.", reply_markup=main_keyboard())
        return
    category = context.user_data.get("last_category_for_new")
    if not category:
        await update.message.reply_text("Errore: nessuna categoria selezionata.", reply_markup=main_keyboard())
        return
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    fixed_jobs.setdefault(category, []).append(text)
    save_json_file(FIXED_JOBS_FILE, fixed_jobs)
    context.user_data.pop("expecting_new_fixed", None)
    context.user_data.pop("last_category_for_new", None)
    await update.message.reply_text(f"✅ Nuovo lavoro fisso '{text}' aggiunto a '{category}'.", reply_markup=main_keyboard())


async def prompt_extra_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expecting_extra_job"] = True
    await update.message.reply_text("Scrivi il lavoro extra per oggi (testo libero):", reply_markup=simple_keyboard([["Annulla"]]))


async def handle_extra_job_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() in ("annulla", "anulla"):
        context.user_data.pop("expecting_extra_job", None)
        await update.message.reply_text("Annullato.", reply_markup=main_keyboard())
        return
    data = load_data()
    rec = get_today_record(data)
    rec["lavori_extra"].append(text)
    save_data(data)
    context.user_data.pop("expecting_extra_job", None)
    await update.message.reply_text(f"✅ Lavoro extra aggiunto: {text}", reply_markup=main_keyboard())


# ---------------- ORE / ENTRATA / USCITA HANDLERS ----------------
async def handle_entrata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    rec = get_today_record(data)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec["entrata"] = now
    save_data(data)
    await update.message.reply_text(f"✅ Entrata registrata: {now}", reply_markup=main_keyboard())


async def handle_uscita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    rec = get_today_record(data)
    if not rec.get("entrata"):
        await update.message.reply_text("⚠️ Non hai registrato l'entrata oggi.", reply_markup=main_keyboard())
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec["uscita"] = now
    # compute ore lavorate if possible
    try:
        rec["ore_lavorate"] = calculate_hours(rec["entrata"], rec["uscita"])
    except Exception:
        rec["ore_lavorate"] = None
    save_data(data)
    await update.message.reply_text(f"✅ Uscita registrata: {now}\nOre lavorate (stim.): {rec.get('ore_lavorate')}", reply_markup=main_keyboard())


async def handle_inizio_lavoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    rec = get_today_record(data)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec["inizio_lavoro"] = now
    save_data(data)
    await update.message.reply_text(f"✅ Inizio sessione registrato: {now}", reply_markup=main_keyboard())


async def handle_fine_lavoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    rec = get_today_record(data)
    if not rec.get("inizio_lavoro"):
        await update.message.reply_text("⚠️ Non hai registrato l'inizio della sessione.", reply_markup=main_keyboard())
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec["fine_lavoro"] = now
    try:
        rec["ore_sessione"] = calculate_hours(rec["inizio_lavoro"], rec["fine_lavoro"])
    except Exception:
        rec["ore_sessione"] = None
    save_data(data)
    await update.message.reply_text(f"✅ Fine sessione registrata: {now}\nOre sessione: {rec.get('ore_sessione')}", reply_markup=main_keyboard())


# ---------------- EXPORT EXCEL ----------------

if text == "Esporta Excel":
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Registro lavori"

        # intestazioni
        ws.append(["Azione", "Inizio", "Fine", "Orario", "Ore", "Lavoro"])

        # scrittura righe
        for r in data[user]["records"]:
            ws.append([
                r.get("azione", ""),
                r.get("inizio", ""),
                r.get("fine", ""),
                r.get("orario", ""),
                r.get("ore", ""),
                r.get("lavoro", "")
            ])

        # nome file Excel vero
        filename = "registro_lavoro.xlsx"
        wb.save(filename)

        # invio file
        await update.message.reply_document(
            open(filename, "rb"),
            caption="📄 Esportazione completata"
        )

    except Exception as e:
        await update.message.reply_text(f"Errore durante esportazione: {str(e)}")

    return


# ---------------- RESET MESE ----------------
async def reset_mese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # simple reset: clear data file
    save_data({})
    await update.message.reply_text("🔄 Tutti i dati sono stati resettati.", reply_markup=main_keyboard())


# ---------------- MAIN MESSAGE ROUTER ----------------
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user != OWNER_ID:
        return

    text = update.message.text.strip()

    # priority: flows (expecting flags)
    if context.user_data.get("expecting_new_fixed_category"):
        await handle_new_fixed_job_category(update, context)
        return
    if context.user_data.get("expecting_new_fixed_newcategory_name"):
        await handle_new_fixed_job_category_name(update, context)
        return
    if context.user_data.get("expecting_new_fixed"):
        await handle_new_fixed_job_name(update, context)
        return
    if context.user_data.get("expecting_extra_job"):
        await handle_extra_job_text(update, context)
        return

    # Main commands mapping
    if text == "Entrata":
        await handle_entrata(update, context)
        return
    if text == "Uscita":
        await handle_uscita(update, context)
        return
    if text == "Inizio lavoro":
        await handle_inizio_lavoro(update, context)
        return
    if text == "Fine lavoro":
        await handle_fine_lavoro(update, context)
        return
    if text == "Lavori del giorno":
        await lavori_del_giorno(update, context)
        return
    if text == "Lavori fissi":
        await show_categories(update, context)
        return
    if text == "Lavoro extra":
        await prompt_extra_job(update, context)
        return
    if text == "Aggiungi nuovo lavoro fisso":
        await prompt_new_fixed_job_category(update, context)
        return
    if text == "Chiudi" or text == "Indietro":
        await update.message.reply_text("Ok", reply_markup=main_keyboard())
        # cleanup flags
        context.user_data.pop("browse_category", None)
        context.user_data.pop("expecting_new_fixed", None)
        context.user_data.pop("expecting_extra_job", None)
        context.user_data.pop("expecting_new_fixed_category", None)
        context.user_data.pop("expecting_new_fixed_newcategory_name", None)
        context.user_data.pop("last_category_for_new", None)
        return
    if text == "Esporta Excel":
        await export_excel(update, context)
        return
    if text == "Reset mese":
        await reset_mese(update, context)
        return

    # If user selected a category name while browsing categories:
    fixed_jobs = load_json_file(FIXED_JOBS_FILE, DEFAULT_FIXED_JOBS)
    if text in fixed_jobs.keys():
        await show_jobs_in_category(update, context, text)
        return

    # If user selected a job name while browsing a category:
    current_cat = context.user_data.get("browse_category")
    if current_cat:
        # check if text is a job inside current category
        jobs_in_cat = fixed_jobs.get(current_cat, [])
        if text in jobs_in_cat:
            await add_fixed_job_to_today(update, context, text)
            return

    # If none matched, fallback
    await update.message.reply_text("Comando non riconosciuto. Usa i pulsanti.", reply_markup=main_keyboard())


# ---------------- STARTUP ----------------
def main():
    ensure_fixed_jobs()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("Bot lavoro avviato...")
    app.run_polling()


if __name__ == "__main__":
    main()
