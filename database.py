import json
import os

DB_PATH = "db.json"
SETTINGS_DB_PATH = "settings.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- WORDS DATABASE ---

def add_user_word(user_id, word_data):
    data = load_json(DB_PATH)
    uid = str(user_id)
    if uid not in data:
        data[uid] = []
    data[uid].append(word_data)
    save_json(data, DB_PATH)

def get_user_words(user_id):
    data = load_json(DB_PATH)
    return data.get(str(user_id), [])

def get_words_by_user(user_id):  # 🔧 добавляем эту функцию
    return get_user_words(user_id)

def delete_user_word(user_id, word_to_delete):
    data = load_json(DB_PATH)
    uid = str(user_id)
    if uid in data:
        data[uid] = [w for w in data[uid] if w['word'].lower() != word_to_delete.lower()]
        save_json(data, DB_PATH)
        return True
    return False

# --- SETTINGS DATABASE ---

def get_user_settings(user_id):
    data = load_json(SETTINGS_DB_PATH)
    return data.get(str(user_id), {})

def set_user_setting(user_id, key, value):
    data = load_json(SETTINGS_DB_PATH)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {}
    data[uid][key] = value
    save_json(data, SETTINGS_DB_PATH)

def set_default_settings(user_id):
    default = {
        "translate_words": True,
        "frequency": 1,
        "words_per_message": 1,
        "category": "Любая тема",
        "translate_examples": True,
    }
    data = load_json(SETTINGS_DB_PATH)
    data[str(user_id)] = default
    save_json(data, SETTINGS_DB_PATH)

def get_user_setting(user_id, key, default=None):
    settings = get_user_settings(user_id)
    return settings.get(key, default)
