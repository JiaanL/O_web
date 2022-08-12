from django.shortcuts import render
import ctypes
from ctypes import c_char_p, cdll

from tokenize import Token
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.db.models import Max, Min
from django.db import IntegrityError
from django.db.models import Max, Min, Avg, Q, F
from rest_framework.views import APIView 

from .models import *
from datastorage.models import *
from datavisualization.models import *
from .help_function import *

import pandas as pd
import numpy as np
import json
import pickle
import os
import tqdm
import time
import threading
from collections import OrderedDict, defaultdict

import ctypes
from ctypes import c_char_p, cdll
GoInt64 = ctypes.c_int64
GoInt = GoInt64
archive_node = "http://localhost:19545"

from pandarallel import pandarallel
pandarallel.initialize(progress_bar=False)


__library = cdll.LoadLibrary('../eth_crawler/library.so')
get_single_block_time = __library.get_single_block_time
get_single_block_time.argtypes = [c_char_p, GoInt]
get_single_block_time.restype = c_char_p


SECONDS_PER_YEAR = 365 * 24 * 60 * 60
RAY = 1e27


ray_mul = lambda a,b: (a * b + RAY/2) / RAY
ray_div = lambda a,b: (a * RAY + b/2) / b
combine_block_n_index = lambda x: int(str(x['block_num']) + str(x['index']).zfill(6))


token_dict = dict(
    usdc = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
    usdt = '0xdac17f958d2ee523a2206206994597c13d831ec7',
    dai =  '0x6b175474e89094c44da98b954eedeac495271d0f',
    # common collateral asset
    weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
)
decimal_dict = dict(
    usdc = 6,
    usdt = 6,
    dai =  18,
    # common collateral asset
    weth = 18
)

liquidation_threshold_dict = dict(
    usdc = 0.88,
    usdt = None, # not allowed as collateral
    dai =  0.8,
    # common collateral asset
    weth = 0.85
)
revert_token_dict = {v: k for k, v in token_dict.items()}

def get_potential_target():
    data = pd.DataFrame(
        list(
            LendingPoolInteraction.objects.all().values()
        )
    )
    return data['on_behalf_of'].unique().tolist()


def get_interaction_data(target):
    data = pd.DataFrame(
        list(
            LendingPoolInteraction.objects.filter(
                on_behalf_of=target
            ).annotate(
                 block_num=F('block_number__number'),
            ).all().values()
        )
    )
    return data

def get_reserves_status():
    data = pd.DataFrame(
        list(
            ReservesStatus.objects.annotate(
                 block_num=F('block_number__number'),
            ).all().values()
        )
    )
    return data

def get_liquidation_call(target=None):
    if target is None:
        data = pd.DataFrame(
            list(
                LiquidationCall.objects.annotate(
                    block_num=F('block_number__number'),
                ).all().values()
            )
        )
    else:
        data = pd.DataFrame(
            list(
                LiquidationCall.objects.filter(
                    on_behalf_of=target
                ).annotate(
                    block_num=F('block_number__number'),
                ).all().values()
            )
        )
    return data

# Block Time
def get_block_time(block_num):
    try:
        res = get_single_block_time(
            archive_node.encode(), 
            GoInt(int(block_num))
        )
        res = res.decode("utf-8")
        res = json.loads(s=res)#.items()#, columns=['BlockNum', 'Timestamp'])
        
        return res[str(block_num)]
    except Exception as e: 
        print(e)

def cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p):
    block_time = get_block_time(block_num)
    block_time_p = get_block_time(block_num_p)
    exp = block_time - block_time_p
    
    ###### Reference #####: https://etherscan.io/address/0xc6845a5c768bf8d7681249f8927877efda425baf#code
    expMinusOne = exp - 1
    expMinusTwo = exp - 2 if exp > 2 else 0
    ratePerSecond = stable_borrow_rate_p / SECONDS_PER_YEAR
    basePowerTwo = ray_mul(ratePerSecond, ratePerSecond) # (ratePerSecond * ratePerSecond + 0.5 * RAY)/RAY
    basePowerThree = ray_mul(basePowerTwo, ratePerSecond)#  + 0.5 * RAY)/RAY
    secondTerm = (exp * expMinusOne * basePowerTwo) / 2
    thirdTerm = (exp * expMinusOne * expMinusTwo * basePowerThree) / 6
    compounded_interest = RAY + (ratePerSecond * exp) + (secondTerm) + (thirdTerm)
    new_stable_balance = ray_mul(stable_debt_amount_p, compounded_interest)
    balance_increase = new_stable_balance - stable_debt_amount_p
    ########################################################################

    return new_stable_balance, balance_increase

def update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
        rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate,
        collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict):
    
    
    # ['int', 'liquidityRate'],  # 存钱利息
    # ['int', 'stableBorrowRate'],  # 固定贷款利息
    # ['int', 'variableBorrowRate'], # 可变贷款利息
    # ['int', 'liquidityIndex'], # 存钱token价值指数
    # ['int', 'variableBorrowIndex'], # 可变贷款token价值指数
    # stable = 1, variable = 2
    
    a_token_amount_i = ray_div(amount_i, liquidity_index)
    
    variable_debt_amount_i = ray_div(amount_i, variable_borrow_index)

    # For Stable Debt
    stable_debt_amount_i = amount_i #/ stable_borrow_rate
    stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name_i]
    if stable_debt_amount_p != None:
        new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)

    if action_i == "ReserveUsedAsCollateralEnabled":
        collatearl_able_dict[token_name_i] = True
    elif action_i == "ReserveUsedAsCollateralDisabled":
        collatearl_able_dict[token_name_i] = False
    elif action_i == "Deposit":
        if collatearl_able_dict[token_name_i] == False and collateral_dict[token_name_i] == 0:
            collatearl_able_dict[token_name_i] = True
        collateral_dict[token_name_i] += a_token_amount_i
    elif action_i == 'Withdraw':
        if (collateral_dict[token_name_i] - a_token_amount_i) < 0:
            return False, np.abs(collateral_dict[token_name_i] - a_token_amount_i)
        collateral_dict[token_name_i] -= a_token_amount_i
    elif action_i == "Borrow":
        if rate_mode_i == '1': # stable
            if stable_debt_dict[token_name_i][0] is None:
                stable_debt_dict[token_name_i] = [stable_debt_amount_i, stable_borrow_rate, block_num]
            else:
                stable_debt_dict[token_name_i] = [new_stable_balance + stable_debt_amount_i, stable_borrow_rate, block_num]
        elif rate_mode_i == '2': # variable
            variable_debt_dict[token_name_i] += variable_debt_amount_i
        else:
            assert False, "rate_mode_i error"
    elif action_i == "Repay":
        if rate_mode_i == '1':
            if (new_stable_balance - stable_debt_amount_i) < 0:
                return False, np.abs(new_stable_balance - stable_debt_amount_i)
            stable_debt_dict[token_name_i] = [new_stable_balance - stable_debt_amount_i, stable_borrow_rate, block_num]
        elif rate_mode_i == '2': # variable
            if (variable_debt_dict[token_name_i] - variable_debt_amount_i) < 0:
                return False, np.abs(variable_debt_dict[token_name_i] - variable_debt_amount_i)
            variable_debt_dict[token_name_i] -= variable_debt_amount_i
    elif action_i == 'RebalanceStableBorrowRate':
        stable_debt_dict[token_name_i] = [new_stable_balance, stable_borrow_rate, block_num]
    else:
        assert False, "Interaction Data error"

    return True, 0

def get_token_value(block_num, index, 
    collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict,
    reserves_status,
    fix_decimal=False):
    # collateral_dict = defaultdict(float)
    # collatearl_able_dict = defaultdict(lambda :True)
    # variable_debt_dict = defaultdict(float)
    # stable_debt_dict = defaultdict(lambda : [None, None, None])
    collateral_in_original_unit = defaultdict(float)
    var_debt_in_original_unit = defaultdict(float)
    sta_debt_in_original_unit = defaultdict(float)

    block_n_index = combine_block_n_index(dict(block_num=block_num, index=index))

    for token_name, able in collatearl_able_dict.items():
        decimal_fixer = 1
        if able:
            tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
                 (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
            if fix_decimal:
                decimal_fixer = 10 ** decimal_dict[token_name]
            collateral_in_original_unit[token_name] = ray_mul(collateral_dict[token_name], tmp_status["liquidity_index"]) / decimal_fixer
    
    for token_name, able in variable_debt_dict.items():
        decimal_fixer = 1
        tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
                 (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
        if fix_decimal:
            decimal_fixer = 10 ** decimal_dict[token_name]
        var_debt_in_original_unit[token_name] = ray_mul(variable_debt_dict[token_name], tmp_status["variable_borrow_index"]) / decimal_fixer

    for token_name, stable_debt in stable_debt_dict.items():
        decimal_fixer = 1
        if stable_debt[0] is not None:
            stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name]
            new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)
            if fix_decimal:
                decimal_fixer = 10 ** decimal_dict[token_name]
            sta_debt_in_original_unit[token_name] = new_stable_balance / decimal_fixer
    return collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit

def get_price_data(until_block_num, previous_block = 6424):
    ttt = pd.DataFrame(
        list(
            BlockPrice.objects.filter(
                Q(block_number__number__lte=until_block_num) &
                Q(block_number__number__gte=(until_block_num - previous_block))
            ).annotate(
                block_num=F('block_number__number'),
                oracle_name=F('token_pair__oracle__name'),
                token0 = F('token_pair__token0'),
                token1 = F('token_pair__token1'),
            ).all().values()
        )
    )
    return ttt.sort_values("block_num")

def invert_transformation(df_train, df_forecast):
    """Revert back the differencing to get the forecast to original scale."""
    df_fc = df_forecast.copy()
    columns = df_train.columns
    for col in columns:        
        # Roll back 1st Diff
        df_fc[str(col)] = (df_train[col].iloc[-1] + df_fc[col].cumsum()) # np.exp(df_train[col].iloc[-1] + df_fc[col].cumsum())
    return df_fc

def cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict):
    hf_list = []
    for i in range(price_prediction.shape[0]):
        collatearl_m_threshold_in_eth = 0
        debt_m_threshold_in_eth = 0
        for token_name, token_amount in token_value_dicts['collateral'].items():
            if token_name == 'weth':
                collatearl_m_threshold_in_eth += token_amount * liquidation_threshold_dict[token_name]
            else:
                collatearl_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]  * liquidation_threshold_dict[token_name]

        for token_name, token_amount in token_value_dicts['var_debt'].items():
            if token_name == 'weth':
                debt_m_threshold_in_eth += token_amount
            else:
                debt_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]

        for token_name, token_amount in token_value_dicts['sta_debt'].items():
            if token_name == 'weth':
                debt_m_threshold_in_eth += token_amount
            else:
                debt_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]
        collatearl_m_threshold_in_eth, debt_m_threshold_in_eth

        hf = (collatearl_m_threshold_in_eth/debt_m_threshold_in_eth)
        hf_list.append(hf)
    return pd.Series(hf_list)#, columns=['hf'])

def cal_pct_be_liquidated(mc_simulation_row):
    return (mc_simulation_row < 1).sum()/mc_simulation_row.count()
