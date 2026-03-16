from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests
from googleapiclient.discovery import build
import json
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = "data/credentials/token.json"
CREDS_PATH = "data/credentials/credentials.json"

creds = None

if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(google.auth.transport.requests.Request())
        except Exception:
            creds = None

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

service = build("calendar", "v3", credentials=creds)

# Find the ChoresPlanner calendar
calendars = service.calendarList().list().execute()
print(calendars["items"])
chores_calendar = next(
    (c for c in calendars["items"] if c["summary"] == "ChoresPlanner"), None
)
if not chores_calendar:
    raise RuntimeError("ChoresPlanner calendar not found. Did it get deleted?")

calendar_id = chores_calendar["id"]
print(calendar_id)

event = service.events().insert(
    calendarId=calendar_id,
    body={
        "summary": "Test Chore Event 6",
        "description": "Created by ChoresPlanner test script",
        "start": {
            "dateTime": "2026-02-27T10:00:00",
            "timeZone": "Europe/Amsterdam",
        },
        "end": {
            "dateTime": "2026-02-27T10:30:00",
            "timeZone": "Europe/Amsterdam",
        },
        "recurrence": [
            "RRULE:FREQ=MONTHLY;BYDAY=2WE,-1FR"
        ],
    }
).execute()

print(json.dumps(event, indent=2))
