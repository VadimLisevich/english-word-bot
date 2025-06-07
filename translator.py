import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


def translate_word(word: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Переведи на русский слово '{word}' одним словом."}
            ],
            max_tokens=20,
            temperature=0.3,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ошибка перевода слова '{word}': {e}")
        return "ошибка перевода"


def translate_text(text: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Переведи на русский следующий текст:\n{text}"}
            ],
            max_tokens=100,
            temperature=0.3,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ошибка перевода текста: {e}")
        return "ошибка перевода"
