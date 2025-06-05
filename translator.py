import os
import openai
import random

openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_word(word):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Переведи слово на русский. Только перевод, без пояснений."},
                {"role": "user", "content": word}
            ]
        )
        return response.choices[0].message["content"].strip()
    except Exception:
        return "ошибка перевода"

def generate_example(word, category):
    try:
        prompt_map = {
            "Афоризмы": "Придумай афоризм с этим словом",
            "Цитаты": "Придумай известную цитату с этим словом",
            "Кино": "Придумай реплику из фильма с этим словом и укажи название фильма",
            "Песни": "Придумай строчку из песни с этим словом и укажи название песни",
            "Любая тема": "Придумай предложение с этим словом из повседневной жизни"
        }

        prompt = prompt_map.get(category, prompt_map["Любая тема"])

        full_prompt = f"{prompt}. Затем переведи это предложение на русский. Укажи источник в конце."

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты создаёшь короткие примеры на английском и переводишь их на русский."},
                {"role": "user", "content": f"Слово: {word}. {full_prompt}"}
            ]
        )
        content = response.choices[0].message["content"].strip()
        parts = content.split("\n")
        en = parts[0].strip()
        ru = parts[1].strip() if len(parts) > 1 else ""
        source = ""
        for p in parts:
            if "source" in p.lower() or "источник" in p.lower():
                source = p.replace("Источник:", "").replace("Source:", "").strip(". ")
        return en, source or category, ru
    except Exception:
        return "⚠️ Ошибка генерации примера.", "", ""
