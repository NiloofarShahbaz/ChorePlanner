from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.chores_planner.models.chore import Chore
from src.chores_planner.serializers.chore import ChoreGetModel


class TestListChores:
    async def test_empty(self, client):
        response = await client.get("/chores/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all(self, client, db_session):
        chore1 = Chore(name="Vacuum", duration=timedelta(minutes=30), start_from=datetime(2026, 3, 24))
        chore2 = Chore(name="Mop", duration=timedelta(minutes=20), start_from=datetime(2026, 3, 25))
        db_session.add_all([chore1, chore2])
        await db_session.commit()

        response = await client.get("/chores/")
        assert response.status_code == 200
        names = [c["name"] for c in response.json()]
        assert "Vacuum" in names
        assert "Mop" in names

    async def test_returns_chore_data(self, client, db_session):
        chore = Chore(
            name="Dishes",
            duration=timedelta(minutes=15),
            start_from=datetime(2026, 3, 24),
            rrules=["RRULE:FREQ=DAILY"],
        )
        db_session.add(chore)
        await db_session.commit()
        await db_session.refresh(chore)

        response = await client.get("/chores/")
        assert response.status_code == 200
        expected = ChoreGetModel.model_validate(chore, from_attributes=True).model_dump(mode="json")
        assert response.json() == [expected]


class TestCreateChore:
    async def test_calls_google_calendar_service(self, client):
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
        mock_instance.create_calendar_events.assert_called_once()

    async def test_without_rrules(self, client):
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

    async def test_invalid_rrule(self, client):
        response = await client.post(
            "/chore/",
            json={"name": "Bad chore", "rrules": ["NOT_A_VALID_RULE"]},
        )
        assert response.status_code == 422

    async def test_returns_created_object(self, client):
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
                json={"name": "Sweep", "duration": "PT1H", "rrules": ["RRULE:FREQ=MONTHLY"]},
            )

        assert response.status_code == 200
        expected = ChoreGetModel.model_validate(mock_chore, from_attributes=True).model_dump(mode="json")
        assert response.json() == expected
