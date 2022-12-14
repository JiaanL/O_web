# Generated by Django 4.0.6 on 2022-08-02 20:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datastorage', '0002_summary'),
        ('datavisualization', '0014_delete_latencupdaterecord'),
    ]

    operations = [
        migrations.CreateModel(
            name='LatencUpdateRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_block_number', models.IntegerField(default=2147483647, verbose_name='Min Block Number')),
                ('max_block_number', models.IntegerField(default=-1, verbose_name='Max Block Number')),
                ('frequency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datavisualization.frequency')),
                ('source_token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_primary_sum_token_pair', to='datastorage.tokenpair')),
                ('target_token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_secondary_sum_token_pair', to='datastorage.tokenpair')),
            ],
            options={
                'unique_together': {('source_token_pair', 'target_token_pair', 'frequency')},
            },
        ),
    ]
