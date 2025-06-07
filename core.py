from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from database import (
    add_user, add_user_word, get_user_settings, set_user_setting,
    delete_word, get_words_by_user, init_user_settings
)
from translator import translate_word, translate_text
from phrases import get_random_phrase_with_word

async def start_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    init_user_settings(user_id)
    await update.message.reply_text("👋 Привет! Я помогу тебе выучить английские слова. Начнём настройку.")
    await ask_translate_words(update, context)

async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_words_no")]
    ]
    await update.message.reply_text("🔤 Переводить ли добавленные слова?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    settings_map = {
        "translate_words_": "translate_words",
        "reminders_": "reminders_per_day",
        "words_": "words_per_reminder",
        "category_": "category",
        "translate_phrases_": "translate_phrases"
    }

    for prefix, setting in settings_map.items():
        if data.startswith(prefix):
            value = data.replace(prefix, "")
            if value.isdigit():
                value = int(value)
            elif value.lower() in ["yes", "да"]:
                value = True
            elif value.lower() in ["no", "нет"]:
                value = False
            set_user_setting(user_id, setting, value)

    next_step = {
        "translate_words_": ask_reminders_per_day,
        "reminders_": ask_words_per_reminder,
        "words_": ask_category,
        "category_": ask_translate_phrases,
        "translate_phrases_": done_settings
    }

    for prefix, func in next_step.items():
        if data.startswith(prefix):
            await func(update, context)
            break

async def ask_reminders_per_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="reminders_1")],
        [InlineKeyboardButton("2", callback_data="reminders_2")],
        [InlineKeyboardButton("3", callback_data="reminders_3")]
    ]
    await update.effective_message.reply_text("🕒 Сколько раз в день отправлять фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_words_per_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="words_1"), InlineKeyboardButton("2", callback_data="words_2")],
        [InlineKeyboardButton("3", callback_data="words_3"), InlineKeyboardButton("5", callback_data="words_5")]
    ]
    await update.effective_message.reply_text("📚 Сколько слов присылать за раз?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="category_Афоризмы")],
        [InlineKeyboardButton("Цитаты", callback_data="category_Цитаты")],
        [InlineKeyboardButton("Кино", callback_data="category_Кино")],
        [InlineKeyboardButton("Песни", callback_data="category_Песни")],
        [InlineKeyboardButton("Любая тема", callback_data="category_Любая тема")]
    ]
    await update.effective_message.reply_text("🎭 Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_translate_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases_yes")],
        [InlineKeyboardButton("Нет", callback_data="translate_phrases_no")]
    ]
    await update.effective_message.reply_text("🌍 Переводить ли фразы?", reply_markup=InlineKeyboardMarkup(keyboard))

async def done_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("✅ Настройка завершена! Используй /menu, чтобы изменить настройки в любой момент.")

start = CommandHandler("start", start_func)
menu = CommandHandler("menu", start_func)
handle_callback = CallbackQueryHandler(handle_callback)

async def handle_message_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()

    settings = get_user_settings(user_id)
    translate = settings.get("translate_words", True)
    category = settings.get("category", "Любая тема")
    translate_phrase = settings.get("translate_phrases", True)

    word_translation = translate_word(word) if translate else "Без перевода"
    phrase_data = get_random_phrase_with_word(word, category)

    phrase = phrase_data.get("phrase")
    source = phrase_data.get("source")
    phrase_translation = translate_text(phrase) if translate_phrase else None

    add_user_word(user_id, word, word_translation, source, phrase, phrase_translation)

    text = f"Слово '{word}' (перевод: {word_translation}) – добавлено в базу ✅\n\n"
    text += f"📘 Пример: {phrase}\n"
    if phrase_translation:
        text += f"💬 Перевод: {phrase_translation}\n"
    text += f"Источник: {source}"

    await update.message.reply_text(text)

handle_message = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_func)

add_word = handle_message

delete_word_command = CommandHandler("delete", lambda u, c: u.message.reply_text("Удаление пока не реализовано"))

view_words_command = CommandHandler("words", lambda u, c: u.message.reply_text("Просмотр пока не реализован"))

async def send_reminders(bot, user_id, settings):
    from random import choice
    words = get_words_by_user(user_id)
    if not words:
        return

    count = settings.get("words_per_reminder", 1)
    selected_words = [choice(words) for _ in range(count)]

    for word_data in selected_words:
        word = word_data["word"]
        translation = word_data["translation"]
        phrase = word_data["phrase"]
        phrase_translation = word_data["phrase_translation"]
        source = word_data["source"]

        text = f"Слово '{word}' (перевод: {translation})\n"
        text += f"📘 {phrase}\n"
        if phrase_translation:
            text += f"💬 Перевод: {phrase_translation}\n"
        text += f"Источник: {source}"

        await bot.send_message(chat_id=user_id, text=text)
