import os
import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from openai.types.chat import ChatCompletion

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Переменные окружения
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
DATA_FILE = "words.json"

if not BOT_TOKEN or not OPENAI_KEY:
    logging.error("❌ ОШИБКА: Переменные окружения TELEGRAM_BOT_TOKEN и OPENAI_API_KEY обязательны.")
    exit(1)

# Загрузка и сохранение слов пользователя
def load_words():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка при чтении файла базы: {e}")
        return {}

def save_words(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла базы: {e}")

# Получить перевод и пример с OpenAI
async def get_translation_and_example(word: str) -> str:
    logging.info(f"📨 Отправка запроса в OpenAI для слова: {word}")
    prompt = f"""Ты — учитель английского. Дай краткий перевод слова "{word}" и один интересный пример его использования в фразе (можно из фильма, песни, пословицы и т.д.). Формат:
Перевод: ...
Фраза: ..."""

    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response: ChatCompletion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        result = response.choices[0].message.content.strip()
        logging.info(f"✅ Ответ OpenAI получен: {result}")
        return result
    except Exception as e:
        logging.error(f"❌ Ошибка в OpenAI API: {e}")
        raise e

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"👤 Новый пользователь: {update.effective_user.id}")
    await update.message.reply_text(
        "👋 Привет! Просто пришли мне слово на английском — я дам перевод и пример фразы ✍️"
    )

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip().lower()
    user_id = str(update.effective_user.id)
    logging.info(f"📩 Пользователь {user_id} отправил слово: {word}")

    data = load_words()
    if user_id not in data:
        data[user_id] = []

    if word in data[user_id]:
        logging.info(f"🔁 Слово уже есть в базе у пользователя {user_id}")
        await update.message.reply_text("Это слово уже есть в твоей базе знаний ✍️")
        return

    await update.message.reply_text("⏳ Думаю...")

    try:
        result = await get_translation_and_example(word)
        data[user_id].append(word)
        save_words(data)
        await update.message.reply_text(f"✅ Добавлено!\n\n{result}")
    except Exception as e:
        await update.message.reply_text("⚠️ Произошла ошибка. Проверь API-ключ или повтори позже.")
        logging.exception("‼️ Сбой при обработке слова")

# Фейковый HTTP-сервер для Render
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive.")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"🌐 Запуск фейкового HTTP-сервера на порту {port}")
    server = HTTPServer(("", port), PingHandler)
    server.serve_forever()

# Основной запуск
if __name__ == "__main__":
    logging.info("🚀 Запуск Telegram-бота")

    # Фейковый HTTP-сервер в отдельном потоке (нужен Render'у)
    threading.Thread(target=run_fake_server).start()

    # Telegram bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
