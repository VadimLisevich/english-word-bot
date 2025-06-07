import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_word(word):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — переводчик с английского на русский."},
                {"role": "user", "content": f"Переведи слово '{word}' на русский."}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка перевода слова: {e}")
        return "Примерный перевод"

def translate_text(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — переводчик с английского на русский."},
                {"role": "user", "content": f"Переведи этот текст на русский: {text}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка перевода текста: {e}")
        return ""
