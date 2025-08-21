rom aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import asyncio
import google.generativeai as genai
import requests
import time
import os

# --- Загрузка конфига ---
# Скопируй config.example.py → config.py и заполни
try:
    from config import *
except ImportError:
    raise Exception("Создай config.py на основе config.example.py")

# --- Настройка Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# --- Инициализация бота ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- Генерация текста ---
def generate_news(topic="технологии"):
    prompt = f"Напиши короткую, живую новость на 3–4 предложения на тему: {topic}. Без заголовка."
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

# --- TTS: текст в речь (Yandex) ---
def text_to_speech(text, output_file="audio.mp3"):
    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    headers = {'Authorization': f'Api-Key {YANDEX_API_KEY}'}

    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': 'alena',
        'format': 'mp3',
        'speed': '1.0'
    }

    response = requests.post(url, headers=headers, data=data, stream=True)
    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file
    else:
        raise Exception(f"TTS error: {response.text}")

# --- Создание видео с аватаром (D-ID) ---
def create_avatar_video(text):
    # Озвучиваем текст
    audio_file = "temp_audio.mp3"
    text_to_speech(text, audio_file)

    # Загружаем аудио на временный хостинг
    with open(audio_file, 'rb') as f:
        upload_resp = requests.post('https://file.io', files={'file': f})
    audio_url = upload_resp.json()['link']

    # Отправляем в D-ID
    talk_url = "https://api.d-id.com/talks"
    headers = {
        "Authorization": DID_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "source_url": AVATAR_IMAGE_URL,
        "script": {
            "type": "audio",
            "audio_url": audio_url
        },
        "config": {
            "fluent": True,
            "pad_audio": 0.0
        }
    }

    response = requests.post(talk_url, json=payload, headers=headers)
    if response.status_code != 201:
        raise Exception(f"D-ID error: {response.text}")
    
    talk_id = response.json()['id']

    # Ждём готовности
    while True:
        status = requests.get(f"{talk_url}/{talk_id}", headers=headers)
        data = status.json()
        if data.get('status') == 'done':
            return data['result_url']
        elif data.get('status') == 'error':
            raise Exception(f"Ошибка D-ID: {data}")
        time.sleep(5)

# --- Обработчик команд ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🎙️ Привет! Я — цифровой новостной спикер. Жми /news, чтобы посмотреть выпуск!")

@dp.message_handler(commands=['news'])
async def send_news(message: types.Message):
    await message.answer("⏳ Генерирую новость...")

    try:
        # 1. Генерация текста
        text = generate_news("новости технологий")

        # 2. Создание видео (в отдельном потоке)
        loop = asyncio.get_event_loop()
        video_url = await loop.run_in_executor(None, create_avatar_video, text)

        # 3. Отправка видео
        await message.answer_video(video=video_url, caption="🎥 Ваш персональный выпуск новостей")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
