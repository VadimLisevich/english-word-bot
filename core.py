import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
)

from database import (
    init_user_settings,
    set_user_setting,
    get_user_settings,
    add_user_word,
    get_words_by_user,
    delete_word,
    get_random_phrase_with_word,
)
from translator import translate_word, translate_text

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_settings(user_id)

    keyboard = [
        [InlineKeyboardButton("🔠 Перевод слов", callback_data="setting_translate_words")],
        [InlineKeyboardButton("🕒 Частота рассылки", callback_data="setting_frequency")],
        [InlineKeyboardButton("🔢 Кол-во слов за раз", callback_data="setting_words_per_message")],
        [InlineKeyboardButton("🎭 Источник фраз", callback_data="setting_category")],
        [InlineKeyboardButton("🌍 Перевод фраз", callback_data="setting_translate_phrases")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я помогу тебе запомнить английские слова 📚\n\nВыбери настройки:",
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔠 Перевод слов", callback_data="setting_translate_words")],
        [InlineKeyboardButton("🕒 Частота рассылки", callback_data="setting_frequency")],
        [InlineKeyboardButton("🔢 Кол-во слов за раз", callback_data="setting_words_per_message")],
        [InlineKeyboardButton("🎭 Источник фраз", callback_data="setting_category")],
        [InlineKeyboardButton("🌍 Перевод фраз", callback_data="setting_translate_phrases")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Настройки:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data.startswith("setting_"):
        setting = data.replace("setting_", "")
        options = {
            "translate_words": [("Да", 1), ("Нет", 0)],
            "frequency": [("1 раз", 1), ("2 раза", 2), ("3 раза", 3)],
            "words_per_message": [("1", 1), ("2", 2), ("3", 3), ("5", 5)],
            "category": [("Афоризмы", "Афоризмы"), ("Цитаты", "Цитаты"),
                         ("Кино", "Кино"), ("Песни", "Песни"), ("Любая тема", "Любая тема")],
            "translate_phrases": [("Да", 1), ("Нет", 0)],
        }
        buttons = [
            [InlineKeyboardButton(text, callback_data=f"value_{setting}_{value}")]
            for text, value in options.get(setting, [])
        ]
        markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text(f"Выбери значение для {setting}:", reply_markup=markup)

    elif data.startswith("value_"):
        _, setting, value = data.split("_", 2)
        if setting in ["translate_words", "frequency", "words_per_message", "translate_phrases"]:
            set_user_setting(user_id, setting, int(value))
        elif setting == "category":
            set_user_setting(user_id, setting, value)

        await query.message.reply_text("✅ Настройка сохранена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    settings = get_user_settings(user_id)

    add_user_word(user_id, word)

    translation = translate_word(word) if settings["translate_words"] else None

    phrase_data = get_random_phrase_with_word(word, settings["category"])
    if not phrase_data:
        await update.message.reply_text(
            f"Слово '{word}' (перевод: {translation or '—'}) – добавлено в базу ✅\n"
            "Но пример с этим словом не найден 😔"
        )
        return

    phrase, phrase_translation, source = phrase_data
    full_translation = translate_text(phrase) if settings["translate_phrases"] else None

    response = f"Слово '{word}' (перевод: {translation or '—'}) – добавлено в базу ✅\n\n"
    response += f"📘 {phrase}\n"
    if settings["translate_phrases"]:
        response += f"📙 Перевод: {full_translation or phrase_translation}\n"
    response += f"Источник: {source}"

    await update.message.reply_text(response)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    from random import choice
    job = context.job
    user_id = job.chat_id
    settings = get_user_settings(user_id)
    words = get_words_by_user(user_id)

    if not words:
        return

    from telegram import Bot
    bot: Bot = context.bot

    for _ in range(settings["words_per_message"]):
        word = choice(words)
        translation = translate_word(word) if settings["translate_words"] else None
        phrase_data = get_random_phrase_with_word(word, settings["category"])
        if not phrase_data:
            continue

        phrase, phrase_translation, source = phrase_data
        full_translation = translate_text(phrase) if settings["translate_phrases"] else None

        message = f"Слово '{word}' (перевод: {translation or '—'})\n\n📘 {phrase}\n"
        if settings["translate_phrases"]:
            message += f"📙 Перевод: {full_translation or phrase_translation}\n"
        message += f"Источник: {source}"

        await bot.send_message(chat_id=user_id, text=message)
