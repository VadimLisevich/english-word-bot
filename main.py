import os
import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai

openai.api_key = os.environ["OPENAI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATA_FILE = "words.json"

logging.basicConfig(level=logging.INFO)

def load_words():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_words(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Просто пришли мне слово на английском — я дам перевод и пример фразы ✍️"
    )

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

# HTTP-сервер, чтобы Render "видел" открытый порт
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))  # Render задаёт переменную PORT
    server = HTTPServer(("", port), PingHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем фейковый сервер в отдельном потоке
    threading.Thread(target=run_fake_server).start()

    # Запускаем Telegram-бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
