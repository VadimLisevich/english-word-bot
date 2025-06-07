import json
import os

WORDS_DB_PATH = "words_db.json"
SETTINGS_DB_PATH = "settings_db.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Работа со словами
def get_user_words(user_id):
    data = load_json(WORDS_DB_PATH)
    return data.get(str(user_id), [])

def add_user_word(user_id, word, translation):
    data = load_json(WORDS_DB_PATH)
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append({"word": word, "translation": translation})
    save_json(data, WORDS_DB_PATH)

def remove_user_word(user_id, word):
    data = load_json(WORDS_DB_PATH)
    user_id = str(user_id)
    if user_id in data:
        data[user_id] = [w for w in data[user_id] if w["word"] != word]
        save_json(data, WORDS_DB_PATH)

# Работа с настройками
def get_user_settings(user_id):
    data = load_json(SETTINGS_DB_PATH)
    return data.get(str(user_id), {})

def update_user_settings(user_id, new_settings):
    data = load_json(SETTINGS_DB_PATH)
    data[str(user_id)] = new_settings
    save_json(data, SETTINGS_DB_PATH)

def clear_user_data(user_id):
    uid = str(user_id)
    words = load_json(WORDS_DB_PATH)
    settings = load_json(SETTINGS_DB_PATH)
    if uid in words:
        del words[uid]
        save_json(words, WORDS_DB_PATH)
    if uid in settings:
        del settings[uid]
        save_json(settings, SETTINGS_DB_PATH)
