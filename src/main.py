from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import (
    TortoiseConfig,
    register_tortoise,
    tortoise_exception_handlers,
)

from src.api.routers.chores import chores_router
from src.db import TORTOISE_ORM

load_dotenv()

app = FastAPI(
    title="Chores Planner Server",
    exception_handlers=tortoise_exception_handlers(),
)
app.include_router(chores_router, prefix="")

register_tortoise(app, config=TortoiseConfig.from_dict(TORTOISE_ORM))
