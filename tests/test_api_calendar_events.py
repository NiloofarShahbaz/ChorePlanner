from unittest.mock import AsyncMock, patch

from src.chores_planner.models.calendar_event import StatusChoices


async def test_update_status_to_done(client, db_session, vacuum_calendar_event):
    with patch("src.api.routers.calendar_events.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.update_event_status = AsyncMock(return_value=vacuum_calendar_event)

        response = await client.patch(
            f"/calendar-event/{vacuum_calendar_event.id}/status",
            json={"status": "Done"},
        )

    assert response.status_code == 200
    mock_instance.update_event_status.assert_called_once_with(vacuum_calendar_event.id, StatusChoices.DONE, db_session)


async def test_update_status_response_shape(client, vacuum_calendar_event):
    vacuum_calendar_event.status = StatusChoices.DONE

    with patch("src.api.routers.calendar_events.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.update_event_status = AsyncMock(return_value=vacuum_calendar_event)

        response = await client.patch(
            f"/calendar-event/{vacuum_calendar_event.id}/status",
            json={"status": "Done"},
        )

    data = response.json()
    assert data["id"] == vacuum_calendar_event.id
    assert data["status"] == "Done"
    assert data["calendar_event_id"] == "gcal_abc"


async def test_update_status_not_found(client):
    with patch("src.api.routers.calendar_events.GoogleCalendarService") as MockService:
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
