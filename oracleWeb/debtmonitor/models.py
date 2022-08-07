from django.db import models
from numpy import char
from datastorage.models import * 
from datavisualization.models import * 

# Create your models here.
class LendingPoolInteraction(models.Model):
    # # ForeignKey
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)
    # Data
    index = models.IntegerField(default=-1)
    

    # agent = models.CharField(max_length=100, default='') # user, msg.sender
    on_behalf_of = models.CharField(max_length=100, default='') # token reciver, debt holder
    
    action = models.CharField(max_length=100, default='') # what action was taken
    reserve = models.CharField(max_length=100, default='') # reserve, asset, what token was interacted
    amount = models.FloatField(default=-1)


    rate_mode = models.CharField(max_length=100, default='') 
    rate = models.FloatField(default=-1)

    class Meta:
        unique_together = ('index', 'block_number',)


class LendingPoolUpdateSummary(models.Model):
    action = models.CharField(max_length=100, default='', unique=True) # what action was taken
    # min_block_number = models.IntegerField('Min Block Number', default=-1)
    # max_block_number = models.IntegerField('Max Block Number', default=-1)
    min_block_number = models.IntegerField('Min Block Number', default=2147483647) # mysql maxint
    max_block_number = models.IntegerField('Max Block Number', default=-1)
    data_amount = models.IntegerField('Data Amount', default=-1)


class LiquidationCall(models.Model):
    # ForeignKey
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)
    # Data
    index = models.IntegerField(default=-1)
    # agent = models.CharField(max_length=100, default='') # user, msg.sender
    on_behalf_of = models.CharField(max_length=100, default='') # 被liquidate的人
    
    # action = mo dels.CharField(max_length=100, default='') # what action was taken
    collateral_asset = models.CharField(max_length=100, default='') # reserve, asset, what token was interacted
    debt_asset = models.CharField(max_length=100, default='') # reserve, asset, what token was interacted
    
    debt_to_cover = models.FloatField(default=-1)
    liquidated_collateral_amount = models.FloatField(default=-1)
    liquidator = models.CharField(max_length=100, default='')

    # rate_mode = models.CharField(max_length=100, default='') 
    # rate = models.FloatField(default=-1)
    receive_atoken = models.BooleanField(default=False)

    class Meta:
        unique_together = ('index', 'block_number',)

class ReservesStatus(models.Model):
    # # ForeignKey
    block_number = models.ForeignKey(BlockNumber, on_delete=models.CASCADE)
    # Data
    index = models.IntegerField(default=-1)
    
    
    reserve = models.CharField(max_length=100, default='') # reserve, asset, what token was interacted
    liquidity_rate = models.FloatField(default=-1)
    stable_borrow_rate = models.FloatField(default=-1)
    variable_borrow_rate = models.FloatField(default=-1)
    liquidity_index = models.FloatField(default=-1)
    variable_borrow_index = models.FloatField(default=-1)
    
    class Meta:
        unique_together = ('index', 'block_number',)


    # emit Borrow(
    #   vars.asset,
    #   vars.user,
    #   vars.onBehalfOf,
    #   vars.amount,
    #   vars.interestRateMode,
    #   DataTypes.InterestRateMode(vars.interestRateMode) == DataTypes.InterestRateMode.STABLE
    #     ? currentStableRate
    #     : reserve.currentVariableBorrowRate,
    #   vars.referralCode
    # );

    # emit Repay(asset, onBehalfOf, msg.sender, paybackAmount);
    # emit Withdraw(asset, msg.sender, to, amountToWithdraw);
    # emit Deposit(asset, msg.sender, onBehalfOf, amount, referralCode);
    # emit Swap(asset, msg.sender, rateMode);
    # emit ReserveUsedAsCollateralDisabled(collateralAsset, user);
    # emit ReserveUsedAsCollateralEnabled(collateralAsset, user);
    # emit Transfer(user, address(0), amount);
    # emit Burn(user, receiverOfUnderlying, amount, index);



    # # Data
    # current = models.FloatField(default=-1)
    # # price_updated_at = models.DateTimeField(auto_now=False, default=None)
    # # Meta
    # data_crawled_at = models.DateTimeField(auto_now=True)

    