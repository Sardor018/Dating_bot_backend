# schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# Схема для создания/обновления пользователя
class UserCreate(BaseModel):
    selected_language: Optional[str] = None  # Выбранный язык
    name: Optional[str] = None              # Имя пользователя
    instagram: Optional[str] = None         # Instagram аккаунт
    about: Optional[str] = None             # О себе
    country: Optional[str] = None           # Страна
    city: Optional[str] = None              # Город
    birthday: Optional[date] = None         # Дата рождения
    gender: Optional[str] = None            # Пол

# Схема для ответа с данными пользователя
class UserResponse(UserCreate):
    id: int
    is_verified: bool

    class Config:
        orm_mode = True  # Позволяет работать с объектами SQLAlchemy

# Схема для загрузки фотографий
class PhotoUpload(BaseModel):
    user_id: int
    # Здесь предполагается, что файлы будут обрабатываться через FormData,
    # поэтому для Pydantic можно оставить только идентификатор пользователя.

# Схема для загрузки селфи
class SelfieUpload(BaseModel):
    user_id: int
    # Аналогично для селфи, файл обрабатывается отдельно

# Схема для подтверждения соглашения
class AgreementCreate(BaseModel):
    user_id: int
    accepted: bool

class LikeRequest(BaseModel):
    chat_id: int
    target_chat_id: int