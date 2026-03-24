from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.db import Base
from src.chores_planner.services.google_calendar import GoogleCalendarService
from src.chores_planner.models.calendar_event import CalendarEvent
from src.chores_planner.serializers.chore import ChoreCreateModel


def make_chore_data(**kwargs) -> ChoreCreateModel:
    defaults = dict(
        name="Vacuum",
        start_from=datetime(2026, 3, 24, 10, 0),
        duration=timedelta(minutes=30),
        rrules=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
    )
    defaults.update(kwargs)
    return ChoreCreateModel(**defaults)


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


def make_google_service_mock(event_id="event_abc123", start_dt="2026-03-30T10:00:00"):
    mock_event = {
        "id": event_id,
        "start": {"dateTime": start_dt},
    }
    mock_events = MagicMock()
    mock_events.insert.return_value.execute.return_value = mock_event

    mock_service = MagicMock()
    mock_service.events.return_value = mock_events
    mock_service.__enter__ = MagicMock(return_value=mock_service)
    mock_service.__exit__ = MagicMock(return_value=False)
    return mock_service


async def _creds():
    return MagicMock()


async def test_create_calendar_events_calls_google_insert(session):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(), session)

    mock_service.events.return_value.insert.assert_called_once()
    mock_service.events.return_value.insert.return_value.execute.assert_called_once()


async def test_create_calendar_events_event_body_summary(session):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(name="Mop floors"), session)

    body = mock_service.events.return_value.insert.call_args.kwargs["body"]
    assert body["summary"] == "Mop floors"


async def test_create_calendar_events_event_body_recurrence(session):
    mock_service = make_google_service_mock()
    rrules = ["RRULE:FREQ=WEEKLY;BYDAY=TU"]

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(rrules=rrules), session)

    body = mock_service.events.return_value.insert.call_args.kwargs["body"]
    assert body["recurrence"] == rrules


async def test_create_calendar_events_event_duration(session):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(duration=timedelta(hours=2)), session)

    body = mock_service.events.return_value.insert.call_args.kwargs["body"]
    start_dt = datetime.fromisoformat(body["start"]["dateTime"])
    end_dt = datetime.fromisoformat(body["end"]["dateTime"])
    assert end_dt - start_dt == timedelta(hours=2)


async def test_create_calendar_events_start_time_uses_start_from(session):
    mock_service = make_google_service_mock()
    start_from = datetime(2026, 3, 30, 9, 30)  # Monday

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(
            make_chore_data(start_from=start_from, rrules=["RRULE:FREQ=WEEKLY;BYDAY=MO"]),
            session,
        )

    body = mock_service.events.return_value.insert.call_args.kwargs["body"]
    start_dt = datetime.fromisoformat(body["start"]["dateTime"])
    assert start_dt.time() == start_from.time()


async def test_create_calendar_events_timezone(session):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(), session)

    body = mock_service.events.return_value.insert.call_args.kwargs["body"]
    assert body["start"]["timeZone"] == "Europe/Amsterdam"
    assert body["end"]["timeZone"] == "Europe/Amsterdam"


async def test_create_calendar_events_persists_calendar_event(session):
    event_id = "evt_xyz"
    mock_service = make_google_service_mock(event_id=event_id)

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(), session)

    result = await session.execute(select(CalendarEvent))
    events = result.scalars().all()
    assert len(events) == 1
    assert events[0].calendar_event_id == event_id


async def test_create_calendar_events_uses_calendar_id(session, monkeypatch):
    import src.chores_planner.services.google_calendar as gcal_module
    monkeypatch.setattr(gcal_module, "CALENDAR_ID", "test@group.calendar.google.com")

    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.create_calendar_events(make_chore_data(), session)

    insert_kwargs = mock_service.events.return_value.insert.call_args.kwargs
    assert insert_kwargs["calendarId"] == "test@group.calendar.google.com"


async def test_create_calendar_events_google_api_error_propagates(session):
    mock_events = MagicMock()
    mock_events.insert.return_value.execute.side_effect = Exception("Google API error")

    mock_service = MagicMock()
    mock_service.events.return_value = mock_events
    mock_service.__enter__ = MagicMock(return_value=mock_service)
    mock_service.__exit__ = MagicMock(return_value=False)

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()

        with pytest.raises(Exception, match="Google API error"):
            await svc.create_calendar_events(make_chore_data(), session)
