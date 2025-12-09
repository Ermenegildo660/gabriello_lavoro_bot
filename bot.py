import json
import os
from datetime import datetime
import pytz

from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# --------------------------
# CONFIG
# --------------------------

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # tuo ID

# timezone Italia
TZ = pytz.timezone("Europe/Rome")

# --------------------------
# LAVORI FISSI
# --------------------------

LAVORI_FISSI = [
    "Lavaggio settimanale scalette pasticceria",
    "Lavaggio settimanale rampa panificio",
    "Pulizia settimanale forni rotor Polin/Bongard precotto/cotto/pizzeria",
    "Soffiatura bruciatori platea/Werner",
    "Pulizia tappeto semi automatico pane forni platea",
    "Pulizia linee taglio pane e imbustaggio",
    "Pulizia settimanale linea tappetti panetteria",
    "Pulizia filtri sala farina silos",
    "Lavaggio corridoio e aspirapolvere dietro forni",
    "Pulizia volumetrica spezzatrice pizza",
    "Pulizia volumetrica spezzatrice pagnotte",
    "Controllo numeri pozzetti acqua/vvf",
    "Pulizia robot scarica carrelli zona cotto",
    "Pulizia mensile linea taglio pane acqua Beor",
    "Lavaggio lavastoviglie Velox",
    "Pulizia mensile frontale forno platea 10",
    "Pulizia mensile frontale forno platea 11",
    "Pulizia sopra forni rotor/Polin zona cotto",
    "Pulizia mensile 4 frontali forni rotor",
    "Pulizia sopra forni rotor/Polin zona precotto",
    "Pulizia lavastoviglie tunnel resi",
    "Pulizia mensile forni rotor precotto",
    "Pulizia teglie farina su carrello",
    "Manutenzione addolcitori (sale/cillit)",
    "Lavaggio carrelli e teglie legno",
    "Pulizia mensile frontali rotor 1/2/3",
    "Pulizia rotor Polin cotto (1 pezzo)",
    "Pulizia rotor Polin cotto (2 pezzi)",
    "Pulizia rotor Polin farcitura pizze (2 pezzi)",
    "Pulizia linea impacchettamento pizza",
    "Lavaggio bandelle cella negativa pasticceria",
    "Pulizia totale cella negativa pasticceria"
]

# --------------------------
# FUNZIONI BASE
# --------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def now_it():
    """Orario corretto italiano anche su Railway"""
    return datetime.now(TZ)

# --------------------------
# TASTIERE
# --------------------------

def menu_principale():
    return ReplyKeyboardMarkup([
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Lavori del giorno", "Lavori fissi"],
        ["Esporta Excel", "Backup dati"],
        ["Reset mese"]
    ], resize_keyboard=True)

def menu_lavori():
    return ReplyKeyboardMarkup(
        [["Scrivi lavoro extra"], ["Indietro"]],
        resize_keyboard=True
    )

def menu_lavori_fissi():
    righe = [[l] for l in LAVORI_FISSI]
    righe.append(["Indietro"])
    return ReplyKeyboardMarkup(righe, resize_keyboard=True)

# --------------------------
# START
# --------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("Accesso non autorizzato.")
    await update.message.reply_text("Bot lavoro attivo.", reply_markup=menu_principale())

# --------------------------
# LINK AUTOMATICI
# --------------------------

async def entrata_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.text = "Entrata"
    return await handle_message(update, context)

async def uscita_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.text = "Uscita"
    return await handle_message(update, context)

# --------------------------
# HANDLER PRINCIPALE
# --------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    if user not in data:
        data[user] = {"records": [], "work_start": None}

    now = now_it()
    now_date = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    adding_extra = context.user_data.get("adding_extra_work", False)

    # --------------------------
    # COMANDI BASE
    # --------------------------

    if text == "Indietro":
        context.user_data["adding_extra_work"] = False
        return await update.message.reply_text("Menu principale", reply_markup=menu_principale())

    if text == "Entrata":
        data[user]["records"].append({
            "data": now_date,
            "azione": "Entrata",
            "inizio": now_time,
            "fine": "",
            "ore": "",
            "lavoro": ""
        })
        save_data(data)
        return await update.message.reply_text(f"Entrata registrata alle {now_time}")

    if text == "Uscita":
        data[user]["records"].append({
            "data": now_date,
            "azione": "Uscita",
            "inizio": "",
            "fine": now_time,
            "ore": "",
            "lavoro": ""
        })
        save_data(data)
        return await update.message.reply_text(f"Uscita registrata alle {now_time}")

    if text == "Inizio lavoro":
        data[user]["work_start"] = f"{now_date} {now_time}"
        save_data(data)
        return await update.message.reply_text(f"Inizio lavoro registrato alle {now_time}")

    if text == "Fine lavoro":
        start_str = data[user]["work_start"]
        if not start_str:
            return await update.message.reply_text("Prima premi 'Inizio lavoro'.")

        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
        diff = now - start_dt
        ore = round(diff.total_seconds() / 3600, 2)

        data[user]["records"].append({
            "data": now_date,
            "azione": "Sessione lavoro",
            "inizio": start_dt.strftime("%H:%M:%S"),
            "fine": now_time,
            "ore": ore,
            "lavoro": ""
        })
        data[user]["work_start"] = None
        save_data(data)
        return await update.message.reply_text(f"Fine lavoro.\nOre lavorate: {ore} h")

    # --------------------------
    # LAVORI DEL GIORNO
    # --------------------------

    if text == "Lavori del giorno":
        context.user_data["adding_extra_work"] = True
        return await update.message.reply_text("Scrivi il lavoro:", reply_markup=menu_lavori())

    if adding_extra:
        if text == "Scrivi lavoro extra":
            return await update.message.reply_text("Scrivi il testo del lavoro:", reply_markup=menu_lavori())

        data[user]["records"].append({
            "data": now_date,
            "azione": "Lavoro extra",
            "inizio": now_time,
            "fine": "",
            "ore": "",
            "lavoro": text
        })
        save_data(data)
        context.user_data["adding_extra_work"] = False
        return await update.message.reply_text("Lavoro registrato.", reply_markup=menu_principale())

    # --------------------------
    # LAVORI FISSI
    # --------------------------

    if text == "Lavori fissi":
        return await update.message.reply_text("Seleziona un lavoro:", reply_markup=menu_lavori_fissi())

    if text in LAVORI_FISSI:
        data[user]["records"].append({
            "data": now_date,
            "azione": "Lavoro fisso",
            "inizio": now_time,
            "fine": "",
            "ore": "",
            "lavoro": text
        })
        save_data(data)
        return await update.message.reply_text("Lavoro registrato.", reply_markup=menu_principale())

    # --------------------------
    # RESET MESE
    # --------------------------

    if text == "Reset mese":
        data[user]["records"] = []
        data[user]["work_start"] = None
        save_data(data)
        return await update.message.reply_text("Dati del mese resettati.")

    # --------------------------
    # ESPORTA EXCEL
    # --------------------------

    if text == "Esporta Excel":
        await genera_excel(update)
        return

    # BACKUP
    if text == "Backup dati":
        await update.message.reply_document(InputFile(DATA_FILE), caption="Backup completato")
        return

    await update.message.reply_text("Comando non valido.", reply_markup=menu_principale())

# --------------------------
# GENERAZIONE EXCEL ORDINATO
# --------------------------

async def genera_excel(update: Update):
    from openpyxl import Workbook

    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    if user not in data or not data[user]["records"]:
        return await update.message.reply_text("Nessun dato da esportare.")

    wb = Workbook()
    ws = wb.active
    ws.title = "Registro lavori"

    ws.append(["Data", "Azione", "Ora inizio", "Ora fine", "Ore lavorate", "Lavoro"])

    for r in data[user]["records"]:
        ws.append([
            r.get("data", ""),
            r.get("azione", ""),
            r.get("inizio", ""),
            r.get("fine", ""),
            r.get("ore", ""),
            r.get("lavoro", "")
        ])

    file_path = "/var/tmp/registro_lavoro.xlsx"
    wb.save(file_path)

    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=InputFile(f, filename="registro_lavoro.xlsx"),
            caption="Esportazione completata"
        )

# --------------------------
# MAIN
# --------------------------

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("entrata_auto", entrata_auto))
    app.add_handler(CommandHandler("uscita_auto", uscita_auto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
