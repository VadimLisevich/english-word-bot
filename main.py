import os
import json
import logging
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import OpenAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Файлы
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "user_words.json"
PHRASES_FILE = "phrases.json"

# Настройки логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Тематики
CATEGORIES = {
    "афоризм": "Афоризм",
    "цитата": "Цитата",
    "кино": "Кино",
    "Песни": "Песни",
    "любая тема": "Любая тема"
}

# Загрузка данных
def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


# Стартовая настройка
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data["settings_step"] = 0
    settings = load_json(SETTINGS_FILE)
    settings[user_id] = {}
    save_json(SETTINGS_FILE, settings)
    await update.message.reply_text(
        "Привет! Этот бот помогает учить английские слова через фразы. "
        "Тебе нужно просто писать сюда слова, которые ты никак не можешь запомнить, "
        "а я буду тебе в течение дня давать примеры фраз с использованием этих слов.\n\n"
        "Окей, давай настроим бота!"
    )
    await ask_translate_words(update)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data["settings_step"] = 0
    settings = load_json(SETTINGS_FILE)
    settings[user_id] = {}
    save_json(SETTINGS_FILE, settings)
    await ask_translate_words(update)


# Шаг 1
async def ask_translate_words(update: Update):
    keyboard = [
        [InlineKeyboardButton("Без перевода", callback_data="translate_words_no")],
        [InlineKeyboardButton("Нужен перевод", callback_data="translate_words_yes")],
    ]
    await update.message.reply_text("Нужен ли тебе перевод слова или просто хочешь добавлять его в базу?",
                                    reply_markup=InlineKeyboardMarkup(keyboard))


# Шаг 2–6
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    settings = load_json(SETTINGS_FILE)

    data = query.data

    if data.startswith("translate_words_"):
        settings[user_id]["translate_words"] = data.endswith("yes")
        await query.message.reply_text("Как часто ты хочешь, чтобы я писал тебе?",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("1", callback_data="frequency_1")],
                                           [InlineKeyboardButton("2", callback_data="frequency_2")],
                                           [InlineKeyboardButton("3", callback_data="frequency_3")]
                                       ]))

    elif data.startswith("frequency_"):
        settings[user_id]["frequency"] = int(data.split("_")[1])
        await query.message.reply_text("Отлично! А сколько слов за один раз ты хочешь повторять?",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("1", callback_data="count_1")],
                                           [InlineKeyboardButton("2", callback_data="count_2")],
                                           [InlineKeyboardButton("3", callback_data="count_3")],
                                           [InlineKeyboardButton("5", callback_data="count_5")]
                                       ]))

    elif data.startswith("count_"):
        settings[user_id]["count"] = int(data.split("_")[1])
        await query.message.reply_text("Окей, а откуда лучше брать примеры фраз?",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("Афоризм", callback_data="source_афоризм")],
                                           [InlineKeyboardButton("Цитата", callback_data="source_цитата")],
                                           [InlineKeyboardButton("Кино", callback_data="source_кино")],
                                           [InlineKeyboardButton("Песни", callback_data="source_Песни")],
                                           [InlineKeyboardButton("Любая тема", callback_data="source_любая тема")]
                                       ]))

    elif data.startswith("source_"):
        settings[user_id]["source"] = data.split("_")[1]
        await query.message.reply_text("Перевод для фраз нужен?",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("Да", callback_data="translate_phrase_yes")],
                                           [InlineKeyboardButton("Нет", callback_data="translate_phrase_no")]
                                       ]))

    elif data.startswith("translate_phrase_"):
        settings[user_id]["translate_phrase"] = data.endswith("yes")
        save_json(SETTINGS_FILE, settings)
        await query.message.reply_text(
            "🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu"
        )

    save_json(SETTINGS_FILE, settings)


# Обработка слов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    settings = load_json(SETTINGS_FILE)
    words = load_json(WORDS_FILE)

    if user_id not in settings or "translate_words" not in settings[user_id]:
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    text = update.message.text.strip().lower()

    if text.startswith("/delete "):
        word_to_delete = text[8:].strip().lower()
        if user_id in words and word_to_delete in words[user_id]:
            words[user_id].remove(word_to_delete)
            save_json(WORDS_FILE, words)
            await update.message.reply_text(f"Слово '{word_to_delete}' удалено из базы 🗑️")
        else:
            await update.message.reply_text(f"Слово '{word_to_delete}' не найдено в базе.")
        return

    words.setdefault(user_id, [])
    if text not in words[user_id]:
        words[user_id].append(text)
        save_json(WORDS_FILE, words)

        if settings[user_id].get("translate_words"):
            try:
                translation = get_translation(text)
                await update.message.reply_text(f"Слово '{text}' (перевод: {translation}) – добавлено в базу ✅")
            except Exception:
                await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅ (перевод не получен)")
        else:
            await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅")
    else:
        await update.message.reply_text(f"Слово '{text}' уже в базе 👌")


# Получение перевода
def get_translation(word):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": f"Переведи слово '{word}' на русский одним словом."
        }],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


# Фразы
def load_phrases_by_category(category):
    phrases = load_json(PHRASES_FILE)
    if category == "любая тема":
        all_phrases = []
        for cat_phrases in phrases.values():
            all_phrases.extend(cat_phrases)
        return all_phrases
    return phrases.get(category, [])


# Авторассылка
async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    settings = load_json(SETTINGS_FILE)
    words = load_json(WORDS_FILE)

    for user_id, config in settings.items():
        user_words = words.get(user_id, [])
        if not user_words:
            continue

        count = config.get("count", 1)
        selected_words = random.sample(user_words, min(count, len(user_words)))
        source = config.get("source", "любая тема")
        phrases = load_phrases_by_category(source)
        random.shuffle(phrases)

        for word in selected_words:
            phrase_obj = next((p for p in phrases if word.lower() in p["text"].lower()), None)
            if phrase_obj:
                reply = f"📘 Пример:\n\"{phrase_obj['text']}\" Source: {CATEGORIES.get(source, 'Фраза')}.\n"
                if config.get("translate_phrase") and "translation" in phrase_obj:
                    reply += f"\n\"{phrase_obj['translation']}\" Источник: {CATEGORIES.get(source, 'Фраза')}."
                try:
                    await context.bot.send_message(chat_id=int(user_id), text=reply)
                except Exception as e:
                    logging.error(f"❌ Не удалось отправить сообщение {user_id}: {e}")


# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, "interval", hours=8)
    scheduler.start()

    logging.info("🚀 Бот запущен")
    app.run_polling()
