import logging
import os
import random
import asyncio
from datetime import time
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import (
    init_db, add_word, get_user_settings, set_user_setting,
    get_words_by_user, delete_word, get_random_user_words
)
from translator import translate_word, generate_example

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
application = Application.builder().token(TOKEN).build()
scheduler = AsyncIOScheduler()

user_states = {}

CATEGORIES = ['Афоризмы', 'Цитаты', 'Кино', 'Песни', 'Любая тема']

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Перезапустить настройку", callback_data="menu")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "intro"}
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я бот, который помогает учить английские слова.\nЯ буду присылать тебе фразы с новыми словами каждый день.",
    )
    await ask_translate_words(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "intro"}
    await ask_translate_words(update, context)

async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id]["step"] = "translate_words"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Нужен ли перевод слов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
            [InlineKeyboardButton("Нет", callback_data="translate_words_no")]
        ])
    )

async def ask_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id]["step"] = "frequency"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Как часто ты хочешь, чтобы я писал тебе?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 раз в день", callback_data="frequency_1")],
            [InlineKeyboardButton("2 раза в день", callback_data="frequency_2")],
            [InlineKeyboardButton("3 раза в день", callback_data="frequency_3")]
        ])
    )

async def ask_words_per_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id]["step"] = "words_per_message"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Сколько слов отправлять за раз?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data="words_1"),
             InlineKeyboardButton("2", callback_data="words_2")],
            [InlineKeyboardButton("3", callback_data="words_3"),
             InlineKeyboardButton("5", callback_data="words_5")]
        ])
    )

async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id]["step"] = "category"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Откуда брать фразы?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(cat, callback_data=f"category_{cat}") for cat in CATEGORIES]
        ])
    )

async def ask_translate_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id]["step"] = "translate_phrases"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Нужен ли перевод фраз?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
            [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
        ])
    )

async def finish_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Настройка завершена. Чтобы изменить параметры, используй команду /menu.",
        reply_markup=get_main_menu()
    )
    schedule_user_reminders(update.effective_user.id)

def schedule_user_reminders(user_id):
    settings = get_user_settings(user_id)
    times = {1: [time(11, 0)], 2: [time(11, 0), time(15, 0)], 3: [time(11, 0), time(15, 0), time(19, 0)]}
    for t in times.get(settings["frequency"], [time(11, 0)]):
        scheduler.add_job(
            send_reminders,
            trigger=CronTrigger(hour=t.hour, minute=t.minute),
            args=[user_id],
            id=f"reminder_{user_id}_{t.hour}"
        )

async def send_reminders(user_id):
    settings = get_user_settings(user_id)
    words = get_random_user_words(user_id, settings["words_per_message"])
    for word in words:
        translation = translate_word(word)
        phrase, source, example_translation = generate_example(word, settings["category"])
        message = f"Слово '{word}' (перевод: {translation})\n\n📘 Пример:\n{phrase} Source: {source}.\n{example_translation}"
        await application.bot.send_message(chat_id=user_id, text=message)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.strip()
    user_id = update.effective_user.id
    translation = translate_word(word)
    add_word(user_id, word)
    settings = get_user_settings(user_id)
    phrase, source, example_translation = generate_example(word, settings["category"])
    text = (
        f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
        f"📘 Пример:\n{phrase} Source: {source}.\n{example_translation}"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "menu":
        await menu(update, context)
    elif data.startswith("translate_words_"):
        set_user_setting(user_id, "translate_words", data.endswith("yes"))
        await ask_frequency(update, context)
    elif data.startswith("frequency_"):
        set_user_setting(user_id, "frequency", int(data[-1]))
        await ask_words_per_message(update, context)
    elif data.startswith("words_"):
        set_user_setting(user_id, "words_per_message", int(data.split("_")[1]))
        await ask_category(update, context)
    elif data.startswith("category_"):
        set_user_setting(user_id, "category", data.split("_", 1)[1])
        await ask_translate_phrases(update, context)
    elif data.startswith("translate_phrases_"):
        set_user_setting(user_id, "translate_phrases", data.endswith("yes"))
        await finish_settings(update, context)

async def delete_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    words = get_words_by_user(user_id)
    if not words:
        await update.message.reply_text("У тебя нет добавленных слов.")
        return
    keyboard = [[InlineKeyboardButton(w, callback_data=f"del_{w}")] for w in words]
    await update.message.reply_text("Выбери слово для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("del_"):
        word = data[4:]
        delete_word(update.effective_user.id, word)
        await query.answer()
        await query.message.reply_text(f"Слово '{word}' удалено из базы ✅")

def main():
    init_db()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("delete", delete_word_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CallbackQueryHandler(handle_delete_callback, pattern=r"^del_"))
    scheduler.start()
    application.run_polling()

if __name__ == "__main__":
    main()
