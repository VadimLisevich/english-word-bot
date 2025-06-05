import logging
import asyncio
import nest_asyncio
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import json
from dotenv import load_dotenv
import random
from pytz import timezone

nest_asyncio.apply()
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
TOKEN = os.getenv("BOT_TOKEN")
PORTUGAL_TZ = timezone('Europe/Lisbon')

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

user_settings = {}
user_words = {}

if os.path.exists("user_data.json"):
    with open("user_data.json", "r") as f:
        data = json.load(f)
        user_settings = data.get("settings", {})
        user_words = data.get("words", {})

def save_user_data():
    with open("user_data.json", "w") as f:
        json.dump({"settings": user_settings, "words": user_words}, f)

async def translate_word(word):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Translate the word '{word}' from English to Russian."
            }]
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

async def generate_example(word, category):
    prompt_map = {
        "Кино": f"Give a movie quote using the word '{word}'. Name the movie.",
        "Песни": f"Give a song lyric using the word '{word}'. Name the song.",
        "Афоризмы": f"Give an aphorism using the word '{word}'.",
        "Цитаты": f"Give a quote from a famous person using the word '{word}'. Name the person.",
        "Любая тема": f"Give a sentence in any style using the word '{word}' and mention the source style (movie, book, etc.)."
    }

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": prompt_map.get(category, prompt_map["Любая тема"])
            }]
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "Ошибка генерации примера"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {
        "translate_words": None,
        "frequency": None,
        "words_per_message": None,
        "phrase_source": None,
        "translate_phrases": None
    }
    save_user_data()
    await update.message.reply_text(
        "Привет! Я помогу тебе учить английские слова. Давай настроим всё под тебя 🙂"
    )
    await ask_translate_words(update, context)

async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes"),
         InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await update.message.reply_text("Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {
        "translate_words": None,
        "frequency": None,
        "words_per_message": None,
        "phrase_source": None,
        "translate_phrases": None
    }
    save_user_data()
    await ask_translate_words(update, context)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data.startswith("translate_words_"):
        user_settings[user_id]["translate_words"] = data.endswith("yes")
        await query.message.reply_text("Как часто отправлять фразы?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 раз в день", callback_data="freq_1")],
            [InlineKeyboardButton("2 раза в день", callback_data="freq_2")],
            [InlineKeyboardButton("3 раза в день", callback_data="freq_3")]
        ]))

    elif data.startswith("freq_"):
        user_settings[user_id]["frequency"] = int(data.split("_")[1])
        await query.message.reply_text("Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data="count_1"),
             InlineKeyboardButton("2", callback_data="count_2")],
            [InlineKeyboardButton("3", callback_data="count_3"),
             InlineKeyboardButton("5", callback_data="count_5")]
        ]))

    elif data.startswith("count_"):
        user_settings[user_id]["words_per_message"] = int(data.split("_")[1])
        await query.message.reply_text("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Афоризмы", callback_data="source_Афоризмы")],
            [InlineKeyboardButton("Цитаты", callback_data="source_Цитаты")],
            [InlineKeyboardButton("Кино", callback_data="source_Кино")],
            [InlineKeyboardButton("Песни", callback_data="source_Песни")],
            [InlineKeyboardButton("Любая тема", callback_data="source_Любая тема")]
        ]))

    elif data.startswith("source_"):
        user_settings[user_id]["phrase_source"] = data.split("_", 1)[1]
        await query.message.reply_text("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="translate_phrases_yes"),
             InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
        ]))

    elif data.startswith("translate_phrases_"):
        user_settings[user_id]["translate_phrases"] = data.endswith("yes")
        save_user_data()
        await query.message.reply_text("Настройка завершена ✅\n\nЧтобы изменить параметры, набери /menu")

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.strip().lower()

    if user_id not in user_words:
        user_words[user_id] = []

    if word not in user_words[user_id]:
        user_words[user_id].append(word)
        save_user_data()
        translation = await translate_word(word) if user_settings.get(user_id, {}).get("translate_words") else None
        phrase = await generate_example(word, user_settings.get(user_id, {}).get("phrase_source", "Любая тема"))
        response = f"Слово '{word}'"
        if translation:
            response += f" (перевод: {translation})"
        response += " – добавлено в базу ✅"
        await update.message.reply_text(response)
        await update.message.reply_text(f"Пример: {phrase}")
    else:
        await update.message.reply_text("Это слово уже есть в твоей базе.")

async def send_reminders():
    for user_id, settings in user_settings.items():
        words = user_words.get(user_id, [])
        if not words or not settings:
            continue
        count = settings.get("words_per_message", 1)
        selected_words = random.sample(words, min(count, len(words)))
        for word in selected_words:
            translation = await translate_word(word) if settings.get("translate_words") else None
            phrase = await generate_example(word, settings.get("phrase_source", "Любая тема"))
            text = f"Слово: {word}"
            if translation:
                text += f" (перевод: {translation})"
            text += f"\nПример: {phrase}"
            # Функция отправки в чат будет реализована отдельно
            application.bot.send_message(chat_id=int(user_id), text=text)

if __name__ == "__main__":
    scheduler = AsyncIOScheduler(timezone=PORTUGAL_TZ)
    scheduler.add_job(send_reminders, CronTrigger(hour=11, minute=0))
    scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0))
    scheduler.add_job(send_reminders, CronTrigger(hour=19, minute=0))
    scheduler.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_word))

    asyncio.get_event_loop().run_until_complete(application.run_polling())
