from __future__ import annotations
from enum import StrEnum
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db import Base


class StatusChoices(StrEnum):
    PENDING = "Pending"
    DONE = "Done"
    POSTPONED = "Postponed" 
    CANCELED = "Canceled"
    

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_event_id: Mapped[str] = mapped_column(String(250), unique=True)
    starts_from: Mapped[datetime] = mapped_column(DateTime) # TODO: Do we need this?
    chore_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chores.id", ondelete="SET NULL"),
        nullable=True,
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assignee.id", ondelete="SET NULL"), nullable=True
    )
    
    is_parent: Mapped[bool] = mapped_column(default=False)
    status: Mapped[StatusChoices] = mapped_column(default=StatusChoices.PENDING)
    status_data: Mapped[JSON | None] = mapped_column(JSON(none_as_null=True), default=None)
    
    assignee: Mapped[Optional["AssigneeUser"]] = relationship(back_populates="events")
    chore: Mapped[Optional["Chore"]] = relationship(back_populates="events")
