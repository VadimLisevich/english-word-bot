import random

phrases = {
    "Кино": [
        {"text": "I'm executing the plan perfectly, just like always.", "source": "Фильм: Inception"},
        {"text": "Life finds a way.", "source": "Фильм: Jurassic Park"},
        {"text": "May the Force be with you.", "source": "Фильм: Star Wars"},
    ],
    "Песни": [
        {"text": "We will, we will rock you!", "source": "Песня: Queen – We Will Rock You"},
        {"text": "Hello from the other side.", "source": "Песня: Adele – Hello"},
        {"text": "Cause baby you're a firework.", "source": "Песня: Katy Perry – Firework"},
    ],
    "Афоризмы": [
        {"text": "The only limit to our realization of tomorrow is our doubts of today.", "source": "Афоризм: Franklin D. Roosevelt"},
        {"text": "In the middle of difficulty lies opportunity.", "source": "Афоризм: Albert Einstein"},
    ],
    "Цитаты": [
        {"text": "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.", "source": "Цитата: Ralph Waldo Emerson"},
        {"text": "The purpose of our lives is to be happy.", "source": "Цитата: Dalai Lama"},
    ],
    "Любая тема": []  # будет заполнено из всех остальных категорий
}

# объединяем все в "Любая тема"
for category in ["Кино", "Песни", "Афоризмы", "Цитаты"]:
    phrases["Любая тема"].extend(phrases[category])

def get_random_phrase_with_word(word: str, category: str) -> dict:
    matching_phrases = [p for p in phrases.get(category, []) if word.lower() in p["text"].lower()]
    if matching_phrases:
        return random.choice(matching_phrases)
    return random.choice(phrases.get(category, [])) if phrases.get(category) else {}
