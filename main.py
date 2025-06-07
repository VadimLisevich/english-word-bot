import sqlite3
import random

DB_NAME = "data.db"


def create_tables():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                translate_word INTEGER DEFAULT 1,
                send_frequency INTEGER DEFAULT 1,
                words_per_message INTEGER DEFAULT 1,
                category TEXT DEFAULT 'Любая тема',
                translate_phrase INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                user_id INTEGER,
                word TEXT,
                PRIMARY KEY (user_id, word)
            )
        """)
        conn.commit()


def init_user_settings(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()


def set_user_setting(user_id, key, value):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()


def get_user_settings(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "translate_word": row[1],
                "send_frequency": row[2],
                "words_per_message": row[3],
                "category": row[4],
                "translate_phrase": row[5],
            }
        return None


def add_user_word(user_id, word):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO words (user_id, word) VALUES (?, ?)", (user_id, word))
        conn.commit()


def get_words_by_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM words WHERE user_id = ?", (user_id,))
        return [row[0] for row in cursor.fetchall()]


def delete_word(user_id, word):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
        conn.commit()


def get_all_user_ids():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]


def get_random_phrase_with_word(word, category):
    phrases = {
        "Кино": [
            (f"I'm watching how he {word} everything around him.", "Inception"),
            (f"She {word} like a pro – very cinematic.", "Interstellar"),
        ],
        "Песни": [
            (f"And then she {word} the rhythm of my heart.", "Imagine"),
            (f"We {word} like stars in the night.", "Bohemian Rhapsody"),
        ],
        "Афоризмы": [
            (f"One who {word} wisely, lives fully.", "Лао-Цзы"),
            (f"To {word} is to shape the future.", "Сократ"),
        ],
        "Цитаты": [
            (f"He who {word} others is powerful.", "Цезарь"),
            (f"Only those who {word} understand truth.", "Ницше"),
        ],
        "Любая тема": [
            (f"When you {word} clearly, the world listens.", "Unknown"),
            (f"To {word} means to act with purpose.", "Unknown"),
        ]
    }

    options = phrases.get(category, phrases["Любая тема"])
    return random.choice(options)
