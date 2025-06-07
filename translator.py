import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


def translate_word(word: str, target_language: str = "Russian") -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Ты переводчик с английского на {target_language}."},
                {"role": "user", "content": f"Переведи слово '{word}' на {target_language}. Только перевод, без кавычек и пояснений."}
            ],
            temperature=0.3,
            max_tokens=20,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка перевода слова: {e}")
        return "Примерный перевод"


def translate_text(text: str, target_language: str = "Russian") -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Ты переводчик с английского на {target_language}."},
                {"role": "user", "content": f"Переведи следующий текст: '{text}'"}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка перевода текста: {e}")
        return ""
