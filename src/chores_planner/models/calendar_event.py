from tortoise import Model, fields

from .chore import Chore


class CalendarEvent(Model):
    id = fields.IntField(primary_key=True)
    calendar_event_id = fields.CharField(max_length=250, unique=True)
    starts_from = fields.DatetimeField()
    chore = fields.OneToOneField(
        Chore, related_name="event", on_delete=fields.SET_NULL, null=True
    )
