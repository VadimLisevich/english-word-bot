import logging
import os
import pytz
from datetime import time
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core import start, menu, handle_callback, add_word, send_reminders

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Инициализация логов
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# Инициализация бота
application = ApplicationBuilder().token(TOKEN).build()

# Хэндлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_word))

# Планировщик
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Lisbon"))
scheduler.add_job(send_reminders, CronTrigger(hour=11, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=19, minute=0))
scheduler.start()

# Запуск
if __name__ == "__main__":
    application.run_polling()
