import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, LargeBinary, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY  # Для PostgreSQL
from dotenv import load_dotenv
load_dotenv()
# Конфигурация из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)  # echo=True для дебаггинга
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    chat_id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    instagram = Column(String, nullable=True)
    bio = Column(String, nullable=False)
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    birth_date = Column(String, nullable=False)  # Лучше использовать Date
    gender = Column(String, nullable=False)
    photos = Column(ARRAY(LargeBinary), nullable=True)  # Массив фотографий
    is_profile_complete = Column(Boolean, default=False)
    liked = Column(ARRAY(BigInteger), default=[])  # Массив ID вместо строки

    __table_args__ = {'extend_existing': True}

# Создание таблиц
Base.metadata.create_all(engine)