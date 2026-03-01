from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('chores', '0002_auto_20260228_1113')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Chore',
            name='preferred_time',
            field=fields.CharField(max_length=15),
        ),
    ]
