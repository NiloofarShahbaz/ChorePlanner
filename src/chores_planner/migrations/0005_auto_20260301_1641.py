from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('chores', '0004_auto_20260301_1613')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='CalendarEvent',
            name='chore',
            field=fields.OneToOneField('chores.Chore', source_field='chore_id', null=True, db_constraint=True, to_field='id', related_name='event', on_delete=OnDelete.SET_NULL),
        ),
    ]
