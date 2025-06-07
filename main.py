import os
import logging
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters
from core import (
    start, menu, handle_message_func, handle_callback,
    add_word_command, view_words_command, delete_word_command
)
from database import init_db
from scheduler import schedule_reminders

nest_asyncio.apply()
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

async def main():
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("add", add_word_command))
    application.add_handler(CommandHandler("view", view_words_command))
    application.add_handler(CommandHandler("delete", delete_word_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_func))
    application.add_handler(CallbackQueryHandler(handle_callback))

    schedule_reminders(application)
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
