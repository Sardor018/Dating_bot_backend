import os
import asyncio
import base64
import shutil
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from aiogram import F
from datetime import datetime
from fastapi.responses import JSONResponse
from app.database import SessionLocal, User, engine
from app import database

# Импортируем наши модели, схемы и настройки базы данных
import schemas


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

# Создаем таблицы в базе данных (если они еще не созданы)
database.Base.metadata.create_all(bind=engine)

# Зависимость для получения сессии БД в каждом запросе
def get_db():
    db = SessionLocal()  # Открываем новую сессию
    try:
        yield db  # Возвращаем сессию для использования в эндпоинте
    finally:
        db.close()  # Закрываем сессию после обработки запроса

# Эндпоинт для сохранения выбранного языка (создание/обновление пользователя)
# Эндпоинты FastAPI
@app.get("/check_user")
async def check_user(chat_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter_by(chat_id=chat_id).first()
        return {"is_profile_complete": user.is_profile_complete if user else False}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/like")
async def like_user(request: schemas.LikeRequest, db: Session = Depends(get_db)):
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
        "min_age_partner": user.min_age_partner if user.min_age_partner is not None else 18,  # Значение по умолчанию
        "photos": photos_base64,
        "is_profile_complete": user.is_profile_complete
    }

@app.post("/api/user/language", response_model=schemas.UserResponse)
def set_language(selected_language: str = Form(...), db: Session = Depends(get_db)):
    """
    Принимает выбранный язык и создает нового пользователя.
    """
    user = database.User(selected_language=selected_language)
    db.add(user)
    db.commit()
    db.refresh(user)  # Обновляем объект пользователя, чтобы получить его id
    return user  # Возвращаем данные пользователя

# Эндпоинт для сохранения личных данных пользователя
@app.post("/api/user/profile", response_model=schemas.UserResponse)
def update_profile(
    user_id: int = Form(...),
    name: str = Form(...),
    instagram: str = Form(""),
    about: str = Form(""),
    country: str = Form(""),
    city: str = Form(""),
    birthday: str = Form(...),  # Принимаем дату в виде строки
    gender: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Обновляет данные профиля пользователя.
    """
    # Получаем пользователя по идентификатору
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    # Обновляем поля профиля
    user.name = name
    user.instagram = instagram
    user.about = about
    user.country = country
    user.city = city
    try:
        # Преобразуем строку в дату
        user.birthday = datetime.strptime(birthday, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты")
    user.gender = gender

    db.commit()
    db.refresh(user)
    return user

# Эндпоинт для загрузки фотографий и соглашения
@app.post("/api/user/photos")
def upload_photos_and_agreement(
    user_id: int = Form(...),
    accepted: bool = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Загружает до 3 фотографий и сохраняет согласие с юридическим соглашением.
    """
    # Проверяем лимит фотографий
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Можно загрузить не более 3 фотографий")

    # Сохраняем каждое фото на диск и создаем запись в БД
    photo_paths = []
    for file in files:
        file_location = f"uploads/photos/{user_id}_{file.filename}"
        # Создаем директорию, если не существует
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)  # Записываем файл на диск
        photo_paths.append(file_location)
        # Создаем запись для каждого фото
        photo = database.Photo(user_id=user_id, file_path=file_location)
        db.add(photo)

    # Создаем запись о принятии соглашения
    agreement = database.Agreement(user_id=user_id, accepted=accepted)
    db.add(agreement)
    db.commit()
    return JSONResponse(content={"detail": "Фотографии и соглашение сохранены"})

# Эндпоинт для загрузки селфи для верификации пользователя
@app.post("/api/user/selfie")
def upload_selfie(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Принимает селфи, сохраняет его и отмечает пользователя как верифицированного.
    """
    file_location = f"uploads/selfies/{user_id}_{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)  # Сохраняем файл селфи на диск

    # Создаем запись селфи в БД
    selfie = database.Selfie(user_id=user_id, file_path=file_location)
    db.add(selfie)

    # Обновляем статус пользователя на верифицированного
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_verified = True

    db.commit()
    return JSONResponse(content={"detail": "Селфи сохранено, аккаунт подтвержден"})

# Эндпоинт для получения данных пользователя (например, для редактирования профиля)
@app.get("/api/user/profile/{user_id}", response_model=schemas.UserResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """
    Возвращает данные пользователя по его идентификатору.
    """
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

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
