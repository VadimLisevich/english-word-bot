from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

# Временная база
user_words = {}         # user_id: [word1, word2, ...]
user_settings = {}      # user_id: {'translate_phrase': True}

# Фиктивные функции для перевода и примеров (замени при подключении API)
def translate_word(word):
    return f"Перевод слова '{word}'"

def translate_phrase(phrase):
    return f"Перевод фразы: {phrase}"

def get_example_with_word(word):
    # Здесь должна быть реальная логика подбора фразы с этим словом
    return {
        "text": f"The word '{word}' appears in this example sentence.",
        "source": "Фильм: Inception"
    }

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {'translate_phrase': True}
    user_words[user_id] = []
    await update.message.reply_text("👋 Привет! Отправь мне английское слово, и я добавлю его в базу.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 Меню настроек пока в разработке.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Обработка кнопки")

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip()
    translation = translate_word(word)
    example = get_example_with_word(word)
    phrase_translation = translate_phrase(example["text"]) if user_settings.get(user_id, {}).get('translate_phrase') else None

    user_words.setdefault(user_id, []).append(word)

    response = f"Слово '{word}' (перевод: {translation}) – добавлено в базу ✅\n\n"
    response += f"📘 Пример: {example['text']}\n"
    if phrase_translation:
        response += f"{phrase_translation}\n"
    response += f"Источник: {example['source']}"
    await update.message.reply_text(response)

async def send_reminders():
    for user_id, words in user_words.items():
        if not words:
            continue
        word = random.choice(words)
        example = get_example_with_word(word)
        translation = translate_word(word)
        phrase_translation = translate_phrase(example["text"]) if user_settings.get(user_id, {}).get('translate_phrase') else None

        message = f"Слово '{word}' (перевод: {translation})\n"
        message += f"📘 {example['text']}\n"
        if phrase_translation:
            message += f"{phrase_translation}\n"
        message += f"Источник: {example['source']}"

        # Здесь предполагается, что context у тебя глобально сохранён или замокан
        try:
            await application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Не удалось отправить сообщение {user_id}: {e}")
