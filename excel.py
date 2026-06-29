from telegram import InputFile
from openpyxl import Workbook

from database import get_records

EXCEL_PATH = "/var/tmp/registro_lavoro.xlsx"


def crea_excel():
    records = get_records()

    if not records:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Registro lavori"

    ws.append(["Data", "Azione", "Ora inizio", "Ora fine", "Ore lavorate", "Lavoro"])

    for r in records:
        ws.append([
            r.get("data", ""),
            r.get("azione", ""),
            r.get("inizio", ""),
            r.get("fine", ""),
            r.get("ore", ""),
            r.get("lavoro", "")
        ])

    wb.save(EXCEL_PATH)
    return EXCEL_PATH


async def invia_excel_message(message):
    file_path = crea_excel()

    if not file_path:
        return await message.reply_text("Nessun dato da esportare.")

    with open(file_path, "rb") as f:
        await message.reply_document(
            InputFile(f, filename="registro_lavoro.xlsx"),
            caption="Esportazione completata ✔"
        )


async def invia_excel_bot(bot, chat_id):
    file_path = crea_excel()

    if not file_path:
        return await bot.send_message(
            chat_id=chat_id,
            text="Excel automatico: oggi non ci sono dati da esportare."
        )

    with open(file_path, "rb") as f:
        await bot.send_document(
            chat_id=chat_id,
            document=InputFile(f, filename="registro_lavoro.xlsx"),
            caption="Excel automatico giornaliero ✔"
        )
