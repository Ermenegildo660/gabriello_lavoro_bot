import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ------------------------
# CONFIGURAZIONE
# ------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
OWNER_ID = 361555418   # tuo chat_id

DATA_FILE = "storico.json"


# ------------------------
# GESTIONE DATI
# ------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def nowtime():
    return datetime.now().strftime("%H:%M:%S")

def find_today(data):
    for d in data:
        if d["data"] == today():
            return d
    return None


# ------------------------
# START
# ------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Bot privato.")
        return

    keyboard = [
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Mostra entrata", "Mostra uscita"],
        ["Esporta dati"]
    ]

    await update.message.reply_text(
        "Bot attivo.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ------------------------
# FUNZIONI BOT
# ------------------------

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("Bot privato.")
        return

    data = load_data()
    rec = find_today(data)

    # Entrata
    if text == "Entrata":
        if not rec:
            rec = {
                "data": today(),
                "entrata": nowtime(),
                "uscita": None,
                "inizio": None,
                "fine": None
            }
            data.append(rec)
        else:
            rec["entrata"] = nowtime()

        save_data(data)
        await update.message.reply_text(f"Entrata registrata: {rec['entrata']}")

    # Uscita
    elif text == "Uscita":
        if not rec:
            await update.message.reply_text("Prima registra l'entrata.")
            return

        rec["uscita"] = nowtime()
        save_data(data)
        await update.message.reply_text(f"Uscita registrata: {rec['uscita']}")

    # Inizio lavoro
    elif text == "Inizio lavoro":
        if not rec:
            rec = {
                "data": today(),
                "entrata": None,
                "uscita": None,
                "inizio": nowtime(),
                "fine": None
            }
            data.append(rec)
        else:
            rec["inizio"] = nowtime()

        save_data(data)
        await update.message.reply_text(f"Inizio lavoro: {rec['inizio']}")

    # Fine lavoro
    elif text == "Fine lavoro":
        if not rec:
            await update.message.reply_text("Devi registrare l'inizio lavoro.")
            return

        rec["fine"] = nowtime()
        save_data(data)
        await update.message.reply_text(f"Fine lavoro: {rec['fine']}")

    # Mostra entrata
    elif text == "Mostra entrata":
        msg = rec["entrata"] if rec and rec["entrata"] else "Nessuna entrata registrata."
        await update.message.reply_text(f"Entrata: {msg}")

    # Mostra uscita
    elif text == "Mostra uscita":
        msg = rec["uscita"] if rec and rec["uscita"] else "Nessuna uscita registrata."
        await update.message.reply_text(f"Uscita: {msg}")

    # Esporta dati
    elif text == "Esporta dati":
        filename = "storico.txt"
        with open(filename, "w") as f:
            for r in data:
                f.write(json.dumps(r, indent=4))
                f.write("\n\n")

        await update.message.reply_document(InputFile(filename))
        await update.message.reply_text("Dati esportati.")


# ------------------------
# WEBHOOK
# ------------------------

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_buttons))

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{BOT_TOKEN}"
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
