from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base
from src.chores_planner.models.calendar_event import CalendarEvent, StatusChoices
from src.chores_planner.models.chore import Chore
from src.chores_planner.services.google_calendar import GoogleCalendarService


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _seed(session, chore_name="Vacuum", calendar_event_id="gcal_001"):
    chore = Chore(name=chore_name, duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
    session.add(chore)
    await session.flush()

    event = CalendarEvent(
        calendar_event_id=calendar_event_id,
        starts_from=datetime(2026, 3, 30, 10, 0),
        chore_id=chore.id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def _creds():
    return MagicMock()


def make_google_service_mock():
    mock_service = MagicMock()
    mock_service.__enter__ = MagicMock(return_value=mock_service)
    mock_service.__exit__ = MagicMock(return_value=False)
    mock_service.events.return_value.patch.return_value.execute.return_value = {}
    return mock_service


async def test_update_event_status_done_patches_google_title(session):
    event = await _seed(session, chore_name="Mop floors", calendar_event_id="gcal_xyz")
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(event.id, StatusChoices.DONE, session)

    patch_call = mock_service.events.return_value.patch
    patch_call.assert_called_once()
    call_kwargs = patch_call.call_args.kwargs
    assert call_kwargs["eventId"] == "gcal_xyz"
    assert call_kwargs["body"]["summary"] == "✅ Mop floors"


async def test_update_event_status_done_updates_db_status(session):
    event = await _seed(session)
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        updated = await svc.update_event_status(event.id, StatusChoices.DONE, session)

    assert updated.status == StatusChoices.DONE


async def test_update_event_status_done_persists_to_db(session):
    event = await _seed(session)
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(event.id, StatusChoices.DONE, session)

    result = await session.execute(select(CalendarEvent).where(CalendarEvent.id == event.id))
    refreshed = result.scalar_one()
    assert refreshed.status == StatusChoices.DONE


async def test_update_event_status_not_found_raises(session):
    svc = GoogleCalendarService()
    with pytest.raises(ValueError, match="not found"):
        await svc.update_event_status(9999, StatusChoices.DONE, session)


async def test_update_event_status_non_done_skips_google_api(session):
    event = await _seed(session)

    with patch("src.chores_planner.services.google_calendar.build") as mock_build:
        svc = GoogleCalendarService()
        await svc.update_event_status(event.id, StatusChoices.PENDING, session)

    mock_build.assert_not_called()


async def test_update_event_status_uses_calendar_id(session, monkeypatch):
    import src.chores_planner.services.google_calendar as gcal_module
    monkeypatch.setattr(gcal_module, "CALENDAR_ID", "test@group.calendar.google.com")

    event = await _seed(session)
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(event.id, StatusChoices.DONE, session)

    patch_kwargs = mock_service.events.return_value.patch.call_args.kwargs
    assert patch_kwargs["calendarId"] == "test@group.calendar.google.com"


async def test_update_event_status_google_api_error_propagates(session):
    event = await _seed(session)
    mock_service = make_google_service_mock()
    mock_service.events.return_value.patch.return_value.execute.side_effect = Exception("API error")

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        with pytest.raises(Exception, match="API error"):
            await svc.update_event_status(event.id, StatusChoices.DONE, session)
