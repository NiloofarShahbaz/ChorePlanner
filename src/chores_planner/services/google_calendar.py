import os
from datetime import datetime
from functools import cached_property
from zoneinfo import ZoneInfo
from logging import getLogger

from dateutil.rrule import rrulestr
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import CREDENTIALS_PATH, TOKEN_PATH
from src.chores_planner.models.calendar_event import CalendarEvent, StatusChoices
from src.chores_planner.models.chore import Chore
from src.chores_planner.serializers.chore import ChoreCreateModel

LOGGER = getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")


class GoogleCalendarService:
    @cached_property
    async def credentials(self) -> Credentials:
        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return creds

    async def create_calendar_events(
        self, chore_data: ChoreCreateModel, db: AsyncSession
    ) -> Chore:
        with build("calendar", "v3", credentials=await self.credentials) as service:
            rule = rrulestr(chore_data.rrule_str, dtstart=chore_data.start_from)
            start_time = rule.after(chore_data.start_from, inc=True)
            end_time = start_time + chore_data.duration

            try:
                event = (
                    service.events()
                    .insert(
                        calendarId=CALENDAR_ID,
                        body={
                            "summary": chore_data.name,
                            "description": "Created by ChoresPlanner :D",
                            "start": {
                                "dateTime": start_time.isoformat(),
                                "timeZone": "Europe/Amsterdam",
                            },
                            "end": {
                                "dateTime": end_time.isoformat(),
                                "timeZone": "Europe/Amsterdam",
                            },
                            "recurrence": chore_data.rrules,
                        },
                    )
                    .execute()
                )
            except Exception:
                raise

            chore_obj = Chore(**chore_data.model_dump())

            db.add(chore_obj)
            await db.flush()

            # Store the parent recurring event
            tz = ZoneInfo("Europe/Amsterdam")
            parent_start = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(tz).replace(tzinfo=None)
            parent_event = CalendarEvent(
                calendar_event_id=event["id"],
                starts_from=parent_start,
                chore_id=chore_obj.id,
                is_parent=True,
            )
            db.add(parent_event)

            # Fetch all individual instances (paginated)
            all_instances = []
            page_token = None
            while True:
                instances_result = (
                    service.events()
                    .instances(
                        calendarId=CALENDAR_ID,
                        eventId=event["id"],
                        pageToken=page_token,
                    )
                    .execute()
                )
                all_instances.extend(instances_result.get("items", []))
                page_token = instances_result.get("nextPageToken")
                if not page_token:
                    break

            for instance in all_instances:
                instance_start = instance["start"].get("dateTime", instance["start"].get("date"))
                parsed = datetime.fromisoformat(instance_start)
                # Convert to local time and store as naive datetime
                local_dt = parsed.astimezone(tz).replace(tzinfo=None)
                db.add(CalendarEvent(
                    calendar_event_id=instance["id"],
                    starts_from=local_dt,
                    chore_id=chore_obj.id,
                    is_parent=False,
                ))

            await db.commit()
            await db.refresh(chore_obj)

            return chore_obj

    async def update_event_status(
        self, event_id: int, status: StatusChoices, db: AsyncSession
    ) -> CalendarEvent:
        result = await db.execute(
            select(CalendarEvent)
            .options(selectinload(CalendarEvent.chore))
            .where(CalendarEvent.id == event_id)
        )
        cal_event = result.scalar_one_or_none()
        if cal_event is None:
            raise ValueError(f"CalendarEvent {event_id} not found")

        if status == StatusChoices.DONE:
            with build("calendar", "v3", credentials=await self.credentials) as service:
                if cal_event.chore:
                    summary = cal_event.chore.name
                else:
                    existing = service.events().get(
                        calendarId=CALENDAR_ID,
                        eventId=cal_event.calendar_event_id,
                    ).execute()
                    summary = existing.get("summary", "")
                service.events().patch(
                    calendarId=CALENDAR_ID,
                    eventId=cal_event.calendar_event_id,
                    body={"summary": f"✅ {summary}"},
                ).execute()

        cal_event.status = status
        await db.commit()
        await db.refresh(cal_event)
        return cal_event

    async def delete_chore(self, chore_id: int, db: AsyncSession) -> None:
        result = await db.execute(
            select(Chore)
            .options(selectinload(Chore.events))
            .where(Chore.id == chore_id)
        )
        chore = result.scalar_one_or_none()
        if chore is None:
            raise ValueError(f"Chore {chore_id} not found")

        # Find the parent event to delete from Google Calendar
        parent_events = [e for e in chore.events if e.is_parent]
        if parent_events:
            with build("calendar", "v3", credentials=await self.credentials) as service:
                for parent in parent_events:
                    service.events().delete(
                        calendarId=CALENDAR_ID,
                        eventId=parent.calendar_event_id,
                    ).execute()

        # Delete all calendar events from DB
        for event in chore.events:
            await db.delete(event)

        await db.delete(chore)
        await db.commit()
