from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.chores_planner.models.calendar_event import CalendarEvent, StatusChoices
from src.chores_planner.models.chore import Chore


async def _seed(db_session, chore_name="Vacuum"):
    chore = Chore(name=chore_name, duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
    db_session.add(chore)
    await db_session.flush()

    event = CalendarEvent(
        calendar_event_id="gcal_abc",
        starts_from=datetime(2026, 3, 30, 10, 0),
        chore_id=chore.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


async def test_update_status_to_done(client, db_session):
    event = await _seed(db_session)

    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.update_event_status = AsyncMock(return_value=event)

        response = await client.patch(
            f"/calendar-event/{event.id}/status",
            json={"status": "Done"},
        )

    assert response.status_code == 200
    mock_instance.update_event_status.assert_called_once_with(event.id, StatusChoices.DONE, db_session)


async def test_update_status_response_shape(client, db_session):
    event = await _seed(db_session)
    event.status = StatusChoices.DONE

    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.update_event_status = AsyncMock(return_value=event)

        response = await client.patch(
            f"/calendar-event/{event.id}/status",
            json={"status": "Done"},
        )

    data = response.json()
    assert data["id"] == event.id
    assert data["status"] == "Done"
    assert data["calendar_event_id"] == "gcal_abc"


async def test_update_status_not_found(client):
    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.update_event_status = AsyncMock(side_effect=ValueError("not found"))

        response = await client.patch(
            "/calendar-event/9999/status",
            json={"status": "Done"},
        )

    assert response.status_code == 404


async def test_update_status_invalid_status(client):
    response = await client.patch(
        "/calendar-event/1/status",
        json={"status": "InvalidStatus"},
    )
    assert response.status_code == 422
