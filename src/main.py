from dotenv import load_dotenv
from fastapi import FastAPI

from src.api.routers.chores import chores_router

load_dotenv()

app = FastAPI(title="Chores Planner Server")
app.include_router(chores_router, prefix="")
