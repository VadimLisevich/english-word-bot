import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import os
import openai

# Загрузка переменных окружения
load_dotenv('.env.example')
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Настройка логирования
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)

# Память пользователей
user_settings = {}
user_words = {}

# Создание планировщика
scheduler = AsyncIOScheduler()

# Категории фраз
CATEGORIES = ['Афоризмы', 'Цитаты', 'Кино', 'Песни', 'Любая тема']

async def translate_word(word: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Переведи слово '{word}' с английского на русский одним словом."
            }]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

async def generate_example(word: str, category: str) -> tuple[str, str, str]:
    try:
        prompt = f"Придумай короткую фразу на английском с использованием слова '{word}' в контексте категории '{category}'. Укажи также источник, например, название фильма или песни. Ответ в формате: Фраза на английском. Источник. Перевод."
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        parts = response.choices[0].message.content.strip().split('\n')
        english, source, translation = parts[0], parts[1], parts[2]
        return english.strip(), source.strip(), translation.strip()
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "⚠️ Ошибка генерации примера.", "", ""

# === Команды ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {}
    await ask_translate_words(update)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {}
    await ask_translate_words(update)

# === Вопросы по настройке ===

async def ask_translate_words(update: Update):
    keyboard = [[InlineKeyboardButton("Да", callback_data='translate_words_yes'),
                 InlineKeyboardButton("Нет", callback_data='translate_words_no')]]
    await update.message.reply_text("Нужен перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_frequency(context, user_id):
    keyboard = [[InlineKeyboardButton("1", callback_data='frequency_1'),
                 InlineKeyboardButton("2", callback_data='frequency_2'),
                 InlineKeyboardButton("3", callback_data='frequency_3')]]
    await context.bot.send_message(chat_id=user_id, text="Как часто ты хочешь, чтобы я писал тебе?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_words_per_message(context, user_id):
    keyboard = [[InlineKeyboardButton(str(n), callback_data=f'words_{n}')] for n in [1, 2, 3, 5]]
    await context.bot.send_message(chat_id=user_id, text="Сколько слов присылать за один раз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_category(context, user_id):
    keyboard = [[InlineKeyboardButton(cat, callback_data=f'category_{cat}')] for cat in CATEGORIES]
    await context.bot.send_message(chat_id=user_id, text="Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_translate_phrases(context, user_id):
    keyboard = [[InlineKeyboardButton("Да", callback_data='translate_phrases_yes'),
                 InlineKeyboardButton("Нет", callback_data='translate_phrases_no')]]
    await context.bot.send_message(chat_id=user_id, text="Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

# === Обработка кнопок ===

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("translate_words"):
        user_settings[user_id]["translate_words"] = data.endswith("yes")
        await ask_frequency(context, user_id)
    elif data.startswith("frequency"):
        user_settings[user_id]["frequency"] = int(data.split('_')[1])
        await ask_words_per_message(context, user_id)
    elif data.startswith("words_"):
        user_settings[user_id]["words_per_message"] = int(data.split('_')[1])
        await ask_category(context, user_id)
    elif data.startswith("category_"):
        user_settings[user_id]["category"] = data.split('_')[1]
        await ask_translate_phrases(context, user_id)
    elif data.startswith("translate_phrases"):
        user_settings[user_id]["translate_phrases"] = data.endswith("yes")
        await context.bot.send_message(chat_id=user_id, text="Настройка завершена ✅\n\nЕсли хочешь изменить — напиши /menu")
        schedule_user_reminders(user_id, context)

# === Обработка новых слов ===

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    if user_id not in user_settings:
        await update.message.reply_text("Сначала используй /start для настройки бота.")
        return

    user_words.setdefault(user_id, set()).add(word)

    translate = await translate_word(word)
    category = user_settings[user_id].get("category", "Любая тема")
    eng_phrase, source, ru_phrase = await generate_example(word, category)

    response = f"Слово '{word}' (перевод: {translate}) – добавлено в базу ✅\n\n📘 Пример:\n{eng_phrase}\n{ru_phrase} Источник: {source}."
    await update.message.reply_text(response)

# === Планировщик ===

def schedule_user_reminders(user_id, context):
    scheduler.remove_all_jobs(jobstore=None)

    times = []
    match user_settings[user_id]["frequency"]:
        case 1: times = ["11:00"]
        case 2: times = ["11:00", "15:00"]
        case 3: times = ["11:00", "15:00", "19:00"]

    for time in times:
        hour, minute = map(int, time.split(":"))
        scheduler.add_job(
            send_reminders,
            trigger=CronTrigger(hour=hour, minute=minute),
            args=[context, user_id],
            id=f"reminder_{user_id}_{hour}"
        )

async def send_reminders(context, user_id):
    words = list(user_words.get(user_id, []))
    if not words:
        return

    count = user_settings[user_id].get("words_per_message", 1)
    selected = random.sample(words, min(count, len(words)))

    for word in selected:
        translate = await translate_word(word)
        category = user_settings[user_id].get("category", "Любая тема")
        eng_phrase, source, ru_phrase = await generate_example(word, category)
        text = f"🕒 Напоминание!\n\nСлово: {word}\nПеревод: {translate}\n\n📘 Пример:\n{eng_phrase}\n{ru_phrase} Источник: {source}"
        await context.bot.send_message(chat_id=user_id, text=text)

# === Главный запуск ===

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler.start()
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
