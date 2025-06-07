import sqlite3
from datetime import datetime

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    translate_words INTEGER DEFAULT 1,
    frequency INTEGER DEFAULT 1,
    words_per_message INTEGER DEFAULT 1,
    category TEXT DEFAULT 'Любая тема',
    translate_phrases INTEGER DEFAULT 1
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_words (
    user_id INTEGER,
    word TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS phrases (
    phrase TEXT,
    word TEXT,
    translation TEXT,
    category TEXT,
    source TEXT
)
''')

conn.commit()

def init_user_settings(user_id):
    cursor.execute('SELECT 1 FROM user_settings WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO user_settings (user_id)
            VALUES (?)
        ''', (user_id,))
        conn.commit()

def set_user_setting(user_id, setting, value):
    cursor.execute(f'''
        UPDATE user_settings
        SET {setting} = ?
        WHERE user_id = ?
    ''', (value, user_id))
    conn.commit()

def get_user_settings(user_id):
    cursor.execute('''
        SELECT translate_words, frequency, words_per_message, category, translate_phrases
        FROM user_settings
        WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            'translate_words': bool(row[0]),
            'frequency': row[1],
            'words_per_message': row[2],
            'category': row[3],
            'translate_phrases': bool(row[4])
        }
    return {
        'translate_words': True,
        'frequency': 1,
        'words_per_message': 1,
        'category': 'Любая тема',
        'translate_phrases': True
    }

def add_user_word(user_id, word):
    cursor.execute('''
        INSERT INTO user_words (user_id, word, added_at)
        VALUES (?, ?, ?)
    ''', (user_id, word.lower(), datetime.utcnow()))
    conn.commit()

def get_words_by_user(user_id):
    cursor.execute('''
        SELECT word FROM user_words
        WHERE user_id = ?
    ''', (user_id,))
    return [row[0] for row in cursor.fetchall()]

def delete_word(user_id, word):
    cursor.execute('''
        DELETE FROM user_words
        WHERE user_id = ? AND word = ?
    ''', (user_id, word.lower()))
    conn.commit()

def add_phrase(word, phrase, translation, category, source):
    cursor.execute('''
        INSERT INTO phrases (word, phrase, translation, category, source)
        VALUES (?, ?, ?, ?, ?)
    ''', (word.lower(), phrase, translation, category, source))
    conn.commit()

def get_random_phrase_with_word(word, category=None):
    if category and category != "Любая тема":
        cursor.execute('''
            SELECT phrase, translation, source
            FROM phrases
            WHERE word = ? AND category = ?
            ORDER BY RANDOM()
            LIMIT 1
        ''', (word.lower(), category))
    else:
        cursor.execute('''
            SELECT phrase, translation, source
            FROM phrases
            WHERE word = ?
            ORDER BY RANDOM()
            LIMIT 1
        ''', (word.lower(),))
    return cursor.fetchone()
