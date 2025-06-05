import logging
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Логирование
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# База пользователей
USERS_FILE = "users.json"
user_settings = {}

# Категории
CATEGORIES = ["Афоризмы", "Цитаты", "Кино", "Песни", "Любая тема"]

# Планировщик
scheduler = AsyncIOScheduler()

# Загрузка пользовательских данных
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Сохранение пользовательских данных
def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_settings, f, ensure_ascii=False, indent=2)

# Функции рассылки
async def send_reminders():
    now = datetime.now().strftime("%H:%M")
    for user_id, settings in user_settings.items():
        times = {
            "1": ["11:00"],
            "2": ["11:00", "15:00"],
            "3": ["11:00", "15:00", "19:00"],
        }.get(settings.get("frequency"), [])

        if now in times:
            count = int(settings.get("words_per_day", 1))
            for _ in range(count):
                await send_example(user_id)

async def send_example(user_id):
    words = user_settings[user_id].get("words", [])
    if not words:
        return
    word = words[-1]
    example, source = await generate_example(word, user_settings[user_id].get("category", "Любая тема"))
    text = f"💬 *{word}*\n📘 {example}\n🎬 {source}"
    if user_settings[user_id].get("translate_phrases") == "yes":
        translation = await translate_text(example)
        if translation:
            text += f"\n\n📖 _{translation}_"
    try:
        await app.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

# Перевод текста
async def translate_text(text):
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Переведи на русский язык."},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None

# Генерация примера
async def generate_example(word, category):
    try:
        prompt = f"Придумай короткую фразу на английском с использованием слова '{word}', из категории '{category}'. Укажи источник (например, название фильма, песни и т.п.)."
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content.strip()
        if "—" in text:
            example, source = map(str.strip, text.split("—", 1))
        else:
            example, source = text, "Unknown source"
        return example, source
    except Exception as e:
        logger.error(f"Error generating example for word '{word}': {e}")
        return "⚠️ Ошибка генерации примера", "Source: —"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = user_settings.get(user_id, {"words": []})
    save_users()
    await update.message.reply_text(
        "Привет! Я помогу тебе выучить новые английские слова.\n\nНачнём настройку:"
    )
    await ask_translate_words(update)

# Пошаговая настройка
async def ask_translate_words(update):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")],
    ]
    await update.message.reply_text(
        "Нужен перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_frequency(query):
    keyboard = [
        [InlineKeyboardButton("1 раз в день", callback_data="frequency_1")],
        [InlineKeyboardButton("2 раза в день", callback_data="frequency_2")],
        [InlineKeyboardButton("3 раза в день", callback_data="frequency_3")],
    ]
    await query.message.reply_text(
        "Как часто ты хочешь чтобы я писал тебе?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def ask_words_per_day(query):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="words_1")],
        [InlineKeyboardButton("2", callback_data="words_2")],
        [InlineKeyboardButton("3", callback_data="words_3")],
        [InlineKeyboardButton("5", callback_data="words_5")],
    ]
    await query.message.reply_text(
        "Сколько слов присылать за один раз?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def ask_category(query):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in CATEGORIES]
    await query.message.reply_text(
        "Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_translate_phrases(query):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")],
    ]
    await query.message.reply_text(
        "Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finish_setup(query):
    await query.message.reply_text("✅ Настройка завершена! Для повторной настройки используй команду /menu.")

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data.startswith("translate_words_"):
        user_settings[user_id]["translate_words"] = data.split("_")[-1]
        await ask_frequency(query)

    elif data.startswith("frequency_"):
        user_settings[user_id]["frequency"] = data.split("_")[-1]
        await ask_words_per_day(query)

    elif data.startswith("words_"):
        user_settings[user_id]["words_per_day"] = data.split("_")[-1]
        await ask_category(query)

    elif data.startswith("cat_"):
        user_settings[user_id]["category"] = data.split("_", 1)[1]
        await ask_translate_phrases(query)

    elif data.startswith("translate_phrases_"):
        user_settings[user_id]["translate_phrases"] = data.split("_")[-1]
        await finish_setup(query)

    save_users()

# Команда /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_translate_words(update)

# Обработка слов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.strip()
    user_settings[user_id]["words"].append(word)
    save_users()
    translation = await translate_text(word) if user_settings[user_id].get("translate_words") == "yes" else None
    text = f"Слово '{word}'"
    if translation:
        text += f" (перевод: {translation})"
    text += " – добавлено в базу ✅"
    await update.message.reply_text(text)
    await send_example(user_id)

# Основной запуск
async def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler.add_job(send_reminders, CronTrigger(minute="0", hour="11,15,19"))
    scheduler.start()
    logger.info("Scheduler started")

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
