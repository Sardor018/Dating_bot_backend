import os
import asyncio
import base64
import shutil
import logging
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from aiogram import F
from fastapi.responses import JSONResponse
from app.database import SessionLocal, User, engine
from app import schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/check_user")
async def check_user(chat_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    return {
        "is_verified": user.is_verified if user else False,
        "selected_language": user.selected_language if user else None
    }

@app.post("/api/user/language")
async def set_language(chat_id: int = Form(...), selected_language: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        # Set defaults for optional fields to avoid NOT NULL violations
        user = User(
            chat_id=chat_id,
            selected_language=selected_language,
            instagram="",  # Default to empty string if NOT NULL constraint exists
            name=None,
            about=None,
            country=None,
            city=None,
            birthday=None,
            gender=None
        )
        db.add(user)
    else:
        user.selected_language = selected_language
    db.commit()
    db.refresh(user)
    return {"chat_id": user.chat_id, "selected_language": user.selected_language}

@app.post("/api/user/profile")
async def update_profile(
    chat_id: int = Form(...),
    name: str = Form(...),
    instagram: str = Form(default=""),
    about: str = Form(default=""),
    country: str = Form(default=""),
    city: str = Form(default=""),
    birthday: str = Form(...),
    gender: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.name = name
    user.instagram = instagram
    user.about = about
    user.country = country
    user.city = city
    user.birthday = datetime.strptime(birthday, "%Y-%m-%d").date()
    user.gender = gender

    db.commit()
    db.refresh(user)
    return {"chat_id": user.chat_id, "name": user.name}

@app.post("/api/user/photos")
async def upload_photos_and_agreement(
    chat_id: int = Form(...),
    accepted: bool = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Можно загрузить не более 3 фотографий")

    photo_paths = []
    for file in files:
        file_location = f"uploads/photos/{chat_id}_{file.filename}"
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        photo = Photo(user_chat_id=chat_id, file_path=file_location)
        db.add(photo)
        photo_paths.append(file_location)

    agreement = db.query(Agreement).filter_by(user_chat_id=chat_id).first()
    if not agreement:
        agreement = Agreement(user_chat_id=chat_id, accepted=accepted)
        db.add(agreement)
    else:
        agreement.accepted = accepted

    db.commit()
    return {"detail": "Фотографии и соглашение сохранены"}

@app.post("/api/user/selfie")
async def upload_selfie(
    chat_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    file_location = f"uploads/selfies/{chat_id}_{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    selfie = db.query(Selfie).filter_by(user_chat_id=chat_id).first()
    if not selfie:
        selfie = Selfie(user_chat_id=chat_id, file_path=file_location)
        db.add(selfie)
    else:
        selfie.file_path = file_location

    user.is_verified = True
    db.commit()
    return {"detail": "Селфи сохранено, аккаунт подтвержден"}

@app.get("/api/user/profile/{chat_id}")
async def get_profile(chat_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    photos = [photo.file_path for photo in user.photos] if user.photos else []
    selfie = user.selfie.file_path if user.selfie else None
    agreement = user.agreement.accepted if user.agreement else False

    return {
        "chat_id": user.chat_id,
        "selected_language": user.selected_language,
        "name": user.name,
        "instagram": user.instagram,
        "about": user.about,
        "country": user.country,
        "city": user.city,
        "birthday": user.birthday.isoformat() if user.birthday else None,
        "gender": user.gender,
        "photos": photos,
        "selfie": selfie,
        "agreement": agreement,
        "is_verified": user.is_verified
    }

# Telegram Bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Войти", web_app=WebAppInfo(url=WEB_APP_URL))
    ]])
    await message.answer('Нажми кнопку, чтобы войти в приложение:', reply_markup=keyboard)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot=bot, update=update)
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    webhook_url = "https://dating-bot-backend.onrender.com/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook установлен: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

async def bot_session_close():
    await bot.session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)