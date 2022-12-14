# Generated by Django 4.0.6 on 2022-07-23 16:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlockNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(default=-1, unique=True, verbose_name='Block Number')),
            ],
        ),
        migrations.CreateModel(
            name='Oracle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Oracle Name')),
            ],
        ),
        migrations.CreateModel(
            name='TokenPair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token0', models.CharField(default='', max_length=50, verbose_name='NA')),
                ('token1', models.CharField(default='', max_length=50, verbose_name='NA')),
                ('support', models.BooleanField(default=False)),
                ('oracle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.oracle')),
            ],
            options={
                'unique_together': {('oracle', 'token0', 'token1')},
            },
        ),
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=-1)),
                ('current', models.FloatField(default=-1)),
                ('data_crawled_at', models.DateTimeField(auto_now=True)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
                ('token_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.tokenpair')),
            ],
            options={
                'unique_together': {('block_number', 'index')},
            },
        ),
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.CharField(default='', max_length=50, unique=True, verbose_name='UTC Timestamp String')),
                ('datetime', models.DateTimeField(default=None, unique=True, verbose_name='UTC Datetime')),
                ('utc_time_str', models.CharField(default='', max_length=50, unique=True, verbose_name='UTC Time String')),
                ('number', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
            ],
            options={
                'unique_together': {('number', 'timestamp', 'utc_time_str')},
            },
        ),
    ]
