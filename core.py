from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from database import (
    add_user,
    set_user_setting,
    get_user_settings,
    add_user_word,
    get_words_by_user,
    delete_word
)
from phrases import get_random_phrase_with_word
from translator import translate_word, translate_text

SETTINGS = [
    ("translate_word", "Нужен ли перевод слов?"),
    ("reminders_per_day", "Как часто отправлять фразы?"),
    ("words_per_reminder", "Сколько слов присылать?"),
    ("category", "Откуда брать фразы?"),
    ("phrase_translation_required", "Нужен ли перевод фраз?")
]

SETTING_OPTIONS = {
    "translate_word": [("Да", "yes"), ("Нет", "no")],
    "reminders_per_day": [("1 раз", "1"), ("2 раза", "2"), ("3 раза", "3")],
    "words_per_reminder": [("1", "1"), ("2", "2"), ("3", "3"), ("5", "5")],
    "category": [("Афоризмы", "Aphorisms"), ("Цитаты", "Quotes"), ("Кино", "Movies"), ("Песни", "Songs"), ("Любая тема", "Any")],
    "phrase_translation_required": [("Да", "yes"), ("Нет", "no")]
}

user_states = {}

start = CommandHandler("start", lambda update, context: start_settings(update, context, True))
menu = CommandHandler("menu", lambda update, context: start_settings(update, context, False))

async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, greeting: bool):
    user_id = update.effective_user.id
    add_user(user_id)
    user_states[user_id] = 0
    if greeting:
        await context.bot.send_message(chat_id=user_id, text="Привет! Я помогу тебе учить английские слова.")
    await ask_next_setting(update, context)

async def ask_next_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, 0)
    if state >= len(SETTINGS):
        await context.bot.send_message(chat_id=user_id, text="✅ Настройка завершена. Чтобы изменить параметры, используй /menu")
        return
    key, question = SETTINGS[state]
    buttons = [[InlineKeyboardButton(text, callback_data=f"{key}:{value}")] for text, value in SETTING_OPTIONS[key]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=user_id, text=question, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    setting, value = query.data.split(":")
    set_user_setting(user_id, setting, value)
    user_states[user_id] = user_states.get(user_id, 0) + 1
    await ask_next_setting(update, context)

handle_callback = CallbackQueryHandler(handle_callback)

async def handle_message_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    settings = get_user_settings(user_id)

    word_translation = translate_word(word) if settings.get("translate_word") == "yes" else "Без перевода"
    category = settings.get("category", "Any")
    phrase_data = get_random_phrase_with_word(word, category)

    if not phrase_data:
        await context.bot.send_message(chat_id=user_id, text=f"Не удалось найти фразу с этим словом.")
        return

    phrase = phrase_data["text"]
    source = phrase_data["source"]

    phrase_translation = translate_text(phrase) if settings.get("phrase_translation_required") == "yes" else ""

    add_user_word(user_id, word, phrase, source)

    message = f"Слово '{word}' (перевод: {word_translation}) – добавлено в базу ✅\n\n"
    message += f"📘 Пример: {phrase}\n"
    if phrase_translation:
        message += f"📗 Перевод: {phrase_translation}\n"
    message += f"Источник: {source}"

    await context.bot.send_message(chat_id=user_id, text=message)

handle_message_func = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_func)

async def send_reminders(app, user_id):
    settings = get_user_settings(user_id)
    words = get_words_by_user(user_id)
    if not words:
        return

    count = int(settings.get("words_per_reminder", 1))
    selected = words[:count]

    for word_entry in selected:
        word = word_entry[0]
        word_translation = translate_word(word) if settings.get("translate_word") == "yes" else "Без перевода"
        category = settings.get("category", "Any")
        phrase_data = get_random_phrase_with_word(word, category)
        if not phrase_data:
            continue
        phrase = phrase_data["text"]
        source = phrase_data["source"]
        phrase_translation = translate_text(phrase) if settings.get("phrase_translation_required") == "yes" else ""

        message = f"Слово '{word}' (перевод: {word_translation})\n"
        message += f"📘 {phrase}\n"
        if phrase_translation:
            message += f"📗 Перевод: {phrase_translation}\n"
        message += f"Источник: {source}"

        await app.bot.send_message(chat_id=user_id, text=message)
