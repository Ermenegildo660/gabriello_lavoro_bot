import json
import os
from datetime import datetime, time as dtime
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # tuo ID Telegram

# --------------------------
# LETTURA / SALVATAGGIO DATI
# --------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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

# --------------------------
# LAVORI FISSI (TUTTI, UNO PER RIGA)
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
    "Pulizia mensile pesa linea ingredienti",
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

def menu_lavori_fissi():
    righe = []
    for lavoro in LAVORI_FISSI:
        righe.append([lavoro])  # uno per riga
    righe.append(["Indietro"])
    return ReplyKeyboardMarkup(righe, resize_keyboard=True)

# --------------------------
# START
# --------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("Accesso non autorizzato.")
    await update.message.reply_text(
        "Bot lavoro attivo.",
        reply_markup=menu_principale()
    )

# --------------------------
# HANDLER PRINCIPALE
# --------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    if not update.message or not update.message.text:
        return

    text = update.message.text
    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    if user not in data:
        data[user] = {
            "records": [],
            "work_start": None
        }

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    adding_extra = context.user_data.get("adding_extra_work", False)

    # INDIETRO
    if text == "Indietro":
        context.user_data["adding_extra_work"] = False
        await update.message.reply_text(
            "Menu principale",
            reply_markup=menu_principale()
        )
        return

    # ENTRATA
    if text == "Entrata":
        data[user]["records"].append({"azione": "Entrata", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Entrata registrata\n{now_str}")
        return

    # USCITA
    if text == "Uscita":
        data[user]["records"].append({"azione": "Uscita", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Uscita registrata\n{now_str}")
        return

    # INIZIO LAVORO
    if text == "Inizio lavoro":
        data[user]["work_start"] = now_str
        save_data(data)
        await update.message.reply_text(f"Inizio lavoro registrato\n{now_str}")
        return

    # FINE LAVORO
    if text == "Fine lavoro":
        start_time_str = data[user]["work_start"]
        if not start_time_str:
            await update.message.reply_text("Prima premi 'Inizio lavoro'.")
            return
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        diff = now - start_dt
        ore = round(diff.total_seconds() / 3600, 2)
        data[user]["records"].append({
            "azione": "Sessione lavoro",
            "inizio": start_time_str,
            "fine": now_str,
            "ore": ore
        })
        data[user]["work_start"] = None
        save_data(data)
        await update.message.reply_text(f"Fine lavoro\nOre lavorate: {ore} h")
        return

    # LAVORI DEL GIORNO
    if text == "Lavori del giorno":
        context.user_data["adding_extra_work"] = True
        await update.message.reply_text(
            "Scrivi il lavoro (o premi Indietro):",
            reply_markup=menu_lavori()
        )
        return

    # SALVATAGGIO LAVORO EXTRA
    if adding_extra:
        if text == "Scrivi lavoro extra":
            await update.message.reply_text(
                "Scrivi il testo del lavoro:",
                reply_markup=menu_lavori()
            )
            return
        data[user]["records"].append({
            "azione": "Lavoro extra",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)
        context.user_data["adding_extra_work"] = False
        await update.message.reply_text(
            "Lavoro registrato.",
            reply_markup=menu_principale()
        )
        return

    # LAVORI FISSI
    if text == "Lavori fissi":
        await update.message.reply_text(
            "Seleziona un lavoro:",
            reply_markup=menu_lavori_fissi()
        )
        return

    if text in LAVORI_FISSI:
        data[user]["records"].append({
            "azione": "Lavoro fisso",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)
        await update.message.reply_text(
            "Lavoro registrato.",
            reply_markup=menu_principale()
        )
        return

    # RESET MESE
    if text == "Reset mese":
        data[user]["records"] = []
        data[user]["work_start"] = None
        save_data(data)
        await update.message.reply_text("Dati del mese resettati.")
        return

    # ESPORTA EXCEL
    if text == "Esporta Excel":
        await genera_e_invia_excel(update)
        return

    # BACKUP DATI
    if text == "Backup dati":
        if not os.path.exists(DATA_FILE):
            await update.message.reply_text("Nessun dato da salvare.")
            return
        await update.message.reply_document(
            InputFile(DATA_FILE),
            caption="Backup dei dati"
        )
        return

    # FALLBACK
    await update.message.reply_text(
        "Comando non riconosciuto.",
        reply_markup=menu_principale()
    )

# --------------------------
# GENERA EXCEL + INVIO
# --------------------------

async def genera_e_invia_excel(update: Update):
    from openpyxl import Workbook

    data = load_data()
    user_id_str = str(AUTHORIZED_USER_ID)

    if user_id_str not in data or not data[user_id_str].get("records"):
        await update.message.reply_text("Nessun dato da esportare.")
        return

    records = data[user_id_str].get("records", [])

    wb = Workbook()
    ws = wb.active
    ws.title = "Registro lavori"

    ws.append(["Azione", "Inizio", "Fine", "Orario", "Ore", "Lavoro"])

    for r in records:
        ws.append([
            r.get("azione", ""),
            r.get("inizio", ""),
            r.get("fine", ""),
            r.get("orario", ""),
            r.get("ore", ""),
            r.get("lavoro", "")
        ])

    # Usa /tmp su Railway
    os.makedirs("/tmp", exist_ok=True)
    filename = "/tmp/registro_lavoro.xlsx"
    wb.save(filename)

    await update.message.reply_document(
        InputFile(filename),
        caption="Esportazione completata"
    )

# --------------------------
# PROMEMORIA GIORNALIERO
# --------------------------

async def reminder_salvataggio_excel(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=AUTHORIZED_USER_ID,
        text="Promemoria: ricordati di premere 'Esporta Excel' per salvare il registro di oggi."
    )

# --------------------------
# MAIN
# --------------------------

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN non impostato nelle variabili d'ambiente.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Solo promemoria, niente salvataggio automatico
    jq = app.job_queue
    jq.run_daily(reminder_salvataggio_excel, time=dtime(21, 0))  # ~22:00 italiane

    app.run_polling()

if __name__ == "__main__":
    main()
