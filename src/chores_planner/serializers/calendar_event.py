from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.chores_planner.models.calendar_event import StatusChoices


class CalendarEventGetModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_event_id: str
    starts_from: datetime
    chore_id: int | None
    is_parent: bool
    status: StatusChoices
    status_data: dict | None = None


class CalendarEventStatusUpdateModel(BaseModel):
    status: StatusChoices
