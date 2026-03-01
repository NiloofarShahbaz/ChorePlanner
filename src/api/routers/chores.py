from fastapi import APIRouter

from src.chores_planner.models.chore import Chore
from src.chores_planner.serializers.chore import (
    ChoreCreateModel,
    ChoreGetModel,
    ChoreListModel,
)
from src.chores_planner.services.google_calendar import GoogleCalendarService


chores_router = APIRouter()


@chores_router.get("/chores/")
async def list_chores() -> list[ChoreGetModel]:
    queryset = await Chore.all()
    print(queryset[0].frequency_data)
    return ChoreListModel.validate_python(queryset)


@chores_router.post("/chore/")
async def create_chore(chore: ChoreCreateModel) -> ChoreGetModel:
    chore_obj = await GoogleCalendarService().create_calendar_events(chore)
    # chore_obj = await Chore.create(**chore.model_dump())
    return await ChoreGetModel.from_tortoise_orm(chore_obj)
