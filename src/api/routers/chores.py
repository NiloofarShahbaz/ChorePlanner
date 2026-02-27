from fastapi import APIRouter
from src.chores_planner.models.chore import Chore

chores_router = APIRouter()


@chores_router.get("/chores")
async def list_chores():
    print(await Chore.all())
    return {}
