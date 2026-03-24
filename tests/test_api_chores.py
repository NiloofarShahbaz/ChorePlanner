from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.chores_planner.models.chore import Chore


async def test_list_chores_empty(client):
    response = await client.get("/chores/")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_chores_returns_all(client, db_session):
    chore1 = Chore(name="Vacuum", duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
    chore2 = Chore(name="Mop", duration=timedelta(minutes=20), start_from=datetime(2026, 3, 25))
    db_session.add_all([chore1, chore2])
    await db_session.commit()

    response = await client.get("/chores/")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Vacuum" in names
    assert "Mop" in names


async def test_list_chores_shape(client, db_session):
    chore = Chore(
        name="Dishes",
        duration=timedelta(minutes=15),
        start_from=datetime(2026, 3, 24),
        rrules=["RRULE:FREQ=DAILY"],
    )
    db_session.add(chore)
    await db_session.commit()

    response = await client.get("/chores/")
    assert response.status_code == 200
    item = response.json()[0]
    assert "id" in item
    assert "name" in item
    assert "created_at" in item
    assert "updated_at" in item
    assert item["name"] == "Dishes"


async def test_create_chore_calls_google_calendar_service(client):
    mock_chore = Chore(
        id=1,
        name="Laundry",
        duration=timedelta(minutes=45),
        start_from=datetime(2026, 3, 24),
    )
    mock_chore.created_at = datetime(2026, 3, 24)
    mock_chore.updated_at = datetime(2026, 3, 24)

    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.create_calendar_events = AsyncMock(return_value=mock_chore)

        response = await client.post(
            "/chore/",
            json={"name": "Laundry", "rrules": ["RRULE:FREQ=WEEKLY;BYDAY=MO"]},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Laundry"
    mock_instance.create_calendar_events.assert_called_once()


async def test_create_chore_without_rrules(client):
    mock_chore = Chore(
        id=2,
        name="Water plants",
        duration=timedelta(minutes=10),
        start_from=datetime(2026, 3, 24),
    )
    mock_chore.created_at = datetime(2026, 3, 24)
    mock_chore.updated_at = datetime(2026, 3, 24)

    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.create_calendar_events = AsyncMock(return_value=mock_chore)

        response = await client.post("/chore/", json={"name": "Water plants"})

    assert response.status_code == 200
    assert response.json()["name"] == "Water plants"


async def test_create_chore_invalid_rrule(client):
    response = await client.post(
        "/chore/",
        json={"name": "Bad chore", "rrules": ["NOT_A_VALID_RULE"]},
    )
    assert response.status_code == 422


async def test_create_chore_returns_created_object(client):
    mock_chore = Chore(
        id=5,
        name="Sweep",
        duration=timedelta(hours=1),
        start_from=datetime(2026, 4, 1),
        rrules=["RRULE:FREQ=MONTHLY"],
    )
    mock_chore.created_at = datetime(2026, 3, 24)
    mock_chore.updated_at = datetime(2026, 3, 24)

    with patch("src.api.routers.chores.GoogleCalendarService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.create_calendar_events = AsyncMock(return_value=mock_chore)

        response = await client.post(
            "/chore/",
            json={
                "name": "Sweep",
                "duration": "PT1H",
                "rrules": ["RRULE:FREQ=MONTHLY"],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["name"] == "Sweep"
    assert data["rrules"] == ["RRULE:FREQ=MONTHLY"]
