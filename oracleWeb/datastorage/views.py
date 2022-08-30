from tokenize import Token
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.db.models import Max, Min
from django.db import IntegrityError

from .models import *
from .help_function import *

import pandas as pd
import numpy as np
import json
import pickle
import os
import tqdm
import time
import threading

import ctypes
from ctypes import c_char_p, cdll
from pandarallel import pandarallel
pandarallel.initialize(progress_bar=False)


archive_node = "http://localhost:19545"

each_update_amount = 20000

def datastorage(request):
    return HttpResponseRedirect('/datastorage/all_oracle')

def all_oracle(request):
    oracles = Oracle.objects.all()
    
    update_summary = request.GET.get('update_summary', '0')
    assert update_summary in ['0', '1'], "update_summary must be 0 or 1"
    if int(update_summary):
        oracles_info_dict = {}
        for token_pair in TokenPair.objects.all():
            oracle_name = token_pair.oracle.name
            min_max_dict = BlockNumber.objects.filter(price__token_pair__exact=token_pair).aggregate(Min('number'), Max('number'))
            
            # print(min_max_dict)
            min_block_number = min_max_dict.get("number__min",  -1)
            max_block_number = min_max_dict.get("number__max",  -1)
            # print(min_max_dict['number__min'])
            # print(min_block_number, max_block_number)
            # print(type(min_block_number), type(max_block_number))
            
            min_block_number = -1 if min_block_number is None else min_block_number
            max_block_number = -1 if max_block_number is None else max_block_number


            data_amount = Price.objects.filter(token_pair__exact=token_pair).count()
            
            try:
                summary = Summary.objects.get(token_pair__exact=token_pair)
                summary.min_block_number = min_block_number   
                summary.max_block_number = max_block_number
                summary.data_amount = data_amount
                summary.save()
            except Summary.DoesNotExist:
                Summary.objects.create(
                    token_pair=token_pair,
                    min_block_number=min_block_number,
                    max_block_number=max_block_number,
                    data_amount=data_amount
                )
    summaries = {"summaries": Summary.objects.all()}
    # print(summaries)
    return render(request, 'all_oracle.html', summaries)

def oracle_detail(request, oracle_name):
    oracle = Oracle.objects.get(name=oracle_name)
    
    return render(request, 'datastorage/oracle_detail.html', locals())



ORACLES = 'chainlink maker uniswapv2 uniswapv3'.split(' ')
STABLE_COINS = 'usd usdc usdt dai'.split(' ')

def initialize_data(request):
    for oracle in ORACLES:
        oracle_obj = Oracle.objects.create(name=oracle)
        for stable_coin in STABLE_COINS:
            token_pair = ['eth', stable_coin]
            for i in range(2):
                token0, token1 = token_pair[i], token_pair[1-i]
                TokenPair.objects.create(
                    token0=token0, 
                    token1=token1, 
                    oracle=oracle_obj,
                    support=True
                )
    return HttpResponse('initialize TABLES')


def update_block(request):
    min_block_num = Block.objects.aggregate(Min('number')).get("number__min",  np.inf)
    max_block_num = Block.objects.aggregate(Max('number')).get("number__max", -np.inf)
    min_block_num = np.inf if min_block_num is None else min_block_num
    max_block_num = -np.inf if max_block_num is None else max_block_num

    DATA_UPDATE_FORM = f"""
    Block Min : { min_block_num }, Max : { max_block_num }
    <form method='post' action='update_block'>
        BlockFrom: <input type='number' name='block_from'>
        BlockTo: <input type='number' name='block_to'>
        <input type='submit'; value='update_data'>
    </form>
    """
    if request.method == 'GET':
        return HttpResponse(DATA_UPDATE_FORM)
    # if request.method == 'GET':
    #     oracle = request.GET('oracle')
    #     price_type = request.GET('price_type')
    #     block_from = request
    if request.method == 'POST':

        start = time.time()

        block_from = int(request.POST['block_from'])
        block_to = int(request.POST['block_to'])
        assert block_to > block_from, "ERROR: block_to must be greater than block_from"


        blcokFrom = block_from
        blockTo = block_to

        
        # lib = ctypes.cdll.LoadLibrary("eth_crawler/library.so")
        GoInt64 = ctypes.c_int64
        GoInt = GoInt64
        # pandarallel.initialize(progress_bar=False)

        __library = cdll.LoadLibrary('../eth_crawler/library.so')

        get_block_time = __library.get_block_time
        get_block_time.argtypes = [c_char_p, GoInt, GoInt]
        get_block_time.restype = c_char_p

        # Block Time
        try:
            res = get_block_time(
                archive_node.encode(), 
                GoInt(blcokFrom), 
                GoInt(blockTo)
            )
        except Exception as e: 
            print(e)
            return HttpResponse("Archive Node not connected")

        res = res.decode("utf-8")
        res = pd.DataFrame(json.loads(s=res).items(), columns=['BlockNum', 'Timestamp'])
        res['Datetime'] = pd.to_datetime(res['Timestamp'], unit='s', utc=True)
        res['TimeStr'] = res['Datetime'].apply(str)
        block_time_df = res

        

        for block_time_index in tqdm.tqdm(block_time_df.index):
            tmp_block_num = int(block_time_df.loc[block_time_index, 'BlockNum'])
            if tmp_block_num < min_block_num or tmp_block_num > max_block_num:
                # try: 
                tmp_block_num = BlockNumber.objects.get_or_create(number=tmp_block_num)[0]
                # except BlockNumber.DoesNotExist:
                #     tmp_block_num = BlockNumber.objects.create(number=tmp_block_num)
                Block.objects.create(
                    number=tmp_block_num,
                    timestamp=block_time_df.loc[block_time_index, 'Timestamp'],
                    datetime= block_time_df.loc[block_time_index, 'Datetime'].to_pydatetime(),
                    utc_time_str=block_time_df.loc[block_time_index, 'TimeStr'] 
                )
        end = time.time()
        return HttpResponse(f"Data Crawl Completed with time {np.round(end - start, 2)} second"+DATA_UPDATE_FORM)


def block_time_auto_update(request):

    request.GET = request.GET.copy()
    request.POST = request.POST.copy()
    request.method = 'POST'
    request.POST = {}
    request.GET["update_summary"] = "1"
    print_update = request.GET.get("print_update", "0") == "1"
    time_wait = int(request.GET.get("time_wait", "0"))
    # print(print_update)
    # print("--- Updating Summary ---")
    # all_oracle(request) # update all summary
    # print("---  Start Crawling  ---")
    while True:
        min_block_num = Block.objects.aggregate(Min('number')).get("number__min",  np.inf)
        max_block_num = Block.objects.aggregate(Max('number')).get("number__max", -np.inf)
        min_block_num = np.inf if min_block_num is None else min_block_num
        max_block_num = -np.inf if max_block_num is None else max_block_num
        max_block_num = 12980000 if max_block_num < 12980000 else max_block_num
        
        # latest_block = 14956506 #get_latest_block_number()
        # latest_block = 15000000 #get_latest_block_number()
        latest_block = get_latest_block_number()

        time.sleep(time_wait)
        request.POST['block_from'] =  max_block_num # 15200021  #
        # request.POST['block_from'] =  15195000

        request.POST['block_to'] = latest_block
        request.POST['replace'] = "False"

        # if summary.token_pair.oracle.name == "uniswapv3":# and request.POST['token1'] == "dai":
        #     pass
        # else:
        #     continue

        if request.POST['block_to'] > request.POST['block_from']:
            if request.POST['block_to'] > (request.POST['block_from'] + each_update_amount):
                request.POST['block_to'] = request.POST['block_from'] + each_update_amount
            if request.POST['block_to'] > max_block_num:
            
                if print_update:
                    print(f"""
                    Updating Data: 
                    {request.POST['block_from']}
                    {request.POST['block_to']}
                    """)
                
                update_block(request)

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
                    Already Latest: 
                    latest block: {latest_block}
                    """)
        else: print(f"invalid block range {request.POST['block_from']} {request.POST['block_to']}")
    
    



def block_time_auto_update_view(request):
    t = threading.Thread(target=block_time_auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    return HttpResponse("started")


def insert_price(df, token_pair, replace=False):
    # try: 
    block_number = BlockNumber.objects.get_or_create(number=df["BlockNum"])[0]
    # except BlockNumber.DoesNotExist:
    #     block_number = BlockNumber.objects.create(number=df["BlockNum"])
    index = df["Index"]
    current = df["Current"]
    # try:
    #     Price.objects.get(
    #         block_number=block_number,
    #         index=index
    #     )
    # except Price.DoesNotExist:
        # print(token_pair,block_number,index,current)
    obj, created = Price.objects.get_or_create(
        # oracle=oracle,
        token_pair=token_pair,
        block_number=block_number,
        index=index,
        current=current
    )
    # except IntegrityError:
    if replace:
        new_p = Price.objects.get(
            token_pair=token_pair,
            block_number=block_number,
            index=index
        )
        new_p.current = current
        new_p.save()
    return 1

def update_data_from_csv(request, oracle_name):
    if oracle_name == 'uniswapv2':
        with open("/Users/anl/Library/CloudStorage/OneDrive-Personal/学习/课程资料/ICL/学习中/3 - Summer/Oracles/Code/eth_crawler/data/price/uniswap_v2_eth_usdc_raw.pickle", "rb") as output_file:
            uniswap_v2_usdc_eth_price_df = pickle.load(output_file)
            update_data_from_csv_inner(
                oracle='uniswapv2', 
                token0='eth', 
                token1='usdc',
                res=uniswap_v2_usdc_eth_price_df
            )
            uniswap_v2_usdc_eth_price_df['Current'] = 1.0/uniswap_v2_usdc_eth_price_df['Current']
            update_data_from_csv_inner(
                oracle='uniswapv2', 
                token0='usdc', 
                token1='eth',
                res=uniswap_v2_usdc_eth_price_df
            )
        with open("/Users/anl/Library/CloudStorage/OneDrive-Personal/学习/课程资料/ICL/学习中/3 - Summer/Oracles/Code/eth_crawler/data/price/uniswap_v2_eth_usdt_raw.pickle", "rb") as output_file:
            uniswap_v2_usdt_eth_price_df = pickle.load(output_file)
            update_data_from_csv_inner(
                oracle='uniswapv2', 
                token0='eth', 
                token1='usdt',
                res=uniswap_v2_usdt_eth_price_df
            )
            uniswap_v2_usdt_eth_price_df['Current'] = 1.0/uniswap_v2_usdt_eth_price_df['Current']
            update_data_from_csv_inner(
                oracle='uniswapv2', 
                token0='usdt', 
                token1='eth',
                res=uniswap_v2_usdt_eth_price_df
            )
    else:
        with open("/Users/anl/Library/CloudStorage/OneDrive-Personal/学习/课程资料/ICL/学习中/3 - Summer/Oracles/Code/eth_crawler/data/price/uniswap_v3_eth_usdc_005_raw.pickle", "rb") as output_file:
            uniswap_v3_usdc_eth_price_df = pickle.load(output_file)
            update_data_from_csv_inner(
                oracle='uniswapv3', 
                token0='eth', 
                token1='usdc',
                res=uniswap_v3_usdc_eth_price_df
            )
            uniswap_v3_usdc_eth_price_df['Current'] = 1.0/uniswap_v3_usdc_eth_price_df['Current']
            update_data_from_csv_inner(
                oracle='uniswapv3', 
                token0='usdc', 
                token1='eth',
                res=uniswap_v3_usdc_eth_price_df
            )
        with open("/Users/anl/Library/CloudStorage/OneDrive-Personal/学习/课程资料/ICL/学习中/3 - Summer/Oracles/Code/eth_crawler/data/price/uniswap_v3_eth_usdt_005_raw.pickle", "rb") as output_file:
            uniswap_v3_usdt_eth_price_df = pickle.load(output_file)
            update_data_from_csv_inner(
                oracle='uniswapv3', 
                token0='eth', 
                token1='usdt',
                res=uniswap_v3_usdt_eth_price_df
            )
            uniswap_v3_usdt_eth_price_df['Current'] = 1.0/uniswap_v3_usdt_eth_price_df['Current']
            update_data_from_csv_inner(
                oracle='uniswapv3', 
                token0='usdt', 
                token1='eth',
                res=uniswap_v3_usdt_eth_price_df
            )
    return HttpResponse(f'read {oracle_name} csv done')

def update_data_from_csv_inner(oracle, token0, token1, res):
    # oracle_name = oracle
    # token_pair_name = f"{token0}_{token1}"
    # try:
    oracle = Oracle.objects.get_or_create(name=oracle)[0]
    # except Oracle.DoesNotExist:
    #     oracle = Oracle.objects.create(name=oracle)
    # try: 
    token_pair = TokenPair.objects.get_or_create(oracle=oracle, token0=token0, token1=token1)[0]
    # except TokenPair.DoesNotExist:
    #     token_pair = TokenPair.objects.create(oracle=oracle, token0=token0, token1=token1)

    res = res.reset_index(drop=True)

    # pandarallel.initialize(progress_bar=False)
    # pandas row apply
    from tqdm import tqdm
    tqdm.pandas()
    res.progress_apply(insert_price, args=(token_pair,), axis=1)
    
    # for data_index in tqdm.tqdm(res.index):


    #     try: 
    #         # print(res.loc[data_index,"BlockNum"])
    #         block_number = BlockNumber.objects.get(number=res.loc[data_index,"BlockNum"])
    #     except BlockNumber.DoesNotExist:
    #         block_number = BlockNumber.objects.create(number=res.loc[data_index,"BlockNum"])
    #     index = res.loc[data_index, "Index"]
    #     current = res.loc[data_index, "Current"]
        
    #     try:
    #         Price.objects.get(
    #             block_number=block_number,
    #             index=index
    #         )
    #     except Price.DoesNotExist:
    #         Price.objects.create(
    #             # oracle=oracle,
    #             token_pair=token_pair,
    #             block_number=block_number,
    #             index=index,
    #             current=current
    #         )
    
    

def update_data(request):
    BACK_TO_MAIN = f"""
    <a href="../main">Back To Main Web</a><br \><br \>
    """ 
    DATA_UPDATE_FORM = f"""
    <form method='post' action='update_data'>
        Oracle: <input type='text' name='oracle' value={request.GET.get("oracle", "")}>
        token0: <input type='text' name='token0' value={request.GET.get("token0", "")}>
        token1: <input type='text' name='token1' value={request.GET.get("token1", "")}>
        <br \><br \>
        BlockFrom: <input type='number' name='block_from' value={request.GET.get("from", "")}>
        BlockTo: <input type='number' name='block_to' value={request.GET.get("to", "")}>
        <label for="replace">Replace Database Data</label>
        <select id="replace" name="replace">
            <option value="True">True</option>
            <option value="False">False</option>
        </select>
        <br \><br \>
        <input type='submit'; value='update_data'>
    </form>
    """
    token_pair_info = ""
    if request.method == 'GET':
        oracle = request.GET.get("oracle", "")
        token0 = request.GET.get("token0", "")
        token1 = request.GET.get("token1", "")
        try:
            oracle_obj=Oracle.objects.get(name=oracle)
            try:
                token_pair_obj=TokenPair.objects.get(oracle=oracle_obj, token0=token0, token1=token1)
                try:
                    summary = Summary.objects.get(
                        token_pair__exact=token_pair_obj
                    )
                    token_pair_info = f"""
                    {oracle}, {token0}/{token1} 
                    <br \><br \>
                    Min Block Number: {summary.min_block_number}
                    Max Block Number: {summary.max_block_number}
                    <br \>
                    <br \>
                    """ 
                except Summary.DoesNotExist:
                    pass
            except TokenPair.DoesNotExist:
                pass
        except Oracle.DoesNotExist:
            pass
        return HttpResponse(BACK_TO_MAIN + token_pair_info + DATA_UPDATE_FORM)
    # if request.method == 'GET':
    #     oracle = request.GET('oracle')
    #     price_type = request.GET('price_type')
    #     block_from = request
    if request.method == 'POST':
        start = time.time()
        oracle = request.POST['oracle'].lower()
        token0 = request.POST['token0'].lower()
        token1 = request.POST['token1'].lower()
        replace= True if request.POST['replace'] == 'True' else False
        block_from = int(request.POST['block_from'])
        block_to = int(request.POST['block_to'])
        assert block_to > block_from, "ERROR: block_to must be greater than block_from"

        data_source = f"{oracle}_{token0}_{token1}"
        blcokFrom = block_from
        blockTo = block_to

        # lib = ctypes.cdll.LoadLibrary("eth_crawler/library.so")
        GoInt64 = ctypes.c_int64
        GoInt = GoInt64

        # pandarallel.initialize(progress_bar=False)

        __library = cdll.LoadLibrary('../eth_crawler/library.so')
        get_log_data = __library.get_log_data
        get_log_data.argtypes = [c_char_p, c_char_p, GoInt, GoInt]
        get_log_data.restype = c_char_p

        res = get_log_data(
            data_source.encode(), 
            archive_node.encode(), 
            GoInt(blcokFrom), 
            GoInt(blockTo)
        )

        res = res.decode("utf-8").split(';')[:-1]
        res = pd.DataFrame(list(map(lambda x: json.loads(s=x), res)))
        
        if res.shape[0] > 0:
            # Chainlink
            if oracle == 'chainlink':
                if token0 == 'eth':
                    res['Current'] = res['Current'].apply(lambda x: hex2int(x)*10e-9)
                    # res['Current'] = res['Current'].parallel_apply(lambda x: hex2int(x)*10e-9)
                else:
                    res['Current'] = res['Current'].apply(lambda x: hex2int(x)/10**18)
                    # res['Current'] = res['Current'].parallel_apply(lambda x: hex2int(x)/10**18)
            
            # UniswapV2
            elif oracle == 'uniswapv2':
                cut_point = int(len(res['Data'].iloc[0])/2)
                res['Reserve1'] = res['Data'].apply(lambda x: x[cut_point:])
                res['Reserve0'] = res['Data'].apply(lambda x: x[:cut_point])
                # res['Reserve1'] = res['Data'].parallel_apply(lambda x: x[cut_point:])
                # res['Reserve0'] = res['Data'].parallel_apply(lambda x: x[:cut_point])
                
                if token0 in 'dai usdt usdc':
                    stable_token = token0
                    stable_i = 0
                elif token1 in 'dai usdt usdc':
                    stable_token = token1
                    stable_i = 1
                
                # r0 is eth for USDT
                r0, r1 = reformat_log_uniswap_v2(res, stable_token=stable_token)
                
                if stable_token == 'usdt':
                    
                    # USDT/ETH
                    if stable_i == 0:
                        res['Current'] = r0 / r1
                    
                    # ETH/USDT
                    else:
                        res['Current'] = r1 / r0

                else:
                    # USDC or DAI /ETH
                    if stable_i == 0:
                        res['Current'] = r1 / r0
                    
                    # ETH/USDC or DAI
                    else:
                        res['Current'] = r0 / r1
            
            # UniswapV3
            elif oracle == 'uniswapv3':
                cut_gap = int(len(res['Data'].iloc[0])/5)
                cut_start = 0
                for i, new_col in enumerate("amount0 amount1 sqrtPriceX96 liquidity tick".split(" ")):
                    cut_end = cut_start + cut_gap
                    res[new_col] = res['Data'].apply(lambda x: hex2int(x[cut_start:cut_end]))
                    cut_start = cut_end
            
                if token0 == 'eth':
                    if token1 == 'usdt':
                        res['Current'] = res['sqrtPriceX96'].apply(cal_price_eth_left)
                        # res['Current'] = res['sqrtPriceX96'].parallel_apply(cal_price_eth_left)
                    elif token1 == 'dai':
                        res['Current'] = res['sqrtPriceX96'].apply(cal_price_eth_right)/10**12
                        # res['Current'] = res['sqrtPriceX96'].parallel_apply(cal_price_eth_right)/10**12
                    else:
                        res['Current'] = res['sqrtPriceX96'].apply(cal_price_eth_right)
                        # res['Current'] = res['sqrtPriceX96'].parallel_apply(cal_price_eth_right)
                else:
                    if token0 == 'usdt':
                        res['Current'] = 1 / res['sqrtPriceX96'].apply(cal_price_eth_left)
                        # res['Current'] = 1 / res['sqrtPriceX96'].parallel_apply(cal_price_eth_left)
                    elif token0 == 'dai':
                        res['Current'] = 1 / res['sqrtPriceX96'].apply(cal_price_eth_right) * 10**12
                        # res['Current'] = 1 / res['sqrtPriceX96'].parallel_apply(cal_price_eth_right) * 10**12
                    else:
                        res['Current'] = 1 / res['sqrtPriceX96'].apply(cal_price_eth_right)
                        # res['Current'] = 1 / res['sqrtPriceX96'].parallel_apply(cal_price_eth_right)

            # Maker
            elif oracle == 'maker':
                assert token0 == 'eth' and token1 == 'usd', "ERROR: Maker Oracle only support ETH/USD"
                cut_gap = int(len(res['Data'].iloc[0])/2)
                cut_start = 0
                for i, new_col in enumerate("Current Age".split(" ")):
                    cut_end = cut_start + cut_gap
                    res[new_col] = res['Data'].apply(lambda x: hex2int(x[cut_start:cut_end]))
                    cut_start = cut_end
                res['Current'] = res['Current'] * 10e-19

            res = res[['Current', 'BlockNum', 'Index']]

            oracle_name = oracle
            token_pair_name = f"{token0}_{token1}"
            # try:
            oracle = Oracle.objects.get_or_create(name=oracle)[0]
            # except Oracle.DoesNotExist:
            #     oracle = Oracle.objects.create(name=oracle)
            # try: 
            token_pair = TokenPair.objects.get_or_create(oracle=oracle, token0=token0, token1=token1)[0]
            # except TokenPair.DoesNotExist:
            #     token_pair = TokenPair.objects.create(oracle=oracle, token0=token0, token1=token1)

            # pandarallel.initialize(progress_bar=True)
            # pandas row apply
            # from tqdm import tqdm
            # tqdm.pandas()
            res.apply(insert_price, args=(token_pair,replace,), axis=1)

            # min_block_num = Block.objects.aggregate(Min('number')).get("number__min",  np.inf)
            # max_block_num = Block.objects.aggregate(Max('number')).get("number__max", -np.inf)
            # ttt = Price.objects.BlockNum.aggregate(Min('number')).get("number__min",  np.inf).filter(token_pair__exact=token_pair)

            # Price.objects.filter(token_pair__)
            # ttt = Price.objects.prefetch_related('token_pair', 'block_number').filter(token_pair__exact=token_pair).aggregate(Min('number')).get("number__min",  np.inf)

            # block_num_list = []
            # for price_i in Price.objects.filter(token_pair__exact=token_pair).all():
            #     block_num_list.append(int(price_i.block_number.number))

            min_max_dict = BlockNumber.objects.filter(price__token_pair__exact=token_pair).aggregate(Min('number'), Max('number'))

            min_b = min_max_dict.get("number__min",  np.inf)
            max_b = min_max_dict.get("number__max",  -np.inf)

            end = time.time()

            DATA_UPDATE_FORM = f"""
            <form method='post' action='update_data'>
                Oracle: <input type='text' name='oracle' value={request.POST.get("oracle", "")}>
                token0: <input type='text' name='token0' value={request.POST.get("token0", "")}>
                token1: <input type='text' name='token1' value={request.POST.get("token1", "")}>
                <br \><br \>
                BlockFrom: <input type='number' name='block_from' value={request.POST.get("from", "")}>
                BlockTo: <input type='number' name='block_to' value={request.POST.get("to", "")}>
                <label for="replace">Replace Database Data</label>
               
                <select id="replace" name="replace">
                    <option value="True">True</option>
                    <option value="False">False</option>
                </select>
                 <br \><br \>
                <input type='submit'; value='update_data'>
            </form>
            """
            
            return HttpResponse(BACK_TO_MAIN + f"""
            Data Crawl Completed with time {end - start} second;
            <br \><br \>
            {oracle_name}, {token_pair_name}
            <br \><br \>
            Min Block Number: {min_b}
            Max Block Number: {max_b}
            <br \><br \>
            """ + DATA_UPDATE_FORM)
    return HttpResponse(BACK_TO_MAIN + DATA_UPDATE_FORM)

def get_latest_block_number():
    __library = cdll.LoadLibrary('../eth_crawler/library.so')
    get_latest_block_num = __library.get_latest_block_num
    get_latest_block_num.argtypes = [c_char_p]
    get_latest_block_num.restype = int
    res = get_latest_block_num(
        # data_source.encode(), 
        archive_node.encode(), 
        # GoInt(blcokFrom), 
        # GoInt(blockTo)
    )
    return res



def auto_update(request):

    request.GET = request.GET.copy()
    request.POST = request.POST.copy()
    request.method = 'POST'
    request.POST = {}
    request.GET["update_summary"] = "1"
    print_update = request.GET.get("print_update", "0") == "1"
    time_wait = int(request.GET.get("time_wait", "0"))
    # print(print_update)
    # print("--- Updating Summary ---")
    # all_oracle(request) # update all summary
    # print("---  Start Crawling  ---")
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        # print(t, getattr(t, "do_run", True))
        t = threading.currentThread()
        for summary in Summary.objects.all():
            if getattr(t, "do_run", True) is False:
                break
            # latest_block = 14956506 #get_latest_block_number()
            # latest_block = 15000000 #get_latest_block_number()
            latest_block = get_latest_block_number()
            if summary.data_amount > 0:
                time.sleep(time_wait)
                request.POST['oracle'] = summary.token_pair.oracle.name
                request.POST['token0'] = summary.token_pair.token0
                request.POST['token1'] = summary.token_pair.token1
                request.POST['block_from'] =  summary.max_block_number # 15200021  #
                # request.POST['block_from'] =  15195000

                request.POST['block_to'] = latest_block
                request.POST['replace'] = "False"

                # if summary.token_pair.oracle.name == "uniswapv3":# and request.POST['token1'] == "dai":
                #     pass
                # else:
                #     continue

                if request.POST['block_to'] > request.POST['block_from']:
                    if request.POST['block_to'] > (request.POST['block_from'] + each_update_amount):
                        request.POST['block_to'] = request.POST['block_from'] + each_update_amount
                    if request.POST['block_to'] > summary.max_block_number:
                    
                        if print_update:
                            print(f"""
                            Updating Data: 
                            {request.POST['oracle']}
                            {request.POST['token0']}
                            {request.POST['token1']}
                            {request.POST['block_from']}
                            {request.POST['block_to']}
                            """)
                        
                        update_data(request)

                        # summary = Summary.objects.get(token_pair__exact=token_pair)
                        # summary.min_block_number = min_block_number   
                        # if summary.max_block_number < request.POST['block_to']:
                        summary.max_block_number = request.POST['block_to']
                        summary.save()
                        # summary.max_block_number = request.POST['block_to']
                        # # summary.data_amount = data_amount
                        # summary.save()
                    else:
                        if print_update:
                            print(f"""
                            Already Latest: 
                            {request.POST['oracle']}
                            {request.POST['token0']}
                            {request.POST['token1']}
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


# def update_data(request, oracle_name):
#     oracle = Oracle.objects.get(name=oracle_name)
#     oracle.update_data()
#     return HttpResponseRedirect('/datastorage/all_oracle')

if __name__ == "__main__":
    update_data_from_csv("test")