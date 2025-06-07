import logging
import asyncio
import nest_asyncio
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler
)
from core import (
    start, menu, handle_callback, add_word, delete_word_command, send_reminders
)
from database import get_all_user_ids, get_user_settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

nest_asyncio.apply()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(CommandHandler("add", add_word))
application.add_handler(CommandHandler("delete", delete_word_command))


def schedule_reminders(app):
    scheduler = AsyncIOScheduler()

    def create_job(hour):
        scheduler.add_job(lambda: asyncio.create_task(send_reminders({'application': app})),
                          CronTrigger(hour=hour, minute=0))

    user_ids = get_all_user_ids()
    for user_id in user_ids:
        settings = get_user_settings(user_id)
        frequency = int(settings.get("frequency", 1))
        hours = [11, 15, 19][:frequency]
        for hour in hours:
            create_job(hour)

    scheduler.start()


async def main():
    schedule_reminders(application)
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
