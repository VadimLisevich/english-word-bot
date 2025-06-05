import logging
import random
import os
import asyncio
from datetime import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

user_settings = {}
user_words = {}

scheduler = AsyncIOScheduler()

async def translate_word(word: str) -> str:
    try:
        prompt = f"Translate the English word '{word}' into Russian with no explanations."
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

async def generate_example(word: str, category: str) -> (str, str):
    try:
        prompt = (
            f"Give one example sentence using the English word '{word}' "
            f"in the context of {category}. Mention the exact name of the source (movie, song, book, etc)."
        )
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        output = response.choices[0].message.content.strip()
        return output, category
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "⚠️ Ошибка генерации примера.", ""

def get_time_list(frequency: int):
    if frequency == 1:
        return [time(11, 0)]
    elif frequency == 2:
        return [time(11, 0), time(15, 0)]
    elif frequency == 3:
        return [time(11, 0), time(15, 0), time(19, 0)]
    return []

def schedule_user_reminders(application: Application, user_id: int):
    settings = user_settings.get(user_id)
    if not settings:
        return
    frequency = settings.get("frequency")
    times = get_time_list(frequency)
    for t in times:
        scheduler.add_job(
            send_reminders,
            CronTrigger(hour=t.hour, minute=t.minute),
            args=[application, user_id],
            id=f"reminder_{user_id}_{t}",
            replace_existing=True
        )

async def send_reminders(application: Application, user_id: int):
    settings = user_settings.get(user_id, {})
    words = user_words.get(user_id, [])
    count = settings.get("count", 1)
    category = settings.get("category", "любая тема")
    include_translation = settings.get("translate", True)

    if not words:
        await application.bot.send_message(chat_id=user_id, text="У тебя ещё нет слов в базе.")
        return

    selected_words = random.sample(words, min(count, len(words)))
    for word_entry in selected_words:
        word = word_entry["word"]
        translation = word_entry.get("translation", "")
        example, source = await generate_example(word, category)

        message = f"📘 Слово: {word}"
        if include_translation:
            message += f"\nПеревод: {translation}"
        message += f"\n\n📘 Пример:\n{example}"
        if source:
            message += f"\nИсточник: {source}"
        await application.bot.send_message(chat_id=user_id, text=message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {}
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_yes"),
         InlineKeyboardButton("Нет", callback_data="translate_no")]
    ]
    await update.message.reply_text("Нужен перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    settings = user_settings.setdefault(user_id, {})

    if data.startswith("translate_"):
        settings["translate"] = data == "translate_yes"
        keyboard = [
            [InlineKeyboardButton("1", callback_data="freq_1"),
             InlineKeyboardButton("2", callback_data="freq_2"),
             InlineKeyboardButton("3", callback_data="freq_3")]
        ]
        await query.message.reply_text("Как часто ты хочешь, чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("freq_"):
        settings["frequency"] = int(data.split("_")[1])
        keyboard = [
            [InlineKeyboardButton("1", callback_data="count_1"),
             InlineKeyboardButton("2", callback_data="count_2"),
             InlineKeyboardButton("3", callback_data="count_3"),
             InlineKeyboardButton("5", callback_data="count_5")]
        ]
        await query.message.reply_text("Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("count_"):
        settings["count"] = int(data.split("_")[1])
        keyboard = [
            [InlineKeyboardButton("Афоризмы", callback_data="cat_Афоризмы")],
            [InlineKeyboardButton("Цитаты", callback_data="cat_Цитаты")],
            [InlineKeyboardButton("Кино", callback_data="cat_Кино")],
            [InlineKeyboardButton("Песни", callback_data="cat_Песни")],
            [InlineKeyboardButton("Любая тема", callback_data="cat_любая тема")]
        ]
        await query.message.reply_text("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("cat_"):
        settings["category"] = data.split("_", 1)[1]
        keyboard = [
            [InlineKeyboardButton("Да", callback_data="example_translate_yes"),
             InlineKeyboardButton("Нет", callback_data="example_translate_no")]
        ]
        await query.message.reply_text("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("example_translate_"):
        settings["example_translate"] = data.endswith("yes")
        await query.message.reply_text("✅ Настройка завершена! Используй команду /menu для изменения настроек.")
        schedule_user_reminders(context.application, user_id)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    translation = await translate_word(word)
    example, source = await generate_example(word, user_settings.get(user_id, {}).get("category", "любая тема"))

    user_words.setdefault(user_id, []).append({
        "word": word,
        "translation": translation
    })

    message = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n📘 Пример:\n{example}"
    if source:
        message += f"\nИсточник: {source}"
    await update.message.reply_text(message)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_word))

    scheduler.start()
    app.run_polling()

if __name__ == "__main__":
    main()
