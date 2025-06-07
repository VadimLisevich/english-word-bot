import sqlite3

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    translate_word INTEGER DEFAULT 1,
    reminders_per_day INTEGER DEFAULT 1,
    words_per_reminder INTEGER DEFAULT 1,
    phrase_category TEXT DEFAULT 'Любая тема',
    translate_phrase INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    word TEXT,
    translation TEXT
)
""")

def init_user_settings(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        conn.commit()

def set_user_setting(user_id, key, value):
    cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()

def get_user_settings(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "translate_word": row[1],
            "reminders_per_day": row[2],
            "words_per_reminder": row[3],
            "phrase_category": row[4],
            "translate_phrase": row[5]
        }
    return None

def add_user_word(user_id, word, translation):
    cursor.execute(
        "INSERT INTO words (user_id, word, translation) VALUES (?, ?, ?)",
        (user_id, word, translation)
    )
    conn.commit()

def get_words_by_user(user_id):
    cursor.execute("SELECT word, translation FROM words WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def delete_word(user_id, word):
    cursor.execute("DELETE FROM words WHERE user_id = ? AND word = ?", (user_id, word))
    conn.commit()

def get_all_user_ids():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]

def get_random_phrase_with_word(word, category):
    # Заглушка – ты можешь заменить этот блок на свой парсер/базу фраз
    dummy_phrases = {
        "Кино": [
            ("I'm executing the plan perfectly, just like always.", "Фильм: Inception"),
            ("May the Force be with you.", "Фильм: Star Wars"),
        ],
        "Песни": [
            ("Cause baby you're a firework!", "Песня: Firework — Katy Perry"),
            ("We will, we will rock you!", "Песня: Queen"),
        ],
        "Афоризмы": [
            ("The only limit to our realization of tomorrow is our doubts of today.", "Афоризм: F.D. Roosevelt"),
        ],
        "Цитаты": [
            ("Be yourself; everyone else is already taken.", "Цитата: Oscar Wilde"),
        ],
        "Любая тема": [
            ("The quick brown fox jumps over the lazy dog.", "Пример: Английская скороговорка"),
        ]
    }

    phrases = dummy_phrases.get(category, dummy_phrases["Любая тема"])
    for phrase, source in phrases:
        if word.lower() in phrase.lower():
            return phrase, source
    return phrases[0]
