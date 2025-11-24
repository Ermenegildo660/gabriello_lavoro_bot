import json
import os
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # il tuo ID TELEGRAM

# Coordinate della tua posizione di lavoro
LAVORO_LAT = 45.663178
LAVORO_LON = 8.783582
MAX_DISTANZA_METRI = 150  # distanza tollerata

# -------------------------------
# UTILITÀ
# -------------------------------

def distanza_da_lavoro(lat, lon):
    R = 6371000
    dlat = radians(lat - LAVORO_LAT)
    dlon = radians(lon - LAVORO_LON)
    a = (sin(dlat / 2) ** 2 +
         cos(radians(LAVORO_LAT)) * cos(radians(lat)) *
         sin(dlon / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def carica_dati():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def salva_dati(dati):
    with open(DATA_FILE, "w") as f:
        json.dump(dati, f, indent=4)

# -------------------------------
# START
# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("Accesso negato.")

    keyboard = [
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Lavori fissi", "Lavori del giorno"],
        ["Esporta Excel", "Backup dati"],
        ["Reset mese"]
    ]

    await update.message.reply_text(
        "Bot lavoro attivo.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# -------------------------------
# POSIZIONE
# -------------------------------

async def salva_posizione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posizione = update.message.location
    context.user_data["posizione"] = posizione
    await update.message.reply_text("📍 Posizione aggiornata!")

# -------------------------------
# ENTRATA CON POSIZIONE OPZIONALE
# -------------------------------

async def handle_entrata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posizione = context.user_data.get("posizione")

    if posizione is None:
        await update.message.reply_text("⚠️ Nessuna posizione ricevuta. Entrata registrata comunque.")
    else:
        distanza = distanza_da_lavoro(posizione.latitude, posizione.longitude)
        if distanza > MAX_DISTANZA_METRI:
            await update.message.reply_text(
                f"⚠️ Sei fuori dalla zona lavoro ({int(distanza)} m). Entrata registrata comunque."
            )
        else:
            await update.message.reply_text("📍 Posizione valida. Entrata registrata.")

    entrata = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data["entrata"] = entrata

    await update.message.reply_text(f"Entrata registrata: {entrata}")

    # INIZIO LAVORO AUTOMATICO DOPO 10 MINUTI
    context.job_queue.run_once(inizio_lavoro_automatico, 600, chat_id=update.effective_chat.id)

async def inizio_lavoro_automatico(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="⏱️ Sono passati 10 minuti. Inizio lavoro registrato automaticamente."
    )
    context.user_data["inizio"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------
# USCITA CON POSIZIONE OPZIONALE
# -------------------------------

async def handle_uscita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posizione = context.user_data.get("posizione")

    if posizione is None:
        await update.message.reply_text("⚠️ Nessuna posizione ricevuta. Uscita registrata comunque.")
    else:
        distanza = distanza_da_lavoro(posizione.latitude, posizione.longitude)
        if distanza > MAX_DISTANZA_METRI:
            await update.message.reply_text(
                f"⚠️ Sei fuori dalla zona lavoro ({int(distanza)} m). Uscita registrata comunque."
            )
        else:
            await update.message.reply_text("📍 Posizione valida. Uscita registrata.")

    uscita = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data["uscita"] = uscita

    await update.message.reply_text(f"Uscita registrata: {uscita}")

# -------------------------------
# INIZIO / FINE LAVORO
# -------------------------------

async def handle_inizio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data["inizio"] = ora
    await update.message.reply_text(f"Inizio lavoro registrato: {ora}")

async def handle_fine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "inizio" not in context.user_data:
        return await update.message.reply_text("Prima premi 'Inizio lavoro'.")

    inizio = datetime.strptime(context.user_data["inizio"], "%Y-%m-%d %H:%M:%S")
    fine = datetime.now()
    ore = round((fine - inizio).total_seconds() / 3600, 2)

    context.user_data["fine"] = fine.strftime("%Y-%m-%d %H:%M:%S")

    await update.message.reply_text(f"Fine lavoro. Ore lavorate: {ore}")

    dati = carica_dati()
    dati.append({
        "data": inizio.date().isoformat(),
        "inizio": context.user_data["inizio"],
        "fine": context.user_data["fine"],
        "ore": ore
    })
    salva_dati(dati)

# -------------------------------
# LAVORI FISSI
# -------------------------------

LAVORI_FISSI = [
    "Lavaggio settimanale scalette pasticceria",
    "Lavaggio settimanale rampa panificio",
    "Pulizia settimanale forni rotor Polin/Bongard",
    "Soffiatura bruciatori platea",
    "Pulizia tappeto semi automatico",
    "Pulizia linee taglio e imbustaggio",
    "Pulizia linea tappeti panetteria",
    "Pulizia filtri sala farina silos",
]

async def handle_lavori_fissi(update: Update, context):
    keyboard = [[lavoro] for lavoro in LAVORI_FISSI]
    await update.message.reply_text(
        "Seleziona un lavoro:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def registra_lavoro(update: Update, context):
    lavoro = update.message.text
    ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dati = carica_dati()
    dati.append({
        "data": datetime.now().date().isoformat(),
        "lavoro": lavoro,
        "orario": ora
    })
    salva_dati(dati)

    await update.message.reply_text("Lavoro registrato.")

# -------------------------------
# ESPORTA EXCEL
# -------------------------------

from openpyxl import Workbook

async def esporta_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dati = carica_dati()

    wb = Workbook()
    sh = wb.active
    sh.append(["Data", "Inizio", "Fine", "Ore", "Lavoro", "Orario"])

    for r in dati:
        sh.append([
            r.get("data", ""),
            r.get("inizio", ""),
            r.get("fine", ""),
            r.get("ore", ""),
            r.get("lavoro", ""),
            r.get("orario", "")
        ])

    file_path = "/tmp/registro_lavoro.xlsx"
    wb.save(file_path)

    await update.message.reply_document(InputFile(file_path))

# -------------------------------
# RESET MESE
# -------------------------------

async def reset_mese(update: Update, context):
    salva_dati([])
    await update.message.reply_text("Registro del mese azzerato.")

# -------------------------------
# MAIN
# -------------------------------

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, salva_posizione))

    app.add_handler(MessageHandler(filters.Regex("^Entrata$"), handle_entrata))
    app.add_handler(MessageHandler(filters.Regex("^Uscita$"), handle_uscita))

    app.add_handler(MessageHandler(filters.Regex("^Inizio lavoro$"), handle_inizio))
    app.add_handler(MessageHandler(filters.Regex("^Fine lavoro$"), handle_fine))

    app.add_handler(MessageHandler(filters.Regex("^Lavori fissi$"), handle_lavori_fissi))
    app.add_handler(MessageHandler(filters.Regex(".*"), registra_lavoro))

    app.add_handler(MessageHandler(filters.Regex("^Esporta Excel$"), esporta_excel))
    app.add_handler(MessageHandler(filters.Regex("^Reset mese$"), reset_mese))

    app.run_polling()

if __name__ == "__main__":
    main()
