import logging
import os
import random
import asyncio
from datetime import time
from dotenv import load_dotenv
from uuid import uuid4

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_settings = {}
user_words = {}

scheduler = AsyncIOScheduler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {
        "translate_words": None,
        "frequency": None,
        "words_per_message": None,
        "category": None,
        "translate_phrases": None,
    }
    await context.bot.send_message(chat_id=user_id, text="👋 Привет! Я помогу тебе выучить новые английские слова. Давай настроим всё по порядку.")
    await ask_translate_words(update, context)

async def ask_translate_words(update, context):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")],
    ]
    await context.bot.send_message(chat_id=update.effective_user.id, text="🔤 Переводить добавляемые слова?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_frequency(update, context):
    keyboard = [
        [InlineKeyboardButton("1 раз в день", callback_data="frequency_1")],
        [InlineKeyboardButton("2 раза в день", callback_data="frequency_2")],
        [InlineKeyboardButton("3 раза в день", callback_data="frequency_3")],
    ]
    await context.bot.send_message(chat_id=update.effective_user.id, text="🕒 Как часто ты хочешь, чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_words_per_message(update, context):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="wpm_1"),
         InlineKeyboardButton("2", callback_data="wpm_2")],
        [InlineKeyboardButton("3", callback_data="wpm_3"),
         InlineKeyboardButton("5", callback_data="wpm_5")],
    ]
    await context.bot.send_message(chat_id=update.effective_user.id, text="📦 Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_category(update, context):
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="category_aphorisms")],
        [InlineKeyboardButton("Цитаты", callback_data="category_quotes")],
        [InlineKeyboardButton("Кино", callback_data="category_movies")],
        [InlineKeyboardButton("Песни", callback_data="category_songs")],
        [InlineKeyboardButton("Любая тема", callback_data="category_any")],
    ]
    await context.bot.send_message(chat_id=update.effective_user.id, text="🎭 Откуда брать примеры фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_translate_phrases(update, context):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")],
    ]
    await context.bot.send_message(chat_id=update.effective_user.id, text="🌍 Переводить фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def finish_setup(update, context):
    await context.bot.send_message(chat_id=update.effective_user.id, text="✅ Настройка завершена! Чтобы изменить параметры, используй /menu.")
    schedule_user_reminders(update.effective_user.id)

def schedule_user_reminders(user_id):
    settings = user_settings.get(user_id)
    if not settings:
        return

    scheduler.remove_all_jobs(jobstore=str(user_id))

    hours = {
        "1": [11],
        "2": [11, 15],
        "3": [11, 15, 19],
    }.get(str(settings["frequency"]), [])

    for hour in hours:
        scheduler.add_job(
            send_reminders,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[user_id],
            id=f"{user_id}_{hour}",
            jobstore=str(user_id)
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.callback_query.data
    await update.callback_query.answer()

    if data.startswith("translate_words"):
        user_settings[user_id]["translate_words"] = data.endswith("yes")
        await ask_frequency(update, context)
    elif data.startswith("frequency"):
        user_settings[user_id]["frequency"] = int(data.split("_")[1])
        await ask_words_per_message(update, context)
    elif data.startswith("wpm"):
        user_settings[user_id]["words_per_message"] = int(data.split("_")[1])
        await ask_category(update, context)
    elif data.startswith("category"):
        user_settings[user_id]["category"] = data.split("_")[1]
        await ask_translate_phrases(update, context)
    elif data.startswith("translate_phrases"):
        user_settings[user_id]["translate_phrases"] = data.endswith("yes")
        await finish_setup(update, context)

async def generate_translation(word: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Translate the word '{word}' to Russian only as one word."}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation error for word '{word}': {e}")
        return "ошибка перевода"

async def generate_example(word: str, category: str) -> tuple[str, str, str]:
    try:
        topic = {
            "movies": "from a famous movie",
            "songs": "from a popular song",
            "quotes": "from a well-known quote",
            "aphorisms": "from a classic aphorism",
            "any": "from any context"
        }.get(category, "any")

        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Give me one English sentence using the word '{word}' in context ({topic}), then translate it to Russian, and specify the exact source (e.g., movie title, song name). Format:\nEN: ...\nRU: ...\nSource: ..."}
            ],
        )
        content = response.choices[0].message.content
        lines = content.split("\n")
        en, ru, source = "", "", ""
        for line in lines:
            if line.lower().startswith("en:"):
                en = line[3:].strip()
            elif line.lower().startswith("ru:"):
                ru = line[3:].strip()
            elif line.lower().startswith("source:"):
                source = line[7:].strip()
        return en, ru, source
    except Exception as e:
        logger.error(f"Error generating example for word '{word}': {e}")
        return None, None, None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    if word.startswith("/delete "):
        word_to_delete = word.replace("/delete", "").strip()
        user_words.setdefault(user_id, set()).discard(word_to_delete)
        await update.message.reply_text(f"❌ Слово '{word_to_delete}' удалено из базы.")
        return

    if user_id not in user_words:
        user_words[user_id] = set()

    if word in user_words[user_id]:
        await update.message.reply_text("⚠️ Это слово уже есть в базе.")
        return

    user_words[user_id].add(word)
    settings = user_settings.get(user_id, {})
    translation = await generate_translation(word) if settings.get("translate_words") else "без перевода"
    en, ru, source = await generate_example(word, settings.get("category", "any"))
    result = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
    if en and ru and source:
        result += f"📘 Пример:\n\"{en}\"\n\"{ru}\"\nИсточник: {source}"
    else:
        result += "📘 Пример:\n⚠️ Ошибка генерации примера."
    await update.message.reply_text(result)

async def send_reminders(user_id):
    settings = user_settings.get(user_id)
    if not settings:
        return

    words = list(user_words.get(user_id, []))
    if not words:
        return

    selected_words = random.sample(words, min(len(words), settings["words_per_message"]))
    for word in selected_words:
        translation = await generate_translation(word) if settings.get("translate_words") else "без перевода"
        en, ru, source = await generate_example(word, settings.get("category", "any"))
        text = f"📌 Слово: {word} (перевод: {translation})\n\n"
        if en and ru and source:
            text += f"📘 Пример:\n\"{en}\"\n\"{ru}\"\nИсточник: {source}"
        else:
            text += "📘 Пример:\n⚠️ Ошибка генерации примера."
        application = context.bot.application
        await application.bot.send_message(chat_id=user_id, text=text)

if __name__ == "__main__":
    async def main():
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("menu", start))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        scheduler.start()
        await app.run_polling()

    asyncio.run(main())
