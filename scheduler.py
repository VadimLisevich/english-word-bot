from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_all_user_ids, get_user_settings, get_words_by_user
from phrases import get_random_phrase_with_word
from translator import translate_text
import asyncio

scheduler = AsyncIOScheduler()

def schedule_reminders(application):
    scheduler.add_job(lambda: send_reminders(application), CronTrigger(hour=11, minute=0))
    scheduler.add_job(lambda: send_reminders(application), CronTrigger(hour=15, minute=0))
    scheduler.add_job(lambda: send_reminders(application), CronTrigger(hour=19, minute=0))
    scheduler.start()

async def send_reminders(application):
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        settings = get_user_settings(user_id)
        if not settings:
            continue

        reminders_per_day = settings.get("reminders_per_day", 1)
        current_hour = int(asyncio.get_event_loop().time() // 3600) % 24
        if reminders_per_day == 1 and current_hour != 11:
            continue
        elif reminders_per_day == 2 and current_hour not in (11, 15):
            continue
        elif reminders_per_day == 3 and current_hour not in (11, 15, 19):
            continue

        words = get_words_by_user(user_id)
        if not words:
            continue

        words_per_message = settings.get("words_per_message", 1)
        category = settings.get("category", "any")
        translate_phrase = settings.get("translate_phrase", False)

        sample_words = [w["word"] for w in words]
        selected_words = sample_words[:words_per_message]

        for word in selected_words:
            phrase, source = get_random_phrase_with_word(word, category) or ("Пример не найден.", "Источник не найден.")
            phrase_translation = translate_text(phrase) if translate_phrase else None

            text = f"Слово '{word}'\n📘 {phrase}"
            if phrase_translation:
                text += f"\n💬 Перевод: {phrase_translation}"
            text += f"\nИсточник: {source}"

            await application.bot.send_message(chat_id=user_id, text=text)
