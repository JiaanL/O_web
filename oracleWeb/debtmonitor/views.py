from multiprocessing.sharedctypes import Value
from unittest.mock import NonCallableMagicMock
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

from pyecharts.charts import Line, Bar
import pyecharts.options as opts

from .models import *
from datastorage.models import *
from datavisualization.models import *
from .help_function import *
from .debt_function import *

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
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        
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


TargetContract = '0xb1b7f5dd1173c180eba4d91f8e78559e8a0b8b11'
ReservesStatusStart = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0].max_block_number
PreviousBlockForTrain = 6424
ReservesStatusEnd = ReservesStatusStart - PreviousBlockForTrain
ReservesStatusEndIndex = 100000
StepAhead = 100
MCAmount = 1000
HFChartDone = False
EMPTYPLOT = Line()
EMPTYPLOT = EMPTYPLOT.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
EMPTYPLOT = EMPTYPLOT.dump_options_with_quotes()


HF_chart = EMPTYPLOT
HF_previous_chart = EMPTYPLOT
Previous_chart_done = False
MC_chart = EMPTYPLOT
DebtData = None


def healthfactor_chart_view(request):
    have_data = False

    summary = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0]
    # summaries =BlockPriceUpdateRecord.objects.all()
    latest_block_num = summary.max_block_number

    potential=False

    if request.method == "POST":
        global TargetContract, ReservesStatusStart, ReservesStatusEnd, StepAhead, MCAmount, HFChartDone, ReservesStatusEndIndex, PreviousBlockForTrain, Previous_chart_done
        # global StartBlock, EndBolck, Oracles
        
        # ReservesStatusStart = int(request.POST.get("StartBlock", ReservesStatusStart))
        ReservesStatusEnd = int(request.POST.get("EndBlock", ReservesStatusEnd))
        ReservesStatusEndIndex = int(request.POST.get("EndIndex", ReservesStatusEndIndex))
        # PreviousBlockForTrain = ReservesStatusStart - ReservesStatusEnd
        PreviousBlockForTrain = int(request.POST.get("PreviousBlockForTrain", ReservesStatusEndIndex))

        StepAhead = int(request.POST.get("StepAhead", StepAhead))
        MCAmount = int(request.POST.get("MCAmount", MCAmount))

        TargetContract = request.POST.get("TargetContract", TargetContract)

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

                HFChartDone = False
                Previous_chart_done=False

                t = threading.Thread(target=gen_hf_chart)
                t.setDaemon(True)
                t.start()


    content = dict(
        step_ahead=StepAhead,
        mc_amount=MCAmount,
        potential=potential,
        have_data=have_data,
        reserve_status_end=ReservesStatusEnd,
        summary=summary,
        previous_block_for_train=PreviousBlockForTrain,
        reserves_status_end_index=ReservesStatusEndIndex,
        # previous_block_for_train=PreviousBlockForTrain,
        target_contract=TargetContract,
    )
    
    return render(request,"hf_chart.html", content)




def gen_hf_chart(hf_config=None):
    print('-------- START genarting hf chart --------')
    global HF_chart, HFChartDone, MC_chart, HF_previous_chart, Previous_chart_done
    global TargetContract, ReservesStatusEnd, StepAhead, MCAmount, ReservesStatusEndIndex, PreviousBlockForTrain

    if hf_config is not None:
        TargetContract = hf_config['target_address']
        ReservesStatusEnd = hf_config['reserve_status_end']
        StepAhead = hf_config['step_ahead']
        MCAmount = hf_config['mc_amount']
        ReservesStatusEndIndex = hf_config['reserves_status_end_index']
        PreviousBlockForTrain = hf_config['previous_block_for_train']

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

    for index_i in sub_interaction_df.index:

        action_i = sub_interaction_df.loc[index_i, 'action']
        block_n_index = sub_interaction_df.loc[index_i, 'block_n_index']
        block_num = sub_interaction_df.loc[index_i, 'block_num']
        index = sub_interaction_df.loc[index_i, 'index']

        # block_time = get_block_time(block_num)
        before_data = from_df[from_df['block_n_index_x'] == block_n_index]#['amount'].values[0]
        liquidity_index = before_data['liquidity_index'].values[0]
        variable_borrow_index = before_data['variable_borrow_index'].values[0]
        stable_borrow_rate = before_data['stable_borrow_rate'].values[0]
        
        if action_i == "LiquidationCall":
            'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
            liquidation_i = liquidation_df[liquidation_df['block_n_index'] == block_n_index].copy().reset_index(drop=True)
            collateral_asset = liquidation_i.loc[0, 'collateral_asset']
            debt_asset = liquidation_i.loc[0, 'debt_asset']
            debt_to_cover = liquidation_i.loc[0, 'debt_to_cover']
            liquidated_collateral_amount = liquidation_i.loc[0, 'liquidated_collateral_amount']

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

            update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
            rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate,
            collateral_dict, collatearl_able_dict, variable_debt_dict, stable_debt_dict)
    
    
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

    collatearl_in_eth = 0
    debt_in_eth = 0
    for token_name, token_amount in token_value_dicts['collateral'].items():
        if token_name == 'weth':
            collatearl_in_eth += token_amount
        else:
            collatearl_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

    for token_name, token_amount in token_value_dicts['var_debt'].items():
        if token_name == 'weth':
            debt_in_eth += token_amount
        else:
            debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

    for token_name, token_amount in token_value_dicts['sta_debt'].items():
        if token_name == 'weth':
            debt_in_eth += token_amount
        else:
            debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

    collatearl_m_threshold_in_eth = 0
    debt_m_threshold_in_eth = 0
    for token_name, token_amount in token_value_dicts['collateral'].items():
        if token_name == 'weth':
            collatearl_m_threshold_in_eth += token_amount * liquidation_threshold_dict[token_name]
        else:
            collatearl_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]  * liquidation_threshold_dict[token_name]

    for token_name, token_amount in token_value_dicts['var_debt'].items():
        if token_name == 'weth':
            debt_m_threshold_in_eth += token_amount
        else:
            debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

    for token_name, token_amount in token_value_dicts['sta_debt'].items():
        if token_name == 'weth':
            debt_m_threshold_in_eth += token_amount
        else:
            debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]
    collatearl_m_threshold_in_eth, debt_m_threshold_in_eth

    current_healthfactor = (collatearl_m_threshold_in_eth/debt_m_threshold_in_eth)

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
    hf_actual_series.index = var_train_df['block_num']

    line = Line()
    line.add_xaxis((hf_actual_series.index+1).to_list())
    line.add_yaxis(
        'Health Factor', 
        hf_actual_series.to_list(), 
        symbol="circle",
        symbol_size=1,
        label_opts=opts.LabelOpts(is_show=False),
    )
    line.add_yaxis(
        'HF = 1', 
        [1 for _ in range(len(hf_actual_series))], 
        symbol="circle",
        symbol_size=1,
        label_opts=opts.LabelOpts(is_show=False),
    )
    line = line.set_global_opts(
        title_opts=opts.TitleOpts(title="HF Previous Plot"),
        xaxis_opts=opts.AxisOpts(
            type_="value", 
            is_scale=True,
            name="Block Number",
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            # axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),
            is_scale=True,
            name="Health Factor",
        ),
    )
    HF_previous_chart = line.dump_options_with_quotes()
    Previous_chart_done=True

    train_data = var_train_df.set_index('block_num')
    # test_data = var_train_df[(int(len(var_train_df)*train_test_split)+1):].set_index('block_num')
    tmp_df = train_data.copy()#.set_index('block_num')
    # log_df = np.log(tmp_df)
    log_f_diff = tmp_df.diff().dropna() 
    log_f_diff = log_f_diff.reset_index(drop=True)
    train_success = False

    trained_var = get_var_result(log_f_diff, maxlags=None)

    # maxlags = 100

    # while not train_success:
    #     try:
    #         trained_var = get_var_result(log_f_diff, maxlags=maxlags)
    #         train_success = True
    #     except ValueError:
            
    #         maxlags -= 2

    #         if maxlags < 0:
    #             print(maxlags)
    #             break
            
    # assert train_success, 'Failed to train VAR, not enough data (previous)'


    def mc_simulate(df, step=240):
        price_diff_prediction = pd.DataFrame(trained_var.simulate_var(step), columns=log_f_diff.columns)
        price_prediction = invert_transformation(tmp_df, price_diff_prediction) 
        hf_df = cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict)
        return hf_df

    mc_hf = pd.DataFrame(range(MCAmount)).parallel_apply(mc_simulate, args=(StepAhead,), axis=1).T
    # vertical_liquidation_pct = mc_hf.parallel_apply(lambda x: (x < 1).any(), axis=0)
    horizontal_liquidation_pct = mc_hf.parallel_apply(cal_pct_be_liquidated, axis=1)#.plot()
    # mc_hf.plot(legend=False)

    line = Line()
    line.add_xaxis((horizontal_liquidation_pct.index+1).to_list())
    line.add_yaxis(
        'probability to be liquidated', 
        horizontal_liquidation_pct.to_list(), 
        symbol="circle",
        symbol_size=1,
        label_opts=opts.LabelOpts(is_show=False),
    )
    line = line.set_global_opts(
        title_opts=opts.TitleOpts(title="HF Plot"),
        xaxis_opts=opts.AxisOpts(
            type_="value", 
            is_scale=True,
            name="Step Ahead",
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            # axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),
            is_scale=True,
            name="Probability of HF below 1",
        ),
    )

    line = line.dump_options_with_quotes()
    # line = json.loads(line)

    HF_chart = line
    HFChartDone = True

    # MC_chart = 1
    global DebtData
    DebtData = dict(
        collatearl_in_eth=collatearl_in_eth, 
        debt_in_eth=debt_in_eth,
        current_healthfactor=current_healthfactor,
    )


def return_hf_plot():
    global HF_chart
    return HF_chart

def return_hf_previous_plot():
    global HF_previous_chart
    # print(HF_previous_chart)
    return HF_previous_chart

class get_hf_chart(APIView):
    def get(self, request, *args, **kwargs):
        # print("-----------------------------********************")
        
        if not HFChartDone:
            line = Line()
            line = line.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
            line = line.dump_options_with_quotes()
            line = json.loads(line)
            return JsonResponse(line)
        global HF_chart
        return JsonResponse(json.loads(HF_chart))

class get_hf_previous_chart(APIView):
    def get(self, request, *args, **kwargs):
        # print("-----------------------------********************")
        
        if not Previous_chart_done:
            line = Line()
            line = line.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
            line = line.dump_options_with_quotes()
            line = json.loads(line)
            return JsonResponse(line)
        global HF_previous_chart
        return JsonResponse(json.loads(HF_previous_chart))

def debt_monitor_view(request):
    pass
