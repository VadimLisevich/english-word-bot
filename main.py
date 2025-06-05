import logging
import os
import random
import asyncio
import nest_asyncio
from datetime import time
from pytz import timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CallbackContext, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core import (
    handle_message, handle_callback, menu,
    send_reminders, add_word
)
from db import load_users, save_users

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем данные пользователей
users = load_users()

# Настройка переменных
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIMEZONE = timezone("Europe/Lisbon")
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


# Команды
async def start_command(update: Update, context: CallbackContext):
    await start(update, context, users, first_time=True)


async def menu_command(update: Update, context: CallbackContext):
    await start(update, context, users, first_time=False)


async def add_word_command(update: Update, context: CallbackContext):
    await add_word(update, context, users)


# Функция настройки рассылки
def setup_jobs(application):
    scheduler.remove_all_jobs()

    for user_id, settings in users.items():
        if not settings.get("auto_send", True):
            continue

        frequency = settings.get("frequency", 1)
        times = []
        if frequency >= 1:
            times.append(time(hour=11, minute=0))
        if frequency >= 2:
            times.append(time(hour=15, minute=0))
        if frequency == 3:
            times.append(time(hour=19, minute=0))

        for t in times:
            scheduler.add_job(
                send_reminders,
                trigger=CronTrigger(hour=t.hour, minute=t.minute),
                args=[application, user_id, users]
            )

    scheduler.start()


# Основной запуск
async def main():
    nest_asyncio.apply()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("add", add_word_command))
    application.add_handler(CallbackQueryHandler(handle_callback, block=False))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_jobs(application)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()


if __name__ == "__main__":
    asyncio.run(main())
