import os
import random
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
user_data = {}

scheduler = AsyncIOScheduler()
scheduler.start()

CATEGORIES = {
    "Афоризмы": "aphorism",
    "Цитаты": "quote",
    "Кино": "movie",
    "Песни": "song",
    "Любая тема": "any"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "translate_word": None,
        "times_per_day": None,
        "words_per_time": None,
        "category": None,
        "translate_phrase": None,
        "words": []
    }
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я помогу тебе выучить английские слова.")
    await ask_translate_word(update, context)


async def ask_translate_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Да", callback_data="translate_word_yes"),
        InlineKeyboardButton("Нет", callback_data="translate_word_no")
    ]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_times_per_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("1", callback_data="times_1"),
        InlineKeyboardButton("2", callback_data="times_2"),
        InlineKeyboardButton("3", callback_data="times_3")
    ]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Как часто ты хочешь, чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_words_per_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("1", callback_data="words_1"),
        InlineKeyboardButton("2", callback_data="words_2"),
        InlineKeyboardButton("3", callback_data="words_3"),
        InlineKeyboardButton("5", callback_data="words_5")
    ]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"category_{cat}")] for cat in CATEGORIES]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_translate_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Да", callback_data="translate_phrase_yes"),
        InlineKeyboardButton("Нет", callback_data="translate_phrase_no")
    ]]
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def finish_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="✅ Настройка завершена! Используй /menu, чтобы изменить настройки.")
    schedule_user_reminders(update.effective_user.id)


def schedule_user_reminders(user_id):
    hours_map = {
        1: [11],
        2: [11, 15],
        3: [11, 15, 19]
    }
    times = user_data[user_id]["times_per_day"]
    for hour in hours_map.get(times, [11]):
        scheduler.add_job(send_reminders, "cron", hour=hour, minute=0, args=[user_id])


async def send_reminders(user_id):
    user = user_data.get(user_id)
    if not user or not user["words"]:
        return

    words = random.sample(user["words"], min(user["words_per_time"], len(user["words"])))
    bot = application.bot
    for word in words:
        translated, phrase, source, phrase_translated = await get_example_with_translation(word, user["category"])
        msg = f"📌 Слово: {word}"
        if user["translate_word"] and translated:
            msg += f" (перевод: {translated})"
        msg += f"\n\n📘 Пример:\n{phrase}\nИсточник: {source}"
        if user["translate_phrase"] and phrase_translated:
            msg += f"\n\n📙 Перевод:\n{phrase_translated}"
        await bot.send_message(chat_id=user_id, text=msg)


async def get_example_with_translation(word, category_label):
    category = CATEGORIES.get(category_label, "any")
    try:
        prompt = f"""
Translate the word '{word}' to Russian.

Then, give one short example sentence using this word, in context of the category "{category}".
Mention the specific source (e.g. name of the movie, song, book, etc).

Format:
Translation: ...
Sentence: ...
Source: ...
Sentence_Translation: ...
"""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content
        parts = dict(line.split(": ", 1) for line in content.splitlines() if ": " in line)
        return (
            parts.get("Translation", "ошибка перевода"),
            parts.get("Sentence", "⚠️ Ошибка генерации примера."),
            parts.get("Source", "неизвестно"),
            parts.get("Sentence_Translation", "")
        )
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "ошибка перевода", "⚠️ Ошибка генерации примера.", "", ""


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "translate_word_yes":
        user_data[user_id]["translate_word"] = True
        await ask_times_per_day(update, context)
    elif data == "translate_word_no":
        user_data[user_id]["translate_word"] = False
        await ask_times_per_day(update, context)
    elif data.startswith("times_"):
        user_data[user_id]["times_per_day"] = int(data.split("_")[1])
        await ask_words_per_time(update, context)
    elif data.startswith("words_"):
        user_data[user_id]["words_per_time"] = int(data.split("_")[1])
        await ask_category(update, context)
    elif data.startswith("category_"):
        category = data.split("_", 1)[1]
        user_data[user_id]["category"] = category
        await ask_translate_phrase(update, context)
    elif data == "translate_phrase_yes":
        user_data[user_id]["translate_phrase"] = True
        await finish_setup(update, context)
    elif data == "translate_phrase_no":
        user_data[user_id]["translate_phrase"] = False
        await finish_setup(update, context)


async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    user_data[user_id]["words"].append(word)

    translated, phrase, source, phrase_translated = await get_example_with_translation(word, user_data[user_id]["category"])

    message = f"Слово '{word}' (перевод: {translated}) – добавлено в базу ✅\n\n📘 Пример:\n{phrase}\nИсточник: {source}"
    if user_data[user_id]["translate_phrase"] and phrase_translated:
        message += f"\n\n📙 Перевод:\n{phrase_translated}"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def main():
    global application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))
    application.run_polling()


if __name__ == "__main__":
    main()
