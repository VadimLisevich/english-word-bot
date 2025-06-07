import os
import logging
import asyncio
import pytz
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core import (
    start,
    menu,
    handle_message,
    handle_callback,
    send_reminders,
)
from database import get_all_user_ids, get_user_settings
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Lisbon"))

def schedule_reminders(application):
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        settings = get_user_settings(user_id)
        frequency = settings.get("frequency", 1)

        times = {
            1: ["11:00"],
            2: ["11:00", "15:00"],
            3: ["11:00", "15:00", "19:00"]
        }.get(frequency, ["11:00"])

        for t in times:
            hour, minute = map(int, t.split(":"))
            scheduler.add_job(
                send_reminders,
                trigger=CronTrigger(hour=hour, minute=minute),
                args=[application.job_queue],
                kwargs={"chat_id": user_id},
                id=f"reminder_{user_id}_{t}",
                replace_existing=True
            )

async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    schedule_reminders(application)
    scheduler.start()

    logging.info("Бот запущен")
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
