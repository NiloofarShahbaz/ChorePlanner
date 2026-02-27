from tortoise import migrations
from tortoise.migrations import operations as ops
import datetime
import functools
from src.chores_planner.models.chore import FrequencyChoices
from json import dumps, loads
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Chore',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(unique=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('image', fields.CharField(null=True, max_length=1024)),
                ('frequency', fields.CharEnumField(description='DAILY: daily\nMONTHLY: monthly\nYEARLY: yearly', enum_type=FrequencyChoices, max_length=7)),
                ('frequency_interval', fields.IntField(default=1)),
                ('frequency_data', fields.JSONField(encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('duration', fields.TimeDeltaField(default=datetime.timedelta(seconds=1800.0))),
            ],
            options={'table': 'chore', 'app': 'chores', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='CalendarEvent',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('calendar_event_id', fields.CharField(unique=True, max_length=250)),
                ('starts_from', fields.DatetimeField(auto_now=False, auto_now_add=False)),
                ('chore', fields.ForeignKeyField('chores.Chore', source_field='chore_id', null=True, db_constraint=True, to_field='id', related_name='events', on_delete=OnDelete.SET_NULL)),
            ],
            options={'table': 'calendarevent', 'app': 'chores', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
