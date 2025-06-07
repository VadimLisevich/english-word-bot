from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user_settings,
    set_user_setting,
    add_user_word,
    get_words_by_user,
    delete_word,
    get_random_phrase_with_word,
)
from translation import translate_word, translate_phrase
from scheduler import schedule_reminders
import random

settings_questions = [
    {"key": "translate_word", "question": "Нужен ли перевод слов?", "options": [("Да", "yes"), ("Нет", "no")]},
    {"key": "frequency", "question": "Как часто отправлять фразы?", "options": [("1 раз в день", "1"), ("2 раза в день", "2"), ("3 раза в день", "3")]},
    {"key": "words_per_message", "question": "Сколько слов присылать за раз?", "options": [("1", "1"), ("2", "2"), ("3", "3"), ("5", "5")]},
    {"key": "phrase_topic", "question": "Откуда брать фразы?", "options": [("Афоризмы", "Aphorisms"), ("Цитаты", "Quotes"), ("Кино", "Movies"), ("Песни", "Songs"), ("Любая тема", "Any")]},
    {"key": "translate_phrase", "question": "Нужен ли перевод фраз?", "options": [("Да", "yes"), ("Нет", "no")]},
]

user_states = {}

def get_settings_keyboard(question_data):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=f"set:{question_data['key']}:{value}")]
        for text, value in question_data["options"]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для изучения английских слов. Давай настроим твой опыт 📚")
    user_states[update.effective_user.id] = 0
    await ask_next_setting(update, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id] = 0
    await ask_next_setting(update, context)

async def ask_next_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state_index = user_states.get(user_id, 0)
    if state_index < len(settings_questions):
        question_data = settings_questions[state_index]
        await context.bot.send_message(chat_id=user_id, text=question_data["question"], reply_markup=get_settings_keyboard(question_data))
    else:
        await context.bot.send_message(chat_id=user_id, text="✅ Настройка завершена. Используй /menu для повторной настройки.")
        schedule_reminders(context.application, user_id)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("set:"):
        _, key, value = data.split(":")
        set_user_setting(user_id, key, value)
        user_states[user_id] += 1
        await ask_next_setting(update, context)
    elif data.startswith("delete:"):
        _, word = data.split(":")
        delete_word(user_id, word)
        await query.edit_message_text(f"Слово '{word}' удалено из базы ❌")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    settings = get_user_settings(user_id)
    translation = translate_word(word) if settings.get("translate_word") == "yes" else None

    add_user_word(user_id, word)

    phrase_data = get_random_phrase_with_word(word, settings.get("phrase_topic", "Any"))
    if not phrase_data:
        await update.message.reply_text(f"Слово '{word}' (перевод: {translation or 'без перевода'}) – добавлено в базу ✅\n❗️Не удалось найти пример фразы с этим словом.")
        return

    phrase, source = phrase_data
    phrase_translation = translate_phrase(phrase) if settings.get("translate_phrase") == "yes" else None

    response = f"Слово '{word}' (перевод: {translation or 'без перевода'}) – добавлено в базу ✅\n\n📘 {phrase}"
    if phrase_translation:
        response += f"\n📍 Перевод: {phrase_translation}"
    if source:
        response += f"\nИсточник: {source}"
    await update.message.reply_text(response)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    all_users = get_user_settings()  # возвращает словарь {user_id: settings}
    for user_id, settings in all_users.items():
        words = get_words_by_user(user_id)
        if not words:
            continue

        words_sample = random.sample(words, min(len(words), int(settings.get("words_per_message", 1))))
        for word in words_sample:
            translation = translate_word(word) if settings.get("translate_word") == "yes" else None
            phrase_data = get_random_phrase_with_word(word, settings.get("phrase_topic", "Any"))
            if not phrase_data:
                continue
            phrase, source = phrase_data
            phrase_translation = translate_phrase(phrase) if settings.get("translate_phrase") == "yes" else None

            text = f"Слово '{word}' (перевод: {translation or 'без перевода'})"
            text += f"\n📘 {phrase}"
            if phrase_translation:
                text += f"\n📍 Перевод: {phrase_translation}"
            if source:
                text += f"\nИсточник: {source}"

            await app.bot.send_message(chat_id=user_id, text=text)
