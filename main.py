import os
import logging
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

user_data = {}
word_database = {}

scheduler = AsyncIOScheduler()

def translate_word(word: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Translate the English word '{word}' to Russian."
            }],
            max_tokens=20,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation error for '{word}': {e}")
        return "ошибка перевода"

def generate_example(word: str, category: str) -> tuple[str, str, str]:
    try:
        prompt = (
            f"Generate a short sentence using the word '{word}' from the category '{category.lower()}' "
            f"and specify the exact source title (like a movie name, book, etc). Also give a Russian translation. "
            f"Return it in the format: sentence | source | translation"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{ "role": "user", "content": prompt }],
            max_tokens=80,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        sentence, source, translation = map(str.strip, text.split("|"))
        return sentence, source, translation
    except Exception as e:
        logging.error(f"Error generating example for word '{word}': {e}")
        return "⚠️ Ошибка генерации примера.", "", ""

def schedule_reminders(user_id: int):
    scheduler.remove_all_jobs(jobstore=str(user_id))
    times = user_data[user_id].get("frequency", 1)
    hours = [11, 15, 19][:times]
    for hour in hours:
        scheduler.add_job(
            send_reminder,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[user_id],
            id=f"{user_id}_{hour}",
            jobstore=str(user_id),
            replace_existing=True,
        )

async def send_reminder(user_id: int):
    if user_id not in word_database or not word_database[user_id]:
        return
    word = random.choice(list(word_database[user_id].keys()))
    category = user_data.get(user_id, {}).get("category", "Кино")
    translation = word_database[user_id][word]["translation"]
    sentence, source, ru = generate_example(word, category)
    message = (
        f"📚 Слово: *{word}* (перевод: {translation})\n\n"
        f"📘 Пример:\n{sentence}\nПеревод: {ru}\nИсточник: {source}"
    )
    try:
        await application.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Failed to send reminder: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"step": "translate", "frequency": 1, "category": "Кино"}
    word_database[user_id] = {}
    await update.message.reply_text("Привет! Я помогу тебе учить английские слова. Хочешь перевод слов?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="translate_yes"), InlineKeyboardButton("Нет", callback_data="translate_no")]
    ]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    category = user_data.get(user_id, {}).get("category", "Кино")
    translation = translate_word(word)
    sentence, source, ru = generate_example(word, category)

    word_database.setdefault(user_id, {})[word] = {
        "translation": translation,
        "category": category,
    }

    text = (
        f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
        f"📘 Пример:\n{sentence}\nПеревод: {ru}\nИсточник: {source}"
    )
    await update.message.reply_text(text)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("translate_"):
        user_data[user_id]["step"] = "frequency"
        await context.bot.send_message(chat_id=user_id, text="Как часто присылать слова?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 раз", callback_data="freq_1")],
            [InlineKeyboardButton("2 раза", callback_data="freq_2")],
            [InlineKeyboardButton("3 раза", callback_data="freq_3")]
        ]))
    elif data.startswith("freq_"):
        freq = int(data.split("_")[1])
        user_data[user_id]["frequency"] = freq
        user_data[user_id]["step"] = "category"
        await context.bot.send_message(chat_id=user_id, text="Выбери тему фраз:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Кино", callback_data="cat_Кино")],
            [InlineKeyboardButton("Песни", callback_data="cat_Песни")],
            [InlineKeyboardButton("Книги", callback_data="cat_Книги")],
            [InlineKeyboardButton("Бизнес", callback_data="cat_Бизнес")],
        ]))
    elif data.startswith("cat_"):
        category = data.split("_")[1]
        user_data[user_id]["category"] = category
        await context.bot.send_message(chat_id=user_id, text="Настройка завершена. Можешь прислать слово.")

        # Запустить рассылку
        schedule_reminders(user_id)

application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

scheduler.start()

if __name__ == "__main__":
    application.run_polling()
