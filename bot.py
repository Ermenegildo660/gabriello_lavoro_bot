import json
import os
import math
from datetime import datetime, time as dtime
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # il tuo ID

# --------------------------
# COORDINATE DEL LAVORO
# --------------------------

# Coordinate fornite (Cassano Magnago)
WORK_LAT = 45.6595
WORK_LON = 8.8290
WORK_RADIUS = 120   # metri di tolleranza

# Calcolo distanza (formula Haversine)
def distanza(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# --------------------------
# LETTURA / SCRITTURA DATI
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
# INIZIO LAVORO AUTOMATICO
# --------------------------

async def auto_inizio_lavoro(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = str(AUTHORIZED_USER_ID)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data[user]["work_start"] = now
    save_data(data)

    await context.bot.send_message(
        chat_id=AUTHORIZED_USER_ID,
        text=f"⏱ Inizio lavoro automatico registrato.\n{now}"
    )


# --------------------------
# HANDLER PRINCIPALE
# --------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    if user not in data:
        data[user] = {"records": [], "work_start": None}

    # Leggo ultima posizione ricevuta
    last_pos = context.user_data.get("last_position")

    # Entrata con controllo posizione
    if text == "Entrata":
        if not last_pos:
            return await update.message.reply_text("⚠️ Nessuna posizione ricevuta. Invia la posizione in tempo reale.")

        dist = distanza(last_pos["lat"], last_pos["lon"], WORK_LAT, WORK_LON)

        if dist > WORK_RADIUS:
            return await update.message.reply_text(f"❌ Sei fuori zona ({int(dist)} m). Entrata non registrata.")

        # Registrazione entrata
        data[user]["records"].append({"azione": "Entrata", "orario": now_str})
        save_data(data)

        # Avvio automatico inizio lavoro
        context.job_queue.run_once(auto_inizio_lavoro, when=600)

        return await update.message.reply_text(
            f"Entrata registrata ✔️\n{now_str}\n\n"
            f"📍 Sei entro {int(dist)} metri dal posto.\n"
            "⏱ Inizio lavoro partirà automaticamente tra 10 minuti."
        )

    # Uscita con controllo posizione
    if text == "Uscita":
        if not last_pos:
            return await update.message.reply_text("⚠️ Nessuna posizione ricevuta. Invia la posizione in tempo reale.")

        dist = distanza(last_pos["lat"], last_pos["lon"], WORK_LAT, WORK_LON)

        if dist > WORK_RADIUS:
            return await update.message.reply_text(f"❌ Sei fuori zona ({int(dist)} m). Uscita non registrata.")

        data[user]["records"].append({"azione": "Uscita", "orario": now_str})
        save_data(data)

        return await update.message.reply_text(
            f"Uscita registrata ✔️\n{now_str}\n📍 Sei entro {int(dist)} metri dal posto."
        )

    # Inizio lavoro manuale
    if text == "Inizio lavoro":
        data[user]["work_start"] = now_str
        save_data(data)
        return await update.message.reply_text(f"Inizio lavoro registrato\n{now_str}")

    # Fine lavoro
    if text == "Fine lavoro":
        start = data[user]["work_start"]
        if not start:
            return await update.message.reply_text("Prima premi 'Inizio lavoro'.")

        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        ore = round((now - start_dt).total_seconds() / 3600, 2)

        data[user]["records"].append({
            "azione": "Sessione lavoro",
            "inizio": start,
            "fine": now_str,
            "ore": ore
        })

        data[user]["work_start"] = None
        save_data(data)

        return await update.message.reply_text(f"Fine lavoro\nOre lavorate: {ore}")

    # Lavori del giorno
    if text == "Lavori del giorno":
        context.user_data["adding_extra_work"] = True
        return await update.message.reply_text("Scrivi il lavoro:", reply_markup=menu_lavori())

    # Lavoro extra
    if context.user_data.get("adding_extra_work", False):
        data[user]["records"].append({
            "azione": "Lavoro extra",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)
        context.user_data["adding_extra_work"] = False
        return await update.message.reply_text("Lavoro registrato.", reply_markup=menu_principale())

    # Lavori fissi
    if text == "Lavori fissi":
        return await update.message.reply_text("Seleziona un lavoro:", reply_markup=menu_lavori_fissi())

    if text in LAVORI_FISSI:
        data[user]["records"].append({
            "azione": "Lavoro fisso",
            "lavoro": text,
            "orario": now_str
        })
        save_data(data)
        return await update.message.reply_text("Lavoro registrato.", reply_markup=menu_principale())

    # Reset mese
    if text == "Reset mese":
        data[user] = {"records": [], "work_start": None}
        save_data(data)
        return await update.message.reply_text("Dati del mese resettati.")

    # Esporta excel
    if text == "Esporta Excel":
        await genera_excel(update)
        return

    # Backup
    if text == "Backup dati":
        return await update.message.reply_document(InputFile(DATA_FILE), caption="Backup")

    await update.message.reply_text("Comando non riconosciuto.", reply_markup=menu_principale())


# --------------------------
# POSIZIONE IN TEMPO REALE
# --------------------------

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    context.user_data["last_position"] = {"lat": lat, "lon": lon}
    print(f"Posizione aggiornata: {lat}, {lon}")


# --------------------------
# GENERA EXCEL
# --------------------------

async def genera_excel(update: Update):
    from openpyxl import Workbook
    from telegram import InputFile

    data = load_data()
    user = str(AUTHORIZED_USER_ID)
    records = data.get(user, {}).get("records", [])

    if not records:
        return await update.message.reply_text("Nessun dato da esportare.")

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

    file_path = "/var/tmp/registro_lavoro.xlsx"
    wb.save(file_path)

    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=InputFile(f, filename="registro_lavoro.xlsx"),
            caption="Esportazione completata"
        )


# --------------------------
# PROMEMORIA
# --------------------------

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=AUTHORIZED_USER_ID,
        text="Promemoria: ricordati di esportare l'Excel oggi 📝"
    )


# --------------------------
# MAIN
# --------------------------

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    jq = app.job_queue
    jq.run_daily(reminder, time=dtime(21, 0))

    app.run_polling()


if __name__ == "__main__":
    main()
