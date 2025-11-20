import json
import os
from datetime import datetime, time as dtime
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

DATA_FILE = "dati.json"
AUTHORIZED_USER_ID = 361555418  # il tuo ID

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

# ----------------------------------------------------
# FUNZIONI UTILI
# ----------------------------------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ----------------------------------------------------
# TASTIERE
# ----------------------------------------------------

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

# ----------------------------------------------------
# START
# ----------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("❌ Bot privato.")
    await update.message.reply_text(
        "Ciao — bot lavoro attivo.",
        reply_markup=menu_principale()
    )

# ----------------------------------------------------
# HANDLER PRINCIPALE
# ----------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    data = load_data()
    user = str(AUTHORIZED_USER_ID)

    # Se non esiste, creo struttura base
    if user not in data:
        data[user] = {
            "records": [],
            "work_start": None
        }

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Flag per gestire lavori extra
    adding_extra = context.user_data.get("adding_extra_work", False)

    # -----------------------------------
    # GESTIONE "INDIETRO"
    # -----------------------------------
    if text == "Indietro":
        context.user_data["adding_extra_work"] = False
        await update.message.reply_text(
            "Torno al menu principale",
            reply_markup=menu_principale()
        )
        return

    # -----------------------------------
    # ENTRATA
    # -----------------------------------
    if text == "Entrata":
        data[user]["records"].append({"azione": "Entrata", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Entrata registrata 🟢\n{now_str}")
        return

    # -----------------------------------
    # USCITA
    # -----------------------------------
    if text == "Uscita":
        data[user]["records"].append({"azione": "Uscita", "orario": now_str})
        save_data(data)
        await update.message.reply_text(f"Uscita registrata 🔴\n{now_str}")
        return

    # -----------------------------------
    # INIZIO LAVORO
    # -----------------------------------
    if text == "Inizio lavoro":
        data[user]["work_start"] = now_str
        save_data(data)
        await update.message.reply_text(f"Inizio lavoro registrato 🟦\n{now_str}")
        return

    # -----------------------------------
    # FINE LAVORO + CALCOLO ORE
    # -----------------------------------
    if text == "Fine lavoro":
        start_time_str = data[user]["work_start"]

        if not start_time_str:
            await update.message.reply_text("⚠️ Non hai premuto 'Inizio lavoro'.")
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

        await update.message.reply_text(f"Fine lavoro 🟪\nOre lavorate: {ore} h")
        return

    # -----------------------------------
    # LAVORI DEL GIORNO
    # -----------------------------------
    if text == "Lavori del giorno":
        context.user_data["adding_extra_work"] = True
        await update.message.reply_text(
            "Scrivi il lavoro che hai fatto (oppure premi 'Indietro'):",
            reply_markup=menu_lavori()
        )
        return

    # -----------------------------------
    # SALVATAGGIO LAVORO EXTRA
    # -----------------------------------
    if adding_extra:
        if text == "Scrivi lavoro extra":
            await update.message.reply_text(
                "Scrivi il testo del lavoro da registrare:",
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
            "✔ Lavoro extra registrato.",
            reply_markup=menu_principale()
        )
        return

    # -----------------------------------
    # LAVORI FISSI
    # -----------------------------------
    if text == "Lavori fissi":
        await update.message.reply_text(
            "Seleziona un lavoro fisso:",
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
            "✔ Lavoro fisso registrato.",
            reply_markup=menu_principale()
        )
        return

    # -----------------------------------
    # RESET MESE
    # -----------------------------------
    if text == "Reset mese":
        data[user]["records"] = []
        data[user]["work_start"] = None
        save_data(data)
        await update.message.reply_text("🔄 Tutti i dati del mese sono stati resettati.")
        return

    # -----------------------------------
    # ESPORTA EXCEL (manuale)
    # -----------------------------------
    if text == "Esporta Excel":
        await genera_e_invia_excel(update, data, user)
        return

    # -----------------------------------
    # BACKUP DATI
    # -----------------------------------
    if text == "Backup dati":
        if not os.path.exists(DATA_FILE):
            await update.message.reply_text("Nessun dato da salvare 😅")
            return

        await update.message.reply_document(
            InputFile(DATA_FILE),
            caption="📦 Backup completo dei dati (dati.json)"
        )
        return

    # Fallback
    await update.message.reply_text(
        "Comando non riconosciuto. Usa i pulsanti 😊",
        reply_markup=menu_principale()
    )

# ----------------------------------------------------
# FUNZIONE RIUTILIZZABILE: GENERA & INVIA EXCEL
# ----------------------------------------------------

async def genera_e_invia_excel(update_or_context, data=None, user_id_str=None, auto=False):
    """
    Se auto=False -> chiamata dal comando 'Esporta Excel' (via update).
    Se auto=True  -> chiamata dal job giornaliero (via context).
    """
    try:
        from openpyxl import Workbook
    except ImportError:
        # se manca openpyxl
        if not auto:
            # solo se chiamata manuale ha senso rispondere
            await update_or_context.message.reply_text("Errore: openpyxl non è installato.")
        return

    if data is None or user_id_str is None:
        data = load_data()
        user_id_str = str(AUTHORIZED_USER_ID)

    if user_id_str not in data:
        # nessun dato
        if not auto:
            await update_or_context.message.reply_text("Nessun dato da esportare.")
        return

    records = data[user_id_str].get("records", [])

    from openpyxl import Workbook
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

    filename = "registro_lavoro.xlsx"
    wb.save(filename)

    # invio in base a chi chiama
    if auto:
        # chiamata da job giornaliero
        bot = update_or_context.bot
        await bot.send_document(
            chat_id=AUTHORIZED_USER_ID,
            document=InputFile(filename),
            caption="📄 Esportazione automatica di fine giornata"
        )
    else:
        # chiamata manuale da comando
        await update_or_context.message.reply_document(
            InputFile(filename),
            caption="📄 Ecco il registro in Excel"
        )

# ----------------------------------------------------
# JOB GIORNALIERO: ESPORTAZIONE AUTOMATICA
# ----------------------------------------------------

async def export_excel_fine_giornata(context: ContextTypes.DEFAULT_TYPE):
    # genera Excel dai dati correnti e lo invia
    await genera_e_invia_excel(context, auto=True)

# ----------------------------------------------------
# MAIN
# ----------------------------------------------------

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Job giornaliero: esportazione automatica a fine giornata
    jq = app.job_queue
    # 22:00 UTC ≈ 23:00 italiane (Railway usa UTC)
    jq.run_daily(export_excel_fine_giornata, time=dtime(22, 0))

    app.run_polling()

if __name__ == "__main__":
    main()
