from sre_parse import GLOBAL_FLAGS
from tokenize import Token
from django.shortcuts import render
from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.db.models import Max, Min, Avg, Q, F
from django.db import IntegrityError
from regex import B

from .models import * 
from datastorage.models import *
from .help_function import * 

import pandas as pd
import numpy as np
import json
import pickle
import os
import tqdm
import time
from random import randrange
from collections import defaultdict
import threading

from pyecharts.charts import Line, Bar
import pyecharts.options as opts
from rest_framework.views import APIView 

import ctypes
from ctypes import c_char_p, cdll
from pandarallel import pandarallel
pandarallel.initialize(progress_bar=False)
import swifter

# Create your views here.
def block_granularity_update(request):
    # replace = True if request.GET.get('replace', "False") == "True" else False
    block_from = int(request.GET.get('block_from', "-1"))
    block_to = int(request.GET.get('block_to', "-1"))
    # block_df = pd.DataFrame(list(BlockNumber.objects.all().values()))
    # print(block_df.head())
    for summary in Summary.objects.all():
        if summary.data_amount > 0:
            
            try:
                update_record = BlockPriceUpdateRecord.objects.get(token_pair=summary.token_pair)
            except BlockPriceUpdateRecord.DoesNotExist:
                update_record = BlockPriceUpdateRecord.objects.create(token_pair=summary.token_pair)
            

            # print(summary.token_pair.oracle.name, summary.token_pair.token0, summary.token_pair.token1)

            # if summary.token_pair.oracle.name == 'uniswapv2':
            #     print(summary.min_block_number, summary.max_block_number)
            #     print(update_record.min_block_number, update_record.max_block_number)
            block_from_i = block_from
            block_to_i = block_to
            if block_from_i == -1:
                block_from_i = summary.min_block_number
            if block_to_i == -1:
                block_to_i = summary.max_block_number
            
            price = pd.DataFrame(
                list(
                    Price.objects.filter(
                        Q(token_pair=summary.token_pair) &\
                        Q(block_number__number__gte=block_from_i) &\
                        Q(block_number__number__lte=block_to_i) &\
                        (Q(block_number__number__gt=update_record.max_block_number) |\
                        Q(block_number__number__lt=update_record.min_block_number))
                    ).all().values()
                )
            )
            # if summary.token_pair.oracle.name == 'uniswapv2':
            #     print(price)
            #     print(pd.DataFrame(
            #         list(
            #             Price.objects.filter(
            #                 Q(token_pair=summary.token_pair) &\
            #                 # Q(block_number__number__gte=block_from_i) &\
            #                 # Q(block_number__number__lte=block_to_i) &\
            #                 Q(block_number__number__gt=update_record.max_block_number) 
            #                 # Q(block_number__number__lt=update_record.min_block_number)
            #             ).all().values()
            #         )
            #     ))

            b_price_list = [] 
            if price.shape[0] > 0:
                price = price['block_number_id current'.split(' ')]
                # price.columns = ['block_number', 'current']
                # get blcok average
                price = price.groupby('block_number_id').apply(np.mean)[['current']]
                # price.groupby('block_number').parallel_apply(lambda x: x.sort_values(by='index'))

            
            # for block_price_i in block_price:  
                for block_id_i in tqdm.tqdm(price.index): 
                    if price.loc[block_id_i]['current'] > 5000:
                        print(summary.token_pair, block_id_i, price.loc[block_id_i]['current'])

                    b_price_list.append(BlockPrice(
                        token_pair=summary.token_pair, 
                        block_number_id=block_id_i,
                        # block_number=block_number_obj, 
                        current=price.loc[block_id_i]['current']
                    ))
            if len(b_price_list) > 0:
                for i in range(len(b_price_list)//900000+1):
                    sub_list = b_price_list[i*900000:(i+1)*900000]
                    try:
                        BlockPrice.objects.bulk_create(sub_list)
                    except IntegrityError:
                        for tmp_obj in tqdm.tqdm(sub_list):
                            try:
                                tmp_obj.save()
                            except IntegrityError:
                                pass        
                # BlockPrice.objects.bulk_create(b_price_list)
                update_record.max_block_number = max(block_to_i, update_record.max_block_number)
                update_record.min_block_number = min(block_from_i, update_record.min_block_number)
                update_record.save()
            


    return HttpResponse("Done")
    # return render(request, 'datavisualization/block_granularity_update.html')


def block_granularity_auto_update(request):
    time_wait = int(request.GET.get("time_wait", "10"))
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        time.sleep(time_wait)
        block_granularity_update(request)
        print("--- block granularity auto updated ---")
    

def block_granularity_auto_update_view(request):
    t = threading.Thread(target=block_granularity_auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    return HttpResponse("started")


latency_targets = {
    # from : [to]
    "uniswapv3_eth_usdc":["chainlink_eth_usd", "maker_eth_usd"],
    "uniswapv3_eth_usdt":["chainlink_eth_usd", "maker_eth_usd"],
    "uniswapv3_eth_dai":["chainlink_eth_usd", "maker_eth_usd"],
    "uniswapv2_eth_usdc":["chainlink_eth_usd", "maker_eth_usd"],
    "uniswapv2_eth_usdt":["chainlink_eth_usd", "maker_eth_usd"],
    "uniswapv2_eth_dai":["chainlink_eth_usd", "maker_eth_usd"],
}
global_block_from = 12980000
irf_periods = 300
# latency_targets = [
#     "chainlink_eth_usd",
#     "maker_eth_usd",
#     "uniswap_eth_usdc"
# ]

def latency_data_auto_gen(request):
    def while_update(request):
        while True:
            latency_data_gen(request)
            time.sleep(5)
    t = threading.Thread(target=while_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    return HttpResponse("started")


def latency_data_gen(request):
    block_from = int(request.GET.get('block_from', "-1"))
    if block_from < global_block_from and block_from > 0:
        block_from = global_block_from

    block_to = int(request.GET.get('block_to', "-1"))
    frequency = int(request.GET.get('frequency', "6424"))
    
    frequency_obj = Frequency.objects.get_or_create(frequency_num=frequency)[0]
    
    needed_data = []
    for source, targets in latency_targets.items():
        needed_data.append(source)
        for target in targets:
            needed_data.append(target)
    needed_data = list(set(needed_data))

    # token_pair_list = []
    # data_list = []

    # print(block_from, block_to, frequency)
    for target in needed_data:
        oracle_name, token0, token1 = target.split('_')
        token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
        summary = BlockPriceUpdateRecord.objects.get(
            token_pair=token_pair,
        )
    # for summary in BlockPriceUpdateRecord.objects.all():
        
        # if (summary.token_pair.oracle.name == "chainlink" or\
        #     summary.token_pair.oracle.name == "maker" or\
        #     summary.token_pair.oracle.name == "uniswapv3") and\
        #     summary.token_pair.token0 == "eth" and\
        #     (summary.token_pair.token1 == "usd" or\
        #     summary.token_pair.token1 == "usc"):
        # except LatencUpdateRecord.DoesNotExist:
        #     update_record = LatencUpdateRecord.objects.create(
        #         token_pair=summary.token_pair,
        #         frequency=Frequency.objects.get(frequency_num=frequency)
        #     )
        if block_from == -1:
            block_from = summary.min_block_number
        if block_to == -1:
            block_to = summary.max_block_number

        if block_from < summary.min_block_number:
            block_from = summary.min_block_number
        if block_to > summary.max_block_number:
            block_to = summary.max_block_number
        
        # token_pair_list.append(token_pair)

        # update_record = LatencUpdateRecord.objects.get_or_create(
        #     token_pair=summary.token_pair,
        #     frequency=frequency_obj
        # )[0]

        # bp = pd.DataFrame(
        #     list(
        #         BlockPrice.objects.filter(
        #             Q(token_pair=token_pair) &\
        #             # Q(token_pair=chainlink) &\
        #             # Q(token_pair=uniswapv3) &\
        #             Q(block_number__number__gte=block_from) &\
        #             Q(block_number__number__lte=block_to) &\
        #             Q(block_number__number__gte=update_record.max_block_number) &\
        #             Q(block_number__number__lte=update_record.min_block_number)
        #         ).annotate(
        #             block_num=F('block_number__number'),
        #             # token_pair__token0=F('token_pair__token0'),
        #             # token_pair__token1=F('token_pair__token1'),
        #             # token_pair__oracle__name=F('token_pair__oracle__name'),
        #         ).all().values()
        #     )
        # )
        # bp = bp['block_num current'.split(' ')]
        # bp.columns = ['block_number', target]
        # df = df.merge(bp, on='block_number', how='left')

        # bp['block_number'] = bp['block_number__number']

        # data_list.append(bp)

    # row concat
    # data = pd.concat(data_list)
    # data['log_current'] = np.log(data['current'])
    


    block_time = pd.DataFrame([i for i in range(block_from, block_to)], columns=['block_num'])

    block_points = pd.DataFrame([i for i in range(global_block_from, block_to, frequency)], columns=['block_num'])

    block_points = block_points[block_points['block_num'] >= block_from].reset_index(drop=True)
    # print(block_points)
    # print("-------------------")
    for source, targets in latency_targets.items():
        oracle_name, token0, token1 = source.split('_')
        source_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
        source_bp = pd.DataFrame(
            list(
                BlockPrice.objects.filter(
                    Q(token_pair=source_token_pair) &\
                    Q(block_number__number__gte=block_from) &\
                    Q(block_number__number__lte=block_to)
                    # Q(block_number__number__gte=update_record.max_block_number) &\
                    # Q(block_number__number__lte=update_record.min_block_number)
                ).annotate(
                    block_num=F('block_number__number'),
                ).all().values()
            )
        )
        source_bp = source_bp["block_num current".split(' ')]
        source_bp.columns = ['block_num', source]
        source_df = block_time.merge(source_bp, on='block_num', how='left')
        for target in targets:
            
            oracle_name, token0, token1 = target.split('_')
            target_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
            update_record = LatencyUpdateRecord.objects.get_or_create(
                source_token_pair=source_token_pair,
                target_token_pair=target_token_pair,
                frequency=frequency_obj
            )[0]

            target_bp = pd.DataFrame(
                list(
                    BlockPrice.objects.filter(
                        Q(token_pair=target_token_pair) &\
                        Q(block_number__number__gte=block_from) &\
                        Q(block_number__number__lte=block_to) &\
                        (Q(block_number__number__gte=update_record.max_block_number) |\
                        Q(block_number__number__lte=update_record.min_block_number))
                    ).annotate(
                        block_num=F('block_number__number'),
                    ).all().values()
                )
            )
            # print(block_from, block_to ,update_record.min_block_number, update_record.max_block_number )
            # print(source_df)
            # print(target_bp)
            # print("----------**---------")
            if target_bp.shape[0] <= 0:
                continue
            # print("----------*---------")
            # print(update_record.max_block_number, update_record.min_block_number)
            # print(source, target)
            # print(target_bp)
            
            target_bp = target_bp["block_num current".split(' ')]
            target_bp.columns = ['block_num', target]
            
            
            tmp_source_df = source_df[(source_df['block_num'] >= update_record.max_block_number)|(source_df['block_num'] <= update_record.min_block_number)]
            # tmp_source_df = tmp_source_df[tmp_source_df['block_num'] <= update_record.min_block_number]
            df = tmp_source_df.merge(target_bp, on='block_num', how='left')
            df = df.fillna(method='ffill').dropna().reset_index(drop=True)
            

            # print(source_df)
            # print(target_bp)
            # print(df)
            # print([i for i in df['block_num']])
            # print(tmp_source_df)
            # print(target_bp)
            # print(df)
            
            # for i in range(len(block_points)):
            def train_var(block_point):
                # block_point = block_points[i]
                block_point = block_point["block_num"]
                # print(block_point)
                next_block_point = block_point + frequency
                if block_from <= block_point and \
                    block_to >= next_block_point and\
                    (update_record.max_block_number < block_point or\
                    update_record.min_block_number > next_block_point):
                    
                    tmp_df = df[df["block_num"] >= block_point]
                    tmp_df = tmp_df[tmp_df["block_num"] < next_block_point].reset_index(drop=True)
                    
                    # if tmp_df.shape[0] == 


                    tmp_df.set_index('block_num', inplace=True)
                    tmp_df = np.log(tmp_df)
                    log_f_diff = tmp_df.diff().dropna() 
                    log_f_diff = log_f_diff.reset_index(drop=True)
                    
                    # VAR irf model
                    model = get_var_result(log_f_diff)

                    try:
                        tmp_df = get_model_irf_df(model, irf_periods, log_f_diff.columns, return_data='weighted_avg_latency')
                        print(tmp_df)
                        return_value = tmp_df.loc[source, target]
                        if return_value < 1:
                            return_value = np.nan
                        return return_value
                    except Exception as e:
                        print(e)
                        return np.nan
                    
                    # exec(f"{models_type}_irf_list.append(tmp_df)")


            

            tqdm.tqdm.pandas()
            print("start latency traning model")
            # print(df)
            # print(block_points)
            result_df = block_points.progress_apply(train_var, axis=1).to_frame()
            # print(result_df)

            # result_df = block_points.swifter.progress_bar(True).apply(train_var, axis=1).to_frame()
            
            # result_df = block_points.parallel_apply(train_var, axis=1).to_frame()

            result_df = block_points.merge(result_df, left_index=True, right_index=True)
            result_df.columns = ["block_num", "latency"]
            if result_df.iloc[-1, 1] == None:
                result_df = result_df.iloc[:-1,:]
            # result_df.fillna(method='ffill', inplace=True)
            result_df.dropna(inplace=True)
            # print(result_df)


            latency_result_list = []
            for df_index in tqdm.tqdm(result_df.index): 
                block_num_i = result_df.loc[df_index, "block_num"]
                latency_i = result_df.loc[df_index, "latency"]
                latency_result_list.append(LatencyRecord(
                    source_token_pair=source_token_pair,
                    target_token_pair=target_token_pair,
                    block_number=BlockNumber.objects.get_or_create(number=block_num_i)[0],
                    frequency=frequency_obj,
                    latency=latency_i
                ))
            if len(latency_result_list) > 0:
                for i in range(len(latency_result_list)//900000+1):
                    sub_list = latency_result_list[i*900000:(i+1)*900000]
                    try:
                        LatencyRecord.objects.bulk_create(sub_list)
                    except IntegrityError:
                        for tmp_obj in tqdm.tqdm(sub_list):
                            try:
                                tmp_obj.save()
                            except IntegrityError:
                                pass  
                
                # BlockPrice.objects.bulk_create(b_price_list)
                update_record.max_block_number = max(max(result_df['block_num']), update_record.max_block_number)
                update_record.min_block_number = min(min(result_df['block_num']), update_record.min_block_number)
                update_record.save()


    # print(result_df)
    return HttpResponse("Done")
                    

def latency_auto_update(request):
    time_wait = int(request.GET.get("time_wait", "10"))
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        time.sleep(time_wait)
        latency_data_gen(request)
        print("--- latency auto updated ---")
    

def latency_auto_update_view(request):
    t = threading.Thread(target=latency_auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    return HttpResponse("started")








    


    # for tmp_log_price_df in tqdm.tqdm(np.split(log_price_df, df_split_index(log_price_df, each_range=df_split_each_range))):
    #     if len(tmp_log_price_df.index) == 0: continue
    #     start_block_num_list.append(tmp_log_price_df.index[0])
    #     end_block_num_list.append(tmp_log_price_df.index[-1])

    #     tmp_log_price_df = tmp_log_price_df.reset_index(drop=True)
        
    #     # print(f'size of df {tmp_log_price_df.shape}')

    #     # test stationary
    #     p_value_result = tmp_log_price_df.parallel_apply(my_adfuller_p_value, axis=0)
    #     p_value_result_list.append(pd.DataFrame(p_value_result, columns=['p_value']))
    #     # make stationary
    #     log_f_diff = tmp_log_price_df.diff().dropna() 
    #     log_f_diff = log_f_diff.reset_index(drop=True)
    #     log_diff_p_value_result = log_f_diff.parallel_apply(my_adfuller_p_value, axis=0)
    #     log_diff_p_value_result_list.append(pd.DataFrame(log_diff_p_value_result, columns=['p_value']))
        
    #     # VAR model
    #     fitted_model_result = main_multi_p(log_f_diff, split_num=split_num, model='var')
    #     fitted_var_model_list.append(fitted_model_result)

    #     # VECM model
    #     fitted_model_result = main_multi_p(tmp_log_price_df, split_num=split_num, model='vecm')
    #     fitted_vecm_model_list.append(fitted_model_result)
    

    # block_price_df = pd.concat(data_list, axis=1)

    return HttpResponse("Done")

    # BlockPrice.objects.filter(token_pair__token0__name='ETH').select_related('blocknumber')



StartBlock = -1
EndBolck = -1
Oracles = []

EMPTYPLOT = Line()
EMPTYPLOT = EMPTYPLOT.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
EMPTYPLOT = EMPTYPLOT.dump_options_with_quotes()

PricePlot = EMPTYPLOT


# def price_line_chart(request):
#     have_data = False
#     summaries =BlockPriceUpdateRecord.objects.all()
#     for summary in summaries:
#         summary.used = False
#     line="{}"
#     min_block = max([i.min_block_number for i in summaries])
#     max_block = min([i.max_block_number for i in summaries])

#     if request.method == "POST":
        
#         global StartBlock, EndBolck, Oracles
        
#         StartBlock = int(request.POST.get("StartBlock"))
#         EndBolck = int(request.POST.get("EndBlock"))

#         min_block, max_block = StartBlock, EndBolck

#         Oracles = request.POST.getlist("Oracles")
#         have_data = True
#         print(StartBlock,EndBolck,Oracles)
#         line = Line()
#         line.add_xaxis([i for i in range(StartBlock,EndBolck+1)])
#         block_df = pd.DataFrame([i for i in range(StartBlock, EndBolck+1)], columns=['block_number'])
#         for oracle in Oracles:
#             oracle_name, token0, token1 = oracle.split("_")
#             token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
#             b_price = BlockPrice.objects.filter(token_pair=token_pair, block_number__number__gte=StartBlock, block_number__number__lte=EndBolck).all()
#             b_price_dict = {i.block_number.number:i.current for i in b_price}
#             b_price_df = pd.DataFrame(b_price_dict.items(), columns=['block_number', 'current'])
#             b_price_df = b_price_df.merge(block_df, left_on='block_number', right_on='block_number', how='right')
#             b_price_df = b_price_df.fillna(method="ffill")
#             line.add_yaxis(oracle_name, b_price_df['current'].to_list())
#             for summary in summaries:
#                 if summary.token_pair == token_pair:
#                     summary.used = True


#         line = line.set_global_opts(title_opts=opts.TitleOpts(title="Price Line Plot"))

#         line = line.dump_options_with_quotes()

#         line = json.loads(line)


#         # line = JsonResponse(json.loads(line))
    
#     # from pyecharts.faker import Faker
    

#     print(line)

#     # return HttpResponse(c.render_embed())
#     content = dict(
#         have_data=have_data,
#         summaries=summaries,
#         line=line,
#         min_block=min_block,
#         max_block=max_block,
#     )
#     # print(min_block)
#     return render(request,"price_line_chart.html", content)



def get_price_line_chart(price_plot_config=None):
    global StartBlock, EndBolck, Oracles, PricePlot

    if price_plot_config is not None:
        StartBlock = price_plot_config['start_block']
        EndBolck = price_plot_config['end_block']
        Oracles = price_plot_config['oracles']

    line = Line()

    # print(StartBlock,EndBolck,Oracles)
    # 15330171 15339171 ['chainlink_eth_usd', 'uniswapv3_eth_usdc', 'uniswapv3_eth_usdt', 'uniswapv3_eth_dai']
   
    
    x_axis_data = [i for i in range(StartBlock,EndBolck+1)]
    block_df = pd.DataFrame(x_axis_data, columns=['block_number'])
    # print(block_df)
    line = line.add_xaxis(x_axis_data)
    # line = line.add_xaxis(xaxis_data=[i for i in range(len(x_axis_data))])
    # print([i for i in range(len(x_axis_data))])
    for oracle in Oracles:
        # print(oracle)
        oracle_name, token0, token1 = oracle.split("_")
        token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
        b_price = BlockPrice.objects.filter(token_pair=token_pair, block_number__number__gte=StartBlock, block_number__number__lte=EndBolck).all()
        b_price_dict = {i.block_number.number:i.current for i in b_price}
        b_price_df = pd.DataFrame(b_price_dict.items(), columns=['block_number', 'current'])
        b_price_df = b_price_df.merge(block_df, left_on='block_number', right_on='block_number', how='right')
        b_price_df = b_price_df.fillna(method="ffill")
        b_price_df = b_price_df.fillna(method="bfill")
        b_price_df = b_price_df.reset_index(drop=True)
        # print(b_price_df)
        line = line.add_yaxis(
            series_name=oracle, 
            y_axis=b_price_df['current'].to_list(),
            symbol="circle",
            symbol_size=1,
            label_opts=opts.LabelOpts(is_show=False),
        )

    
    line = line.set_global_opts(
        title_opts=opts.TitleOpts(title="Price Line Plot"),
        xaxis_opts=opts.AxisOpts(
            type_="value", 
            is_scale=True,
            name="block_number",
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            # axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),
            is_scale=True,
            name="price",
        ),
    )

    line = line.dump_options_with_quotes()

    PricePlot = line


    return line

def return_price_plot():
    global PricePlot
    return PricePlot

class gen_price_line_chart(APIView):
    def get(self, request, *args, **kwargs):
        # print("-----------------------------********************")
        # print(json.loads(get_price_line_chart()))
        return JsonResponse(json.loads(get_price_line_chart()))


def price_line_chart_view(request):
    have_data = False
    summaries =BlockPriceUpdateRecord.objects.all()
    for summary in summaries:
        summary.used = False
    
    min_block = max([i.min_block_number for i in summaries])
    max_block = min([i.max_block_number for i in summaries])

    if request.method == "POST":
        
        global StartBlock, EndBolck, Oracles
        
        StartBlock = int(request.POST.get("StartBlock"))
        EndBolck = int(request.POST.get("EndBlock"))

        min_block, max_block = StartBlock, EndBolck

        Oracles = request.POST.getlist("Oracles")
        have_data = True
        print(StartBlock,EndBolck,Oracles)
        for oracle in Oracles:
            oracle_name, token0, token1 = oracle.split("_")
            token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
            for summary in summaries:
                if summary.token_pair == token_pair:
                    summary.used = True

            # summary = BlockPriceUpdateRecord.objects.get(token_pair=token_pair)

    # return HttpResponse(c.render_embed())
    content = dict(
        have_data=have_data,
        summaries=summaries,
        # line=line,
        min_block=min_block,
        max_block=max_block,
    )
    
    return render(request,"price_line_chart.html", content)

LatencyStartBlock = -1
LatencyEndBolck = -1
LatencyOracles = latency_targets
LatencyFrequency = 6424

EMPTYPLOT = Line()
EMPTYPLOT = EMPTYPLOT.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
EMPTYPLOT = EMPTYPLOT.dump_options_with_quotes()
LatencyChart = EMPTYPLOT

def get_latency_chart(latency_config=None):
    global LatencyStartBlock, LatencyEndBolck, LatencyOracles, LatencyChart


    if latency_config is not None:
        LatencyStartBlock= latency_config['start_block']
        LatencyEndBolck = latency_config['end_block']
        LatencyOracles = latency_config['oracles']

    line = Line()
   
    
    # x_axis_data = [i for i in range(LatencyStartBlock,LatencyEndBolck+1)]

    block_points = pd.DataFrame([i for i in range(global_block_from, LatencyEndBolck, LatencyFrequency)], columns=['block_number'])
    block_points = block_points[block_points['block_number'] >= LatencyStartBlock]
    # block_df = pd.DataFrame(x_axis_data, columns=['block_number'])
    # print(block_df)
    line = line.add_xaxis(block_points['block_number'].to_list())
    # line = line.add_xaxis(xaxis_data=[i for i in range(len(x_axis_data))])
    # print([i for i in range(len(x_axis_data))])
    for source, targets in LatencyOracles.items():
        oracle_name, token0, token1 = source.split("_")
        source_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
        for target in targets:
            oracle_name, token0, token1 = target.split("_")
            target_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
            latency_data = LatencyRecord.objects.filter(
                frequency__frequency_num=LatencyFrequency,
                source_token_pair=source_token_pair, 
                target_token_pair=target_token_pair, 
                block_number__number__gte=LatencyStartBlock, 
                block_number__number__lte=LatencyEndBolck
            ).all()
            # b_price = BlockPrice.objects.filter(token_pair=target_token_pair, block_number__number__gte=LatencyStartBlock, block_number__number__lte=LatencyEndBolck).all()
            latency_dict = {i.block_number.number:i.latency for i in latency_data}

            latency_df = pd.DataFrame(latency_dict.items(), columns=['block_number', 'latency'])
            latency_df = latency_df.merge(block_points, left_on='block_number', right_on='block_number', how='right')
            latency_df = latency_df.fillna(method="ffill")
            latency_df = latency_df.fillna(method="bfill")
            latency_df = latency_df.reset_index(drop=True)
            print(oracle_name, latency_df['latency'].mean())
            # print(b_price_df)
            line = line.add_yaxis(
                series_name=source + ' -> ' + target, 
                y_axis=latency_df['latency'].to_list(),
                symbol="circle",
                symbol_size=1,
                label_opts=opts.LabelOpts(is_show=False),
                is_smooth=True
            )

    
    line = line.set_global_opts(
        title_opts=opts.TitleOpts(title="Latency Plot"),
        xaxis_opts=opts.AxisOpts(
            type_="value", 
            is_scale=True,
            name="block_number",
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            # axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True),
            is_scale=True,
            name="latency",
        ),
    )

    line = line.dump_options_with_quotes()

    LatencyChart = line

    return line

def return_latency_plot():
    global LatencyChart
    return LatencyChart

class gen_latency_chart(APIView):
    def get(self, request, *args, **kwargs):
        # print("-----------------------------********************")
        return JsonResponse(json.loads(get_latency_chart()))

def latency_chart_view(request):
    have_data = False
    summaries =LatencyUpdateRecord.objects.all()
    # summaries =BlockPriceUpdateRecord.objects.all()
    for summary in summaries:
        summary.used = False
    
    min_block = max([i.min_block_number for i in summaries])
    max_block = min([i.max_block_number for i in summaries])

    if request.method == "POST":
        global LatencyStartBlock, LatencyEndBolck, LatencyOracles
        # global StartBlock, EndBolck, Oracles
        
        LatencyStartBlock = int(request.POST.get("StartBlock"))
        LatencyEndBolck = int(request.POST.get("EndBlock"))

        min_block, max_block = LatencyStartBlock, LatencyEndBolck

        # Source = request.POST.get("Source")
        # Targets = request.POST.getlist("Targets")
        # LatencyOracles = {Source : Targets}
        Oracles = request.POST.getlist("Oracles")
        LatencyOracles = defaultdict(list)
        for j in [i.split(';') for i in Oracles]:
            LatencyOracles[j[0]].append(j[1])

        have_data = True
        print(LatencyStartBlock,LatencyEndBolck,LatencyOracles)
        for source, targets in LatencyOracles.items():
            oracle_name, token0, token1 = source.split("_")
            source_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
            for target in targets:
                oracle_name, token0, token1 = target.split("_")
                target_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                for summary in summaries:
                    if summary.source_token_pair == source_token_pair and\
                        summary.target_token_pair == target_token_pair:
                        summary.used = True

            # summary = BlockPriceUpdateRecord.objects.get(token_pair=token_pair)

    # return HttpResponse(c.render_embed())
    content = dict(
        have_data=have_data,
        summaries=summaries,
        # line=line,
        min_block=min_block,
        max_block=max_block,
    )
    
    return render(request,"latency_chart.html", content)


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





# class gen_price_line_chart(APIView):
#     def get(self, request, *args, **kwargs):
#         # print("-----------------------------********************")
#         return JsonResponse(json.loads(get_price_line_chart()))


# def price_line_chart_view(request):
#     have_data = False
#     summaries =BlockPriceUpdateRecord.objects.all()
#     for summary in summaries:
#         summary.used = False
    
#     min_block = max([i.min_block_number for i in summaries])
#     max_block = min([i.max_block_number for i in summaries])

#     if request.method == "POST":
        
#         global StartBlock, EndBolck, Oracles
        
#         StartBlock = int(request.POST.get("StartBlock"))
#         EndBolck = int(request.POST.get("EndBlock"))

#         min_block, max_block = StartBlock, EndBolck

#         Oracles = request.POST.getlist("Oracles")
#         have_data = True
#         print(StartBlock,EndBolck,Oracles)
#         for oracle in Oracles:
#             oracle_name, token0, token1 = oracle.split("_")
#             token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
#             for summary in summaries:
#                 if summary.token_pair == token_pair:
#                     summary.used = True

#             # summary = BlockPriceUpdateRecord.objects.get(token_pair=token_pair)

#     # return HttpResponse(c.render_embed())
#     content = dict(
#         have_data=have_data,
#         summaries=summaries,
#         # line=line,
#         min_block=min_block,
#         max_block=max_block,
#     )
    
#     return render(request,"price_line_chart.html", content)




