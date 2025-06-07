import random

PHRASES = {
    "Афоризмы": [
        {"phrase": "Success usually comes to those who are too busy to be looking for it.", "source": "Афоризм"},
        {"phrase": "The harder you work for something, the greater you'll feel when you achieve it.", "source": "Афоризм"},
        {"phrase": "Dream big and dare to fail.", "source": "Афоризм"},
    ],
    "Цитаты": [
        {"phrase": "The only limit to our realization of tomorrow is our doubts of today.", "source": "Цитата: Franklin D. Roosevelt"},
        {"phrase": "In the middle of every difficulty lies opportunity.", "source": "Цитата: Albert Einstein"},
        {"phrase": "Life is what happens when you're busy making other plans.", "source": "Цитата: John Lennon"},
    ],
    "Кино": [
        {"phrase": "I'm going to make him an offer he can't refuse.", "source": "Фильм: The Godfather"},
        {"phrase": "May the Force be with you.", "source": "Фильм: Star Wars"},
        {"phrase": "I'll be back.", "source": "Фильм: The Terminator"},
    ],
    "Песни": [
        {"phrase": "We don't need no education.", "source": "Песня: Pink Floyd – Another Brick in the Wall"},
        {"phrase": "I still haven't found what I'm looking for.", "source": "Песня: U2 – I Still Haven’t Found What I’m Looking For"},
        {"phrase": "Is this the real life? Is this just fantasy?", "source": "Песня: Queen – Bohemian Rhapsody"},
    ],
    "Любая тема": []  # Этот список будет собираться автоматически
}

# Объединение всех фраз для категории "Любая тема"
all_phrases = []
for group in PHRASES.values():
    all_phrases.extend(group)
PHRASES["Любая тема"] = all_phrases


def get_random_phrase_with_word(word: str, category: str) -> dict:
    # Возвращает фразу из категории, содержащую слово (если возможно), иначе случайную
    phrases = PHRASES.get(category, [])
    if not phrases:
        phrases = PHRASES["Любая тема"]

    # Пытаемся найти фразу, содержащую слово
    for phrase_data in phrases:
        if word.lower() in phrase_data["phrase"].lower():
            return phrase_data

    return random.choice(phrases)
