import logging
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import (
    add_user_word,
    get_user_settings,
    set_user_setting,
    get_words_by_user,
    delete_word,
    get_random_phrase_with_word,
    init_user_settings,
)
from translator import translate_word, translate_text

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_settings(user_id)

    keyboard = [
        [
            InlineKeyboardButton("🔤 Перевод слов", callback_data="translate_words:yes"),
            InlineKeyboardButton("Без перевода", callback_data="translate_words:no"),
        ],
        [
            InlineKeyboardButton("📆 1 раз в день", callback_data="frequency:1"),
            InlineKeyboardButton("2 раза", callback_data="frequency:2"),
            InlineKeyboardButton("3 раза", callback_data="frequency:3"),
        ],
        [
            InlineKeyboardButton("📚 1 слово", callback_data="word_count:1"),
            InlineKeyboardButton("2", callback_data="word_count:2"),
            InlineKeyboardButton("3", callback_data="word_count:3"),
            InlineKeyboardButton("5", callback_data="word_count:5"),
        ],
        [
            InlineKeyboardButton("🎬 Кино", callback_data="category:Кино"),
            InlineKeyboardButton("🎵 Песни", callback_data="category:Песни"),
            InlineKeyboardButton("📜 Афоризмы", callback_data="category:Афоризмы"),
            InlineKeyboardButton("🎭 Любая тема", callback_data="category:Любая тема"),
        ],
        [
            InlineKeyboardButton("🈯 Перевод фраз", callback_data="translate_phrases:yes"),
            InlineKeyboardButton("Без перевода", callback_data="translate_phrases:no"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Давай настроим твоего помощника 👇", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    setting = data.split(":")[0]
    value = data.split(":")[1]

    if setting == "category":
        setting = "phrase_category"

    set_user_setting(user_id, setting, value)
    await query.edit_message_text(f"✅ Настройка обновлена: {setting} = {value}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()

    translation = translate_word(word)
    add_user_word(user_id, word, translation)

    phrase_data = get_random_phrase_with_word(word, get_user_settings(user_id).get("phrase_category", "Любая тема"))
    if phrase_data:
        phrase = phrase_data["text"]
        source = phrase_data["source"]
        phrase_translation = ""
        if get_user_settings(user_id).get("translate_phrases") == "yes":
            phrase_translation = translate_text(phrase)
        response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
        response += f"📘 Пример: {phrase}\n"
        if phrase_translation:
            response += f"📗 Перевод: {phrase_translation}\n"
        response += f"Источник: {source}"
    else:
        response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n"
        response += "(Фраза не найдена в выбранной категории)"

    await update.message.reply_text(response)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def send_reminders(application):
    from main import send_word_to_user
    from database import get_all_user_ids
    import datetime

    now = datetime.datetime.now()
    hour = now.hour

    for user_id in get_all_user_ids():
        settings = get_user_settings(user_id)
        frequency = int(settings.get("frequency", 1))

        if (frequency == 1 and hour == 11) or \
           (frequency == 2 and hour in [11, 15]) or \
           (frequency == 3 and hour in [11, 15, 19]):

            count = int(settings.get("word_count", 1))
            for _ in range(count):
                await send_word_to_user(application, user_id)

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи слово после команды /add")
        return

    word = context.args[0].strip()
    translation = translate_word(word)
    add_user_word(user_id, word, translation)

    phrase_data = get_random_phrase_with_word(word, get_user_settings(user_id).get("phrase_category", "Любая тема"))
    if phrase_data:
        phrase = phrase_data["text"]
        source = phrase_data["source"]
        phrase_translation = ""
        if get_user_settings(user_id).get("translate_phrases") == "yes":
            phrase_translation = translate_text(phrase)
        response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
        response += f"📘 Пример: {phrase}\n"
        if phrase_translation:
            response += f"📗 Перевод: {phrase_translation}\n"
        response += f"Источник: {source}"
    else:
        response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n"
        response += "(Фраза не найдена в выбранной категории)"

    await update.message.reply_text(response)
