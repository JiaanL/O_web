# Generated by Django 4.0.6 on 2022-08-07 16:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('datastorage', '0002_summary'),
        ('debtmonitor', '0007_alter_lendingpoolinteraction_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LendingPoolUpdateSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(default='', max_length=100, unique=True)),
                ('min_block_number', models.IntegerField(default=2147483647, verbose_name='Min Block Number')),
                ('max_block_number', models.IntegerField(default=-1, verbose_name='Max Block Number')),
                ('data_amount', models.IntegerField(default=-1, verbose_name='Data Amount')),
            ],
        ),
        migrations.CreateModel(
            name='ReservesStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=-1)),
                ('reserve', models.CharField(default='', max_length=100)),
                ('liquidity_rate', models.FloatField(default=-1)),
                ('stable_borrow_rate', models.FloatField(default=-1)),
                ('variable_borrow_rate', models.FloatField(default=-1)),
                ('liquidity_index', models.FloatField(default=-1)),
                ('variable_borrow_index', models.FloatField(default=-1)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
            ],
            options={
                'unique_together': {('index', 'block_number')},
            },
        ),
        migrations.CreateModel(
            name='LiquidationCall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=-1)),
                ('on_behalf_of', models.CharField(default='', max_length=100)),
                ('collateral_asset', models.CharField(default='', max_length=100)),
                ('debt_asset', models.CharField(default='', max_length=100)),
                ('debt_to_cover', models.FloatField(default=-1)),
                ('liquidated_collateral_amount', models.FloatField(default=-1)),
                ('liquidator', models.CharField(default='', max_length=100)),
                ('receive_atoken', models.BooleanField(default=False)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
            ],
            options={
                'unique_together': {('index', 'block_number')},
            },
        ),
        migrations.CreateModel(
            name='LendingPoolInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=-1)),
                ('on_behalf_of', models.CharField(default='', max_length=100)),
                ('action', models.CharField(default='', max_length=100)),
                ('reserve', models.CharField(default='', max_length=100)),
                ('amount', models.FloatField(default=-1)),
                ('rate_mode', models.CharField(default='', max_length=100)),
                ('rate', models.FloatField(default=-1)),
                ('block_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datastorage.blocknumber')),
            ],
            options={
                'unique_together': {('index', 'block_number')},
            },
        ),
    ]
