# Generated by Django 4.0.6 on 2022-07-28 07:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('datastorage', '0002_summary'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current', models.FloatField(default=-1)),
                ('data_crawled_at', models.DateTimeField(auto_now=True)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
                ('token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.tokenpair')),
            ],
        ),
    ]
