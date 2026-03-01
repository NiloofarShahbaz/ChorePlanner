from tortoise import migrations
from tortoise.migrations import operations as ops
from src.chores_planner.models.chore import FrequencyChoices
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('chores', '0001_initial')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Chore',
            name='frequency',
            field=fields.CharEnumField(description='DAILY: daily\nWEEKLY: weekly\nMONTHLY: monthly\nYEARLY: yearly', enum_type=FrequencyChoices, max_length=7),
        ),
    ]
