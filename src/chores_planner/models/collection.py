from __future__ import annotations

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    chores: Mapped[list["Chore"]] = relationship(back_populates="collection")

    def __str__(self) -> str:
        return f"{self.name}({self.id})"

