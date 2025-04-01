import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, LargeBinary, BigInteger, Date, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.dialects.postgresql import ARRAY
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)  # Обязательное поле
    selected_language = Column(String, nullable=True)
    name = Column(String, nullable=True)
    instagram = Column(String, nullable=True)  # Поле необязательное
    about = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    birthday = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    liked = Column(ARRAY(BigInteger), default=[])
    is_verified = Column(Boolean, default=False)

    photos = relationship("Photo", back_populates="owner")
    selfie = relationship("Selfie", uselist=False, back_populates="owner")
    agreement = relationship("Agreement", uselist=False, back_populates="owner")

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    user_chat_id = Column(BigInteger, ForeignKey("users.chat_id"), nullable=False)
    file_path = Column(String, nullable=False)  # Храним путь к файлу как строку

    owner = relationship("User", back_populates="photos")

class Selfie(Base):
    __tablename__ = "selfies"

    id = Column(Integer, primary_key=True, index=True)
    user_chat_id = Column(BigInteger, ForeignKey("users.chat_id"), nullable=False)
    file_path = Column(String, nullable=False)

    owner = relationship("User", back_populates="selfie")

class Agreement(Base):
    __tablename__ = "agreements"

    id = Column(Integer, primary_key=True, index=True)
    user_chat_id = Column(BigInteger, ForeignKey("users.chat_id"), nullable=False)
    accepted = Column(Boolean, default=False)

    owner = relationship("User", back_populates="agreement")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    from_user = Column(BigInteger, ForeignKey("users.chat_id"))
    to_user = Column(BigInteger, ForeignKey("users.chat_id"))
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    sender = relationship("User", foreign_keys=[from_user], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[to_user], backref="received_messages")

Base.metadata.create_all(engine)