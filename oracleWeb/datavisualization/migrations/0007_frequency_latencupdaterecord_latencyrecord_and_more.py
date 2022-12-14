# Generated by Django 4.0.6 on 2022-08-02 13:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datastorage', '0002_summary'),
        ('datavisualization', '0006_latencyrecordper6424'),
    ]

    operations = [
        migrations.CreateModel(
            name='Frequency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frequency', models.IntegerField(default=-1, verbose_name='Frequency')),
            ],
        ),
        migrations.CreateModel(
            name='LatencUpdateRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_block_number', models.IntegerField(default=2147483647, verbose_name='Min Block Number')),
                ('max_block_number', models.IntegerField(default=-1, verbose_name='Max Block Number')),
                ('frequency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datavisualization.frequency')),
                ('token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.tokenpair', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='LatencyRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latency', models.FloatField(default=-1)),
                ('data_crawled_at', models.DateTimeField(auto_now=True)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
                ('frequency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datavisualization.frequency')),
                ('token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.tokenpair')),
            ],
            options={
                'unique_together': {('token_pair', 'block_number', 'frequency')},
            },
        ),
        migrations.DeleteModel(
            name='LatencyRecordPer6424',
        ),
    ]
