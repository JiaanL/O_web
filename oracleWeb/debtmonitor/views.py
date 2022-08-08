from django.shortcuts import render
import ctypes
from ctypes import c_char_p, cdll

from tokenize import Token
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.db.models import Max, Min
from django.db import IntegrityError

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
            'address reserve'.split(' '),
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
        assert block_to > block_from, "ERROR: block_to must be greater than block_from"

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
        res = res[['Topic0', 'Topic1', 'Topic2', 'Topic3', 'Data', 'BlockNumber', 'Index']]
        for t0 in res.Topic0.unique():
            assert t0 in [i['topic0'] for i in aave_log_details.values()], f"ERROR: {t0} is not in aave_log_details"
        log_df_dict = OrderedDict()
        for log_name, log_meta in aave_log_details.items():
            sub_df = res[res["Topic0"] == log_meta['topic0']].copy()
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


each_update_amount = 20000

def auto_update(request):

    request.GET = request.GET.copy()
    request.POST = request.POST.copy()
    request.method = 'POST'
    request.POST = {}
    # request.GET["update_summary"] = "1"
    print_update = request.GET.get("print_update", "0") == "1"
    time_wait = int(request.GET.get("time_wait", "0"))
    # print(print_update)
    # print("--- Updating Summary ---")
    # all_oracle(request) # update all summary
    # print("---  Start Crawling  ---")
    while True:
        
        summary = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0]
        latest_block = get_latest_block_number()
        time.sleep(time_wait)

        request.POST['block_from'] =  summary.max_block_number + 1 # 15200021  #
        # request.POST['block_from'] =  15195000

        request.POST['block_to'] = latest_block

        # if summary.token_pair.oracle.name == "uniswapv3":# and request.POST['token1'] == "dai":
        #     pass
        # else:
        #     continue

        if request.POST['block_to'] > request.POST['block_from']:
            if request.POST['block_to'] > (request.POST['block_from'] + each_update_amount - 1):
                request.POST['block_to'] = request.POST['block_from'] + each_update_amount - 1
            if request.POST['block_to'] > summary.max_block_number:
            
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