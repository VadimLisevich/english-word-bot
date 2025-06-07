import sqlite3
from datetime import datetime

DB_NAME = 'bot_database.db'


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            translate_word INTEGER DEFAULT 1,
            send_frequency INTEGER DEFAULT 1,
            words_per_message INTEGER DEFAULT 1,
            phrase_category TEXT DEFAULT 'Любая тема',
            translate_phrase INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            translation TEXT,
            added_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


def add_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()


def set_user_setting(user_id, setting, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f'UPDATE users SET {setting} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()
    conn.close()


def get_user_settings(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {
            'user_id': result[0],
            'translate_word': result[1],
            'send_frequency': result[2],
            'words_per_message': result[3],
            'phrase_category': result[4],
            'translate_phrase': result[5]
        }
    return None


def add_user_word(user_id, word, translation):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO words (user_id, word, translation, added_at) VALUES (?, ?, ?, ?)',
              (user_id, word, translation, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_words_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT word FROM words WHERE user_id = ?', (user_id,))
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words


def delete_word(user_id, word):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM words WHERE user_id = ? AND word = ?', (user_id, word))
    conn.commit()
    conn.close()


def get_random_word(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT word FROM words WHERE user_id = ? ORDER BY RANDOM() LIMIT 1', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def get_all_user_ids():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users
