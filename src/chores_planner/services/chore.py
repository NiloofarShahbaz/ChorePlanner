from src.chores_planner.serializers.chore import (
    ChoreCreateModel,
)
from src.chores_planner.models import Chore, CalendarEvent

class ChoreService:
    async def create_chore(chore_data: ChoreCreateModel):
        chore_obj = await Chore.create(**chore_data.model_dump())
        