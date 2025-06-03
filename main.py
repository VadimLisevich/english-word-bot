import os
import json
import logging
from datetime import datetime
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# Загрузка переменных окружения
openai.api_key = os.environ["OPENAI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATA_FILE = "words.json"

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Загрузка словаря
def load_words():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# Сохранение словаря
def save_words(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Получение перевода и примера
async def get_translation_and_example(word):
    prompt = f"""Ты — учитель английского. Дай краткий перевод слова "{word}" и один интересный пример его использования в фразе (можно из фильма, песни, пословицы и т.д.). Формат: 
Перевод: ...
Фраза: ..."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    return response.choices[0].message["content"]

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот, который помогает учить английские слова.\n\nПросто пришли мне слово на английском — я дам перевод и пример. Всё добавляется в твою базу знаний 📚"
    )

# Обработка слов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    word = update.message.text.strip().lower()
    
    data = load_words()
    if user_id not in data:
        data[user_id] = []

    if word in data[user_id]:
        await update.message.reply_text("Это слово уже есть в твоей базе знаний ✍️")
        return

    await update.message.reply_text("⏳ Думаю...")

    try:
        result = await get_translation_and_example(word)
        data[user_id].append(word)
        save_words(data)
        await update.message.reply_text(f"✅ Добавлено!\n\n{result}")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуй позже.")

# Запуск приложения
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
