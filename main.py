import logging
import os
import random
import sqlite3
from datetime import datetime
from pytz import timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

import nest_asyncio
nest_asyncio.apply()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_NAME = "words.db"
TIMEZONE = "Europe/Lisbon"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

application = ApplicationBuilder().token(TOKEN).build()
scheduler = AsyncIOScheduler(timezone=timezone(TIMEZONE))

user_settings = {}
user_states = {}

default_settings = {
    "word_translation": True,
    "phrase_times": 1,
    "words_per_time": 1,
    "phrase_category": "Любая тема",
    "phrase_translation": True,
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS words (
            user_id INTEGER,
            word TEXT,
            PRIMARY KEY (user_id, word)
        )"""
    )
    conn.commit()
    conn.close()


def add_word(user_id: int, word: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO words (user_id, word) VALUES (?, ?)", (user_id, word))
    conn.commit()
    conn.close()


def get_words(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE user_id = ?", (user_id,))
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words


def delete_word(user_id: int, word: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = default_settings.copy()
    user_states[user_id] = "ask_word_translation"
    await update.message.reply_text(
        "Привет! Я помогу тебе учить английские слова. Начнём настройку!\n\nНужен ли перевод слов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="word_translation_yes")],
            [InlineKeyboardButton("Нет", callback_data="word_translation_no")],
        ]),
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = default_settings.copy()
    user_states[user_id] = "ask_word_translation"
    await update.message.reply_text(
        "Изменим настройки. Нужен ли перевод слов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="word_translation_yes")],
            [InlineKeyboardButton("Нет", callback_data="word_translation_no")],
        ]),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    add_word(user_id, word)
    translation = f"Перевод: {translate_word(word)}" if user_settings[user_id]["word_translation"] else ""
    example, source = get_example_phrase(word, user_settings[user_id]["phrase_category"])
    phrase_text = f"{example}\nИсточник: {source}" if user_settings[user_id]["phrase_translation"] else example

    await update.message.reply_text(
        f"Слово '{word}' ({translation}) – добавлено в базу ✅\n\n📘 Пример: {phrase_text}"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_states.get(user_id)

    data = query.data
    settings = user_settings[user_id]

    if state == "ask_word_translation":
        settings["word_translation"] = data.endswith("yes")
        user_states[user_id] = "ask_phrase_times"
        await query.message.reply_text(
            "Как часто отправлять фразы?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1 раз в день", callback_data="time_1")],
                [InlineKeyboardButton("2 раза в день", callback_data="time_2")],
                [InlineKeyboardButton("3 раза в день", callback_data="time_3")],
            ])
        )
    elif state == "ask_phrase_times":
        settings["phrase_times"] = int(data[-1])
        user_states[user_id] = "ask_words_per_time"
        await query.message.reply_text(
            "Сколько слов присылать за раз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data="words_1"),
                 InlineKeyboardButton("2", callback_data="words_2"),
                 InlineKeyboardButton("3", callback_data="words_3"),
                 InlineKeyboardButton("5", callback_data="words_5")],
            ])
        )
    elif state == "ask_words_per_time":
        settings["words_per_time"] = int(data.split("_")[1])
        user_states[user_id] = "ask_category"
        await query.message.reply_text(
            "Откуда брать фразы?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Афоризмы", callback_data="cat_Афоризмы")],
                [InlineKeyboardButton("Цитаты", callback_data="cat_Цитаты")],
                [InlineKeyboardButton("Кино", callback_data="cat_Кино")],
                [InlineKeyboardButton("Песни", callback_data="cat_Песни")],
                [InlineKeyboardButton("Любая тема", callback_data="cat_Любая тема")],
            ])
        )
    elif state == "ask_category":
        settings["phrase_category"] = data.split("_")[1]
        user_states[user_id] = "ask_phrase_translation"
        await query.message.reply_text(
            "Нужен ли перевод фраз?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Да", callback_data="phrase_translation_yes")],
                [InlineKeyboardButton("Нет", callback_data="phrase_translation_no")],
            ])
        )
    elif state == "ask_phrase_translation":
        settings["phrase_translation"] = data.endswith("yes")
        user_states[user_id] = None
        await query.message.reply_text(
            "✅ Настройка завершена! Чтобы изменить параметры — используй команду /menu"
        )


def translate_word(word):
    return "Примерный перевод"  # тут будет реальный перевод через API, если подключим


def get_example_phrase(word, category):
    examples = {
        "Кино": (f"I'm executing the plan perfectly, just like always.", "Фильм: Inception"),
        "Песни": (f"Keep executing dreams like a rockstar.", "Песня: Rockstar"),
        "Афоризмы": (f"Executing ideas without action is like winking in the dark.", "Афоризм"),
        "Цитаты": (f"She kept executing tasks flawlessly — Steve Jobs", "Цитата: Стив Джобс"),
        "Любая тема": (f"They were executing their duties with pride.", "Произвольный текст"),
    }
    return examples.get(category, examples["Любая тема"])


async def send_reminders():
    for user_id, settings in user_settings.items():
        words = get_words(user_id)
        if not words:
            continue
        selected_words = random.sample(words, min(len(words), settings["words_per_time"]))
        for word in selected_words:
            translation = f" (перевод: {translate_word(word)})" if settings["word_translation"] else ""
            phrase, source = get_example_phrase(word, settings["phrase_category"])
            text = f"Слово '{word}'{translation}\n📘 {phrase}\nИсточник: {source}"
            await application.bot.send_message(chat_id=user_id, text=text)


def schedule_jobs():
    times = [(11, 0), (15, 0), (19, 0)]
    for idx, (hour, minute) in enumerate(times, start=1):
        scheduler.add_job(
            send_reminders,
            CronTrigger(hour=hour, minute=minute),
            id=f"reminder_{idx}",
            replace_existing=True,
        )
    scheduler.start()


if __name__ == "__main__":
    init_db()
    schedule_jobs()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
