# Generated by Django 4.0.6 on 2022-08-02 20:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datastorage', '0002_summary'),
        ('datavisualization', '0012_alter_blockpriceupdaterecord_token_pair_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LatencyRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latency', models.FloatField(default=-1)),
                ('data_crawled_at', models.DateTimeField(auto_now=True)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
                ('frequency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datavisualization.frequency')),
                ('source_token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_primary_token_pair', to='datastorage.tokenpair')),
                ('target_token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_secondary_token_pair', to='datastorage.tokenpair')),
            ],
            options={
                'unique_together': {('source_token_pair', 'target_token_pair', 'block_number', 'frequency')},
            },
        ),
    ]
