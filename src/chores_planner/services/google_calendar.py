import json
import os
from datetime import datetime
from functools import cached_property
from logging import getLogger
from pathlib import Path

from dateutil.rrule import rrulestr
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src import CREDENTIALS_PATH, TOKEN_PATH
from src.chores_planner.models import CalendarEvent, Chore
from src.chores_planner.serializers.chore import ChoreCreateModel, ChoreGetModel

LOGGER = getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")


class GoogleCalendarService:
    @cached_property
    async def credentials(self) -> Credentials:
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

    async def create_calendar_events(self, chore_data: ChoreCreateModel):
        with build("calendar", "v3", credentials=await self.credentials) as service:
            rule = rrulestr(chore_data.calendar_rule, dtstart=datetime.now())
            first_occurrence = rule.after(datetime.now(), inc=True)
            start_time = datetime.combine(first_occurrence, chore_data.preferred_time)
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
                            "recurrence": [chore_data.calendar_rule],
                        },
                    )
                    .execute()
                )
            except Exception:
                raise

            chore_obj = await Chore.create(**chore_data.model_dump())
            calendar_event = await CalendarEvent.create(
                calendar_event_id=event["id"],
                starts_from=event["start"]["dateTime"],
                chore=chore_obj,
            )

            return chore_obj
