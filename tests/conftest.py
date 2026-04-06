from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.chores_planner.models.calendar_event import CalendarEvent
from src.chores_planner.models.chore import Chore
from src.db import Base, get_session_depends
from src.main import app


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session_depends] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def vacuum_chore(db_session):
    chore = Chore(name="Vacuum", duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
    db_session.add(chore)
    await db_session.flush()
    return chore


@pytest_asyncio.fixture
async def vacuum_calendar_event(db_session, vacuum_chore):
    event = CalendarEvent(
        calendar_event_id="gcal_abc",
        starts_from=datetime(2026, 3, 30, 10, 0),
        chore_id=vacuum_chore.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event
