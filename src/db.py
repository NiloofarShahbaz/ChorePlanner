from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from src import DB_PATH
from typing import Annotated
from fastapi import Depends

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        

async def get_session_depends() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session
        
        
SessionDep = Annotated[AsyncSession, Depends(get_session_depends)]