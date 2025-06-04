import os
import logging
import json
import random
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

SETTINGS_FILE = "data/settings.json"
WORDS_FILE = "data/words.json"

CATEGORIES = {
    "афоризмы": "Aphorism",
    "цитаты": "Quote",
    "кино": "Movie",
    "песни": "Song",
    "любая тема": "Phrase",
}

scheduler = AsyncIOScheduler()


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    settings = load_json(SETTINGS_FILE)

    context.user_data["config"] = {}

    await update.message.reply_text(
        "👋 Привет! Я помогу тебе выучить английские слова.\n"
        "Ты присылаешь мне слово — я добавляю его в базу и подбираю фразы с этим словом.\n"
        "Начнём настройку ⬇️"
    )

    await ask_translate_word(update, context)


async def ask_translate_word(update, context):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_word_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_word_no")],
    ]
    await update.message.reply_text("🔤 Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)

    config = context.user_data.get("config", {})

    def send_question(text, buttons):
        return query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(b, callback_data=b)] for b in buttons]))

    if data.startswith("translate_word"):
        config["translate_word"] = data.endswith("yes")
        return await send_question("📨 Как часто присылать фразы?", ["1", "2", "3"])

    if data in ["1", "2", "3"]:
        config["frequency"] = int(data)
        return await send_question("📦 Сколько слов отправлять за раз?", ["1", "2", "3", "5"])

    if data in ["1", "2", "3", "5"]:
        config["count"] = int(data)
        return await send_question("🎭 Откуда брать фразы?", list(CATEGORIES.keys()))

    if data.lower() in CATEGORIES:
        config["source"] = data.lower()
        return await send_question("💬 Нужен ли перевод фраз?", ["Да", "Нет"])

    if data in ["Да", "Нет"]:
        config["translate_phrase"] = data == "Да"

        settings = load_json(SETTINGS_FILE)
        settings[user_id] = config
        save_json(SETTINGS_FILE, settings)

        await query.edit_message_text(
            "🎉 Ура, мы всё настроили!\nЕсли захочешь что-то изменить — просто напиши /menu"
        )
        return


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 Настроим заново:")
    await ask_translate_word(update, context)


async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip().lower()
    user_id = str(update.effective_user.id)

    settings = load_json(SETTINGS_FILE)
    if user_id not in settings:
        await update.message.reply_text("Напиши /start или /menu для настройки 😊")
        return

    words = load_json(WORDS_FILE)
    user_words = words.get(user_id, [])
    if word in user_words:
        await update.message.reply_text(f"Слово '{word}' уже есть в базе ❗️")
        return

    user_words.append(word)
    words[user_id] = user_words
    save_json(WORDS_FILE, words)

    translation = ""
    if settings[user_id].get("translate_word"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Translate the word '{word}' to Russian."}],
            )
            translation = response["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Ошибка при переводе: {e}")

    message = f"Слово '{word}'"
    if translation:
        message += f" (перевод: {translation})"
    message += " – добавлено в базу ✅"

    await update.message.reply_text(message)


def load_phrases_by_category(category):
    file_map = {
        "афоризмы": "phrases_aphorisms.json",
        "цитаты": "phrases_quotes.json",
        "кино": "phrases_movies.json",
        "песни": "phrases_songs.json",
        "любая тема": "phrases_all.json",
    }
    path = f"data/{file_map.get(category, 'phrases_all.json')}"
    if not os.path.exists(path):
        return []
    return load_json(path)


async def send_reminders(bot):
    settings = load_json(SETTINGS_FILE)
    words = load_json(WORDS_FILE)

    for user_id, config in settings.items():
        user_words = words.get(user_id, [])
        if not user_words:
            continue

        count = config.get("count", 1)
        selected_words = random.sample(user_words, min(count, len(user_words)))
        source = config.get("source", "любая тема")
        phrases = load_phrases_by_category(source)
        random.shuffle(phrases)

        for word in selected_words:
            phrase_obj = next((p for p in phrases if word.lower() in p["text"].lower()), None)
            if phrase_obj:
                reply = f"📘 Пример:\n\"{phrase_obj['text']}\" Source: {CATEGORIES.get(source, 'Фраза')}.\n"
                if config.get("translate_phrase") and "translation" in phrase_obj:
                    reply += f"\n\"{phrase_obj['translation']}\" Источник: {CATEGORIES.get(source, 'Фраза')}."
                try:
                    await bot.send_message(chat_id=int(user_id), text=reply)
                except Exception as e:
                    logging.error(f"❌ Не удалось отправить сообщение {user_id}: {e}")


async def delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split()
    if len(parts) != 2:
        return await update.message.reply_text("Используй формат: /delete слово")

    word = parts[1].lower()
    user_id = str(update.effective_user.id)

    words = load_json(WORDS_FILE)
    user_words = words.get(user_id, [])
    if word not in user_words:
        return await update.message.reply_text(f"Слова '{word}' нет в базе ❌")

    user_words.remove(word)
    words[user_id] = user_words
    save_json(WORDS_FILE, words)

    await update.message.reply_text(f"Слово '{word}' удалено из базы 🗑️")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("delete", delete_word))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))

    scheduler.add_job(lambda: send_reminders(app.bot), "interval", hours=8)
    scheduler.start()

    logging.info("🚀 Бот запущен")
    app.run_polling()
