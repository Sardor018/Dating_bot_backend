import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram import F
from orm_query import save_user
from config import TELEGRAM_TOKEN, WEB_APP_URL  # Новый файл config.py

# Инициализация
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message: types.Message):
    chat_id = message.chat.id
    await message.answer(f"Привет! Твой chat_id: {chat_id}")
    try:
        # await save_user(chat_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Войти", web_app=WebAppInfo(url=f"{WEB_APP_URL}?chat_id={chat_id}"))
        ]])
        await message.answer('Нажми кнопку, чтобы войти в приложение:', reply_markup=keyboard)
    except Exception as e:
        await message.answer('Произошла ошибка. Попробуйте позже.')
        print(f"Ошибка: {e}")

async def main():
    await bot.delete_webhook()
    await dp.start_polling(bot)

async def bot_session_close():
    await bot.session.close()

if __name__ == '__main__':
    try:
        print("Бот запущен")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
    finally:
        asyncio.run(bot_session_close())
    