from fastapi import APIRouter
from sqlalchemy import select

from src.chores_planner.models.chore import Chore
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
