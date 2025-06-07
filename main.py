import os
import logging
import nest_asyncio
import asyncio
from datetime import datetime
from pytz import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)
from core import (
    start,
    menu,
    handle_callback,
    handle_message,
    send_reminders,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

# Читаем токен из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

# Для совместимости с Render и Jupyter
nest_asyncio.apply()

# Создаём планировщик задач
scheduler = AsyncIOScheduler(timezone=timezone("Europe/Lisbon"))

# Устанавливаем задания на авторассылку в 11:00, 15:00 и 19:00
scheduler.add_job(send_reminders, CronTrigger(hour=11, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=19, minute=0))
scheduler.start()
logging.info("Scheduler started")

# Основная асинхронная функция запуска бота
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot started")
    await application.run_polling()

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
