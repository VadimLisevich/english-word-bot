import json
import os

DB_PATH = "words_db.json"

def load_words():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_words(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_words(user_id):
    data = load_words()
    return data.get(str(user_id), [])

def add_user_word(user_id, word, translation):
    data = load_words()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append({"word": word, "translation": translation})
    save_words(data)

def remove_user_word(user_id, word):
    data = load_words()
    user_id = str(user_id)
    if user_id in data:
        data[user_id] = [w for w in data[user_id] if w["word"] != word]
        save_words(data)

def clear_user_data(user_id):
    data = load_words()
    user_id = str(user_id)
    if user_id in data:
        del data[user_id]
        save_words(data)
