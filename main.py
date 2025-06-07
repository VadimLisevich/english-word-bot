import asyncio
import logging
import nest_asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from core import (
    start, handle_callback, handle_message_func, menu
)
from database import init_db
from scheduler import schedule_reminders

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

nest_asyncio.apply()
init_db()

from os import getenv
from dotenv import load_dotenv

load_dotenv()
TOKEN = getenv("TELEGRAM_BOT_TOKEN")

async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_func))

    schedule_reminders(application)
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
