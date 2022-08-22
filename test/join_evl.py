import pandas as pd
import numpy as np
import os
import django
from django.db.models import Max, Min, Avg, Q, F
from asgiref.sync import sync_to_async
import tqdm
from collections import defaultdict
from pandarallel import pandarallel
import requests
import json
from matplotlib import pyplot as plt

import ctypes
from ctypes import c_char_p, cdll
GoInt64 = ctypes.c_int64
GoInt = GoInt64
archive_node = "http://localhost:19545"

from etherscan.utils.parsing import ResponseParser as parser
pandarallel.initialize(progress_bar=True)
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rest.settings')
# os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
# django.setup()

from debtmonitor.models import *
from datavisualization.models import *
from datastorage.models import *
from debtmonitor.help_function import *

import debtmonitor.views as dm
import datavisualization.views as dv
import datastorage.views as ds
import oracleWeb.views as ow

from debtmonitor.debt_function import *

import pickle

pandarallel.initialize(progress_bar=True)

def gen_real_hf(reserves_status, TargetContract, ReservesStatusEnd, StepAhead, ReservesStatusEndIndex, MCAmount,  PreviousBlockForTrain=0, print_info=False):

    # reserves_status = get_reserves_status()

    # StepAhead += PreviousBlockForTrain
    reserves_status = reserves_status.copy()
    
    latest_block_num = reserves_status['block_num'].max()
    interaction_df = get_interaction_data(TargetContract)

    until_block_num = latest_block_num
    until_block_num = ReservesStatusEnd
    until_index = ReservesStatusEndIndex

    reserves_status = reserves_status[reserves_status['block_num'] <= ReservesStatusEnd]
    until_block_n_index = combine_block_n_index({'block_num': until_block_num, 'index': until_index})
    # liquidation_index = until_index

    # Start Getting Data #####################################
    liquidation_df = get_liquidation_call(TargetContract)

    # reserves_status['variable_borrow_rate'] = reserves_status['variable_borrow_rate'].astype(int)
    # reserves_status['stable_borrow_rate'] = reserves_status['stable_borrow_rate'].astype(int)
    # reserves_status['liquidity_rate'] = reserves_status['liquidity_rate'].astype(int)
    # liquidation_df['debt_to_cover'] = liquidation_df['debt_to_cover'].astype(int)
    # liquidation_df['liquidated_collateral_amount'] = liquidation_df['liquidated_collateral_amount'].astype(int)
    # interaction_df['amount'] = interaction_df['amount'].astype(int)

    interaction_df = interaction_df['action block_num index on_behalf_of reserve amount rate_mode rate'.split(' ')].copy()
    reserves_status = reserves_status[[
        'reserve', 'block_num', 'index',  
        'liquidity_rate', 'stable_borrow_rate', 'variable_borrow_rate', 
        'liquidity_index','variable_borrow_index'
    ]].copy()
    liquidation_df = liquidation_df[[
        'block_num', 'index', 'on_behalf_of', 
        'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
        'liquidator', 'receive_atoken']].copy()

    interaction_df['block_n_index'] = interaction_df.apply(combine_block_n_index, axis=1)
    reserves_status['block_n_index'] = reserves_status.apply(combine_block_n_index, axis=1)
    liquidation_df['block_n_index'] = liquidation_df.apply(combine_block_n_index, axis=1)

    interaction_df = interaction_df.sort_values('block_n_index').reset_index(drop=True)
    reserves_status = reserves_status.sort_values('block_n_index').reset_index(drop=True)


    # just give a random reserve address, will be swich in the following part
    for index in interaction_df.index:
        if interaction_df.loc[index, 'action'] == "LiquidationCall":
            interaction_df.loc[index, 'reserve'] = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

    # merge


    change_token_address_to_name = lambda x: revert_token_dict[x] if x in revert_token_dict else x
    interaction_df['reserve'] = interaction_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    reserves_status['reserve'] = reserves_status['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    liquidation_df['collateral_asset'] = liquidation_df['collateral_asset'].apply(change_token_address_to_name)
    liquidation_df['debt_asset'] = liquidation_df['debt_asset'].apply(change_token_address_to_name)


    collateral_dict = defaultdict(float)
    collatearl_able_dict = defaultdict(lambda :True)
    variable_debt_dict = defaultdict(float)
    stable_debt_dict = defaultdict(lambda : [None, None, None]) # amount, interest, start time

    if print_info: print(interaction_df)

    sub_interaction_df = interaction_df[interaction_df['block_n_index'] <= until_block_n_index].copy()
    curent_block_index = 0
    hf_list = []
    block_list = []
    have_data = False
    block_n_index = None
    interaction_block_list = sub_interaction_df['block_num'].to_list()
    
    # for tmp_block_num in tqdm.tqdm(reserves_status['block_num'].unique()):
    for tmp_block_num in tqdm.tqdm(range(reserves_status['block_num'].min(), ReservesStatusEnd + StepAhead)):
        if tmp_block_num not in interaction_block_list and tmp_block_num < (ReservesStatusEnd - PreviousBlockForTrain):
            continue
        until_block_num = tmp_block_num
        tmp_reserves_status = reserves_status[reserves_status['block_num'] <= tmp_block_num]#.copy()
        tmp_index = 9999
        tmp_block_n_index = combine_block_n_index(dict(block_num=tmp_block_num, index=tmp_index))
        sub_interaction_df = interaction_df[(interaction_df['block_n_index'] > curent_block_index) & (interaction_df['block_n_index'] <= tmp_block_n_index)].copy()
        
        update_value = False
        for index_i in sub_interaction_df.index:
            update_value = True
            if print_info: print(sub_interaction_df.loc[index_i, :])
            if print_info: print(tmp_reserves_status.iloc[-2:,:])
            have_data = True
            action_i = sub_interaction_df.loc[index_i, 'action']
            block_n_index = sub_interaction_df.loc[index_i, 'block_n_index']
            block_num = sub_interaction_df.loc[index_i, 'block_num']
            index = sub_interaction_df.loc[index_i, 'index']

            # block_time = get_block_time(block_num)
            # before_data = from_df[from_df['block_n_index_x'] == block_n_index]#['amount'].values[0]
            # liquidity_index = tmp_reserves_status['liquidity_index'].values[-1]
            # variable_borrow_index = tmp_reserves_status['variable_borrow_index'].values[0]
            # stable_borrow_rate = tmp_reserves_status['stable_borrow_rate'].values[0]
            
            if action_i == "LiquidationCall":
                'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
                liquidation_i = liquidation_df[liquidation_df['block_n_index'] == block_n_index].copy().reset_index(drop=True)
                if print_info: print(liquidation_i)
                collateral_asset = liquidation_i.loc[0, 'collateral_asset']
                debt_asset = liquidation_i.loc[0, 'debt_asset']
                debt_to_cover = liquidation_i.loc[0, 'debt_to_cover']
                liquidated_collateral_amount = liquidation_i.loc[0, 'liquidated_collateral_amount']

                liquidity_index = tmp_reserves_status[(tmp_reserves_status['reserve']==collateral_asset) & (tmp_reserves_status['block_n_index']<=block_n_index)]['liquidity_index'].values[-1]
                variable_borrow_index = tmp_reserves_status[(tmp_reserves_status['reserve']==debt_asset) & (tmp_reserves_status['block_n_index']<=block_n_index)]['variable_borrow_index'].values[-1]
                stable_borrow_rate = tmp_reserves_status[(tmp_reserves_status['reserve']==debt_asset) & (tmp_reserves_status['block_n_index']<=block_n_index)]['stable_borrow_rate'].values[-1]

                # a_token_amount_i = ray_div(liquidated_collateral_amount, liquidity_index)
                # collateral_dict[collateral_asset] -= a_token_amount_i

                collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit = get_token_value(
                    block_num, index,
                    collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict,reserves_status
                )

                if var_debt_in_original_unit[debt_asset] < debt_to_cover:
                    var_debt_to_liquidate = var_debt_in_original_unit[debt_asset]
                    sta_debt_to_repay = debt_to_cover - var_debt_to_liquidate
                else:
                    var_debt_to_liquidate = debt_to_cover
                    sta_debt_to_repay = 0

                success, remaining_token = update_target_debt_data(
                        "Repay", block_num, var_debt_to_liquidate, debt_asset, 
                        "2", liquidity_index, variable_borrow_index, stable_borrow_rate,
                        collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict
                    )
                assert success

                if sta_debt_to_repay > 0:
                    success, remaining_token = update_target_debt_data(
                        "Repay", block_num, sta_debt_to_repay, debt_asset, 
                        "1", liquidity_index, variable_borrow_index, stable_borrow_rate,
                        collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict
                    )
                    assert success
                
                success, remaining_token = update_target_debt_data(
                    "Withdraw", block_num, liquidated_collateral_amount, collateral_asset, 
                    "-1", liquidity_index, variable_borrow_index, stable_borrow_rate,
                    collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict
                )
                assert success

            else:
                amount_i = sub_interaction_df.loc[index_i, 'amount']
                token_name_i = sub_interaction_df.loc[index_i, 'reserve']
                rate_mode_i = sub_interaction_df.loc[index_i, 'rate_mode']

                liquidity_index = tmp_reserves_status[(tmp_reserves_status['reserve']==token_name_i) & (tmp_reserves_status['block_n_index']<=block_n_index)]['liquidity_index'].values[-1]
                variable_borrow_index = tmp_reserves_status[(tmp_reserves_status['reserve']==token_name_i) & (tmp_reserves_status['block_n_index']<=block_n_index)]['variable_borrow_index'].values[-1]
                stable_borrow_rate = tmp_reserves_status[(tmp_reserves_status['reserve']==token_name_i) & (tmp_reserves_status['block_n_index']<=block_n_index)]['stable_borrow_rate'].values[-1]

                update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
                rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate,
                collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict)
            # print(sub_interaction_df.loc[index_i, :])
            
            if print_info: print("liquidity_index, variable_borrow_index, stable_borrow_rate")
            if print_info: print(liquidity_index, variable_borrow_index, stable_borrow_rate)
            if print_info: print("collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict")
            if print_info: print(collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict)
            
            if print_info: print('---------------------------------------------------------------')
        
        if update_value:
            if print_info: print(get_token_value(until_block_num, until_index, 
                                collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict,
                                reserves_status,
                                fix_decimal=True
                            ))

        if block_n_index is None:
            continue
        curent_block_index = block_n_index
        
        # if not have_data: continue
        if len(variable_debt_dict) == 0 and len(stable_debt_dict) == 0: continue
        # if : continue
        # print(tmp_block_num)
        if tmp_block_num < (ReservesStatusEnd - PreviousBlockForTrain): continue
        # print(999)
        if tmp_block_num > (ReservesStatusEnd + StepAhead): break

        
        token_value_dicts = get_token_value(until_block_num, until_index, 
                                collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict,
                                reserves_status,
                                fix_decimal=True
                            )

        # collateral, var_debt, sta_debt
        token_value_dicts = {i:j for i,j in zip(['collateral', 'var_debt', 'sta_debt'], token_value_dicts)}
        if print_info: print(token_value_dicts)

        price_data = get_price_data(until_block_num, previous_block= 6424*1)
        # price_data = get_price_data(until_block_num, previous_block=PreviousBlockForTrain)
        price_data['token0'] = price_data['token0'].apply(lambda x: 'weth' if x == 'eth' else x)
        price_data['token1'] = price_data['token1'].apply(lambda x: 'weth' if x == 'eth' else x)
        price_data = price_data[['block_num', 'oracle_name', 'token0', 'token1', 'current']]

        block_num_df = pd.DataFrame(
            range(
                price_data.block_num.min(), 
                until_block_num + 1
            ),
            columns=['block_num']
        )
        block_num_df.set_index('block_num', inplace=True)

        uniswapv3_price_dict = {}
        for token in ['usdt', 'dai', 'usdc']:
            sub_price_df = price_data[(price_data['oracle_name'] == 'uniswapv3') & (price_data['token1'] == token)].copy()
            sub_price_df[f'{token}'] = 1/sub_price_df['current']
            sub_price_df.set_index('block_num', inplace=True)
            sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
            sub_price_df.fillna(method='ffill', inplace=True)
            sub_price_df.fillna(method='bfill', inplace=True)
            sub_price_df = sub_price_df[sub_price_df.index > (until_block_num-10)]
            uniswapv3_price_dict[token] = sub_price_df[token]
        chainlink_price_dict ={}
        for token in ['usdt', 'dai', 'usdc']:
            sub_price_df = price_data[(price_data['oracle_name'] == 'chainlink') & (price_data['token0'] == token)].copy()
            sub_price_df[f'{token}'] = sub_price_df['current']
            sub_price_df.set_index('block_num', inplace=True)
            sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
            sub_price_df.fillna(method='ffill', inplace=True)
            sub_price_df.fillna(method='bfill', inplace=True)
            sub_price_df = sub_price_df[sub_price_df.index > (until_block_num-10)]
            chainlink_price_dict[token] = sub_price_df[token]

        used_token_list = []
        price_data_list = []
        price_name_list = []
        for asset_from in ['collateral', 'var_debt', 'sta_debt']:
            for token_name in ['usdc', 'usdt', 'dai']:
            # for token_name, token_amount in token_value_dicts[asset_from].items():
                if token_name == 'weth': continue
                if token_name not in used_token_list:
                    used_token_list.append(token_name)
                    price_data_list.append(chainlink_price_dict[token_name])
                    price_name_list.append(f'chainlink_{token_name}')
                    price_data_list.append(uniswapv3_price_dict[token_name])
                    price_name_list.append(f'uniswapv3_{token_name}')

        var_train_df = pd.concat(price_data_list, axis=1)
        var_train_df.columns = price_name_list
        var_train_df = var_train_df.reset_index(drop=False)

        hf_actual_series = cal_hf(var_train_df, token_value_dicts, liquidation_threshold_dict)
        block_list.append(tmp_block_num)
        hf_list.append(hf_actual_series.iloc[-1])
    
    
    until_block_num = ReservesStatusEnd

    token_value_dicts = get_token_value(until_block_num, until_index, 
                            collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict,
                            reserves_status,
                            fix_decimal=True
                        )

    # collateral, var_debt, sta_debt
    token_value_dicts = {i:j for i,j in zip(['collateral', 'var_debt', 'sta_debt'], token_value_dicts)}

    price_data = get_price_data(until_block_num, previous_block= 6424*1 + PreviousBlockForTrain)
    # price_data = get_price_data(until_block_num, previous_block=PreviousBlockForTrain)
    price_data['token0'] = price_data['token0'].apply(lambda x: 'weth' if x == 'eth' else x)
    price_data['token1'] = price_data['token1'].apply(lambda x: 'weth' if x == 'eth' else x)
    price_data = price_data[['block_num', 'oracle_name', 'token0', 'token1', 'current']]

    block_num_df = pd.DataFrame(
        range(
            price_data.block_num.min(), 
            until_block_num + 1
        ),
        columns=['block_num']
    )
    block_num_df.set_index('block_num', inplace=True)

    uniswapv3_price_dict = {}
    for token in ['usdt', 'dai', 'usdc']:
        sub_price_df = price_data[(price_data['oracle_name'] == 'uniswapv3') & (price_data['token1'] == token)].copy()
        sub_price_df[f'{token}'] = 1/sub_price_df['current']
        sub_price_df.set_index('block_num', inplace=True)
        sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
        sub_price_df.fillna(method='ffill', inplace=True)
        sub_price_df.fillna(method='bfill', inplace=True)
        sub_price_df = sub_price_df[sub_price_df.index > (until_block_num-PreviousBlockForTrain-1)]
        uniswapv3_price_dict[token] = sub_price_df[token]
    chainlink_price_dict ={}
    for token in ['usdt', 'dai', 'usdc']:
        sub_price_df = price_data[(price_data['oracle_name'] == 'chainlink') & (price_data['token0'] == token)].copy()
        sub_price_df[f'{token}'] = sub_price_df['current']
        sub_price_df.set_index('block_num', inplace=True)
        sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
        sub_price_df.fillna(method='ffill', inplace=True)
        sub_price_df.fillna(method='bfill', inplace=True)
        sub_price_df = sub_price_df[sub_price_df.index > (until_block_num-PreviousBlockForTrain-1)]
        chainlink_price_dict[token] = sub_price_df[token]

    used_token_list = []
    price_data_list = []
    price_name_list = []
    for asset_from in ['collateral', 'var_debt', 'sta_debt']:
        for token_name in ['usdc', 'usdt', 'dai']:
        # for token_name, token_amount in token_value_dicts[asset_from].items():
            if token_name == 'weth': continue
            if token_name not in used_token_list:
                used_token_list.append(token_name)
                price_data_list.append(chainlink_price_dict[token_name])
                price_name_list.append(f'chainlink_{token_name}')
                price_data_list.append(uniswapv3_price_dict[token_name])
                price_name_list.append(f'uniswapv3_{token_name}')
    var_train_df = pd.concat(price_data_list, axis=1)
    var_train_df.columns = price_name_list
    var_train_df = var_train_df.reset_index(drop=False)

    # hf_actual_series = cal_hf(var_train_df, token_value_dicts, liquidation_threshold_dict)
    # hf_actual_series.index = var_train_df['block_num']


    train_data = var_train_df.set_index('block_num')
    tmp_df = train_data.copy()
    log_f_diff = tmp_df.diff().dropna() 
    log_f_diff = log_f_diff.reset_index(drop=True)
    train_success = False

    trained_var = get_var_result(log_f_diff, maxlags=None)

    def mc_simulate(df, step=240):
        price_diff_prediction = pd.DataFrame(trained_var.simulate_var(step), columns=log_f_diff.columns)
        price_prediction = invert_transformation(tmp_df, price_diff_prediction) 
        hf_df = cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict)
        return hf_df

    mc_hf = pd.DataFrame(range(MCAmount)).apply(mc_simulate, args=(StepAhead,), axis=1).T
    horizontal_liquidation_pct = pd.DataFrame(mc_hf.apply(cal_pct_be_liquidated, axis=1), columns=['hf'])#.plot()
    # horizontal_liquidation_pct.columns = ['hf']
    horizontal_liquidation_pct['block_num'] = pd.Series(range(ReservesStatusEnd, ReservesStatusEnd + StepAhead))


    hf_df = pd.DataFrame({'block_num': block_list, 'hf': hf_list})
    return hf_df