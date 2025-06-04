import os
import json
import logging
import random
from datetime import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import openai

# === Загрузка переменных окружения ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Логгирование ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === Хранилища ===
USERS_FILE = "users.json"
WORDS_FILE = "words.json"
PHRASES_FILE = "phrases.json"

# === Загрузка данных ===
def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

users = load_json(USERS_FILE)
words = load_json(WORDS_FILE)
phrases = load_json(PHRASES_FILE)

# === Фразы по категориям ===
default_phrases = {
    "Песни": [
        {"sentence": "And I will always love you", "source": "Song", "translation": "И я всегда буду любить тебя"},
        {"sentence": "Let it be, let it be", "source": "Song", "translation": "Пусть будет так, пусть будет так"}
    ],
    "Кино": [
        {"sentence": "May the Force be with you", "source": "Movie", "translation": "Да пребудет с тобой сила"},
        {"sentence": "Here's looking at you, kid", "source": "Movie", "translation": "Смотрю на тебя, малыш"}
    ],
    "Книга": [
        {"sentence": "It was the best of times, it was the worst of times", "source": "Book", "translation": "Это было лучшее из времён, это было худшее из времён"}
    ],
    "Бизнес": [
        {"sentence": "We are executing our plan to expand the business", "source": "Business meeting", "translation": "Мы выполняем наш план по расширению бизнеса"}
    ]
}

# === Сохранение фразы с переводом ===
async def translate_word(word: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a translation bot. Translate to Russian."},
                {"role": "user", "content": f"Translate the word '{word}' to Russian"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "ошибка перевода"

# === Создание пользовательских кнопок ===
def build_menu(buttons):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons])

# === Хендлеры ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users[user_id] = {"step": "translate_words"}
    save_json(USERS_FILE, users)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я помогу тебе выучить английские слова 💬")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Нужен ли тебе перевод слов?", reply_markup=build_menu([("Да", "translate_yes"), ("Нет", "translate_no")]))

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users[user_id] = {"step": "translate_words"}
    save_json(USERS_FILE, users)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Начнём заново настройки. Нужен ли тебе перевод слов?", reply_markup=build_menu([("Да", "translate_yes"), ("Нет", "translate_no")]))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

    await query.answer()

    if user_id not in users:
        users[user_id] = {}

    step = users[user_id].get("step")

    if step == "translate_words":
        users[user_id]["translate_words"] = data.endswith("yes")
        users[user_id]["step"] = "daily_count"
        await query.message.reply_text("Как часто отправлять фразы?", reply_markup=build_menu([("1 раз в день", "1"), ("2 раза в день", "2"), ("3 раза в день", "3")]))
    elif step == "daily_count":
        users[user_id]["times_per_day"] = int(data[0])
        users[user_id]["step"] = "words_per_send"
        await query.message.reply_text("Сколько слов за раз?", reply_markup=build_menu([("1", "1w"), ("2", "2w"), ("3", "3w"), ("5", "5w")]))
    elif step == "words_per_send":
        users[user_id]["words_per_send"] = int(data[0])
        users[user_id]["step"] = "category"
        await query.message.reply_text("Откуда брать фразы?", reply_markup=build_menu([("Песни", "Песни"), ("Кино", "Кино"), ("Книга", "Книга"), ("Бизнес", "Бизнес"), ("Любая тема", "Любая")]))
    elif step == "category":
        users[user_id]["category"] = data
        users[user_id]["step"] = "translate_phrases"
        await query.message.reply_text("Нужен ли перевод фраз?", reply_markup=build_menu([("Да", "phrases_yes"), ("Нет", "phrases_no")]))
    elif step == "translate_phrases":
        users[user_id]["translate_phrases"] = data.endswith("yes")
        users[user_id]["step"] = "done"
        await query.message.reply_text("🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu")
        schedule_user_reminders(user_id)
    save_json(USERS_FILE, users)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if text.startswith("/delete "):
        word = text[8:].strip().lower()
        if user_id in words and word in words[user_id]:
            words[user_id].remove(word)
            await update.message.reply_text(f"Слово '{word}' удалено из базы ❌")
        else:
            await update.message.reply_text(f"Слово '{word}' не найдено в базе.")
        return

    if user_id not in users or users[user_id].get("step") != "done":
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    word = text.lower()
    if user_id not in words:
        words[user_id] = []
    if word not in words[user_id]:
        words[user_id].append(word)
        save_json(WORDS_FILE, words)

        translation = await translate_word(word) if users[user_id].get("translate_words") else "🔇 перевод отключён"
        category = users[user_id].get("category", "Любая")
        example = random.choice(default_phrases.get(category, sum(default_phrases.values(), [])))

        reply = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n📘 Пример:\n\"{example['sentence']}\" Source: {example['source']}.\n\"{example['translation']}\" Источник: {example['source']}."
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(f"Слово '{word}' уже есть в базе.")

# === Авторассылка ===
async def send_reminders():
    for user_id, data in users.items():
        if data.get("step") != "done":
            continue
        times_per_day = data.get("times_per_day", 1)
        hours = {1: [11], 2: [11, 15], 3: [11, 15, 19]}.get(times_per_day, [11])
        now_hour = int(time().hour)
        if now_hour not in hours:
            continue
        wlist = words.get(user_id, [])
        if not wlist:
            continue
        category = data.get("category", "Любая")
        example = random.choice(default_phrases.get(category, sum(default_phrases.values(), [])))
        chosen = random.choice(wlist)
        translation = await translate_word(chosen) if data.get("translate_words") else ""
        text = f"🧠 Слово дня: {chosen} ({translation})\n📘 Пример:\n\"{example['sentence']}\"\n\"{example['translation']}\""
        try:
            await context.bot.send_message(chat_id=int(user_id), text=text)
        except:
            pass

# === Планировщик ===
scheduler = BackgroundScheduler()
for hour in [11, 15, 19]:
    scheduler.add_job(send_reminders, CronTrigger(hour=hour, minute=0))
scheduler.start()

# === Запуск ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()
