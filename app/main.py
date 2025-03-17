from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session
from app.database import SessionLocal, User
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional
import base64

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dating-bot-omega.vercel.app"],  # Укажите URL фронтенда позже
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    @validator('birth_date')
    def validate_birth_date(cls, v):
        from datetime import datetime
        try:
            birth = datetime.strptime(v, '%Y-%m-%d')
            if (datetime.now().year - birth.year) < 18:
                raise ValueError("Minimum age is 18")
            return v
        except ValueError:
            raise ValueError("Invalid date format or age")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/check_user")
async def check_user(chat_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=chat_id).first()
    return {"is_profile_complete": user.is_profile_complete if user else False}

@app.post("/like")
async def like_user(request: LikeRequest, db: Session = Depends(get_db)):
    current_user = db.query(User).filter_by(chat_id=request.chat_id).first()
    target_user = db.query(User).filter_by(chat_id=request.target_chat_id).first()

    if not current_user or not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Добавляем target_chat_id в список liked текущего пользователя
    if not current_user.liked:
        current_user.liked = []
    if request.target_chat_id not in current_user.liked:
        current_user.liked.append(request.target_chat_id)
        db.commit()

    # Проверяем, есть ли взаимный лайк
    match = request.chat_id in (target_user.liked or [])
    return {"match": match}
    

@app.post("/profile")
async def update_profile(
    chat_id: str = Form(...),
    name: str = Form(...),
    instagram: str = Form(None),
    bio: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    photo: UploadFile = File(...),  # Пока одно фото, можно расширить
    db: Session = Depends(get_db)
):
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only images are allowed")
    
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        user = User(chat_id=chat_id)
        db.add(user)
    
    user.name = name
    user.instagram = instagram
    user.bio = bio
    user.country = country
    user.city = city
    user.birth_date = birth_date
    user.gender = gender
    user.photos = user.photos or []  # Инициализируем как пустой массив, если null
    user.photos.append(await photo.read())  # Добавляем новое фото
    user.is_profile_complete = True
    
    db.commit()
    return {"message": "Profile updated successfully"}


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
        "photo": base64.b64encode(c.photo).decode('utf-8') if c.photo else None
    } for c in candidates]

@app.get("/profile/{chat_id}")
async def get_profile(chat_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(chat_id=str(chat_id)).first()  # Преобразуем chat_id в строку
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    photos_base64 = [base64.b64encode(photo).decode('utf-8') for photo in user.photos] if user.photos else []
    
    return {
        "chat_id": str(user.chat_id),  # Преобразуем в строку для соответствия frontend
        "name": user.name,
        "instagram": user.instagram,
        "bio": user.bio,
        "country": user.country,
        "city": user.city,
        "birth_date": user.birth_date,
        "gender": user.gender,
        "photos": photos_base64,
        "is_profile_complete": user.is_profile_complete
    }