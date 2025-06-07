import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    add_user_word,
    get_user_settings,
    set_user_setting,
    get_random_phrase_with_word,
    delete_word,
    get_words_by_user,
    init_user_settings
)
from translator import translate_word, translate_text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_settings(user_id)
    await update.message.reply_text("Привет! Я помогу тебе учить английские слова. Давай настроим бота.")
    await ask_translate_words(update, context)


async def ask_translate_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_words:yes"),
         InlineKeyboardButton("Нет", callback_data="translate_words:no")]
    ]
    await update.message.reply_text("Нужен ли перевод слов?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="frequency:1"),
         InlineKeyboardButton("2", callback_data="frequency:2"),
         InlineKeyboardButton("3", callback_data="frequency:3")]
    ]
    await update.callback_query.message.reply_text("Как часто отправлять фразы? (в день)", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_words_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1", callback_data="count:1"),
         InlineKeyboardButton("2", callback_data="count:2"),
         InlineKeyboardButton("3", callback_data="count:3"),
         InlineKeyboardButton("5", callback_data="count:5")]
    ]
    await update.callback_query.message.reply_text("Сколько слов присылать за раз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Афоризмы", callback_data="category:aphorisms")],
        [InlineKeyboardButton("Цитаты", callback_data="category:quotes")],
        [InlineKeyboardButton("Кино", callback_data="category:movies")],
        [InlineKeyboardButton("Песни", callback_data="category:songs")],
        [InlineKeyboardButton("Любая тема", callback_data="category:any")]
    ]
    await update.callback_query.message.reply_text("Откуда брать фразы?", reply_markup=InlineKeyboardMarkup(keyboard))


async def ask_translate_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="translate_phrases:yes"),
         InlineKeyboardButton("Нет", callback_data="translate_phrases:no")]
    ]
    await update.callback_query.message.reply_text("Нужен ли перевод фраз?", reply_markup=InlineKeyboardMarkup(keyboard))


async def finish_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("✅ Настройка завершена. Для повторной настройки нажми /menu")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key, value = query.data.split(":")
    user_id = query.from_user.id
    set_user_setting(user_id, key, value)

    if key == "translate_words":
        await ask_frequency(update, context)
    elif key == "frequency":
        await ask_words_count(update, context)
    elif key == "count":
        await ask_category(update, context)
    elif key == "category":
        await ask_translate_phrases(update, context)
    elif key == "translate_phrases":
        await finish_setup(update, context)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_translate_words(update, context)


async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи слово после команды /add.")
        return
    word = context.args[0].lower()
    translation = translate_word(word)

    add_user_word(user_id, word, translation)

    settings = get_user_settings(user_id)
    category = settings.get("category", "any")
    phrase_data = get_random_phrase_with_word(word, category)

    if not phrase_data:
        await update.message.reply_text(f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n⚠️ Не удалось найти фразу с этим словом.")
        return

    phrase, source = phrase_data
    msg = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n📘 Пример: {phrase}\nИсточник: {source}"
    if settings.get("translate_phrases", "no") == "yes":
        phrase_translation = translate_text(phrase)
        msg += f"\n💬 Перевод: {phrase_translation}"

    await update.message.reply_text(msg)


async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    application = context.application
    user_ids = get_words_by_user()

    for user_id, words in user_ids.items():
        settings = get_user_settings(user_id)
        count = int(settings.get("count", 1))
        category = settings.get("category", "any")
        send_translation = settings.get("translate_phrases", "no") == "yes"

        words_sample = random.sample(words, min(len(words), count))
        for word, translation in words_sample:
            phrase_data = get_random_phrase_with_word(word, category)
            if phrase_data:
                phrase, source = phrase_data
                message = f"Слово '{word}' (перевод: {translation})\n📘 {phrase}\nИсточник: {source}"
                if send_translation:
                    phrase_translation = translate_text(phrase)
                    message += f"\n💬 Перевод: {phrase_translation}"
                await application.bot.send_message(chat_id=user_id, text=message)


async def delete_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи слово, которое нужно удалить.")
        return

    word = context.args[0].lower()
    success = delete_word(user_id, word)
    if success:
        await update.message.reply_text(f"Слово '{word}' удалено из базы 🗑️")
    else:
        await update.message.reply_text(f"Слово '{word}' не найдено в базе.")
