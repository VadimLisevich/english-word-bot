import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_user, add_user_word, get_user_settings, set_user_setting,
    get_words_by_user, delete_word, get_random_phrase_with_word
)
from translator import translate_word, translate_text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    await update.message.reply_text(
        "Привет! Я помогу тебе выучить английские слова 📚\n\nДавай настроим бота под тебя.")
    await ask_translate_word(update, context)


async def ask_translate_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_word_yes"),
         InlineKeyboardButton("Нет", callback_data="translate_word_no")]
    ]
    await update.effective_chat.send_message("Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_reminders_per_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="reminders_1"),
         InlineKeyboardButton("2", callback_data="reminders_2"),
         InlineKeyboardButton("3", callback_data="reminders_3")]
    ]
    await update.effective_chat.send_message("Как часто отправлять фразы?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_words_per_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="words_1"),
         InlineKeyboardButton("2", callback_data="words_2"),
         InlineKeyboardButton("3", callback_data="words_3"),
         InlineKeyboardButton("5", callback_data="words_5")]
    ]
    await update.effective_chat.send_message("Сколько слов отправлять за раз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="category_aphorisms"),
         InlineKeyboardButton("Цитаты", callback_data="category_quotes")],
        [InlineKeyboardButton("Кино", callback_data="category_movies"),
         InlineKeyboardButton("Песни", callback_data="category_songs")],
        [InlineKeyboardButton("Любая тема", callback_data="category_any")]
    ]
    await update.effective_chat.send_message("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_translate_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrase_yes"),
         InlineKeyboardButton("Нет", callback_data="translate_phrase_no")]
    ]
    await update.effective_chat.send_message("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("translate_word_"):
        value = data.split("_")[-1] == "yes"
        set_user_setting(user_id, "translate_word", value)
        await ask_reminders_per_day(update, context)
    elif data.startswith("reminders_"):
        value = int(data.split("_")[-1])
        set_user_setting(user_id, "reminders_per_day", value)
        await ask_words_per_message(update, context)
    elif data.startswith("words_"):
        value = int(data.split("_")[-1])
        set_user_setting(user_id, "words_per_message", value)
        await ask_category(update, context)
    elif data.startswith("category_"):
        value = data.split("_")[-1]
        set_user_setting(user_id, "category", value)
        await ask_translate_phrase(update, context)
    elif data.startswith("translate_phrase_"):
        value = data.split("_")[-1] == "yes"
        set_user_setting(user_id, "translate_phrase", value)
        await context.bot.send_message(chat_id=user_id, text="✅ Настройка завершена! Введите новое слово.")
        await context.bot.send_message(chat_id=user_id, text="Для изменения настроек введите /menu")
    elif data.startswith("delete_"):
        word = data.split("_", 1)[-1]
        delete_word(user_id, word)
        await context.bot.send_message(chat_id=user_id, text=f"Слово '{word}' удалено из базы ❌")


async def handle_message_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    settings = get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("Сначала пройди настройку — введи /start или /menu")
        return

    word_translation = translate_word(word) if settings.get("translate_word") else "—"

    category = settings.get("category", "any")
    phrase_data = get_random_phrase_with_word(word, category)

    if phrase_data:
        phrase, source = phrase_data
        phrase_translation = translate_text(phrase) if settings.get("translate_phrase") else None
    else:
        phrase = "Пример не найден."
        source = "Источник не найден."
        phrase_translation = None

    add_user_word(user_id, word, word_translation, source, phrase, phrase_translation)

    msg = f"Слово '{word}' (перевод: {word_translation}) – добавлено в базу ✅\n\n📘 Пример: {phrase}"
    if phrase_translation:
        msg += f"\n💬 Перевод: {phrase_translation}"
    msg += f"\nИсточник: {source}"

    await update.message.reply_text(msg)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Изменим настройки 🛠️")
    await ask_translate_word(update, context)
