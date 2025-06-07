import logging
import asyncio
import nest_asyncio
from telegram.ext import ApplicationBuilder
from core import (
    start, handle_message, handle_callback, menu,
    add_word, delete_word_command, view_words_command
)
from database import init_db, get_all_user_ids, get_user_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from os import getenv
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()
init_db()

TOKEN = getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(start)
application.add_handler(menu)
application.add_handler(add_word)
application.add_handler(delete_word_command)
application.add_handler(view_words_command)
application.add_handler(handle_message)
application.add_handler(handle_callback)

scheduler = AsyncIOScheduler()

async def send_reminders_job(application):
    from core import send_reminders
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        settings = get_user_settings(user_id)
        if settings:
            await send_reminders(application.bot, user_id, settings)

def schedule_reminders():
    scheduler.add_job(send_reminders_job, CronTrigger(hour=11, minute=0), args=[application])
    scheduler.add_job(send_reminders_job, CronTrigger(hour=15, minute=0), args=[application])
    scheduler.add_job(send_reminders_job, CronTrigger(hour=19, minute=0), args=[application])
    scheduler.start()

async def main():
    schedule_reminders()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
