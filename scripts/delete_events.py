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

# Delete all events
page_token = None
deleted = 0
while True:
    events = service.events().list(
        calendarId=calendar_id,
        pageToken=page_token,
        singleEvents=True,
    ).execute()

    for event in events.get("items", []):
        service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
        print(f"Deleted: {event.get('summary', '(no title)')} [{event['id']}]")
        deleted += 1

    page_token = events.get("nextPageToken")
    if not page_token:
        break

print(f"\nDone. {deleted} event(s) deleted.")
