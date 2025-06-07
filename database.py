import sqlite3
from datetime import datetime

DB_NAME = "bot_database.db"


def init_db():
    create_tables()


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            translate_words INTEGER DEFAULT 0,
            reminders_per_day INTEGER DEFAULT 1,
            words_per_reminder INTEGER DEFAULT 1,
            category TEXT DEFAULT 'Любая тема',
            translate_phrases INTEGER DEFAULT 0
        )
    ''')

    # Таблица слов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            translation TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def add_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def add_user_if_not_exists(user_id: int):
    add_user(user_id)


def init_user_settings(user_id: int):
    add_user(user_id)


def add_user_word(user_id: int, word: str, translation: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO words (user_id, word, translation) VALUES (?, ?, ?)",
        (user_id, word, translation),
    )
    conn.commit()
    conn.close()


def get_words_by_user(user_id: int, limit: int = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = "SELECT word, translation FROM words WHERE user_id = ? ORDER BY RANDOM()"
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query, (user_id,))
    words = cursor.fetchall()
    conn.close()
    return words


def delete_word(user_id: int, word: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()
    conn.close()


def get_user_settings(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT translate_words, reminders_per_day, words_per_reminder, category, translate_phrases
        FROM users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "translate_words": bool(row[0]),
            "reminders_per_day": row[1],
            "words_per_reminder": row[2],
            "category": row[3],
            "translate_phrases": bool(row[4])
        }
    return None


def set_user_setting(user_id: int, key: str, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def get_all_user_ids():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
