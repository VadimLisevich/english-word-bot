import logging
import os
import random
from datetime import datetime, time
from pytz import timezone

import openai
import nest_asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO
)

# Инициализация API ключей
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Память
user_data = {}

# Фразы по категориям
EXAMPLES = {
    "Афоризмы": [
        ("Patience is bitter, but its fruit is sweet.", "Аристотель"),
        ("Knowing yourself is the beginning of all wisdom.", "Аристотель"),
    ],
    "Цитаты": [
        ("Be yourself; everyone else is already taken.", "Оскар Уайльд"),
        ("To live is the rarest thing in the world. Most people exist, that is all.", "Оскар Уайльд"),
    ],
    "Кино": [
        ("May the Force be with you.", "Звёздные войны"),
        ("I'll be back.", "Терминатор"),
    ],
    "Песни": [
        ("All you need is love.", "The Beatles"),
        ("We don't need no education.", "Pink Floyd"),
    ],
    "Любая тема": [
        ("Keep moving forward.", "Walt Disney"),
        ("The only limit to our realization of tomorrow is our doubts of today.", "Franklin D. Roosevelt"),
    ]
}

# Вспомогательные функции
def get_user_settings(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "translate_words": None,
            "times_per_day": None,
            "words_per_batch": None,
            "phrase_source": None,
            "translate_phrases": None,
            "words": []
        }
    return user_data[user_id]

def get_example(word, category):
    try:
        prompt = f"Provide an example sentence with the English word '{word}' from the category '{category}'. Then give a source title (movie, song, etc)."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return None

def translate_word(word):
    try:
        prompt = f"Translate the English word '{word}' into Russian. Only return the translation without explanations."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "translate_words": None,
        "times_per_day": None,
        "words_per_batch": None,
        "phrase_source": None,
        "translate_phrases": None,
        "words": []
    }
    await update.message.reply_text("Привет! Я помогу тебе выучить английские слова. Давай настроим бота 🛠")
    await ask_translate_words(update, context)

async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await update.message.reply_text("Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

# Обработка ответов
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    settings = get_user_settings(user_id)

    data = query.data
    if data.startswith("translate_words"):
        settings["translate_words"] = data.endswith("yes")
        keyboard = [
            [InlineKeyboardButton("1 раз в день", callback_data="times_1")],
            [InlineKeyboardButton("2 раза в день", callback_data="times_2")],
            [InlineKeyboardButton("3 раза в день", callback_data="times_3")]
        ]
        await query.message.reply_text("Как часто ты хочешь чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("times_"):
        settings["times_per_day"] = int(data.split("_")[1])
        keyboard = [
            [InlineKeyboardButton("1 слово", callback_data="batch_1")],
            [InlineKeyboardButton("2 слова", callback_data="batch_2")],
            [InlineKeyboardButton("3 слова", callback_data="batch_3")],
            [InlineKeyboardButton("5 слов", callback_data="batch_5")]
        ]
        await query.message.reply_text("Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("batch_"):
        settings["words_per_batch"] = int(data.split("_")[1])
        keyboard = [
            [InlineKeyboardButton("Афоризмы", callback_data="source_Афоризмы")],
            [InlineKeyboardButton("Цитаты", callback_data="source_Цитаты")],
            [InlineKeyboardButton("Кино", callback_data="source_Кино")],
            [InlineKeyboardButton("Песни", callback_data="source_Песни")],
            [InlineKeyboardButton("Любая тема", callback_data="source_Любая тема")]
        ]
        await query.message.reply_text("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("source_"):
        settings["phrase_source"] = data.split("_", 1)[1]
        keyboard = [
            [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
            [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
        ]
        await query.message.reply_text("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("translate_phrases"):
        settings["translate_phrases"] = data.endswith("yes")
        await query.message.reply_text("✅ Настройка завершена! Используй команду /menu, чтобы изменить настройки.")
        logging.info(f"Settings for {user_id}: {settings}")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_translate_words(update, context)

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    word = update.message.text.strip()
    settings["words"].append(word)

    translation = translate_word(word) if settings["translate_words"] else "Перевод отключён"
    example = get_example(word, settings["phrase_source"] or "Любая тема")

    response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅"
    if example:
        response += f"\n\n💬 Пример фразы:\n{example}"
    await update.message.reply_text(response)

async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    word = update.message.text.replace("/delete", "").strip()
    if word in settings["words"]:
        settings["words"].remove(word)
        await update.message.reply_text(f"Слово '{word}' удалено из базы ❌")
    else:
        await update.message.reply_text("Такого слова нет в базе.")

# Авторассылка
async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    for user_id, settings in user_data.items():
        if not settings["words"]:
            continue
        words_to_send = random.sample(settings["words"], min(settings["words_per_batch"], len(settings["words"])))
        for word in words_to_send:
            translation = translate_word(word) if settings["translate_words"] else "Перевод отключён"
            example = get_example(word, settings["phrase_source"] or "Любая тема")
            text = f"🧠 Слово: {word}\nПеревод: {translation}"
            if example:
                text += f"\n\n💬 Пример:\n{example}"
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except Exception as e:
                logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

# Планировщик
scheduler = AsyncIOScheduler(timezone=timezone("Europe/Lisbon"))
scheduler.add_job(send_reminders, CronTrigger(hour=11, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=15, minute=0))
scheduler.add_job(send_reminders, CronTrigger(hour=19, minute=0))
scheduler.start()

# Запуск
nest_asyncio.apply()

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("delete", delete_word))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_word))
    await app.run_polling()

import asyncio
asyncio.run(main())
