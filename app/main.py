from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, validator
from typing import Optional, List
import os
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from aiogram import F
import base64
from datetime import datetime

# Предполагается, что база данных настроена в app.database
from app.database import SessionLocal, User

# Загрузка переменных окружения из .env в корне backend
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")  # URL фронтенда

# Инициализация FastAPI
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_APP_URL],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic-модели
class LikeRequest(BaseModel):
    chat_id: int
    target_chat_id: int

class ProfileData(BaseModel):
    chat_id: int
    name: str
    instagram: Optional[str] = None
    bio: str
    country: str
    city: str
    birth_date: str
    gender: str
    min_age_partner: Optional[int] = 18  # Добавлено поле для минимального возраста партнёра

    @validator('birth_date')
    def validate_birth_date(cls, v):
        try:
            birth = datetime.strptime(v, '%Y-%m-%d')
            if (datetime.now().year - birth.year) < 18:
                raise ValueError("Minimum age is 18")
            return v
        except ValueError:
            raise ValueError("Invalid date format or age")

# Зависимость для базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Эндпоинты FastAPI
@app.get("/check_user")
async def check_user(chat_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter_by(chat_id=chat_id).first()
        return {"is_profile_complete": user.is_profile_complete if user else False}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/like")
async def like_user(request: LikeRequest, db: Session = Depends(get_db)):
    current_user = db.query(User).filter_by(chat_id=request.chat_id).first()
    target_user = db.query(User).filter_by(chat_id=request.target_chat_id).first()

    if not current_user or not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not current_user.liked:
        current_user.liked = []
    if request.target_chat_id not in current_user.liked:
        current_user.liked.append(request.target_chat_id)
        db.commit()

    match = request.chat_id in (target_user.liked or [])
    return {"match": match}

@app.post("/profile")
async def update_profile(
    chat_id: str = Form(...),
    name: str = Form(...),
    instagram: Optional[str] = Form(None),
    bio: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    min_age_partner: Optional[int] = Form(18),
    photos: List[UploadFile] = File(...),  # Принимаем несколько файлов
    db: Session = Depends(get_db)
):
    # Проверка формата файлов
    for photo in photos:
        if not photo.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only images are allowed")

    user = db.query(User).filter_by(chat_id=int(chat_id)).first()
    if not user:
        user = User(chat_id=int(chat_id))
        db.add(user)

    # Обновление текстовых данных
    user.name = name
    user.instagram = instagram
    user.bio = bio
    user.country = country
    user.city = city
    user.birth_date = birth_date
    user.gender = gender
    user.min_age_partner = min_age_partner  # Добавлено новое поле

    # Сохранение всех фотографий
    user.photos = user.photos or []
    for photo in photos:
        user.photos.append(await photo.read())

    user.is_profile_complete = True

    try:
        db.commit()
        return {"message": "Profile and photos updated successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates")
async def get_candidates(chat_id: int, db: Session = Depends(get_db)):
    current_user = db.query(User).filter_by(chat_id=chat_id).first()
    if not current_user or not current_user.is_profile_complete:
        raise HTTPException(status_code=400, detail="Profile not completed")
    
    candidates = db.query(User).filter(
        User.is_profile_complete == True,
        User.chat_id != chat_id,
        ~User.chat_id.in_(current_user.liked if current_user.liked else [])
    ).all()
    return [{
        "chat_id": c.chat_id,
        "name": c.name,
        "bio": c.bio,
        "photo": base64.b64encode(c.photos[0]).decode('utf-8') if c.photos and c.photos[0] else None
    } for c in candidates]

@app.get("/profile/{chat_id}")
async def get_profile(chat_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=int(chat_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    photos_base64 = [base64.b64encode(photo).decode('utf-8') for photo in user.photos] if user.photos else []
    return {
        "chat_id": str(user.chat_id),
        "name": user.name,
        "instagram": user.instagram,
        "bio": user.bio,
        "country": user.country,
        "city": user.city,
        "birth_date": user.birth_date,
        "gender": user.gender,
        "min_age_partner": user.min_age_partner,
        "photos": photos_base64,
        "is_profile_complete": user.is_profile_complete
    }

# Инициализация Aiogram
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(F.text == "/start")
async def start(message: types.Message):
    try:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text="Войти",
                web_app=WebAppInfo(url=WEB_APP_URL)  # Без параметров
            )
        ]])
        await message.answer('Нажми кнопку, чтобы войти в приложение:', reply_markup=keyboard)
        print(f"Сообщение отправлено в чат {message.chat.id}")
    except Exception as e:
        await message.answer('Произошла ошибка. Попробуйте позже.')
        print(f"Ошибка в /start: {type(e).__name__} - {str(e)}")

# Эндпоинт для вебхука
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    # Ручная обработка обновления
    await dp.feed_update(bot=bot, update=update)
    return {"status": "ok"}

# Установка вебхука при запуске
@app.on_event("startup")
async def on_startup():
    webhook_url = "https://dating-bot-backend.onrender.com/webhook"
    await bot.set_webhook(webhook_url)
    print(f"Webhook установлен: {webhook_url}")

# Отключение вебхука при завершении
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

# Закрытие сессии бота
async def bot_session_close():
    await bot.session.close()

if __name__ == "__main__":
    import uvicorn
    try:
        print("Бот и сервер запущены")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("Сервер остановлен")
    except Exception as e:
        print(f"Ошибка запуска: {type(e).__name__} - {str(e)}")
    finally:
        asyncio.run(bot_session_close())