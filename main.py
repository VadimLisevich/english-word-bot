import logging
import asyncio
import nest_asyncio
from telegram.ext import ApplicationBuilder
from core import (
    start,
    handle_message_func,
    handle_callback,
    menu,
    send_reminders
)
from database import init_db, get_all_user_ids, get_user_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from os import getenv
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

nest_asyncio.apply()
init_db()

application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(start)
application.add_handler(menu)
application.add_handler(handle_callback)
application.add_handler(handle_message_func)

scheduler = AsyncIOScheduler()

def schedule_reminders(app):
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        settings = get_user_settings(user_id)
        times = {
            1: [(11, 0)],
            2: [(11, 0), (15, 0)],
            3: [(11, 0), (15, 0), (19, 0)],
        }.get(settings.get("reminders_per_day", 1), [(11, 0)])

        for hour, minute in times:
            scheduler.add_job(
                send_reminders,
                CronTrigger(hour=hour, minute=minute),
                args=[app, user_id]
            )

schedule_reminders(application)
scheduler.start()

async def main():
    await application.run_polling()

asyncio.run(main())
