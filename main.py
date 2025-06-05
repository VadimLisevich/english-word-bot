import logging
import os
import random
from datetime import time
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from uuid import uuid4
import openai

# Загрузка переменных из .env.example
load_dotenv(".env.example")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Настройка логов
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

# Память пользователей и слов
user_data = {}
word_db = {}

# Планировщик
scheduler = AsyncIOScheduler()

# Настройки авторассылки
TIME_SLOTS = {
    1: [time(11, 0)],
    2: [time(11, 0), time(15, 0)],
    3: [time(11, 0), time(15, 0), time(19, 0)],
}

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

def get_user_settings(user_id):
    return user_data.get(user_id, {
        "translate": True,
        "send_times": 1,
        "words_per_send": 1,
        "category": "Любая тема",
        "translate_phrases": True,
    })

def get_translation(word):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Переведи слово на русский: {word}"
            }],
            max_tokens=30,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка перевода '{word}': {e}")
        return "ошибка перевода"

def generate_example(word, category):
    try:
        prompt = f"""Придумай короткое предложение на английском с использованием слова "{word}", в стиле категории "{category}". Укажи также перевод фразы на русский и источник, например: фильм, песня, книга, интервью, бизнес-контекст. Ответ строго в формате:
ENGLISH: ...
RUSSIAN: ...
SOURCE: ..."""

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        content = response.choices[0].message.content
        lines = content.strip().split("\n")
        eng = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("ENGLISH:")), None)
        rus = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("RUSSIAN:")), None)
        source = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("SOURCE:")), None)

        if not all([eng, rus, source]):
            raise ValueError("Формат ответа неверный")
        return eng, rus, source
    except Exception as e:
        logging.error(f"Ошибка генерации примера для '{word}': {e}")
        return None, None, None

def schedule_user_reminders(user_id, application):
    settings = get_user_settings(user_id)
    times = TIME_SLOTS.get(settings["send_times"], [time(11, 0)])

    for t in times:
        job_id = f"{user_id}_{t.hour}"
        scheduler.add_job(
            send_reminders,
            trigger=CronTrigger(hour=t.hour, minute=t.minute),
            args=[application, user_id],
            id=job_id,
            replace_existing=True,
        )

async def send_reminders(app, user_id):
    settings = get_user_settings(user_id)
    words = word_db.get(user_id, [])
    if not words:
        return

    selected_words = random.sample(words, min(settings["words_per_send"], len(words)))
    for word in selected_words:
        translation = get_translation(word) if settings["translate"] else "перевод скрыт"
        eng, rus, source = generate_example(word, settings["category"])
        if not eng:
            text = f"⚠️ Ошибка генерации примера для слова '{word}'."
        else:
            text = (
                f"📘 Слово: *{word}* (перевод: {translation})\n\n"
                f"_Пример:_\n{eng}\n{rus}\n_Источник: {source}_"
            )
        await app.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

# ---------- ХЕНДЛЕРЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = get_user_settings(user_id)
    await context.bot.send_message(
        chat_id=user_id,
        text="Привет! Я помогу тебе учить английские слова. Давай настроим работу.",
    )
    await ask_translate_word(update, context)

async def ask_translate_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Да", callback_data="translate_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_no")],
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Нужен ли перевод слов?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data.startswith("translate_"):
        user_data[user_id]["translate"] = (data == "translate_yes")
        buttons = [
            [InlineKeyboardButton("1", callback_data="send_1")],
            [InlineKeyboardButton("2", callback_data="send_2")],
            [InlineKeyboardButton("3", callback_data="send_3")],
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Как часто ты хочешь, чтобы я писал тебе?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif data.startswith("send_"):
        user_data[user_id]["send_times"] = int(data.split("_")[1])
        buttons = [
            [InlineKeyboardButton("1", callback_data="amount_1")],
            [InlineKeyboardButton("2", callback_data="amount_2")],
            [InlineKeyboardButton("3", callback_data="amount_3")],
            [InlineKeyboardButton("5", callback_data="amount_5")],
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Сколько слов присылать за раз?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif data.startswith("amount_"):
        user_data[user_id]["words_per_send"] = int(data.split("_")[1])
        buttons = [
            [InlineKeyboardButton("Афоризмы", callback_data="category_Афоризмы")],
            [InlineKeyboardButton("Цитаты", callback_data="category_Цитаты")],
            [InlineKeyboardButton("Кино", callback_data="category_Кино")],
            [InlineKeyboardButton("Песни", callback_data="category_Песни")],
            [InlineKeyboardButton("Любая тема", callback_data="category_Любая тема")],
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Откуда брать фразы?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif data.startswith("category_"):
        user_data[user_id]["category"] = data.split("_")[1]
        buttons = [
            [InlineKeyboardButton("Да", callback_data="translate_phrase_yes")],
            [InlineKeyboardButton("Нет", callback_data="translate_phrase_no")],
        ]
        await context.bot.send_message(
            chat_id=user_id,
            text="Нужен ли перевод фраз?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif data.startswith("translate_phrase_"):
        user_data[user_id]["translate_phrases"] = (data == "translate_phrase_yes")
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Настройка завершена! Напиши любое английское слово, и я добавлю его в базу.",
        )
        schedule_user_reminders(user_id, context.application)

async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    translation = get_translation(word)
    word_db.setdefault(user_id, []).append(word)

    eng, rus, source = generate_example(word, get_user_settings(user_id)["category"])
    if eng:
        text = (
            f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
            f"📘 Пример:\n{eng}\n{rus}\nИсточник: {source}"
        )
    else:
        text = (
            f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
            "📘 Пример:\n⚠️ Ошибка генерации примера."
        )

    await context.bot.send_message(chat_id=user_id, text=text)

# ---------- ЗАПУСК ----------

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))

    logging.info("Бот запущен...")
    app.run_polling()
