import logging
import os
import json
import random
import asyncio
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

USER_SETTINGS_FILE = "user_settings.json"
USER_WORDS_FILE = "user_words.json"

# ---------- Storage ----------
def load_user_settings():
    if not os.path.exists(USER_SETTINGS_FILE):
        return {}
    with open(USER_SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_user_settings(settings):
    with open(USER_SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def load_user_words():
    if not os.path.exists(USER_WORDS_FILE):
        return {}
    with open(USER_WORDS_FILE, "r") as f:
        return json.load(f)

def save_user_words(words):
    with open(USER_WORDS_FILE, "w") as f:
        json.dump(words, f)

# ---------- GPT Logic ----------
async def get_translation_and_example(word, source_type="any", translate_phrase=True):
    prompt = f"""
You are an English language assistant.
Give a translation for the word '{word}' to Russian.
Then give a sentence using that word in the selected context: {source_type}.
Then mention the source (e.g., song name, movie, etc). Keep it short.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    try:
        lines = content.strip().split("\n")
        translation = lines[0].strip()
        example = lines[1].strip()
        source = lines[2].strip()
        return translation, example, source
    except Exception as e:
        logging.error(f"Ошибка обработки ответа GPT: {e}\n{content}")
        raise e

# ---------- Bot Handlers ----------
user_settings = load_user_settings()
user_words = load_user_words()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {
        "step": "translate_word",
        "translate_word": None,
        "frequency": None,
        "words_per_message": None,
        "source_type": None,
        "translate_phrase": None
    }
    save_user_settings(user_settings)

    await update.message.reply_text(
        "Привет! Этот бот помогает учить английские слова через фразы. Просто пиши сюда слова, которые сложно запомнить — я пришлю фразы с ними в течение дня.\n\nОкей, давай настроим бота!"
    )
    await ask_translate_word(update)

async def ask_translate_word(update: Update):
    buttons = [[KeyboardButton("нужен перевод")], [KeyboardButton("без перевода")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Нужен ли тебе перевод слова или просто хочешь добавлять в базу?", reply_markup=markup)

async def ask_frequency(update: Update):
    buttons = [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Как часто ты хочешь, чтобы я писал тебе?", reply_markup=markup)

async def ask_words_per_message(update: Update):
    buttons = [[KeyboardButton("1")], [KeyboardButton("2")], [KeyboardButton("3")], [KeyboardButton("5")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Сколько слов за один раз ты хочешь повторять?", reply_markup=markup)

async def ask_source_type(update: Update):
    buttons = [[KeyboardButton("афоризм")], [KeyboardButton("цитата")], [KeyboardButton("кино")], [KeyboardButton("песни")], [KeyboardButton("любая тема")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Окей, а откуда лучше брать примеры фраз?", reply_markup=markup)

async def ask_translate_phrase(update: Update):
    buttons = [[KeyboardButton("да")], [KeyboardButton("нет")]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Перевод для фраз нужен?", reply_markup=markup)

async def finish_settings(update: Update):
    await update.message.reply_text("🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_settings[user_id] = {"step": "translate_word"}
    save_user_settings(user_settings)
    await ask_translate_word(update)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_words.setdefault(user_id, [])

    if not context.args:
        await update.message.reply_text("❗ Укажи слово, которое хочешь удалить. Пример: /delete abundance")
        return

    word = context.args[0].lower()
    if word in user_words[user_id]:
        user_words[user_id].remove(word)
        save_user_words(user_words)
        await update.message.reply_text(f"🗑️ Слово '{word}' удалено из базы.")
    else:
        await update.message.reply_text(f"⚠️ Слово '{word}' не найдено в базе.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text.strip().lower()

    if user_id not in user_settings:
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    step = user_settings[user_id].get("step")

    if step == "translate_word":
        user_settings[user_id]["translate_word"] = message == "нужен перевод"
        user_settings[user_id]["step"] = "frequency"
        save_user_settings(user_settings)
        await ask_frequency(update)
    elif step == "frequency":
        if message in ["1", "2", "3"]:
            user_settings[user_id]["frequency"] = int(message)
            user_settings[user_id]["step"] = "words_per_message"
            save_user_settings(user_settings)
            await ask_words_per_message(update)
    elif step == "words_per_message":
        if message in ["1", "2", "3", "5"]:
            user_settings[user_id]["words_per_message"] = int(message)
            user_settings[user_id]["step"] = "source_type"
            save_user_settings(user_settings)
            await ask_source_type(update)
    elif step == "source_type":
        user_settings[user_id]["source_type"] = message
        user_settings[user_id]["step"] = "translate_phrase"
        save_user_settings(user_settings)
        await ask_translate_phrase(update)
    elif step == "translate_phrase":
        user_settings[user_id]["translate_phrase"] = message == "да"
        user_settings[user_id]["step"] = "done"
        save_user_settings(user_settings)
        await finish_settings(update)
    elif user_settings[user_id].get("step") == "done":
        word = message
        user_words.setdefault(user_id, [])

        if word in user_words[user_id]:
            await update.message.reply_text(f"Слово '{word}' уже есть в базе 🗂️")
            return

        if user_settings[user_id].get("translate_word"):
            try:
                translation, example, source = await get_translation_and_example(
                    word,
                    user_settings[user_id].get("source_type", "any"),
                    user_settings[user_id].get("translate_phrase", True)
                )
                await update.message.reply_text(
                    f"🔤 Перевод: {translation}\n💬 Пример: {example}\n📚 {source}"
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при получении перевода слова '{word}': {e}")
                await update.message.reply_text("⚠️ Не удалось получить перевод. Попробуй позже.")

        user_words[user_id].append(word)
        save_user_words(user_words)
        await update.message.reply_text(f"Слово '{word}' добавлено в базу ✅")

# ---------- Run ----------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def scheduler():
    while True:
        now = datetime.now().time()
        if now in [time(11, 0), time(15, 0), time(19, 0)]:
            for user_id, settings in user_settings.items():
                if settings.get("step") != "done":
                    continue

                words = user_words.get(user_id, [])
                if not words:
                    continue

                count = settings.get("words_per_message", 1)
                selected_words = random.sample(words, min(len(words), count))

                for word in selected_words:
                    try:
                        translation, example, source = await get_translation_and_example(
                            word,
                            settings.get("source_type", "any"),
                            settings.get("translate_phrase", True)
                        )
                        msg = f"💬 {example}\n📚 {source}"
                        if settings.get("translate_phrase"):
                            msg = f"💬 {example}\n📚 {source}\n🔤 Перевод слова: {translation}"

                        await app.bot.send_message(chat_id=user_id, text=msg)
                    except Exception as e:
                        logging.error(f"❌ Ошибка при авторассылке: {e}")
            await asyncio.sleep(60)
        await asyncio.sleep(30)

async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await scheduler()

import asyncio
asyncio.run(main())
