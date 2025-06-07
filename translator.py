import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_word(word: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional English-Russian translator."},
                {"role": "user", "content": f"Translate the word '{word}' from English to Russian."}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Примерный перевод"

def translate_text(text: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional English-Russian translator."},
                {"role": "user", "content": f"Translate the following English sentence to Russian:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""
