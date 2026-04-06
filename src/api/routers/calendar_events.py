from fastapi import APIRouter, HTTPException

from src.chores_planner.serializers.calendar_event import (
    CalendarEventGetModel,
    CalendarEventStatusUpdateModel,
)
from src.chores_planner.services.google_calendar import GoogleCalendarService
from src.db import SessionDep

calendar_events_router = APIRouter()


@calendar_events_router.patch("/calendar-event/{event_id}/status")
async def update_calendar_event_status(
    event_id: int,
    data: CalendarEventStatusUpdateModel,
    db: SessionDep,
) -> CalendarEventGetModel:
    try:
        cal_event = await GoogleCalendarService().update_event_status(event_id, data.status, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return CalendarEventGetModel.model_validate(cal_event, from_attributes=True)
