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

# Create your views here.

aave_log_details = OrderedDict(
    ReserveDataUpdated = OrderedDict(
        topic0 = '0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a',
        topic1 = ['address', 'reserve'],
        topic2 = None,
        topic3 = None,
        data = [
            ['int', 'liquidityRate'],
            ['int', 'stableBorrowRate'],
            ['int', 'variableBorrowRate'],
            ['int', 'liquidityIndex'],
            ['int', 'variableBorrowIndex'],
        ]
    ),
    ReserveUsedAsCollateralEnabled = OrderedDict(
        topic0 = '0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'], # user, msg.sender
        topic3 = None,
        data = []
    ),
    ReserveUsedAsCollateralDisabled = OrderedDict(
        topic0 = '0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'], # user, msg.sender
        topic3 = None,
        data = []
    ),
    Deposit = OrderedDict(
        topic0 = '0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'],
        topic3 = ['int', 'referral'],
        data = [
            'address user'.split(' '),
            'int amount'.split(' '),
        ]
    ),
    Withdraw = OrderedDict(
        topic0 = '0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'], # user, msg.sender
        topic3 = ['address', 'to'], # token receiver
        data = [
            'int amount'.split(' '),
        ]
    ),
    Borrow = OrderedDict(
        topic0 = '0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'],
        topic3 = ['int', 'referral'],
        data = [
            'address user'.split(' '),  # user, msg.sender
            'int amount'.split(' '),
            'int rateMode'.split(' '),
            'int rate'.split(' '),
        ]
    ),
    Repay = OrderedDict(
        topic0 = '0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'],  # 
        topic3 = ['address', 'user'], # repayer,  user, msg.sender
        data = [
            'int amount'.split(' '),
        ]
    ),
    FlashLoan = OrderedDict(
        topic0 = '0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac',
        topic1 = ['address', 'target'],
        topic2 = ['address', 'initiator'],
        topic3 = ['address', 'asset'],
        data = [
            'int amount'.split(' '),
            'int premium'.split(' '),
            'int referralCode'.split(' ')
        ]
    ),
    LiquidationCall = OrderedDict(
        topic0 = '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286',
        topic1 = ['address', 'collateralAsset'],
        topic2 = ['address', 'debtAsset'],
        topic3 = ['address', 'onBehalfOf'],
        data = [
            'int debtToCover'.split(' '),
            'int liquidatedCollateralAmount'.split(' '),
            'address liquidator'.split(' '),
            'bool receiveAToken'.split(' '),
        ]
    ),
    Swap = OrderedDict(
        topic0 = '0xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'], # user, msg.sender
        topic3 = None,
        data = [
            'int rateMode'.split(' '),
        ]
    ),
    RebalanceStableBorrowRate = OrderedDict(
        topic0 = '0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300',
        topic1 = ['address', 'reserve'],
        topic2 = ['address', 'onBehalfOf'], # user, msg.sender
        topic3 = None,
        data = []
    )
)

liquidation_pool_target = [
    "ReserveUsedAsCollateralEnabled",
    "ReserveUsedAsCollateralDisabled", 
    "Deposit", 
    "Withdraw",
    "Borrow",
    "Repay",
    "LiquidationCall",
    "Swap",
    "RebalanceStableBorrowRate"
]

insert_col = [
    "BlockNumber", 
    "Index", 
    "reserve", 
    "onBehalfOf", 
    "amount", 
    "rateMode", 
    "rate"
]

ignore_topic0 = [
    '0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
]

address_delete = '000000000000000000000000'
def handel_raw_data(raw_data, raw_data_type):
    if raw_data_type == 'address':
        tmp_address = ''.join(raw_data.split(address_delete))#.copy()
        if tmp_address[:2] != '0x':
            tmp_address = '0x' + tmp_address
        return tmp_address
    if raw_data_type == 'int':
        return hex2int(raw_data)
    if raw_data_type == 'bool':
        return bool(hex2int(raw_data))

def crawl_data(request):
    pass


def data_summary(request):
    summaries = LendingPoolUpdateSummary.objects.all()
    return render(request,"pool_summary.html", {
            "summaries": summaries
        }
    )


def update_data(request):
    
    DATA_UPDATE_FORM = f"""
    <form method='post' action='update_data'>
        BlockFrom: <input type='number' name='block_from' value={request.GET.get("from", "")}>
        BlockTo: <input type='number' name='block_to' value={request.GET.get("to", "")}>
        <label for="replace">Replace Database Data</label>
        <select id="replace" name="replace">
            <option value="True">True</option>
            <option value="False">False</option>
        </select>
        <input type='submit'; value='update_data'>
    </form>
    """
    overall_summaries = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0]
    
    if request.method == 'GET':
        overall_data_summary = f"""
        {overall_summaries.action} 
        block from: {overall_summaries.min_block_number}
        block to: {overall_summaries.max_block_number}
        """
        return HttpResponse(overall_data_summary + DATA_UPDATE_FORM)
    # if request.method == 'GET':
    #     oracle = request.GET('oracle')
    #     price_type = request.GET('price_type')
    #     block_from = request
    if request.method == 'POST':
        start = time.time()
        # replace= True if request.POST['replace'] == 'True' else False
        block_from = int(request.POST['block_from'])
        block_to = int(request.POST['block_to'])
        assert block_to >= block_from, "ERROR: block_to must be greater than block_from"

        archive_node = "http://localhost:19545"
        # data_source = f"{oracle}_{token0}_{token1}"
        blcokFrom = block_from
        blockTo = block_to

        # lib = ctypes.cdll.LoadLibrary("eth_crawler/library.so")
        GoInt64 = ctypes.c_int64
        GoInt = GoInt64

        # pandarallel.initialize(progress_bar=False)

        __library = cdll.LoadLibrary('../eth_crawler/library.so')
        get_aave_log = __library.get_aave_log
        get_aave_log.argtypes = [c_char_p, GoInt, GoInt]
        get_aave_log.restype = c_char_p

        res = get_aave_log(
            # data_source.encode(), 
            archive_node.encode(), 
            GoInt(blcokFrom), 
            GoInt(blockTo)
        )

        res = res.decode("utf-8").split(';')[:-1]
        res = pd.DataFrame(list(map(lambda x: json.loads(s=x), res)))

        if res.shape[0] == 0:
            return HttpResponse("No Data" + DATA_UPDATE_FORM)

        for t in ['Topic0', 'Topic1', 'Topic2', 'Topic3']:
            if t not in res.columns:
                res[t] = res['Topic0'].copy()
        for t0 in res.Topic0.unique():
            assert t0 in [i['topic0'] for i in aave_log_details.values()] or t0 in ignore_topic0, f"ERROR: {t0} is not in aave_log_details"
        res = res[['Topic0', 'Topic1', 'Topic2', 'Topic3', 'Data', 'BlockNumber', 'Index']]
        log_df_dict = OrderedDict()
        for log_name, log_meta in aave_log_details.items():
            # print(log_name)
            sub_df = res[res["Topic0"] == log_meta['topic0']].copy()
            if sub_df.shape[0] == 0:
                continue
            del sub_df['Topic0']
            for i in range(1,4):
                topic_i = log_meta['topic'+str(i)]
                if topic_i is not None:
                    sub_df[topic_i[-1]] = sub_df['Topic'+str(i)].apply(
                        handel_raw_data, 
                        args=(topic_i[0],)
                    )
                del sub_df['Topic'+str(i)]
            if len(log_meta['data']) == 0 or sub_df.shape[0] == 0:
                continue
            cut_gap = int(len(sub_df['Data'].iloc[0])/len(log_meta['data']))
            cut_start = 0
            for data_type, data_name in log_meta['data']:
                cut_end = cut_start + cut_gap
                sub_df[data_name] = sub_df['Data'].apply(
                    lambda x: x[cut_start:cut_end]
                ).apply(
                    handel_raw_data, 
                    args=(data_type,)
                )
                cut_start = cut_end
            del sub_df['Data']
            sub_df['BlockNumber'] = sub_df['BlockNumber'].astype(int)
            sub_df['Index'] = sub_df['Index'].astype(int)
            sub_df = sub_df.reset_index(drop=True)
            log_df_dict[log_name] = sub_df

            
            # for col in sub_df.columns: print(sub_df[col])

        # return HttpResponse(DATA_UPDATE_FORM)
        for log_name, log_df in log_df_dict.items():
            update_record = LendingPoolUpdateSummary.objects.get_or_create(action=log_name)[0]
            if log_name in liquidation_pool_target:
                # log_df = log_df.loc[:, log_df.columns.isin(insert_col)]
                pool_data_list = []
                for df_index in tqdm.tqdm(log_df.index): 
                    extract_cell = lambda x: log_df.loc[df_index].get(x, "-1")
                    pool_data_list.append(LendingPoolInteraction(
                        block_number = BlockNumber.objects.get_or_create(number=extract_cell('BlockNumber'))[0],
                        index = extract_cell('Index'),
                        on_behalf_of = extract_cell('onBehalfOf'),
                        action = log_name,
                        reserve = extract_cell("reserve"),
                        amount = int(extract_cell("amount")),
                        rate_mode = extract_cell("rateMode"),
                        rate = int(extract_cell("rate")),
                    ))
                if len(pool_data_list) > 0:
                    for i in range(len(pool_data_list)//900000+1):
                        sub_list = pool_data_list[i*900000:(i+1)*900000]
                        try:
                            LendingPoolInteraction.objects.bulk_create(sub_list)
                        except IntegrityError:
                            for tmp_obj in tqdm.tqdm(sub_list):
                                try:
                                    tmp_obj.save()
                                except IntegrityError:
                                    pass
                    bn = log_df.get('BlockNumber', pd.Series(["-1"])).values

            if log_name == "ReserveDataUpdated":
                reserve_data_list = []
                for df_index in tqdm.tqdm(log_df.index): 
                    # print(log_df)
                    extract_cell = lambda x: log_df.loc[df_index].get(x, "-1")
                    reserve_data_list.append(ReservesStatus(
                        block_number = BlockNumber.objects.get_or_create(number=extract_cell('BlockNumber'))[0],
                        index = extract_cell('Index'),
                        reserve = extract_cell("reserve"),
                        liquidity_rate = extract_cell("liquidityRate"),
                        stable_borrow_rate = extract_cell("stableBorrowRate"),
                        variable_borrow_rate = extract_cell("variableBorrowRate"),
                        liquidity_index = extract_cell("liquidityIndex"),
                        variable_borrow_index = extract_cell("variableBorrowIndex"),
                    ))
                if len(reserve_data_list) > 0:
                    for i in range(len(reserve_data_list)//900000+1):
                        sub_list = reserve_data_list[i*900000:(i+1)*900000]
                        try:
                            ReservesStatus.objects.bulk_create(sub_list)
                        except IntegrityError:
                            for tmp_obj in tqdm.tqdm(sub_list):
                                try:
                                    tmp_obj.save()
                                except IntegrityError: 
                                    pass
                    bn = log_df.get('BlockNumber', pd.Series(["-1"])).values
                    # 123
            
            if log_name == "LiquidationCall":
                liquidation_call_list = []
                for df_index in tqdm.tqdm(log_df.index): 
                    extract_cell = lambda x: log_df.loc[df_index].get(x, "-1")
                    liquidation_call_list.append(LiquidationCall(
                        block_number = BlockNumber.objects.get_or_create(number=extract_cell('BlockNumber'))[0],
                        index = extract_cell('Index'),
                        on_behalf_of = extract_cell('onBehalfOf'),

                        collateral_asset = extract_cell("collateralAsset"),
                        debt_asset = extract_cell("debtAsset"),
                        debt_to_cover = extract_cell("debtToCover"),
                        liquidated_collateral_amount = extract_cell("liquidatedCollateralAmount"),
                        liquidator = extract_cell("liquidator"),

                        receive_atoken = extract_cell("receiveAToken"),
                    ))
                if len(liquidation_call_list) > 0:
                    for i in range(len(liquidation_call_list)//900000+1):
                        sub_list = liquidation_call_list[i*900000:(i+1)*900000]
                        try:
                            LiquidationCall.objects.bulk_create(sub_list)
                        except IntegrityError:
                            for tmp_obj in tqdm.tqdm(sub_list):
                                try:
                                    tmp_obj.save()
                                except IntegrityError:
                                    pass
                    bn = log_df.get('BlockNumber', pd.Series(["-1"])).values

            update_record.max_block_number = max(max(bn), update_record.max_block_number)
            update_record.min_block_number = min(min(bn), update_record.min_block_number)
            update_record.save()

        overall_summaries.max_block_number = max(block_to, update_record.max_block_number)
        overall_summaries.min_block_number = min(block_from, update_record.min_block_number)
        overall_summaries.save()
        overall_data_summary = f"""
        {overall_summaries.action} 
        block from: {overall_summaries.min_block_number}
        block to: {overall_summaries.max_block_number}
        """  

        end = time.time()
        return HttpResponse(f"""
        Data Crawl Completed with time {end - start} second;
        """ + overall_data_summary + DATA_UPDATE_FORM)
    
    return HttpResponse(DATA_UPDATE_FORM)

def get_latest_block_number():
    __library = cdll.LoadLibrary('../eth_crawler/library.so')
    get_latest_block_num = __library.get_latest_block_num
    get_latest_block_num.argtypes = [c_char_p]
    get_latest_block_num.restype = int
    archive_node = "http://localhost:19545"
    res = get_latest_block_num(
        # data_source.encode(), 
        archive_node.encode(), 
        # GoInt(blcokFrom), 
        # GoInt(blockTo)
    )
    return res


each_update_amount = 50000
contract_create_block = 11362579 

def auto_update(request):

    request.GET = request.GET.copy()
    request.POST = request.POST.copy()
    request.method = 'POST'
    request.POST = {}
    # request.GET["update_summary"] = "1"
    print_update = request.GET.get("print_update", "0") == "1"
    time_wait = int(request.GET.get("time_wait", "20"))
    reverse = request.GET.get('reverse', '0') == "1"
    # print(print_update)
    # print("--- Updating Summary ---")
    # all_oracle(request) # update all summary
    # print("---  Start Crawling  ---")
    while True:
        
        summary = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0]
        latest_block = get_latest_block_number()
        time.sleep(time_wait)

        if reverse:
            request.POST['block_from'] =  contract_create_block
            # request.POST['block_from'] =  15195000

            request.POST['block_to'] = summary.min_block_number - 1 # 15200021  #

            # direction = -1
        else:
            request.POST['block_from'] =  summary.max_block_number + 1 # 15200021  #
            # request.POST['block_from'] =  15195000

            request.POST['block_to'] = latest_block
            # direction = 1

        # if summary.token_pair.oracle.name == "uniswapv3":# and request.POST['token1'] == "dai":
        #     pass
        # else:
        #     continue

        if request.POST['block_to'] > request.POST['block_from']:
            if request.POST['block_to'] > (request.POST['block_from'] + each_update_amount - 1):
                if reverse:
                    request.POST['block_from'] = request.POST['block_to'] - each_update_amount + 1
                else:
                    request.POST['block_to'] = request.POST['block_from'] + each_update_amount - 1
            if request.POST['block_to'] > summary.max_block_number or request.POST['block_from'] < summary.min_block_number:
            
                if print_update:
                    print(f"""
                    Updating AAVE Data: 
                    {request.POST['block_from']}
                    {request.POST['block_to']}
                    """)
                
                update_data(request)

                # summary = Summary.objects.get(token_pair__exact=token_pair)
                # summary.min_block_number = min_block_number   
                # if summary.max_block_number < request.POST['block_to']:
                # summary.max_block_number = request.POST['block_to']
                # summary.save()
                # summary.max_block_number = request.POST['block_to']
                # # summary.data_amount = data_amount
                # summary.save()
            else:
                if print_update:
                    print(f"""
                    AAVE Already Latest: 
                    {summary.min_block_number}
                    {summary.max_block_number}

                    latest block: {latest_block}
                    """)
        else: print(f"invalid block range {request.POST['block_from']} {request.POST['block_to']}")
    
    



def auto_update_view(request):
    t = threading.Thread(target=auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    return HttpResponse("started")



## Reference : https://pyecharts.org/#/zh-cn/web_django
# Create your views here.
def response_as_json(data):
    json_str = json.dumps(data)
    response = HttpResponse(
        json_str,
        content_type="application/json",
    )
    response["Access-Control-Allow-Origin"] = "*"
    return response

def json_response(data, code=200):
    data = {
        "code": code,
        "msg": "success",
        "data": data,
    }
    return response_as_json(data)

def json_error(error_string="error", code=500, **kwargs):
    data = {
        "code": code,
        "msg": error_string,
        "data": {}
    }
    data.update(kwargs)
    return response_as_json(data)

JsonResponse = json_response
JsonError = json_error





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
    __library = cdll.LoadLibrary('../eth_crawler/library.so')

    get_single_block_time = __library.get_single_block_time
    get_single_block_time.argtypes = [c_char_p, GoInt]
    get_single_block_time.restype = c_char_p
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



TargetContract = ''
ReservesStatusStart = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0].max_block_number
ReservesStatusEnd = ReservesStatusStart - 6424
ReservesStatusEndIndex = 100000
StepAhead = 100
MCAount = 1000
hf_chart_done = False


def healthfactor_chart_view(request):
    have_data = False

    summary = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0]
    # summaries =BlockPriceUpdateRecord.objects.all()
    latest_block_num = summary.max_block_number

    if request.method == "POST":
        global TargetContract, ReservesStatusStart, ReservesStatusEnd, StepAhead, MCAount, hf_chart_done, ReservesStatusEndIndex
        # global StartBlock, EndBolck, Oracles
        
        ReservesStatusStart = int(request.POST.get("StartBlock", ReservesStatusStart))
        ReservesStatusEnd = int(request.POST.get("EndBlock", ReservesStatusEnd))
        ReservesStatusEndIndex = int(request.POST.get("EndIndex", ReservesStatusEndIndex))
        TargetContract = int(request.POST.get("TargetContract", TargetContract))

        interaction_df = get_interaction_data(TargetContract)
        interaction_df = interaction_df[interaction_df['action'] != "LiquidationCall"]
        if interaction_df.shape[0] != 0:
            potential = True
            other_token_counter = 0
            for token in set(interaction_df['reserve'].to_list()):
                if token not in token_dict.values():
                    potential = False
                    break
            if potential:
                have_data = True

                hf_chart_done = False

                t = threading.Thread(target=hf_chart,
                                    args=(request,))
                t.setDaemon(True)
                t.start()


    content = dict(
        potential=potential,
        have_data=have_data,
        summary=summary,
    )
    
    return render(request,"healthfactor_chart.html", content)


hf_chart = None

def hf_chart(request):
    global hf_chart, hf_chart_done
    reserves_status = get_reserves_status()
    latest_block_num = reserves_status['block_num'].max()
    interaction_df = get_interaction_data(TargetContract)

    until_block_num = latest_block_num
    until_block_num = ReservesStatusEnd
    until_index = ReservesStatusEndIndex

    until_block_n_index = combine_block_n_index({'block_num': until_block_num, 'index': until_index})
    # liquidation_index = until_index

    # Start Getting Data #####################################
    liquidation_df = get_liquidation_call(TargetContract)

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
    user_df = interaction_df.merge(reserves_status, on=['reserve'], how='left')
    change_token_address_to_name = lambda x: revert_token_dict[x] if x in revert_token_dict else x
    interaction_df['reserve'] = interaction_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    user_df['reserve'] = user_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    reserves_status['reserve'] = reserves_status['reserve'].apply(change_token_address_to_name).reset_index(drop=True)

    liquidation_df['collateral_asset'] = liquidation_df['collateral_asset'].apply(change_token_address_to_name)
    liquidation_df['debt_asset'] = liquidation_df['debt_asset'].apply(change_token_address_to_name)


    def get_liquidation_data(df_row):
        df_row = df_row.copy()
        if df_row['action'] != 'LiquidationCall': return df_row
        # collateral
        block_n_index_x = df_row['block_n_index_x']
        liquidation_row = liquidation_df[liquidation_df['block_n_index'] == block_n_index_x]
        collateral_asset = liquidation_row['collateral_asset'].values[0]
        tmp_reserves_status = reserves_status[\
            (reserves_status['reserve'] == collateral_asset) &\
            (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
        tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

        df_row['block_num_y'] = tmp_reserves_status['block_num']
        df_row['index_y'] = tmp_reserves_status['index']
        df_row['liquidity_rate'] = tmp_reserves_status['liquidity_rate']
        df_row['liquidity_index'] = tmp_reserves_status['liquidity_index']
        df_row['block_n_index_y'] = tmp_reserves_status['block_n_index']

        debt_asset = liquidation_row['debt_asset'].values[0]
        tmp_reserves_status = reserves_status[\
            (reserves_status['reserve'] == debt_asset) &\
            (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
        tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

        df_row['stable_borrow_rate'] = tmp_reserves_status['stable_borrow_rate']
        df_row['variable_borrow_rate'] = tmp_reserves_status['variable_borrow_rate']
        df_row['variable_borrow_index'] = tmp_reserves_status['variable_borrow_index']
        
        return df_row
    
    from_df = user_df[user_df['block_n_index_y'] <= user_df['block_n_index_x']]
    from_df = from_df.loc[from_df.groupby('block_n_index_x').block_n_index_y.idxmax()].reset_index(drop=True)
    from_df = from_df.apply(get_liquidation_data, axis=1)


    # a token
    collateral_dict = defaultdict(float)
    collatearl_able_dict = defaultdict(lambda :True)
    variable_debt_dict = defaultdict(float)
    stable_debt_dict = defaultdict(lambda : [None, None, None]) # amount, interest, start time

    sub_interaction_df = interaction_df[interaction_df['block_n_index'] <= until_block_n_index].copy()

    



class gen_hf_chart(APIView):
    def get(self, request, *args, **kwargs):
        # print("-----------------------------********************")
        
        if not hf_chart_done:
            return JsonResponse("not done yet")
        global hf_chart
        return JsonResponse(json.loads(hf_chart))

def debt_monitor_view(request):
    pass
