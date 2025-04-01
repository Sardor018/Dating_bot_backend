import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, LargeBinary, BigInteger, Date, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.dialects.postgresql import ARRAY  # Для PostgreSQL
from dotenv import load_dotenv
load_dotenv()
# Конфигурация из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)  # echo=True для дебаггинга
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = "users"  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True, index=True)  # Первичный ключ
    chat_id = Column(BigInteger, unique=True, index=True)  # Уникальный chat_id
    selected_language = Column(String, nullable=True) # Выбранный язык
    name = Column(String, nullable=True)  # Имя пользователя
    instagram = Column(String, nullable=False)  # Instagram аккаунт (необязательный)
    about = Column(String, nullable=True)  # О себе
    country = Column(String, nullable=True)  # Страна
    city = Column(String, nullable=True)  # Город
    birthday = Column(Date, nullable=True)  # Дата рождения
    gender = Column(String, nullable=True)  # Пол
    liked = Column(ARRAY(BigInteger), default=[])  # Массив ID вместо строки
    is_verified = Column(Boolean, default=False)  # Статус верификации (после селфи)

    # Связи с другими таблицами
    photos = relationship("Photo", back_populates="owner")
    selfie = relationship("Selfie", uselist=False, back_populates="owner")
    agreement = relationship("Agreement", uselist=False, back_populates="owner")

# Модель фотографий
class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    user_chat_id = Column(BigInteger, ForeignKey("users.chat_id"))  # Используйте chat_id как внешний ключ
    file_path = Column(ARRAY(LargeBinary), nullable=True)

    owner = relationship("User", back_populates="photos", foreign_keys=[user_chat_id])

# Модель селфи (верификация)
class Selfie(Base):
    __tablename__ = "selfies"  # Имя таблицы для селфи

    id = Column(Integer, primary_key=True, index=True)  # Первичный ключ
    user_id = Column(Integer, ForeignKey("users.id"))  # Внешний ключ к пользователю
    file_path = Column(LargeBinary, nullable=False)  # Путь к файлу селфи

    # Связываем селфи с пользователем
    owner = relationship("User", back_populates="selfie")

# Модель соглашения
class Agreement(Base):
    __tablename__ = "agreements"  # Имя таблицы для соглашений

    id = Column(Integer, primary_key=True, index=True)  # Первичный ключ
    user_id = Column(Integer, ForeignKey("users.id"))  # Внешний ключ к пользователю
    accepted = Column(Boolean, default=False)  # Принято ли соглашение (булев тип)

    # Связываем соглашение с пользователем
    owner = relationship("User", back_populates="agreement")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    from_user = Column(BigInteger, ForeignKey("users.id"))
    to_user = Column(BigInteger, ForeignKey("users.id"))
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    sender = relationship("User", foreign_keys=[from_user], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[to_user], backref="received_messages")
# Создание таблиц
Base.metadata.create_all(engine)