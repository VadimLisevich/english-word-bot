import random

def get_translation(word: str) -> str:
    # Простейший пример перевода, можно подключить API или словарь
    dictionary = {
        "execute": "выполнять",
        "plan": "план",
        "perfectly": "идеально",
        "always": "всегда",
        "intersect": "пересекаться",
        "conducts": "проводит",
    }
    return dictionary.get(word.lower(), "перевод не найден")

def get_example_phrase(word: str, category: str):
    # Заглушки с фразами по категориям — можно расширить
    phrases = {
        "Кино": [
            ("I'm executing the plan perfectly, just like always.", "Inception"),
            ("He intersects paths with destiny.", "The Matrix"),
            ("She conducts herself with grace.", "Pride & Prejudice"),
        ],
        "Песни": [
            ("We intersect in the middle of the night.", "Song: Midnight Roads"),
            ("She conducts the music of my heart.", "Song: Symphony Soul"),
        ],
        "Афоризмы": [
            ("To execute a dream, start with action.", "Aphorism"),
            ("Those who conduct well, live well.", "Aphorism"),
        ],
        "Цитаты": [
            ("He who executes swiftly, wins the war.", "Napoleon"),
            ("She who conducts herself with integrity needs no defense.", "Oprah"),
        ],
        "Любая тема": [
            ("He intersects worlds without knowing.", "Sci-fi collection"),
            ("I conduct my business with honor.", "Business Weekly"),
        ],
    }

    # Выбираем категорию
    category_phrases = phrases.get(category, phrases["Любая тема"])

    # Ищем фразу с нужным словом
    matching = [p for p in category_phrases if word.lower() in p[0].lower()]
    if not matching:
        matching = category_phrases

    phrase, source = random.choice(matching)

    # Примитивный перевод фразы (заглушка, можно подключить переводчик)
    phrase_translations = {
        "I'm executing the plan perfectly, just like always.": "Я выполняю план идеально, как всегда.",
        "He intersects paths with destiny.": "Он пересекается с судьбой.",
        "She conducts herself with grace.": "Она ведёт себя с грацией.",
        "We intersect in the middle of the night.": "Мы пересекаемся посреди ночи.",
        "She conducts the music of my heart.": "Она управляет музыкой моего сердца.",
    }

    translation = phrase_translations.get(phrase, "")

    return phrase, f"Фильм: {source}" if category == "Кино" else source, translation
