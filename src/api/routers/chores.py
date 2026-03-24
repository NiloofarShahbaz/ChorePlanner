from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from src.chores_planner.models.chore import Chore
from src.chores_planner.serializers.calendar_event import (
    CalendarEventGetModel,
    CalendarEventStatusUpdateModel,
)
from src.chores_planner.serializers.chore import (
    ChoreCreateModel,
    ChoreGetModel,
    ChoreListModel,
)
from src.chores_planner.services.google_calendar import GoogleCalendarService
from src.db import SessionDep

chores_router = APIRouter()


@chores_router.get("/chores/")
async def list_chores(db: SessionDep) -> list[ChoreGetModel]:
    result = await db.execute(select(Chore))
    chores = result.scalars().all()
    return ChoreListModel.validate_python(chores, from_attributes=True)


@chores_router.post("/chore/")
async def create_chore(
    chore: ChoreCreateModel, db: SessionDep
) -> ChoreGetModel:
    chore_obj = await GoogleCalendarService().create_calendar_events(chore, db)
    return ChoreGetModel.model_validate(chore_obj, from_attributes=True)


@chores_router.patch("/calendar-event/{event_id}/status")
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
