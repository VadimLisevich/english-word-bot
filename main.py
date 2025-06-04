import os
import json
import logging
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI клиента
client = OpenAI(api_key=OPENAI_API_KEY)

# Файлы хранения
SETTINGS_FILE = "user_settings.json"
WORDS_FILE = "words.json"

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger()

# Загрузка настроек и слов
if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
        user_settings = json.load(f)
else:
    user_settings = {}

if os.path.exists(WORDS_FILE):
    with open(WORDS_FILE, "r") as f:
        user_words = json.load(f)
else:
    user_words = {}

# Сохраняем настройки
def save_user_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(user_settings, f)

# Сохраняем слова
def save_user_words():
    with open(WORDS_FILE, "w") as f:
        json.dump(user_words, f)

# Старт команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {}
    await update.message.reply_text(
        "Привет! Этот бот помогает учить английские слова через фразы. Тебе нужно просто писать сюда слова, которые ты никак не можешь запомнить, а я буду тебе в течение дня давать примеры фраз с использованием этих слов.\n\nОкей, давай настроим бота!"
    )
    await ask_translate_word(update)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {}
    await ask_translate_word(update)

# Вопросы по настройке
async def ask_translate_word(update: Update):
    buttons = [[KeyboardButton("нужен перевод")], [KeyboardButton("без перевода")]]
    await update.message.reply_text(
        "Нужен ли тебе перевод слова или ты просто хочешь добавлять его в базу?",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )

async def ask_frequency(update: Update):
    buttons = [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")]]
    await update.message.reply_text(
        "Как часто ты хочешь, чтобы я писал тебе?",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )

async def ask_batch(update: Update):
    buttons = [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")], [KeyboardButton("5")]]
    await update.message.reply_text(
        "Отлично! А сколько слов за один раз ты хочешь повторять?",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )

async def ask_source_type(update: Update):
    buttons = [
        [KeyboardButton("афоризм")],
        [KeyboardButton("цитата")],
        [KeyboardButton("кино")],
        [KeyboardButton("песни")],
        [KeyboardButton("любая тема")],
    ]
    await update.message.reply_text(
        "Окей, а откуда лучше брать примеры фраз?",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )

async def ask_translate_phrase(update: Update):
    buttons = [[KeyboardButton("да")], [KeyboardButton("нет")]]
    await update.message.reply_text(
        "Перевод для фраз нужен?",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()

    if user_id not in user_settings or not user_settings[user_id].get("setup_complete"):
        if text in ["нужен перевод", "без перевода"]:
            user_settings[user_id]["translate_word"] = text == "нужен перевод"
            await ask_frequency(update)
        elif text in ["1", "2", "3"] and "frequency" not in user_settings[user_id]:
            user_settings[user_id]["frequency"] = int(text)
            await ask_batch(update)
        elif text in ["1", "2", "3", "5"] and "batch_size" not in user_settings[user_id]:
            user_settings[user_id]["batch_size"] = int(text)
            await ask_source_type(update)
        elif text in ["афоризм", "цитата", "кино", "песни", "любая тема"]:
            user_settings[user_id]["source_type"] = text
            await ask_translate_phrase(update)
        elif text in ["да", "нет"]:
            user_settings[user_id]["translate_phrase"] = text == "да"
            user_settings[user_id]["setup_complete"] = True
            save_user_settings()
            await update.message.reply_text("🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu")
        else:
            await update.message.reply_text("Пожалуйста, следуй настройке. Или напиши /menu для сброса ✨")
    else:
        # Сохраняем слово в базу
        if user_id not in user_words:
            user_words[user_id] = []
        if text not in user_words[user_id]:
            user_words[user_id].append(text)
            save_user_words()
            await update.message.reply_text(f"Слово '{text}' добавлено в базу ✅")
        else:
            await update.message.reply_text(f"Слово '{text}' уже есть в базе 📚")

# Планировщик рассылки
scheduler = BackgroundScheduler()

async def send_daily_phrases(application: Application):
    now = datetime.now().hour
    for user_id, settings in user_settings.items():
        if not settings.get("setup_complete"):
            continue
        freq = settings.get("frequency", 1)
        if (freq == 1 and now != 11) or (freq == 2 and now not in [11, 15]) or (freq == 3 and now not in [11, 15, 19]):
            continue

        words = user_words.get(user_id, [])
        if not words:
            continue

        batch = settings.get("batch_size", 1)
        sample = random.sample(words, min(batch, len(words)))

        for word in sample:
            phrase = f"Пример фразы с \"{word}\": 'Life is text, and you are the author.' — из фильма 'Stranger Than Fiction'"
            if settings.get("translate_phrase"):
                phrase += "\n(Жизнь — это текст, и ты его автор.)"
            try:
                await application.bot.send_message(chat_id=int(user_id), text=phrase)
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

scheduler.add_job(lambda: app.create_task(send_daily_phrases(app)), "cron", hour="11,15,19")
scheduler.start()

# Запуск бота
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

logger.info("🤖 Бот запущен")
app.run_polling()
