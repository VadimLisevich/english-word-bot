import os
import json
import logging
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

WORDS_FILE = "user_words.json"
SETTINGS_FILE = "user_settings.json"

scheduler = AsyncIOScheduler()
scheduler.start()

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

user_words = load_json(WORDS_FILE)
user_settings = load_json(SETTINGS_FILE)

async def send_message(user_id, text, reply_markup=None):
    try:
        await application.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения {user_id}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {}
    save_json(SETTINGS_FILE, user_settings)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Привет! Этот бот помогает учить английские слова через фразы. "
            "Тебе нужно просто писать сюда слова, которые ты никак не можешь запомнить, "
            "а я буду тебе в течение дня давать примеры фраз с использованием этих слов.\n\n"
            "Окей, давай настроим бота!"
        )
    )
    await ask_translation_preference(update)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {}
    save_json(SETTINGS_FILE, user_settings)
    await ask_translation_preference(update)

async def ask_translation_preference(update: Update):
    keyboard = [
        [InlineKeyboardButton("Без перевода", callback_data="translate_no")],
        [InlineKeyboardButton("Нужен перевод", callback_data="translate_yes")]
    ]
    await update.effective_chat.send_message(
        "Нужен ли тебе перевод слова или ты просто хочешь добавлять его в базу?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_frequency(update: Update):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="frequency_1")],
        [InlineKeyboardButton("2", callback_data="frequency_2")],
        [InlineKeyboardButton("3", callback_data="frequency_3")]
    ]
    await update.effective_chat.send_message(
        "Как часто ты хочешь, чтобы я писал тебе?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_word_count(update: Update):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="wordcount_1")],
        [InlineKeyboardButton("2", callback_data="wordcount_2")],
        [InlineKeyboardButton("3", callback_data="wordcount_3")],
        [InlineKeyboardButton("5", callback_data="wordcount_5")]
    ]
    await update.effective_chat.send_message(
        "Отлично! А сколько слов за один раз ты хочешь повторять?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_source_category(update: Update):
    keyboard = [
        [InlineKeyboardButton("Афоризм", callback_data="source_aphorism")],
        [InlineKeyboardButton("Цитата", callback_data="source_quote")],
        [InlineKeyboardButton("Кино", callback_data="source_movie")],
        [InlineKeyboardButton("Песни", callback_data="source_song")],
        [InlineKeyboardButton("Любая тема", callback_data="source_any")]
    ]
    await update.effective_chat.send_message(
        "Окей, а откуда лучше брать примеры фраз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_translation_for_phrase(update: Update):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="phrase_translate_yes")],
        [InlineKeyboardButton("Нет", callback_data="phrase_translate_no")]
    ]
    await update.effective_chat.send_message(
        "Перевод для фраз нужен?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finish_settings(update: Update):
    await update.effective_chat.send_message(
        "🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu"
    )

def update_user_setting(user_id, key, value):
    user_settings[user_id][key] = value
    save_json(SETTINGS_FILE, user_settings)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    await query.answer()

    if data.startswith("translate_"):
        update_user_setting(user_id, "word_translation", data.endswith("yes"))
        await ask_frequency(update)
    elif data.startswith("frequency_"):
        update_user_setting(user_id, "frequency", int(data.split("_")[1]))
        await ask_word_count(update)
    elif data.startswith("wordcount_"):
        update_user_setting(user_id, "word_count", int(data.split("_")[1]))
        await ask_source_category(update)
    elif data.startswith("source_"):
        update_user_setting(user_id, "source", data.split("_")[1])
        await ask_translation_for_phrase(update)
    elif data.startswith("phrase_translate_"):
        update_user_setting(user_id, "phrase_translation", data.endswith("yes"))
        await finish_settings(update)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.strip()
    if user_id not in user_settings or not user_settings[user_id]:
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    user_words.setdefault(user_id, [])
    if word not in user_words[user_id]:
        user_words[user_id].append(word)
        save_json(WORDS_FILE, user_words)

        translated = ""
        if user_settings[user_id].get("word_translation"):
            try:
                res = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": f"Translate the English word '{word}' to Russian."}],
                    temperature=0.5
                )
                translated = res.choices[0].message.content.strip()
            except Exception as e:
                logging.warning(f"Ошибка перевода: {e}")
        if translated:
            await update.message.reply_text(f"Слово '{word}' (перевод: {translated}) – добавлено в базу ✅")
        else:
            await update.message.reply_text(f"Слово '{word}' добавлено в базу ✅")
    else:
        await update.message.reply_text(f"Слово '{word}' уже есть в базе")

async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Укажи слово, которое хочешь удалить. Пример: /delete hello")
        return
    word = args[0]
    if word in user_words.get(user_id, []):
        user_words[user_id].remove(word)
        save_json(WORDS_FILE, user_words)
        await update.message.reply_text(f"Слово '{word}' удалено из базы 🗑️")
    else:
        await update.message.reply_text(f"Слово '{word}' не найдено в базе.")

async def send_reminders():
    for user_id, words in user_words.items():
        settings = user_settings.get(user_id)
        if not settings:
            continue

        count = settings.get("word_count", 1)
        selected_words = random.sample(words, min(count, len(words)))
        for word in selected_words:
            source = settings.get("source", "any")
            try:
                prompt = f"Give me a {source} sentence using the English word '{word}'"
                if settings.get("phrase_translation"):
                    prompt += " and translate it to Russian"
                prompt += f". Also mention the source (e.g. Book, Movie: Inception, Song: Imagine)."

                res = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                content = res.choices[0].message.content.strip()
                await send_message(user_id, f"📘 Пример:\n{content}")
            except Exception as e:
                logging.warning(f"Ошибка при генерации фразы: {e}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application = app

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("delete", delete_word))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

# Рассылка каждые 8 часов
scheduler.add_job(send_reminders, "interval", hours=8)

if __name__ == "__main__":
    logging.info("🚀 Бот запущен")
    app.run_polling()
