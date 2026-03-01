from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('chores', '0003_auto_20260301_1547')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Chore',
            name='preferred_time',
            field=fields.CharField(max_length=21),
        ),
    ]
