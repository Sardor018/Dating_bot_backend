from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class UserCreate(BaseModel):
    chat_id: int
    selected_language: Optional[str] = None
    name: Optional[str] = None
    instagram: Optional[str] = None
    about: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None

class UserResponse(UserCreate):
    is_verified: bool
    photos: List[str] = []
    selfie: Optional[str] = None
    agreement: Optional[bool] = False

    class Config:
        from_attributes = True

class LikeRequest(BaseModel):
    chat_id: int
    target_chat_id: int