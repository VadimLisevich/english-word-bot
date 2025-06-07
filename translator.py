from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_user, add_user_word, get_user_settings, set_user_setting,
    get_words_by_user, delete_word, init_user_settings
)
from phrases import get_random_phrase_with_word
from translator import translate_word, translate_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    init_user_settings(user_id)

    await update.message.reply_text("Привет! Я помогу тебе выучить английские слова. Начнём настройку.")
    await ask_translate_word(update)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройки:")
    await ask_translate_word(update)

async def ask_translate_word(update: Update):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_word:yes"),
         InlineKeyboardButton("Нет", callback_data="translate_word:no")]
    ]
    await update.message.reply_text("Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if ":" in data:
        setting, value = data.split(":")
        set_user_setting(user_id, setting, value)
        next_question = {
            "translate_word": ask_reminders_per_day,
            "reminders_per_day": ask_words_per_message,
            "words_per_message": ask_category,
            "category": ask_translate_phrase,
            "translate_phrase": settings_complete
        }
        if setting in next_question:
            await next_question[setting](query.message)

async def ask_reminders_per_day(message):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="reminders_per_day:1"),
         InlineKeyboardButton("2", callback_data="reminders_per_day:2"),
         InlineKeyboardButton("3", callback_data="reminders_per_day:3")]
    ]
    await message.reply_text("Как часто отправлять фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_words_per_message(message):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="words_per_message:1"),
         InlineKeyboardButton("2", callback_data="words_per_message:2"),
         InlineKeyboardButton("3", callback_data="words_per_message:3"),
         InlineKeyboardButton("5", callback_data="words_per_message:5")]
    ]
    await message.reply_text("Сколько слов присылать за раз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_category(message):
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="category:Афоризмы")],
        [InlineKeyboardButton("Цитаты", callback_data="category:Цитаты")],
        [InlineKeyboardButton("Кино", callback_data="category:Кино")],
        [InlineKeyboardButton("Песни", callback_data="category:Песни")],
        [InlineKeyboardButton("Любая тема", callback_data="category:Любая тема")]
    ]
    await message.reply_text("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_translate_phrase(message):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrase:yes"),
         InlineKeyboardButton("Нет", callback_data="translate_phrase:no")]
    ]
    await message.reply_text("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def settings_complete(message):
    await message.reply_text("✅ Настройка завершена! Введите слово, чтобы я добавил его в базу. Или нажмите /menu, чтобы изменить настройки.")

async def handle_message_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()

    word_translation = translate_word(word)
    settings = get_user_settings(user_id)
    category = settings.get("category", "Любая тема")
    phrase_data = get_random_phrase_with_word(word, category)

    if not phrase_data:
        await update.message.reply_text("Не удалось найти фразу с этим словом.")
        return

    phrase, source = phrase_data
    phrase_translation = translate_text(phrase) if settings.get("translate_phrase") == "yes" else None

    add_user_word(user_id, word, word_translation, source, phrase, phrase_translation)

    response = f"Слово '{word}' (перевод: {word_translation}) – добавлено в базу ✅\n\n📘 Пример: {phrase}\nИсточник: {source}"
    if phrase_translation:
        response += f"\n\n📗 Перевод: {phrase_translation}"

    await update.message.reply_text(response)

async def add_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите слово, которое вы хотите добавить.")

async def view_words_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    words = get_words_by_user(user_id)
    if not words:
        await update.message.reply_text("У вас пока нет добавленных слов.")
        return

    message = "Ваши слова:\n\n"
    for word, translation in words:
        message += f"• {word} – {translation}\n"
    await update.message.reply_text(message)

async def delete_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажите слово, которое хотите удалить: /delete слово")
        return

    word = args[0]
    user_id = update.effective_user.id
    if delete_word(user_id, word):
        await update.message.reply_text(f"Слово '{word}' удалено.")
    else:
        await update.message.reply_text(f"Слово '{word}' не найдено.")
