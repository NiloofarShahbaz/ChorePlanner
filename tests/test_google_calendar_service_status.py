from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from src.chores_planner.models.calendar_event import CalendarEvent, StatusChoices
from src.chores_planner.models.chore import Chore
from src.chores_planner.services.google_calendar import GoogleCalendarService


async def _creds():
    return MagicMock()


def make_google_service_mock():
    mock_service = MagicMock()
    mock_service.__enter__ = MagicMock(return_value=mock_service)
    mock_service.__exit__ = MagicMock(return_value=False)
    mock_service.events.return_value.patch.return_value.execute.return_value = {}
    return mock_service


async def test_update_event_status_done_patches_google_title(db_session):
    chore = Chore(name="Mop floors", duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
    db_session.add(chore)
    await db_session.flush()
    event = CalendarEvent(
        calendar_event_id="gcal_xyz",
        starts_from=datetime(2026, 3, 30, 10, 0),
        chore_id=chore.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(event.id, StatusChoices.DONE, db_session)

    patch_call = mock_service.events.return_value.patch
    patch_call.assert_called_once()
    call_kwargs = patch_call.call_args.kwargs
    assert call_kwargs["eventId"] == "gcal_xyz"
    assert call_kwargs["body"]["summary"] == "✅ Mop floors"


async def test_update_event_status_done_updates_db_status(db_session, vacuum_calendar_event):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        updated = await svc.update_event_status(vacuum_calendar_event.id, StatusChoices.DONE, db_session)

    assert updated.status == StatusChoices.DONE


async def test_update_event_status_done_persists_to_db(db_session, vacuum_calendar_event):
    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(vacuum_calendar_event.id, StatusChoices.DONE, db_session)

    result = await db_session.execute(select(CalendarEvent).where(CalendarEvent.id == vacuum_calendar_event.id))
    refreshed = result.scalar_one()
    assert refreshed.status == StatusChoices.DONE


async def test_update_event_status_not_found_raises(db_session):
    svc = GoogleCalendarService()
    with pytest.raises(ValueError, match="not found"):
        await svc.update_event_status(9999, StatusChoices.DONE, db_session)


async def test_update_event_status_non_done_skips_google_api(db_session, vacuum_calendar_event):
    with patch("src.chores_planner.services.google_calendar.build") as mock_build:
        svc = GoogleCalendarService()
        await svc.update_event_status(vacuum_calendar_event.id, StatusChoices.PENDING, db_session)

    mock_build.assert_not_called()


async def test_update_event_status_uses_calendar_id(db_session, vacuum_calendar_event, monkeypatch):
    import src.chores_planner.services.google_calendar as gcal_module
    monkeypatch.setattr(gcal_module, "CALENDAR_ID", "test@group.calendar.google.com")

    mock_service = make_google_service_mock()

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(vacuum_calendar_event.id, StatusChoices.DONE, db_session)

    patch_kwargs = mock_service.events.return_value.patch.call_args.kwargs
    assert patch_kwargs["calendarId"] == "test@group.calendar.google.com"


async def test_update_event_status_done_fetches_summary_when_chore_is_none(db_session):
    event = CalendarEvent(
        calendar_event_id="gcal_orphan",
        starts_from=datetime(2026, 3, 30, 10, 0),
        chore_id=None,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    mock_service = make_google_service_mock()
    mock_service.events.return_value.get.return_value.execute.return_value = {
        "summary": "Mop floors",
    }

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        await svc.update_event_status(event.id, StatusChoices.DONE, db_session)

    mock_service.events.return_value.get.assert_called_once()
    patch_kwargs = mock_service.events.return_value.patch.call_args.kwargs
    assert patch_kwargs["body"]["summary"] == "✅ Mop floors"


async def test_update_event_status_google_api_error_propagates(db_session, vacuum_calendar_event):
    mock_service = make_google_service_mock()
    mock_service.events.return_value.patch.return_value.execute.side_effect = Exception("API error")

    with patch("src.chores_planner.services.google_calendar.build", return_value=mock_service):
        svc = GoogleCalendarService()
        svc.__dict__["credentials"] = _creds()
        with pytest.raises(Exception, match="API error"):
            await svc.update_event_status(vacuum_calendar_event.id, StatusChoices.DONE, db_session)
