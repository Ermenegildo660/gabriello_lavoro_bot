import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Entrata", "Uscita"]]
    await update.message.reply_text(
        "Bot attivo.",
    )

# gestisce i pulsanti
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Entrata":
        await update.message.reply_text("Entrata registrata.")
    elif text == "Uscita":
        await update.message.reply_text("Uscita registrata.")
    else:
        await update.message.reply_text("Comando non riconosciuto.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))

    # Webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

