import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# DEBUG: проверим, подхватился ли ключ
print(f"[DEBUG] OPENAI_API_KEY: {openai.api_key}")

def translate_word(word: str) -> str:
    if not openai.api_key:
        print(f"[ERROR] API ключ не найден")
        return "ошибка перевода"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — переводчик. Переводи только одним словом на русский."},
                {"role": "user", "content": f"Переведи слово '{word}' на русский язык."}
            ],
            temperature=0.3,
            max_tokens=20
        )
        translation = response['choices'][0]['message']['content'].strip()
        return translation
    except Exception as e:
        print(f"[ERROR] Ошибка перевода слова '{word}': {e}")
        return "ошибка перевода"

def translate_text(text: str) -> str:
    if not openai.api_key:
        print(f"[ERROR] API ключ не найден")
        return "ошибка перевода"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — переводчик. Переводи текст на русский язык."},
                {"role": "user", "content": f"Переведи: {text}"}
            ],
            temperature=0.5,
            max_tokens=100
        )
        translation = response['choices'][0]['message']['content'].strip()
        return translation
    except Exception as e:
        print(f"[ERROR] Ошибка перевода текста: {e}")
        return "ошибка перевода"
