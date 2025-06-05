import sqlite3
import random

DB_NAME = "words.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS words (
        user_id INTEGER,
        word TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER PRIMARY KEY,
        translate_words BOOLEAN,
        frequency INTEGER,
        words_per_message INTEGER,
        category TEXT,
        translate_phrases BOOLEAN
    )""")
    conn.commit()
    conn.close()

def add_word(user_id, word):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO words (user_id, word) VALUES (?, ?)", (user_id, word))
    conn.commit()
    conn.close()

def get_words_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT word FROM words WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def delete_word(user_id, word):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()
    conn.close()

def get_random_user_words(user_id, count):
    words = get_words_by_user(user_id)
    return random.sample(words, min(count, len(words)))

def get_user_settings(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "translate_words": bool(row[1]),
            "frequency": row[2],
            "words_per_message": row[3],
            "category": row[4],
            "translate_phrases": bool(row[5])
        }
    return {
        "user_id": user_id,
        "translate_words": True,
        "frequency": 1,
        "words_per_message": 1,
        "category": "Любая тема",
        "translate_phrases": True
    }

def set_user_setting(user_id, setting_key, value):
    settings = get_user_settings(user_id)
    settings[setting_key] = value
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO settings (user_id, translate_words, frequency, words_per_message, category, translate_phrases)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, settings["translate_words"], settings["frequency"], settings["words_per_message"], settings["category"], settings["translate_phrases"]))
    conn.commit()
    conn.close()
