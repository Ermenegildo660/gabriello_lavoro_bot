import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # tuo ID

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

# --------------------------
# FUNZIONI UTILI
# --------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --------------------------
# TASTIERE
# --------------------------

def menu_principale():
    return ReplyKeyboardMarkup([
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Lavori del giorno", "Lavori fissi"],
        ["Esporta Excel", "Reset mese"]
    ], resize_keyboard=True)

def menu_lavori():
    return ReplyKeyboardMarkup(
        [["Scrivi lavoro extra"], ["Indietro"]],
        resize_keyboard=True
    )

def menu_lavori_fissi():
    righe = []
    riga = []
    for i, lavoro in enumerate(LAVORI_FISSI, 1):
        riga.append(lavoro)
        if len(riga) == 2:
            righe.append(riga)
            riga = []
    if riga:
        righe.append(riga)

    righe.append(["Indietro"])
    return ReplyKeyboardMarkup(righe, resize_keyboard=True)

# --------------------------
# START
# --------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("❌ Bot privato.")
    return await update.message.reply_text("Ciao — bot lavoro attivo.", reply_markup=menu_principale())

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

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # --------------------------
    # ENTRATA
    # --------------------------
    if text == "Entrata":
        data[user]["records"].append({"azione": "Entrata", "orario": now_str})
        save_data(data)
        return await update.message.reply_text(f"Entrata registrata 🟢\n{now_str}")

    # --------------------------
    # USCITA
    # --------------------------
    if text == "Uscita":
        data[user]["records"].append({"azione": "Uscita", "orario": now_str})
        save_data(data)
        return await update.message.reply_text(f"Uscita registrata 🔴\n{now_str}")

    # --------------------------
    # INIZIO LAVORO
    # --------------------------
    if text == "Inizio lavoro":
        data[user]["work_start"] = now_str
        save_data(data)
        return await update.message.reply_text(f"Inizio lavoro registrato 🟦\n{now_str}")

    # --------------------------
    # FINE LAVORO
    # --------------------------
    if text == "Fine lavoro":
        start_time = data[user]["work_start"]
        if not start_time:
            return await update.message.reply_text("⚠️ Non hai premuto 'Inizio lavoro'.")

        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        diff = now - start_dt
        ore = round(diff.total_seconds() / 3600, 2)

        data[user]["records"].append({
            "azione": "Sessione lavoro",
            "inizio": start_time,
            "fine": now_str,
            "ore": ore
        })
        data[user]["work_start"] = None
        save_data(data)

        return await update.message.reply_text(f"Fine lavoro 🟪\nOre lavorate: **{ore}h**")

    # --------------------------
    # LAVORI DEL GIORNO
    # --------------------------
    if text == "Lavori del giorno":
        context.user_data["adding_work"] = True
        return await update.message.reply_text("Scrivi il lavoro che hai fatto:", reply_markup=menu_lavori())

    if context.user_data.get("adding_work"):
        if text == "Indietro":
            context.user_data["adding_work"] = False
            return await update.message.reply_text("Okay", reply_markup=menu_principale())

        if text == "Scrivi lavoro extra":
            return await update.message.reply_text("Scrivi il lavoro:")

        data[user]["records"].append({
            "azione": "Lavoro extra",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)

        context.user_data["adding_work"] = False
        return await update.message.reply_text("✔ Lavoro registrato.", reply_markup=menu_principale())

    # --------------------------
    # LAVORI FISSI
    # --------------------------
    if text == "Lavori fissi":
        return await update.message.reply_text("Seleziona un lavoro:", reply_markup=menu_lavori_fissi())

    if text in LAVORI_FISSI:
        data[user]["records"].append({
            "azione": "Lavoro fisso",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)
        return await update.message.reply_text("✔ Lavoro fisso registrato.", reply_markup=menu_principale())

    # INDietro SOLO DA LAVORI FISSI
    if text == "Indietro":
        return await update.message.reply_text("Ok Baby 💚", reply_markup=menu_principale())

    # --------------------------
    # RESET
    # --------------------------
    if text == "Reset mese":
        data[user]["records"] = []
        data[user]["work_start"] = None
        save_data(data)
        return await update.message.reply_text("🔄 Dati del mese resettati.")

    # --------------------------
    # EXPORT EXCEL
    # --------------------------
    if text == "Esporta Excel":
        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "Registro"

            ws.append(["Azione", "Inizio", "Fine", "Orario", "Ore", "Lavoro"])

            for r in data[user]["records"]:
                ws.append([
                    r.get("azione", ""),
                    r.get("inizio", ""),
                    r.get("fine", ""),
                    r.get("orario", ""),
                    r.get("ore", ""),
                    r.get("lavoro", "")
                ])

            filename = "registro_lavoro.xlsx"
            wb.save(filename)

            await update.message.reply_document(
                open(filename, "rb"),
                caption="📄 Esportazione completata"
            )

        except Exception as e:
            return await update.message.reply_text(f"Errore: {e}")

        return

# --------------------------
# MAIN
# --------------------------

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
