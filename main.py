import os
import json
import logging
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI, OpenAIError

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

# ---------------- DATA ----------------
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "user_words.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_settings = load_json(SETTINGS_FILE)
user_words = load_json(WORDS_FILE)

# ---------------- НАСТРОЙКА ----------------
DEFAULT_STATE = "start"
SETUP_ORDER = [
    "translate_word", "message_freq", "words_per_batch", "phrase_source", "translate_phrase"
]

def get_next_setting(user_id):
    user_data = user_settings.get(str(user_id), {})
    for key in SETUP_ORDER:
        if key not in user_data:
            return key
    return None

async def start_setup(user_id, context: ContextTypes.DEFAULT_TYPE, greet=True):
    user_settings[str(user_id)] = {"state": DEFAULT_STATE}
    save_json(SETTINGS_FILE, user_settings)
    if greet:
        await context.bot.send_message(chat_id=user_id, text=(
            "👋 Привет! Этот бот помогает учить английские слова через фразы.\n"
            "Просто присылай сюда слова, которые тебе сложно запомнить, и я буду слать примеры фраз в течение дня.\n\n"
            "Окей, давай настроим бота!"
        ))
    await ask_next_question(user_id, context)

async def ask_next_question(user_id, context):
    user_data = user_settings.get(str(user_id), {})
    current_setting = get_next_setting(user_id)

    if not current_setting:
        user_data["state"] = "active"
        await context.bot.send_message(
            chat_id=user_id,
            text="🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu"
        )
        save_json(SETTINGS_FILE, user_settings)
        return

    user_data["state"] = current_setting
    save_json(SETTINGS_FILE, user_settings)

    keyboard = {
        "translate_word": ["Без перевода", "Нужен перевод"],
        "message_freq": ["1", "2", "3"],
        "words_per_batch": ["1", "2", "3", "5"],
        "phrase_source": ["Афоризм", "Цитата", "Кино", "Песня", "Любая тема"],
        "translate_phrase": ["Да", "Нет"]
    }

    messages = {
        "translate_word": "Нужен ли тебе перевод слова?",
        "message_freq": "Как часто ты хочешь получать сообщения в день?",
        "words_per_batch": "Сколько слов повторять за один раз?",
        "phrase_source": "Откуда лучше брать примеры фраз?",
        "translate_phrase": "Нужен ли перевод для фраз?"
    }

    buttons = [
        [InlineKeyboardButton(text, callback_data=text)] for text in keyboard[current_setting]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=user_id, text=messages[current_setting], reply_markup=reply_markup)

# ---------------- CALLBACK ----------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    state = user_settings.get(str(user_id), {}).get("state")
    if not state or state == "active":
        return

    value = query.data
    if state == "translate_word":
        user_settings[str(user_id)]["translate_word"] = (value == "Нужен перевод")
    elif state == "message_freq":
        user_settings[str(user_id)]["message_freq"] = int(value)
    elif state == "words_per_batch":
        user_settings[str(user_id)]["words_per_batch"] = int(value)
    elif state == "phrase_source":
        user_settings[str(user_id)]["phrase_source"] = value
    elif state == "translate_phrase":
        user_settings[str(user_id)]["translate_phrase"] = (value == "Да")

    save_json(SETTINGS_FILE, user_settings)
    await ask_next_question(user_id, context)

# ---------------- ПЕРЕВОД + ПРИМЕР ----------------
async def get_translation_and_example(word, source, translate_phrase=True):
    prompt = (
        f"Give a short example sentence using the word '{word}' in a natural context. "
        f"Source: {source}. Then write the source (e.g., movie or song)."
    )
    if translate_phrase:
        prompt += " Translate the sentence into Russian."

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices[0].message.content
    except OpenAIError as e:
        logging.error(f"OpenAI error: {e}")
        return None

# ---------------- ОБРАБОТКА СООБЩЕНИЙ ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.startswith("/delete "):
        word = text.replace("/delete", "").strip().lower()
        words = user_words.get(str(user_id), [])
        if word in words:
            words.remove(word)
            user_words[str(user_id)] = words
            save_json(WORDS_FILE, user_words)
            await update.message.reply_text(f"❌ Слово '{word}' удалено из базы.")
        else:
            await update.message.reply_text("Слово не найдено.")
        return

    state = user_settings.get(str(user_id), {}).get("state")
    if state != "active":
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    user_words.setdefault(str(user_id), []).append(text.lower())
    save_json(WORDS_FILE, user_words)

    if user_settings[str(user_id)].get("translate_word", False):
        example = await get_translation_and_example(
            text, user_settings[str(user_id)]["phrase_source"],
            translate_phrase=user_settings[str(user_id)].get("translate_phrase", True)
        )
        if example:
            await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅\n\n📘 Пример:\n{example}")
        else:
            await update.message.reply_text(f"Слово '{text}' добавлено, но перевод не получен 😕")
    else:
        await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅")

# ---------------- АВТОРАССЫЛКА ----------------
async def send_daily_messages(app):
    for user_id, settings in user_settings.items():
        if settings.get("state") != "active":
            continue
        words = user_words.get(str(user_id), [])[:settings.get("words_per_batch", 1)]
        for word in words:
            example = await get_translation_and_example(
                word,
                settings.get("phrase_source", "Любая тема"),
                translate_phrase=settings.get("translate_phrase", True)
            )
            if example:
                try:
                    await app.bot.send_message(chat_id=int(user_id), text=f"📚 {word}\n\n{example}")
                except:
                    pass

# ---------------- START / MENU ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_setup(update.effective_user.id, context, greet=True)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_setup(update.effective_user.id, context, greet=False)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_messages, "interval", hours=6, args=[app])
    scheduler.start()

    logging.info("🚀 Бот запущен")
    app.run_polling()
