import sqlite3

DB_NAME = "bot_database.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                translate_words BOOLEAN DEFAULT 1,
                reminders_per_day INTEGER DEFAULT 1,
                words_per_reminder INTEGER DEFAULT 1,
                category TEXT DEFAULT 'Любая тема',
                translate_phrases BOOLEAN DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                user_id INTEGER,
                word TEXT,
                translation TEXT,
                PRIMARY KEY (user_id, word)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phrases (
                word TEXT,
                phrase TEXT,
                translation TEXT,
                category TEXT,
                source TEXT
            )
        """)
        conn.commit()


def init_user_settings(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (user_id) VALUES (?)
            """, (user_id,))
            conn.commit()


def get_user_settings(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        return {}


def set_user_setting(user_id, key, value):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()


def add_user_word(user_id, word, translation):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO words (user_id, word, translation) VALUES (?, ?, ?)
        """, (user_id, word, translation))
        conn.commit()


def get_words_by_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT word, translation FROM words WHERE user_id = ?", (user_id,))
        return cursor.fetchall()


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


def get_random_phrase_with_word(word, category='Любая тема'):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if category == "Любая тема":
            cursor.execute("""
                SELECT phrase, translation, source FROM phrases
                WHERE LOWER(phrase) LIKE '%' || LOWER(?) || '%'
                ORDER BY RANDOM() LIMIT 1
            """, (word,))
        else:
            cursor.execute("""
                SELECT phrase, translation, source FROM phrases
                WHERE LOWER(phrase) LIKE '%' || LOWER(?) || '%' AND category = ?
                ORDER BY RANDOM() LIMIT 1
            """, (word, category))
        return cursor.fetchone()
