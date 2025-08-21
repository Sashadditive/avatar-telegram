from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import asyncio

# Импорт конфига
from config import TELEGRAM_TOKEN, YANDEX_GPT_API_KEY, FOLDER_ID, DID_API_KEY, AVATAR_IMAGE_URL

# Импорт утилит
from utils.generate_text_yandex import generate_news_yandex
from utils.avatar import create_avatar_video

# --- Инициализация бота ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- Обработчики ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🎙️ Привет! Я — цифровой новостной спикер. Жми /news, чтобы посмотреть выпуск!")

@dp.message_handler(commands=['news'])
async def send_news(message: types.Message):
    await message.answer("⏳ Генерирую новость...")

    try:
        # 1. Генерация текста через YandexGPT
        topic = "последние новости в мире технологий"
        news_text = generate_news_yandex(
            topic=topic,
            api_key=YANDEX_GPT_API_KEY,
            folder_id=FOLDER_ID
        )

        # 2. Генерация видео с аватаром
        loop = asyncio.get_event_loop()
        video_url = await loop.run_in_executor(
            None,
            create_avatar_video,
            news_text,
            YANDEX_GPT_API_KEY,  # используем тот же ключ (или можно отдельный TTS)
            DID_API_KEY,
            AVATAR_IMAGE_URL
        )

        # 3. Отправка видео
        await message.answer_video(video=video_url, caption="🎥 Ваш персональный выпуск новостей")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# --- Запуск ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
