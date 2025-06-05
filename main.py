import logging
import os
import random
import asyncio
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

user_settings = {}
user_words = {}

scheduler = AsyncIOScheduler()

FREQUENCY_TIMES = {
    1: [11],
    2: [11, 15],
    3: [11, 15, 19],
}

THEMES = {
    "aphorisms": "Афоризмы",
    "quotes": "Цитаты",
    "movies": "Кино",
    "songs": "Песни",
    "any": "Любая тема",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {}
    await context.bot.send_message(chat_id=user_id, text="Привет! Я помогу тебе выучить английские слова 💬\n\nДавай начнем настройку.")
    await ask_translate_words(update, context)

async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Нужен перевод слов?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="frequency_1")],
        [InlineKeyboardButton("2", callback_data="frequency_2")],
        [InlineKeyboardButton("3", callback_data="frequency_3")]
    ]
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Как часто ты хочешь, чтобы я писал тебе?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_word_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="wordcount_1")],
        [InlineKeyboardButton("2", callback_data="wordcount_2")],
        [InlineKeyboardButton("3", callback_data="wordcount_3")],
        [InlineKeyboardButton("5", callback_data="wordcount_5")]
    ]
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Сколько слов присылать за один раз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=f"theme_{key}")] for key, name in THEMES.items()]
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Откуда брать фразы?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_translate_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
    ]
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Нужен ли перевод фраз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def done_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    schedule_user_reminders(user_id)
    await context.bot.send_message(
        chat_id=user_id,
        text="✅ Настройка завершена! Используй /menu чтобы изменить параметры."
    )

def schedule_user_reminders(user_id):
    scheduler.remove_all_jobs(jobstore="default")
    settings = user_settings.get(user_id)
    if not settings:
        return

    times = FREQUENCY_TIMES.get(settings.get("frequency", 1), [11])
    for hour in times:
        scheduler.add_job(
            send_reminders,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[user_id],
            id=f"reminder_{user_id}_{hour}"
        )

async def send_reminders(user_id):
    settings = user_settings.get(user_id)
    if not settings:
        return

    words = user_words.get(user_id, [])
    if not words:
        return

    selected = random.sample(words, min(settings.get("word_count", 1), len(words)))
    for word in selected:
        await send_word_with_example(user_id, word)

async def send_word_with_example(chat_id, word):
    try:
        translation = await translate_word(word)
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        translation = "ошибка перевода"

    try:
        phrase, source = await generate_example(word)
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        phrase, source = "⚠️ Ошибка генерации примера.", ""

    message = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n📘 Пример:\n{phrase}"
    if source:
        message += f" Source: {source}."
    await application.bot.send_message(chat_id=chat_id, text=message)

async def translate_word(word):
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Переведи слово '{word}' на русский кратко."}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

async def generate_example(word):
    prompt = f"""Составь короткую фразу с английским словом "{word}" в контексте. 
Если задана тема, используй её. В конце укажи источник (например, название фильма или песни)."""

    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    output = response.choices[0].message.content.strip()
    if "Source:" in output:
        phrase, source = output.rsplit("Source:", 1)
        return phrase.strip(), source.strip()
    return output, ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    user_words.setdefault(user_id, []).append(word)
    await send_word_with_example(user_id, word)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {}
    await ask_translate_words(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("translate_words_"):
        user_settings[user_id]["translate_words"] = data.endswith("yes")
        await ask_frequency(update, context)
    elif data.startswith("frequency_"):
        user_settings[user_id]["frequency"] = int(data.split("_")[1])
        await ask_word_count(update, context)
    elif data.startswith("wordcount_"):
        user_settings[user_id]["word_count"] = int(data.split("_")[1])
        await ask_theme(update, context)
    elif data.startswith("theme_"):
        user_settings[user_id]["theme"] = data.split("_")[1]
        await ask_translate_phrases(update, context)
    elif data.startswith("translate_phrases_"):
        user_settings[user_id]["translate_phrases"] = data.endswith("yes")
        await done_setup(update, context)

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    scheduler.start()
    application.run_polling()
