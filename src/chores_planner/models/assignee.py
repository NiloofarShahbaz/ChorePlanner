from __future__ import annotations

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class AssigneeUser(Base):
    __tablename__ = "assignee"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    
    events: Mapped[list["CalendarEvent"]] = relationship(back_populates="assignee")

    def __str__(self) -> str:
        return f"{self.name}({self.id})"

