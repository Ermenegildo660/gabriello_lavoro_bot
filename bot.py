import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # <-- QUI METTI IL TUO ID !!!

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_keyboard():
    return ReplyKeyboardMarkup([
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Esporta Excel", "Reset mese"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("❌ Non sei autorizzato ad usare questo bot.")
        return

    await update.message.reply_text("Ciao! Il bot è attivo 😊", reply_markup=get_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    if user not in data:
        data[user] = {"records": [], "work_start": None}

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # --- ENTRATA ---
    if text == "Entrata":
        data[user]["records"].append({"azione": "Entrata", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Entrata registrata 🟢\n{now_str}")
        return

    # --- USCITA ---
    if text == "Uscita":
        data[user]["records"].append({"azione": "Uscita", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Uscita registrata 🔴\n{now_str}")
        return

    # --- INIZIO LAVORO ---
    if text == "Inizio lavoro":
        data[user]["work_start"] = now_str
        save_data(data)
        await update.message.reply_text(f"Inizio lavoro registrato 🟦\n{now_str}")
        return

    # --- FINE LAVORO + CALCOLO ORE ---
    if text == "Fine lavoro":
        start_time_str = data[user]["work_start"]

        if not start_time_str:
            await update.message.reply_text("⚠️ Non hai premuto 'Inizio lavoro'.")
            return

        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        diff = now - start_time
        ore = round(diff.total_seconds() / 3600, 2)

        # Salvo il record
        data[user]["records"].append({
            "azione": "Sessione lavoro",
            "inizio": start_time_str,
            "fine": now_str,
            "ore": ore
        })

        data[user]["work_start"] = None
        save_data(data)

        await update.message.reply_text(f"Fine lavoro 🟪\nOre lavorate: **{ore}h**")
        return

    # --- RESET MESE ---
    if text == "Reset mese":
        data[user]["records"] = []
        data[user]["work_start"] = None
        save_data(data)
        await update.message.reply_text("🔄 Tutti i dati del mese sono stati resettati!")
        return

    # --- ESPORTAZIONE EXCEL ---
    if text == "Esporta Excel":
        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "Registro lavori"

            ws.append(["Azione", "Inizio", "Fine", "Orario", "Ore"])

            for r in data[user]["records"]:
                ws.append([
                    r.get("azione", ""),
                    r.get("inizio", ""),
                    r.get("fine", ""),
                    r.get("orario", ""),
                    r.get("ore", "")
                ])

            filename = "registro_lavoro.xlsx"
            wb.save(filename)

            await update.message.reply_document(open(filename, "rb"))

        except Exception as e:
            await update.message.reply_text(f"Errore durante esportazione: {str(e)}")

        return

async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
