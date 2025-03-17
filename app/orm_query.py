from database import User, SessionLocal
from sqlalchemy.exc import SQLAlchemyError

async def save_user(chat_id: int) -> bool:
    """
    Сохраняет нового пользователя в базе данных, если он еще не существует.
    Возвращает True, если пользователь уже был или успешно создан.
    """
    try:
        with SessionLocal() as session:
            if session.query(User).filter_by(chat_id=chat_id).first():
                return True
            new_user = User(chat_id=chat_id)
            session.add(new_user)
            session.commit()
            return True
    except SQLAlchemyError as e:
        print(f"Ошибка базы данных при сохранении пользователя: {e}")
        return False

# Альтернатива: переход на асинхронный SQLAlchemy (если нужен полный асинк)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:1D3fg34j0n@localhost/dating_app"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def save_user(chat_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        if await session.get(User, chat_id):
            return True
        session.add(User(chat_id=chat_id))
        await session.commit()
        return True
"""