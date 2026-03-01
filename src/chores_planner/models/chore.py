from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum, Enum

from tortoise import Model, fields


class FrequencyChoices(StrEnum):
    DAILY = "daily", "day"
    WEEKLY = "weekly", "week"
    MONTHLY = "monthly", "month"
    YEARLY = "yearly", "year"

    def __new__(cls, value, translation):
        self = str.__new__(cls, value)
        self._value_ = value
        self.translation = translation
        return self


class Chore(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    image = fields.CharField(
        max_length=1024, null=True, default=None
    )  # TODO: make a separate field type for this.
    frequency = fields.CharEnumField(enum_type=FrequencyChoices, max_length=7)
    frequency_interval = fields.IntField(default=1)
    frequency_data = fields.JSONField()
    duration = fields.TimeDeltaField(default=timedelta(minutes=30))
    preferred_time = fields.CharField(max_length=21) # Because of sqlite3 limitation

    def __str__(self):
        return self.name
