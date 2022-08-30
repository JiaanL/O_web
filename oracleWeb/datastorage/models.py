from operator import mod
from pyexpat import model
from django.db import models

# Create your models here.


class Oracle(models.Model):
    name = models.CharField('Oracle Name', max_length=50, unique=True)

class BlockNumber(models.Model):
    number = models.IntegerField('Block Number', default=-1, unique=True)

class Block(models.Model):
    number = models.OneToOneField(BlockNumber, on_delete=models.CASCADE)
    timestamp = models.CharField('UTC Timestamp String', max_length=50, default='', unique=True)
    datetime = models.DateTimeField('UTC Datetime', default=None, unique=True)
    utc_time_str = models.CharField('UTC Time String', max_length=50, default='', unique=True)

    class Meta:
        unique_together = ('number', 'timestamp', 'utc_time_str',)

# class PriceType(models.Model):
#     oracle = models.ForeignKey(Oracle, on_delete=models.CASCADE)
#     detail = models.CharField('Token1 / Token2', max_length=50, default='')

class TokenPair(models.Model):
    oracle = models.ForeignKey(Oracle, on_delete=models.CASCADE)
    token0 = models.CharField('NA', max_length=50, default='')
    token1 = models.CharField('NA', max_length=50, default='')
    support = models.BooleanField(default=False)

    class Meta:
        unique_together = ('oracle', 'token0', 'token1',)

class Price(models.Model):

    # ForeignKey
    token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE)
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)

    # Data
    index = models.IntegerField(default=-1)
    current = models.FloatField(default=-1)
    # price_updated_at = models.DateTimeField(auto_now=False, default=None)

    # Meta
    data_crawled_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('token_pair', 'block_number', 'index',)
    
class Summary(models.Model):
    token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, unique=True)
    min_block_number = models.IntegerField('Min Block Number', default=-1)
    max_block_number = models.IntegerField('Max Block Number', default=-1)
    data_amount = models.IntegerField('Data Amount', default=-1)
