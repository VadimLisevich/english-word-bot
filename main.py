import os
import json
import logging
import random
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "words.json"
SEND_TIMES = {1: [11], 2: [11, 15], 3: [11, 15, 19]}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ==== Служебные функции ====
def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# ==== Настройки ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data["settings_mode"] = True
    context.user_data["step"] = "translate_word"
    await update.message.reply_text(
        "👋 Привет! Этот бот помогает учить английские слова через фразы.\n\n"
        "Тебе нужно просто писать сюда слова, которые ты никак не можешь запомнить, "
        "а я буду тебе в течение дня давать примеры фраз с использованием этих слов.\n\n"
        "Окей, давай настроим бота!"
    )
    await ask_translate_word(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["settings_mode"] = True
    context.user_data["step"] = "translate_word"
    await update.message.reply_text("🛠 Давай снова настроим бота!")
    await ask_translate_word(update, context)

# ==== Вопросы ====
async def ask_translate_word(update, context):
    kb = [[InlineKeyboardButton("🔕 Без перевода", callback_data="translate_word:no")],
          [InlineKeyboardButton("🔤 Нужен перевод", callback_data="translate_word:yes")]]
    await update.message.reply_text("Нужен ли тебе перевод слова или ты просто хочешь добавлять его в базу?",
                                    reply_markup=InlineKeyboardMarkup(kb))

async def ask_frequency(update, context):
    kb = [[InlineKeyboardButton(str(i), callback_data=f"frequency:{i}")] for i in [1, 2, 3]]
    await update.callback_query.message.reply_text("Как часто ты хочешь, чтобы я писал тебе?",
                                                   reply_markup=InlineKeyboardMarkup(kb))

async def ask_batch_size(update, context):
    kb = [[InlineKeyboardButton(str(i), callback_data=f"batch:{i}")] for i in [1, 2, 3, 5]]
    await update.callback_query.message.reply_text("Сколько слов за один раз ты хочешь повторять?",
                                                   reply_markup=InlineKeyboardMarkup(kb))

async def ask_source_type(update, context):
    types = ["aphorism", "quote", "movie", "song", "any"]
    names = ["🧠 Афоризм", "📖 Цитата", "🎬 Кино", "🎵 Песни", "🌍 Любая тема"]
    kb = [[InlineKeyboardButton(names[i], callback_data=f"source:{types[i]}")] for i in range(5)]
    await update.callback_query.message.reply_text("Окей, а откуда лучше брать примеры фраз?",
                                                   reply_markup=InlineKeyboardMarkup(kb))

async def ask_phrase_translation(update, context):
    kb = [[InlineKeyboardButton("Да", callback_data="phrase_translate:yes")],
          [InlineKeyboardButton("Нет", callback_data="phrase_translate:no")]]
    await update.callback_query.message.reply_text("Перевод для фраз нужен?",
                                                   reply_markup=InlineKeyboardMarkup(kb))

# ==== Callback ====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    settings = load_json(SETTINGS_FILE)
    if user_id not in settings:
        settings[user_id] = {}

    key, value = query.data.split(":")

    if key == "translate_word":
        settings[user_id]["translate_word"] = value == "yes"
        await ask_frequency(update, context)

    elif key == "frequency":
        settings[user_id]["frequency"] = int(value)
        await ask_batch_size(update, context)

    elif key == "batch":
        settings[user_id]["batch_size"] = int(value)
        await ask_source_type(update, context)

    elif key == "source":
        settings[user_id]["source_type"] = value
        await ask_phrase_translation(update, context)

    elif key == "phrase_translate":
        settings[user_id]["translate_phrase"] = value == "yes"
        await query.message.reply_text("🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu")

    save_json(SETTINGS_FILE, settings)

# ==== Генератор фраз ====
def generate_phrase(word, source_type, translate):
    source_map = {
        "aphorism": "афоризм",
        "quote": "цитата",
        "movie": "фильм ‘Inception’",
        "song": "песня ‘Imagine’",
        "any": random.choice(["афоризм", "фильм ‘Matrix’", "цитата из книги"])
    }
    phrase = f"This is an example phrase with the word '{word}'."
    translation = f"Это пример фразы со словом '{word}'."
    source = source_map.get(source_type, "неизвестный источник")
    return f"🧠 Слово: {word}\n💬 Фраза: {phrase}" + (f"\n🔁 Перевод: {translation}" if translate else "") + f"\n📍Источник: {source}"

# ==== Планировщик ====
def send_scheduled_messages(app):
    now = datetime.now()
    settings = load_json(SETTINGS_FILE)
    words = load_json(WORDS_FILE)

    for user_id, cfg in settings.items():
        times = SEND_TIMES.get(cfg.get("frequency", 1), [11])
        if now.hour not in times:
            continue
        batch_size = cfg.get("batch_size", 1)
        word_list = words.get(user_id, [])
        if not word_list:
            continue
        selected = random.sample(word_list, min(len(word_list), batch_size))
        for word in selected:
            text = generate_phrase(word, cfg.get("source_type", "any"), cfg.get("translate_phrase", False))
            try:
                app.bot.send_message(chat_id=int(user_id), text=text)
            except Exception as e:
                logging.error(f"❌ Не удалось отправить сообщение {user_id}: {e}")

# ==== Fake HTTP для Render ====
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive.")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), PingHandler)
    server.serve_forever()

# ==== Запуск ====
if __name__ == "__main__":
    threading.Thread(target=run_fake_server).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   lambda u, c: u.message.reply_text("Напиши /start или /menu для настройки 😊")))

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_scheduled_messages, "cron", minute="0", args=[app])  # каждые полные часы
    scheduler.start()

    logging.info("🤖 Бот с авторассылкой запущен!")
    app.run_polling()
