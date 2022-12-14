# Generated by Django 4.0.6 on 2022-08-07 16:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('debtmonitor', '0008_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='lendingpoolinteraction',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='lendingpoolinteraction',
            name='block_number',
        ),
        migrations.DeleteModel(
            name='LendingPoolUpdateSummary',
        ),
        migrations.AlterUniqueTogether(
            name='liquidationcall',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='liquidationcall',
            name='block_number',
        ),
        migrations.AlterUniqueTogether(
            name='reservesstatus',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='reservesstatus',
            name='block_number',
        ),
        migrations.DeleteModel(
            name='LendingPoolInteraction',
        ),
        migrations.DeleteModel(
            name='LiquidationCall',
        ),
        migrations.DeleteModel(
            name='ReservesStatus',
        ),
    ]
