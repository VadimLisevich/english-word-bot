import logging
import os
import random
from datetime import time

import nest_asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core import (
    add_word,
    delete_word,
    get_example_sentence,
    get_translation,
    load_user_settings,
    remove_word_from_db,
    save_user_settings,
    send_daily_phrases,
    show_words,
    start_setup,
)

load_dotenv()
nest_asyncio.apply()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Логгирование
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

application = ApplicationBuilder().token(TOKEN).build()

user_settings = {}

# ===================== Обработчики =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_setup(update, context, user_settings, is_restart=False)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_setup(update, context, user_settings, is_restart=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_settings:
        user_settings[user_id] = load_user_settings(user_id)

    translation = get_translation(text)
    phrase, source = get_example_sentence(
        text,
        user_settings[user_id]["phrase_category"]
    )
    await add_word(user_id, text)

    response = (
        f"Слово '{text}' (перевод: {translation}) – добавлено в базу ✅\n\n"
        f"📘 Пример: {phrase}\n"
        f"🎬 Источник: {source}"
    )
    await update.message.reply_text(response)


async def show_my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_words(update, context)


async def delete_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_word(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start_setup(update, context, user_settings, is_restart=True, callback_data=query.data)


# ===================== Планировщик =====================

async def send_reminders():
    for user_id, settings in user_settings.items():
        await send_daily_phrases(application.bot, user_id, settings)


scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Lisbon"))
scheduler.add_job(send_reminders, CronTrigger(hour=11, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=19, minute=0))
scheduler.start()

# ===================== Регистрация хендлеров =====================

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CommandHandler("show", show_my_words))
application.add_handler(CommandHandler("delete", delete_word_command))
application.add_handler(CallbackQueryHandler(handle_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===================== Запуск =====================

if __name__ == "__main__":
    application.run_polling()
