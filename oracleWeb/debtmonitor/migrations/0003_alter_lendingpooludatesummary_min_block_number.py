# Generated by Django 4.0.6 on 2022-08-06 08:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debtmonitor', '0002_lendingpooludatesummary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lendingpooludatesummary',
            name='min_block_number',
            field=models.IntegerField(default=2147483647, verbose_name='Min Block Number'),
        ),
    ]
