import logging
import os
import json
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          ContextTypes, filters, ConversationHandler)
from openai import OpenAI

# Константы этапов настройки
(STATE_TRANSLATE_WORDS, STATE_SEND_TIMES, STATE_WORDS_AT_ONCE,
 STATE_PHRASE_SOURCE, STATE_TRANSLATE_PHRASES) = range(5)

# Папка и файлы
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "user_words.json"

# Ключи из Render (не забудь задать их в Environment)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Загрузка или создание словарей
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({}, f)
if not os.path.exists(WORDS_FILE):
    with open(WORDS_FILE, "w") as f:
        json.dump({}, f)

def load_data(filename):
    with open(filename, "r") as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# === Команды ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"⚙️ Пользователь {user_id} начал настройку через /start")
    await update.message.reply_text(
        "Привет! Этот бот помогает учить английские слова через фразы. "
        "Просто пиши сюда слова, которые ты не можешь запомнить, а я буду напоминать их в течение дня через примеры.\n\n"
        "Окей, давай настроим бота!"
    )
    await update.message.reply_text(
        "Нужен ли тебе перевод слова или просто хочешь добавлять их в базу?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("нужен перевод")], [KeyboardButton("без перевода")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_TRANSLATE_WORDS

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"⚙️ Пользователь {user_id} начал настройку через /menu")
    await update.message.reply_text(
        "Настроим параметры заново.\nНужен ли тебе перевод слова?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("нужен перевод")], [KeyboardButton("без перевода")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_TRANSLATE_WORDS

async def set_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = load_data(SETTINGS_FILE)
    settings[user_id] = settings.get(user_id, {})
    settings[user_id]["translate_words"] = (update.message.text == "нужен перевод")
    save_data(SETTINGS_FILE, settings)

    await update.message.reply_text(
        "Как часто тебе писать?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_SEND_TIMES

async def set_send_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = load_data(SETTINGS_FILE)
    settings[user_id]["send_times"] = int(update.message.text)
    save_data(SETTINGS_FILE, settings)

    await update.message.reply_text(
        "Сколько слов повторять за один раз?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")], [KeyboardButton("5")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_WORDS_AT_ONCE

async def set_words_at_once(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = load_data(SETTINGS_FILE)
    settings[user_id]["words_at_once"] = int(update.message.text)
    save_data(SETTINGS_FILE, settings)

    await update.message.reply_text(
        "Откуда брать примеры фраз?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("афоризм")], [KeyboardButton("цитата")], [KeyboardButton("кино")],
             [KeyboardButton("песни")], [KeyboardButton("любая тема")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_PHRASE_SOURCE

async def set_phrase_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = load_data(SETTINGS_FILE)
    settings[user_id]["phrase_source"] = update.message.text
    save_data(SETTINGS_FILE, settings)

    await update.message.reply_text(
        "Перевод для фраз нужен?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("да")], [KeyboardButton("нет")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return STATE_TRANSLATE_PHRASES

async def set_translate_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = load_data(SETTINGS_FILE)
    settings[user_id]["translate_phrases"] = (update.message.text == "да")
    save_data(SETTINGS_FILE, settings)

    await update.message.reply_text(
        "🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu",
        reply_markup=None
    )
    return ConversationHandler.END

# === Основная логика добавления слов ===

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()

    if text.startswith("/delete"):
        word_to_delete = text.split("/delete")[-1].strip()
        words = load_data(WORDS_FILE)
        if word_to_delete in words.get(user_id, []):
            words[user_id].remove(word_to_delete)
            save_data(WORDS_FILE, words)
            await update.message.reply_text(f"Слово '{word_to_delete}' удалено из базы ❌")
        else:
            await update.message.reply_text(f"Слово '{word_to_delete}' не найдено в базе.")
        return

    settings = load_data(SETTINGS_FILE)
    if user_id not in settings:
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    translate = settings[user_id].get("translate_words", False)
    words = load_data(WORDS_FILE)
    words.setdefault(user_id, [])
    if text not in words[user_id]:
        words[user_id].append(text)
        save_data(WORDS_FILE, words)

    if translate:
        try:
            await update.message.reply_text("⏳ Думаю...")
            prompt = f"What does the word '{text}' mean in Russian? Give one phrase as an example of use (from {settings[user_id]['phrase_source']}) with a short explanation."
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = response.choices[0].message.content.strip()
            await update.message.reply_text(f"{reply}\n\n(добавлено в базу ✅)")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await update.message.reply_text(f"⚠️ Произошла ошибка: {e}")
    else:
        await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅")

# === Запуск ===

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("menu", menu)],
        states={
            STATE_TRANSLATE_WORDS: [MessageHandler(filters.TEXT, set_translate_words)],
            STATE_SEND_TIMES: [MessageHandler(filters.TEXT, set_send_times)],
            STATE_WORDS_AT_ONCE: [MessageHandler(filters.TEXT, set_words_at_once)],
            STATE_PHRASE_SOURCE: [MessageHandler(filters.TEXT, set_phrase_source)],
            STATE_TRANSLATE_PHRASES: [MessageHandler(filters.TEXT, set_translate_phrases)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Бот запущен")
    app.run_polling()
