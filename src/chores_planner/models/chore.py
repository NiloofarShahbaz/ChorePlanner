from tortoise import Model, fields
from enum import StrEnum
from datetime import timedelta

class FrequencyChoices(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Chore(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    image = fields.CharField(max_length=1024, null=True, default=None) # TODO: make a separate field for this.
    frequency = fields.CharEnumField(enum_type=FrequencyChoices)
    frequency_interval = fields.IntField(default=1)
    frequency_data = fields.JSONField() # TODO: use pydantic for field_type
    duration = fields.TimeDeltaField(default=timedelta(minutes=30))
    
    def __str__(self):
        return self.name