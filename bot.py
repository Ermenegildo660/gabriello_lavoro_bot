from datetime import datetime, time as dtime

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

from database import (
    AUTHORIZED_USER_ID, TZ, now_it,
    get_user_data, add_record, set_work_start,
    get_work_start, reset_month
)
from excel import invia_excel_message, invia_excel_bot


# --------------------------------------
# CONFIGURAZIONE MINI APP
# --------------------------------------

import os

MINI_APP_URL = os.getenv("MINI_APP_URL")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")


def get_base_url():
    if MINI_APP_URL:
        return MINI_APP_URL.rstrip("/")
    if RAILWAY_PUBLIC_DOMAIN:
        return f"https://{RAILWAY_PUBLIC_DOMAIN}".rstrip("/")
    return ""


# --------------------------------------
# TASTIERE
# --------------------------------------

def menu_principale():
    return ReplyKeyboardMarkup([
        ["Entrata", "Uscita"],
        ["Inizio lavoro", "Fine lavoro"],
        ["Lavori del giorno", "Ore Live"],
        ["Esporta Excel", "Reset mese"]
    ], resize_keyboard=True)


def menu_lavori():
    return ReplyKeyboardMarkup(
        [["Scrivi lavoro extra"], ["Indietro"]],
        resize_keyboard=True
    )


# --------------------------------------
# START
# --------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("Accesso non autorizzato.")

    await update.message.reply_text("Bot attivo 💼", reply_markup=menu_principale())


# --------------------------------------
# INIZIO LAVORO AUTOMATICO
# --------------------------------------

async def auto_inizio_lavoro(context: ContextTypes.DEFAULT_TYPE):
    now = now_it()
    now_date = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    # Se nel frattempo hai già premuto Inizio lavoro manualmente, non sovrascrive
    if get_work_start():
        return

    set_work_start(f"{now_date} {now_time}")

    await context.bot.send_message(
        chat_id=AUTHORIZED_USER_ID,
        text=f"Inizio lavoro automatico registrato alle {now_time} ⏱"
    )


# --------------------------------------
# COMANDI RAPIDI /entrata_auto e /uscita_auto
# --------------------------------------

async def entrata_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    now = now_it()
    now_date = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    add_record({
        "data": now_date,
        "azione": "Entrata",
        "inizio": now_time,
        "fine": "",
        "ore": "",
        "lavoro": ""
    })

    context.job_queue.run_once(auto_inizio_lavoro, when=600)

    return await update.message.reply_text(f"Entrata registrata alle {now_time}")


async def uscita_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    now = now_it()
    now_date = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    add_record({
        "data": now_date,
        "azione": "Uscita",
        "inizio": "",
        "fine": now_time,
        "ore": "",
        "lavoro": ""
    })

    return await update.message.reply_text(f"Uscita registrata alle {now_time}")


# --------------------------------------
# HANDLER PRINCIPALE
# --------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    data, user = get_user_data()

    now = now_it()
    now_date = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M:%S")

    adding_extra = context.user_data.get("adding_extra_work", False)

    # --------------------------
    # INDIETRO
    # --------------------------
    if text == "Indietro":
        context.user_data["adding_extra_work"] = False
        return await update.message.reply_text("Menu principale", reply_markup=menu_principale())

    # Se sei in modalità lavoro extra e premi un tasto del menu,
    # esce dalla modalità e fa il comando richiesto.
    menu_buttons = {
        "Entrata", "Uscita", "Inizio lavoro", "Fine lavoro",
        "Lavori del giorno", "Ore Live", "Esporta Excel", "Reset mese"
    }

    if adding_extra and text in menu_buttons:
        context.user_data["adding_extra_work"] = False
        adding_extra = False

    # --------------------------
    # ENTRATA
    # --------------------------
    if text == "Entrata":
        add_record({
            "data": now_date,
            "azione": "Entrata",
            "inizio": now_time,
            "fine": "",
            "ore": "",
            "lavoro": ""
        })

        context.job_queue.run_once(auto_inizio_lavoro, when=600)

        return await update.message.reply_text(
            f"Entrata registrata alle {now_time} ⏱\n"
            "Tra 10 minuti parte automaticamente Inizio Lavoro."
        )

    # --------------------------
    # USCITA
    # --------------------------
    if text == "Uscita":
        add_record({
            "data": now_date,
            "azione": "Uscita",
            "inizio": "",
            "fine": now_time,
            "ore": "",
            "lavoro": ""
        })

        return await update.message.reply_text(f"Uscita registrata alle {now_time}")

    # --------------------------
    # INIZIO LAVORO
    # --------------------------
    if text == "Inizio lavoro":
        set_work_start(f"{now_date} {now_time}")
        return await update.message.reply_text(f"Inizio lavoro registrato alle {now_time}")

    # --------------------------
    # FINE LAVORO
    # --------------------------
    if text == "Fine lavoro":
        start_str = get_work_start()

        if not start_str:
            return await update.message.reply_text("Prima premi 'Inizio lavoro'.")

        naive_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        start_dt = TZ.localize(naive_dt)
        diff = now - start_dt
        ore = round(diff.total_seconds() / 3600, 2)

        add_record({
            "data": now_date,
            "azione": "Sessione lavoro",
            "inizio": start_dt.strftime("%H:%M:%S"),
            "fine": now_time,
            "ore": ore,
            "lavoro": ""
        })

        set_work_start(None)

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

        add_record({
            "data": now_date,
            "azione": "Lavoro extra",
            "inizio": now_time,
            "fine": "",
            "ore": "",
            "lavoro": text
        })

        context.user_data["adding_extra_work"] = False

        return await update.message.reply_text("Lavoro registrato.", reply_markup=menu_principale())

    # --------------------------
    # ORE LIVE
    # --------------------------
    if text == "Ore Live":
        base_url = get_base_url()

        if not base_url:
            return await update.message.reply_text(
                "Mini app non configurata: manca MINI_APP_URL o dominio Railway."
            )

        url = f"{base_url}/ore-live"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Apri Ore Live ⏱", url=url)]
        ])

        return await update.message.reply_text(
            "Apri la mini app per vedere le ore in tempo reale:",
            reply_markup=keyboard
        )

    # --------------------------
    # RESET
    # --------------------------
    if text == "Reset mese":
        reset_month()
        return await update.message.reply_text("Dati del mese resettati.")

    # --------------------------
    # ESPORTA EXCEL
    # --------------------------
    if text == "Esporta Excel":
        await invia_excel_message(update.message)
        return

    await update.message.reply_text("Comando non valido.", reply_markup=menu_principale())


# --------------------------------------
# EXCEL AUTOMATICO
# --------------------------------------

async def excel_automatico(context: ContextTypes.DEFAULT_TYPE):
    await invia_excel_bot(context.bot, AUTHORIZED_USER_ID)


# --------------------------------------
# AVVIO BOT
# --------------------------------------

def run_bot():
    token = os.getenv("BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("entrata_auto", entrata_auto))
    app.add_handler(CommandHandler("uscita_auto", uscita_auto))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    jq = app.job_queue
    jq.run_daily(excel_automatico, time=dtime(hour=22, minute=0, tzinfo=TZ))

    app.run_polling()
