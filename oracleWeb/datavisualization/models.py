from django.db import models
from datastorage.models import * 

# Create your models here.

class BlockPrice(models.Model):
    # ForeignKey
    token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE)
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)
    # Data
    current = models.FloatField(default=-1)
    # price_updated_at = models.DateTimeField(auto_now=False, default=None)
    # Meta
    data_crawled_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('token_pair', 'block_number',)

class BlockPriceUpdateRecord(models.Model):
    token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, unique=True)
    min_block_number = models.IntegerField('Min Block Number', default=2147483647) # mysql maxint
    max_block_number = models.IntegerField('Max Block Number', default=-1)
    # data_amount = models.IntegerField('Data Amount', default=-1)



class BlockPriceUpdateRecord(models.Model):
    token_pair = models.OneToOneField(TokenPair, on_delete=models.CASCADE)
    min_block_number = models.IntegerField('Min Block Number', default=2147483647) # mysql maxint
    max_block_number = models.IntegerField('Max Block Number', default=-1)
    # data_amount = models.IntegerField('Data Amount', default=-1)

class Frequency(models.Model):
    frequency_num = models.IntegerField('Frequency_num', default=-1, unique=True)

class LatencyUpdateRecord(models.Model):
    source_token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, related_name='related_primary_sum_token_pair')
    target_token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, related_name='related_secondary_sum_token_pair')
    min_block_number = models.IntegerField('Min Block Number', default=2147483647) # mysql maxint
    max_block_number = models.IntegerField('Max Block Number', default=-1)
    frequency = models.ForeignKey(Frequency, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('source_token_pair',"target_token_pair", "frequency",)
    # data_amount = models.IntegerField('Data Amount', default=-1)

class LatencyRecord(models.Model):
    # ForeignKey
    source_token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, related_name='related_primary_token_pair')
    target_token_pair = models.ForeignKey(TokenPair, on_delete=models.CASCADE, related_name='related_secondary_token_pair')
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)
    frequency = models.ForeignKey(Frequency, on_delete=models.CASCADE)
    # Data
    latency = models.FloatField(default=-1)
    # Meta
    data_crawled_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        unique_together = ('source_token_pair', 'target_token_pair','block_number',"frequency",)
