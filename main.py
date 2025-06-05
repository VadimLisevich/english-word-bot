import logging
import os
import random
import sqlite3
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai

# Logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# ENV
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# DB
conn = sqlite3.connect("words.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS words (
    user_id INTEGER,
    word TEXT,
    translation TEXT,
    category TEXT,
    UNIQUE(user_id, word)
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    translate_words INTEGER,
    frequency INTEGER,
    word_count INTEGER,
    category TEXT,
    translate_phrases INTEGER
)
''')
conn.commit()

# Scheduler
scheduler = AsyncIOScheduler()

# --- Utility Functions ---
def get_translation(word: str) -> str:
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Translate '{word}' to Russian."}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

def get_example_sentence(word: str, category: str) -> tuple[str, str]:
    try:
        category_prompt = {
            "Афоризмы": f"an aphorism using the word '{word}'",
            "Цитаты": f"a famous quote using the word '{word}'",
            "Кино": f"a movie quote using the word '{word}' and mention the movie title",
            "Песни": f"a lyric line using the word '{word}' and mention the song name",
            "Любая тема": f"a sentence using the word '{word}' in any context"
        }
        prompt = f"Give {category_prompt.get(category, category_prompt['Любая тема'])}."
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        source = ""
        if "—" in content:
            example, source = content.split("—", 1)
        else:
            example = content
        return example.strip(), source.strip()
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "⚠️ Ошибка генерации примера.", ""

async def send_reminders():
    now = datetime.now().time()
    hour = now.hour
    cursor.execute("SELECT * FROM settings")
    for row in cursor.fetchall():
        user_id, translate_words, freq, word_count, category, translate_phrases = row
        send = (freq == 1 and hour == 11) or \
               (freq == 2 and hour in [11, 15]) or \
               (freq == 3 and hour in [11, 15, 19])
        if send:
            cursor.execute(
                "SELECT word, translation, category FROM words WHERE user_id=? ORDER BY RANDOM() LIMIT ?",
                (user_id, word_count)
            )
            for word, translation, cat in cursor.fetchall():
                phrase, source = get_example_sentence(word, cat)
                text = f"🧠 *{word}* (перевод: _{translation}_)\n\n📘 Пример:\n{phrase}"
                if source:
                    text += f"\n_Source: {source}_"
                await application.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

scheduler.add_job(send_reminders, "cron", hour="11,15,19")

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе учить английские слова. Давай настроим процесс 💬"
    )
    await ask_translate_words(update)

async def ask_translate_words(update: Update):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes"),
         InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await update.message.reply_text("🔤 Нужен перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_frequency(query, context, user_id, translate_words):
    cursor.execute("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE settings SET translate_words=? WHERE user_id=?", (translate_words, user_id))
    conn.commit()
    keyboard = [
        [InlineKeyboardButton("1 раз в день", callback_data="freq_1")],
        [InlineKeyboardButton("2 раза в день", callback_data="freq_2")],
        [InlineKeyboardButton("3 раза в день", callback_data="freq_3")]
    ]
    await context.bot.send_message(chat_id=query.from_user.id, text="🕒 Как часто ты хочешь, чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_word_count(query, context, user_id, freq):
    cursor.execute("UPDATE settings SET frequency=? WHERE user_id=?", (freq, user_id))
    conn.commit()
    keyboard = [
        [InlineKeyboardButton("1", callback_data="count_1"),
         InlineKeyboardButton("2", callback_data="count_2"),
         InlineKeyboardButton("3", callback_data="count_3"),
         InlineKeyboardButton("5", callback_data="count_5")]
    ]
    await context.bot.send_message(chat_id=query.from_user.id, text="📦 Сколько слов присылать за раз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_category(query, context, user_id, count):
    cursor.execute("UPDATE settings SET word_count=? WHERE user_id=?", (count, user_id))
    conn.commit()
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="cat_Афоризмы")],
        [InlineKeyboardButton("Цитаты", callback_data="cat_Цитаты")],
        [InlineKeyboardButton("Кино", callback_data="cat_Кино")],
        [InlineKeyboardButton("Песни", callback_data="cat_Песни")],
        [InlineKeyboardButton("Любая тема", callback_data="cat_Любая тема")]
    ]
    await context.bot.send_message(chat_id=query.from_user.id, text="🎭 Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_translate_phrases(query, context, user_id, category):
    cursor.execute("UPDATE settings SET category=? WHERE user_id=?", (category, user_id))
    conn.commit()
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="trans_phrases_yes"),
         InlineKeyboardButton("Нет", callback_data="trans_phrases_no")]
    ]
    await context.bot.send_message(chat_id=query.from_user.id, text="🌍 Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def finish_setup(query, context, user_id, translate):
    cursor.execute("UPDATE settings SET translate_phrases=? WHERE user_id=?", (translate, user_id))
    conn.commit()
    await context.bot.send_message(chat_id=query.from_user.id, text="✅ Настройка завершена! Используй /menu для повторной настройки.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("translate_words_"):
        await ask_frequency(query, context, user_id, 1 if data.endswith("yes") else 0)
    elif data.startswith("freq_"):
        await ask_word_count(query, context, user_id, int(data.split("_")[1]))
    elif data.startswith("count_"):
        await ask_category(query, context, user_id, int(data.split("_")[1]))
    elif data.startswith("cat_"):
        await ask_translate_phrases(query, context, user_id, data.split("_", 1)[1])
    elif data.startswith("trans_phrases_"):
        await finish_setup(query, context, user_id, 1 if data.endswith("yes") else 0)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_translate_words(update)

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip()
    user_id = update.message.from_user.id
    cursor.execute("SELECT * FROM settings WHERE user_id=?", (user_id,))
    settings = cursor.fetchone()
    if not settings:
        await update.message.reply_text("Сначала нужно настроить бота: /start")
        return

    _, translate_words, _, _, category, _ = settings
    translation = get_translation(word) if translate_words else ""
    cursor.execute("INSERT OR IGNORE INTO words (user_id, word, translation, category) VALUES (?, ?, ?, ?)",
                   (user_id, word, translation, category))
    conn.commit()

    phrase, source = get_example_sentence(word, category)
    text = f"Слово '{word}'"
    if translation:
        text += f" (перевод: {translation})"
    text += " – добавлено в базу ✅\n\n📘 Пример:\n" + phrase
    if source:
        text += f"\n_Source: {source}_"
    await update.message.reply_text(text, parse_mode="Markdown")

# --- Init ---
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("menu", menu))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_word))

if __name__ == "__main__":
    scheduler.start()
    application.run_polling()
