import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_word(word: str) -> str:
    prompt = f"Переведи на русский слово: {word}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.3
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print("Ошибка перевода слова:", e)
        return "ошибка перевода"

def translate_text(text: str) -> str:
    prompt = f"Переведи на русский текст: {text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print("Ошибка перевода текста:", e)
        return "ошибка перевода"
