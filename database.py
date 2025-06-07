import sqlite3
import os

DB_PATH = os.path.join("data", "database.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            translate_word INTEGER DEFAULT 0,
            reminders_per_day INTEGER DEFAULT 1,
            words_per_message INTEGER DEFAULT 1,
            category TEXT DEFAULT 'Любая тема',
            translate_phrase INTEGER DEFAULT 0
        )
    ''')

    # Добавляем недостающие колонки
    for column, col_type, default in [
        ("translate_word", "INTEGER", "0"),
        ("reminders_per_day", "INTEGER", "1"),
        ("words_per_message", "INTEGER", "1"),
        ("category", "TEXT", "'Любая тема'"),
        ("translate_phrase", "INTEGER", "0")
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type} DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # колонка уже есть

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            word_translation TEXT,
            source TEXT,
            phrase TEXT,
            phrase_translation TEXT
        )
    ''')

    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def set_user_setting(user_id, key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    return {}

def init_user_settings(user_id):
    add_user(user_id)

def add_user_word(user_id, word, word_translation, source, phrase, phrase_translation):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO words (user_id, word, word_translation, source, phrase, phrase_translation) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, word, word_translation, source, phrase, phrase_translation)
    )
    conn.commit()
    conn.close()

def get_words_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM words WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def delete_word(user_id, word):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()
    conn.close()

def get_random_phrase_with_word(user_id, word):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT phrase, source, phrase_translation FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "phrase": result[0],
            "source": result[1],
            "translation": result[2]
        }
    return None

def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
