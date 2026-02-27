from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests
from googleapiclient.discovery import build
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
chores_calendar = next(
    (c for c in calendars["items"] if c["summary"] == "ChoresPlanner"), None
)
if not chores_calendar:
    raise RuntimeError("ChoresPlanner calendar not found.")

calendar_id = chores_calendar["id"]

# Find the parent recurring event (singleEvents=False returns parent events)
all_events = service.events().list(
    calendarId=calendar_id,
    singleEvents=False,
).execute()

targets = [e for e in all_events.get("items", []) if e.get("summary") == "Test Chore Event 1"] or []


for event in targets:
    service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
    print(f"Deleted parent event: {event['id']} (removes all occurrences)")

service.events().delete(calendarId=calendar_id, eventId="fuvhmkubk5ik6cjr6dbq8n0bhs").execute()