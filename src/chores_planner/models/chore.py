from __future__ import annotations

from datetime import timedelta, datetime
from enum import StrEnum
from typing import Optional
from sqlalchemy import String, Integer, DateTime, JSON, Interval, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.db import Base

class LabeledStrEnum(StrEnum):
    label: str

    def __new__(cls, value: str, label: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    @classmethod
    def choices(cls):
        return [(member.value, member.label) for member in cls]

    @classmethod
    def values(cls):
        return [member.value for member in cls]

    @classmethod
    def labels(cls):
        return [member.label for member in cls]
        
        
class FrequencyChoices(LabeledStrEnum):
    DAILY = "daily", "day"
    WEEKLY = "weekly", "week"
    MONTHLY = "monthly", "month"
    YEARLY = "yearly", "year"


class Chore(Base):
    __tablename__ = "chores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    image: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    duration: Mapped[timedelta] = mapped_column(Interval, default=timedelta(minutes=30))
    start_from: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    rrules: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True), default=None)
    
    collection_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
    )

    events: Mapped[list["CalendarEvent"]] = relationship(back_populates="chore")
    collection: Mapped[Optional["Collection"]] = relationship(back_populates="chores")

    def __str__(self) -> str:
        return f"{self.name}({self.id})"

