import logging
import os
import json
import random
import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# Файлы
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "user_words.json"

# Категории
CATEGORIES = ["Афоризмы", "Цитаты", "Кино", "Песни", "Любая тема"]

# Загрузка / сохранение
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

user_settings = load_json(SETTINGS_FILE)
user_words = load_json(WORDS_FILE)

# Словарь времён рассылки
REMINDER_TIMES = {1: [11], 2: [11, 15], 3: [11, 15, 19]}
scheduler = BackgroundScheduler()
scheduler.start()

# Начало / меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Привет! Я помогу тебе учить английские слова 📚\n\nДавай сначала настроимся.")
    await ask_translate_words(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Настроим всё заново 🛠️")
    await ask_translate_words(update, context)

# Настройки (вопросы)
async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(buttons))

async def ask_times_per_day(user_id, context):
    buttons = [[InlineKeyboardButton(str(n), callback_data=f"times_per_day_{n}")] for n in [1, 2, 3]]
    await context.bot.send_message(chat_id=user_id, text="Как часто отправлять фразы?", reply_markup=InlineKeyboardMarkup(buttons))

async def ask_words_count(user_id, context):
    buttons = [[InlineKeyboardButton(str(n), callback_data=f"words_count_{n}")] for n in [1, 2, 3, 5]]
    await context.bot.send_message(chat_id=user_id, text="Сколько слов за раз?", reply_markup=InlineKeyboardMarkup(buttons))

async def ask_category(user_id, context):
    buttons = [[InlineKeyboardButton(cat, callback_data=f"category_{cat}")] for cat in CATEGORIES]
    await context.bot.send_message(chat_id=user_id, text="Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(buttons))

async def ask_translate_phrases(user_id, context):
    buttons = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
    ]
    await context.bot.send_message(chat_id=user_id, text="Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(buttons))

async def complete_setup(user_id, context):
    await context.bot.send_message(chat_id=user_id, text="🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu")

# Обработка кнопок
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if user_id not in user_settings:
        user_settings[user_id] = {}

    data = query.data

    if data.startswith("translate_words_"):
        user_settings[user_id]["translate_words"] = data.endswith("yes")
        await ask_times_per_day(user_id, context)

    elif data.startswith("times_per_day_"):
        times = int(data.split("_")[-1])
        user_settings[user_id]["times_per_day"] = times
        await ask_words_count(user_id, context)

    elif data.startswith("words_count_"):
        count = int(data.split("_")[-1])
        user_settings[user_id]["words_count"] = count
        await ask_category(user_id, context)

    elif data.startswith("category_"):
        cat = data.split("_", 1)[-1]
        user_settings[user_id]["category"] = cat
        await ask_translate_phrases(user_id, context)

    elif data.startswith("translate_phrases_"):
        user_settings[user_id]["translate_phrases"] = data.endswith("yes")
        save_json(SETTINGS_FILE, user_settings)
        schedule_user_reminders(user_id, context)
        await complete_setup(user_id, context)

# Перевод слова
def translate_word(word):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Переведи слово '{word}' на русский одним словом."}],
            max_tokens=20
        )
        return res.choices[0].message["content"].strip()
    except Exception:
        return "ошибка перевода"

# Получение фразы
def generate_example(word, category, translate):
    prompt = f"""Придумай короткую фразу (на английском) со словом "{word}" в контексте категории "{category}". 
Укажи источник (конкретное название песни, фильма и т.д.), и переведи фразу на русский, если требуется."""
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return res.choices[0].message["content"].strip()
    except Exception:
        return "⚠️ Ошибка генерации примера."

# Обработка слов
async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.strip()

    if user_id not in user_settings:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Напиши /start или /menu для настройки 😊")
        return

    translate = translate_word(word) if user_settings[user_id].get("translate_words") else "без перевода"
    if user_id not in user_words:
        user_words[user_id] = []

    user_words[user_id].append(word)
    save_json(WORDS_FILE, user_words)

    msg = f"Слово '{word}' (перевод: {translate}) – добавлено в базу ✅"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    category = user_settings[user_id].get("category", "Любая тема")
    need_translation = user_settings[user_id].get("translate_phrases", True)
    example = generate_example(word, category, need_translation)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📘 Пример:\n{example}")

# Удаление слова
async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.replace("/delete ", "").strip().lower()
    if word in user_words.get(user_id, []):
        user_words[user_id].remove(word)
        save_json(WORDS_FILE, user_words)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Слово '{word}' удалено из базы ❌")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Слово '{word}' не найдено в базе")

# Рассылка
async def send_reminders():
    now = datetime.datetime.now().hour
    for user_id, settings in user_settings.items():
        times = REMINDER_TIMES.get(settings.get("times_per_day", 1), [11])
        if now in times:
            count = settings.get("words_count", 1)
            words = random.sample(user_words.get(user_id, []), min(count, len(user_words.get(user_id, []))))
            for word in words:
                translate = translate_word(word) if settings.get("translate_words") else "без перевода"
                msg = f"🧠 Слово дня: '{word}' (перевод: {translate})"
                await send_message(int(user_id), msg, context=None)
                example = generate_example(word, settings.get("category", "Любая тема"), settings.get("translate_phrases", True))
                await send_message(int(user_id), f"📘 Пример:\n{example}", context=None)

async def send_message(user_id, text, context):
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    await app.bot.send_message(chat_id=user_id, text=text)

def schedule_user_reminders(user_id, context):
    for h in [11, 15, 19]:
        scheduler.add_job(send_reminders, CronTrigger(hour=h, minute=0))

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("delete", delete_word))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_word))
    scheduler.add_job(send_reminders, CronTrigger(minute=0))
    app.run_polling()
