from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from rest_framework.views import APIView 

from collections import defaultdict
import threading
import json
from pyecharts.charts import Line
import pyecharts.options as opts
import time

import debtmonitor.views as dm
import datavisualization.views as dv
import datastorage.views as ds

from debtmonitor.models import *
from datavisualization.models import *
from datastorage.models import *

from pandarallel import pandarallel
pandarallel.initialize(progress_bar=True)

Config = dict(
    auto_all=False,
    auto_update_datastorage=False,
    auto_update_granularity=False,
    auto_update_latency=False,
    auto_update_lending_pool=False,

    plot_price=False,
    plot_latency=False,
    plot_hf=False,
)

RunningThread = dict(
    auto_update_datastorage=None,
    auto_update_granularity=None,
    auto_update_latency=None,
    auto_update_lending_pool=None,
    auto_all=None,

    plot_price=None,
    plot_latency=None,
    plot_hf=None,
)

summaries = BlockPriceUpdateRecord.objects.all()
for summary in summaries:
    summary.used = False

PricePlotConfig = dict(
    have_data=False,
    summaries=summaries,
    start_block=max([i.min_block_number for i in summaries]),
    end_block=min([i.max_block_number for i in summaries]),
    oracles=[]
)


summaries =LatencyUpdateRecord.objects.all()
for summary in summaries:
    summary.used = False
LatencyPlotConfig = dict(
    have_data=False,
    summaries=summaries,
    start_block=max([i.min_block_number for i in summaries]),
    end_block=min([i.max_block_number for i in summaries]),
    oracles=defaultdict(list)
)

AvaliableLatencyNum = 6424

summaries =LendingPoolUpdateSummary.objects.all()
for summary in summaries:
    summary.used = False
TargetAddress = '0xb1b7f5dd1173c180eba4d91f8e78559e8a0b8b11'
ReservesStatusStart = LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0].max_block_number
PreviousBlockForTrain = 6424
ReservesStatusEnd = 14948000 #ReservesStatusStart - PreviousBlockForTrain
ReservesStatusEndIndex = 1000
StepAhead = 6424
MCAmount = 300
HFChartDone = False
HF_chart = None
HF_previous_chart = None
Previous_chart_done = False
MC_chart = None
DebtData = None

HFPlotConfig = dict(
    summaries=summaries,
    step_ahead=StepAhead,
    mc_amount=MCAmount,
    potential=True,
    have_data=False,
    reserve_status_end=ReservesStatusEnd,
    summary=summary,
    previous_block_for_train=PreviousBlockForTrain,
    reserves_status_end_index=ReservesStatusEndIndex,
    target_address=TargetAddress,
)

# GranularityContent = dict(
#     have_data=False,
#     summaries=summaries,
#     min_block=PricePlotConfig['start_block'],
#     max_block=PricePlotConfig['end_block'],
# )

AutoUpdateSleepTime = 60 * 5

def main(request):
    global Config, RunningThread, PricePlotConfig
    
    # DataStorage ################################################
    if RunningThread['auto_update_datastorage'] is not None and RunningThread['auto_update_datastorage'].is_alive():
        Config['auto_update_datastorage'] = True
    else:
        Config['auto_update_datastorage'] = False

    
    # Granularity ################################################
    if RunningThread['auto_update_granularity'] is not None and RunningThread['auto_update_granularity'].is_alive():
        Config['auto_update_granularity'] = True
    else:
        Config['auto_update_granularity'] = False

    # Latency ################################################
    if RunningThread['auto_update_latency'] is not None and RunningThread['auto_update_latency'].is_alive():
        Config['auto_update_latency'] = True
    else:
        Config['auto_update_latency'] = False
    
    # Lending Pool ################################################
    if RunningThread['auto_update_lending_pool'] is not None and RunningThread['auto_update_lending_pool'].is_alive():
        Config['auto_update_lending_pool'] = True
    else:
        Config['auto_update_lending_pool'] = False


    if request.method == "POST":
        if request.POST.get('price_plot', False) == 'price_plot_submit':
            PricePlotConfig['start_block'] = int(request.POST.get("PriceStartBlock", PricePlotConfig['start_block']))
            PricePlotConfig['end_block'] = int(request.POST.get("PriceEndBlock", PricePlotConfig['end_block']))

            # price_plot_content['min_block'], price_plot_content['max_block'] = PricePlotConfig['start_block'], PricePlotConfig['end_block']
            PricePlotConfig['oracles'] = Oracles = request.POST.getlist("PricePlotOracles")
            PricePlotConfig['have_data'] = True

            PricePlotConfig['have_data']=True
            # GranularityContent['min_block']=PricePlotConfig['start_block']
            # GranularityContent['max_block']=PricePlotConfig['end_block']

            for i in range(len(PricePlotConfig['summaries'])):
                PricePlotConfig['summaries'][i].used = False

            for oracle in Oracles:
                oracle_name, token0, token1 = oracle.split("_")
                token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                for i in range(len(PricePlotConfig['summaries'])):
                    summary = PricePlotConfig['summaries'][i]
                    if summary.token_pair == token_pair:
                        PricePlotConfig['summaries'][i].used = True
            # print(price_plot_content)
            start_plot_price(request)
        if request.POST.get('latency_plot', False) == 'latency_plot_submit':
            
            LatencyPlotConfig['start_block'] = int(request.POST.get("LatencyStartBlock"))
            LatencyPlotConfig['end_block'] = int(request.POST.get("LatencyEndBlock"))

            LatencyOracles = defaultdict(list)
            for j in [i.split(';') for i in request.POST.getlist("LatencyPlotOracles")]:
                LatencyOracles[j[0]].append(j[1])
            
            LatencyPlotConfig['oracles'] = LatencyOracles

            LatencyPlotConfig['have_data'] = True

            # print(LatencyOracles)
            for i in range(len(LatencyPlotConfig['summaries'])):
                LatencyPlotConfig['summaries'][i].used = False

            for source, targets in LatencyOracles.items():
                oracle_name, token0, token1 = source.split("_")
                source_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                for target in targets:
                    oracle_name, token0, token1 = target.split("_")
                    target_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                    for i in range(len(LatencyPlotConfig['summaries'])):
                        summary = LatencyPlotConfig['summaries'][i]
                        if summary.source_token_pair == source_token_pair and\
                            summary.target_token_pair == target_token_pair:
                            LatencyPlotConfig['summaries'][i].used = True
            start_plot_latency(request)
        
        
        
        if request.POST.get('hf_plot', False) == 'hf_plot_submit':
            
            HFPlotConfig['reserve_status_end'] = int(request.POST.get("DebtMonitorEndBlock", HFPlotConfig['reserve_status_end']))
            HFPlotConfig['reserves_status_end_index'] = int(request.POST.get("DebtMonitorEndIndex", HFPlotConfig['reserves_status_end_index']))

            HFPlotConfig['previous_block_for_train'] = int(request.POST.get("DebtMonitorPreviousBlock", HFPlotConfig['previous_block_for_train']))

            HFPlotConfig['step_ahead'] = int(request.POST.get("DebtMonitorStepAhead", HFPlotConfig['step_ahead'] ))
            HFPlotConfig['mc_amount'] = int(request.POST.get("DebtMonitorMCAmount", HFPlotConfig['mc_amount']))

            HFPlotConfig['target_address'] = request.POST.get("DebtMonitorTarget", HFPlotConfig['target_address'] )
            print(HFPlotConfig)

            interaction_df = dm.get_interaction_data(HFPlotConfig['target_address'])
            interaction_df = interaction_df[interaction_df['action'] != "LiquidationCall"]
            if interaction_df.shape[0] != 0:
                potential = True
                for token in set(interaction_df['reserve'].to_list()):
                    if token not in dm.token_dict.values():
                        potential = False
                        break
                if potential:
                    HFPlotConfig['have_data'] = True
                    start_plot_hf(request)

    

    summaries = BlockPriceUpdateRecord.objects.all()
    for i in range(len(PricePlotConfig['summaries'])):
        PricePlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        PricePlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number

    summaries = LatencyUpdateRecord.objects.all()
    for i in range(len(LatencyPlotConfig['summaries'])):
        LatencyPlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        LatencyPlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number
    
    summaries = LendingPoolUpdateSummary.objects.all()
    for i in range(len(HFPlotConfig['summaries'])):
        HFPlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        HFPlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number

    # print(Config)
    content = dict(
        data_storage_summaries=Summary.objects.all(),
        price_plot_config=PricePlotConfig,
        latency_plot_config=LatencyPlotConfig,
        hf_plot_config=HFPlotConfig,
        lending_pool_summaries=LendingPoolUpdateSummary.objects.all(),
        config=Config,
    )
    print(HFPlotConfig['target_address'])
    return render(request, "oracle_web/oracle_web.html", content)



def auto_main(request):

    global Config, RunningThread, PricePlotConfig, LatencyPlotConfig

    # print(request.POST.get('auto_all', False))
    # return render(request, "oracle_web/oracle_auto_web.html")

    if request.method == "POST":
        for thread_name, thread_obj in RunningThread.items():
            if thread_obj is not None and thread_obj.is_alive():
                pass
            else:
                if thread_name == 'auto_update_datastorage':
                    auto_update_datastorage(request)
                elif thread_name == 'auto_update_granularity':
                    auto_update_granularity(request)
                elif thread_name == 'auto_update_latency':
                    # auto_update_latency(request)
                    pass
                elif thread_name == 'auto_update_lending_pool':
                    auto_update_lending_pool(request)
        # print(request.POST.get('auto_all', False))
        if request.POST.get('auto_all', False) == 'stop_auto_all':
            for t_name in RunningThread.keys():
                t = RunningThread[t_name]
                if t is not None:
                    t.do_run = False
                Config['auto_all'] = False
            for c_name in Config.keys():
                Config[c_name] = False
            print("waiting to break")
        else:
            if RunningThread['auto_all'] is None or not RunningThread['auto_all'].is_alive():
                t = threading.Thread(target=auto_plot,
                                        args=(request,))
                t.setDaemon(True)
                t.start()
                RunningThread['auto_all'] = t
                Config['auto_all'] = True
                HFPlotConfig['have_data'] = True
                PricePlotConfig['have_data'] = True
                LatencyPlotConfig['have_data'] = True



    # DataStorage ################################################
    if RunningThread['auto_update_datastorage'] is not None and RunningThread['auto_update_datastorage'].is_alive():
        Config['auto_update_datastorage'] = True
    else:
        Config['auto_update_datastorage'] = False

    # Granularity ################################################
    if RunningThread['auto_update_granularity'] is not None and RunningThread['auto_update_granularity'].is_alive():
        Config['auto_update_granularity'] = True
    else:
        Config['auto_update_granularity'] = False

    # Latency ################################################
    if RunningThread['auto_update_latency'] is not None and RunningThread['auto_update_latency'].is_alive():
        Config['auto_update_latency'] = True
    else:
        Config['auto_update_latency'] = False
    
    # Lending Pool ################################################
    if RunningThread['auto_update_lending_pool'] is not None and RunningThread['auto_update_lending_pool'].is_alive():
        Config['auto_update_lending_pool'] = True
    else:
        Config['auto_update_lending_pool'] = False


    summaries = BlockPriceUpdateRecord.objects.all()
    for i in range(len(PricePlotConfig['summaries'])):
        PricePlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        PricePlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number

    summaries = LatencyUpdateRecord.objects.all()
    for i in range(len(LatencyPlotConfig['summaries'])):
        LatencyPlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        LatencyPlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number
    
    summaries = LendingPoolUpdateSummary.objects.all()
    for i in range(len(HFPlotConfig['summaries'])):
        HFPlotConfig['summaries'][i].min_block_number =  summaries[i].min_block_number
        HFPlotConfig['summaries'][i].max_block_number =  summaries[i].max_block_number

    content = dict(
        # data_storage_summaries=Summary.objects.all(),
        price_plot_config=PricePlotConfig,
        latency_plot_config=LatencyPlotConfig,
        hf_plot_config=HFPlotConfig,
        lending_pool_summaries=LendingPoolUpdateSummary.objects.all(),
        config=Config,
    )

    return render(request, "oracle_web/oracle_auto_web.html", content)
        

def auto_plot(request):
    global Config, RunningThread, PricePlotConfig, HFPlotConfig, LatencyPlotConfig
    t = threading.currentThread()
    while getattr(t, "do_run", True): 

        if RunningThread['plot_price'] is None or not RunningThread['plot_price'].is_alive():

            summaries = BlockPriceUpdateRecord.objects.all()
            end_block=min([i.max_block_number for i in summaries])

            PricePlotConfig['start_block'] = int(end_block-int(request.POST.get("DebtMonitorPreviousBlock", HFPlotConfig['previous_block_for_train'])))
            PricePlotConfig['end_block'] = int(end_block)

            PricePlotConfig['oracles'] = Oracles = [
                'chainlink_eth_usd',
                'uniswapv3_eth_usdc',
                # 'uniswapv3_eth_usdt',
                'uniswapv3_eth_dai',
            ]
            PricePlotConfig['have_data'] = True
            for oracle in Oracles:
                oracle_name, token0, token1 = oracle.split("_")
                token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                for i in range(len(PricePlotConfig['summaries'])):
                    summary = PricePlotConfig['summaries'][i]
                    if summary.token_pair == token_pair:
                        PricePlotConfig['summaries'][i].used = True
            start_plot_price(request)
        
        if RunningThread['plot_latency'] is None or not RunningThread['plot_latency'].is_alive():

            summaries = LatencyUpdateRecord.objects.all()
            start_block=max([i.min_block_number for i in summaries])
            end_block=min([i.max_block_number for i in summaries])
                
            
            LatencyPlotConfig['start_block'] = int(end_block - AvaliableLatencyNum * 100)
            LatencyPlotConfig['end_block'] = int(end_block)

            # LatencyOracles = defaultdict(list)
            # for j in [i.split(';') for i in request.POST.getlist("LatencyPlotOracles")]:
            #     LatencyOracles[j[0]].append(j[1])
            
            LatencyOracles = {
                'uniswapv3_eth_dai':['chainlink_eth_usd'],
                'uniswapv3_eth_usdc':['chainlink_eth_usd'],
                'uniswapv3_eth_usdt':['chainlink_eth_usd'],
            }
            
            LatencyPlotConfig['oracles'] = LatencyOracles

            LatencyPlotConfig['have_data'] = True

            # print(LatencyOracles)

            for source, targets in LatencyOracles.items():
                oracle_name, token0, token1 = source.split("_")
                source_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                for target in targets:
                    oracle_name, token0, token1 = target.split("_")
                    target_token_pair = TokenPair.objects.get(oracle__name=oracle_name, token0=token0, token1=token1)
                    for i in range(len(LatencyPlotConfig['summaries'])):
                        summary = LatencyPlotConfig['summaries'][i]
                        if summary.source_token_pair == source_token_pair and\
                            summary.target_token_pair == target_token_pair:
                            LatencyPlotConfig['summaries'][i].used = True
            start_plot_latency(request)
        
        
        if RunningThread['plot_hf'] is None or not RunningThread['plot_hf'].is_alive():
            HFPlotConfig['reserve_status_end'] = int(LendingPoolUpdateSummary.objects.get_or_create(action="overall")[0].max_block_number)
            HFPlotConfig['reserves_status_end_index'] = int(9999)
            HFPlotConfig['previous_block_for_train'] = int(request.POST.get("DebtMonitorPreviousBlock", HFPlotConfig['previous_block_for_train']))
            HFPlotConfig['step_ahead'] = int(request.POST.get("DebtMonitorStepAhead", HFPlotConfig['step_ahead'] ))
            HFPlotConfig['mc_amount'] = int(request.POST.get("DebtMonitorMCAmount", HFPlotConfig['mc_amount']))
            HFPlotConfig['target_address'] = request.POST.get("DebtMonitorTarget", HFPlotConfig['target_address'] )
            interaction_df = dm.get_interaction_data(HFPlotConfig['target_address'])
            interaction_df = interaction_df[interaction_df['action'] != "LiquidationCall"]
            if interaction_df.shape[0] != 0:
                potential = True
                for token in set(interaction_df['reserve'].to_list()):
                    if token not in dm.token_dict.values():
                        potential = False
                        break
                if potential:
                    HFPlotConfig['have_data'] = True
                    start_plot_hf(request)
        
        time.sleep(AutoUpdateSleepTime)
        
        

        



# Data Storage Update ######################################################################
def auto_update_datastorage(request):
    global Config, RunningThread

    request.GET = request.GET.copy()
    request.GET['print_update'] = "1"

    t = threading.Thread(target=ds.auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    RunningThread['auto_update_datastorage'] = t
    # redirect to main
    return redirect(reverse(main))

def stop_auto_update_datastorage(request):
    global Config, RunningThread
    t = RunningThread['auto_update_datastorage']
    t.do_run = False
    print("waiting to break")
    # redirect to main
    return redirect(reverse(main))
#############################################################################################


# Granularity Update ######################################################################
def auto_update_granularity(request):
    global Config, RunningThread

    request.GET = request.GET.copy()
    request.GET['print_update'] = "1"

    t = threading.Thread(target=dv.block_granularity_auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    RunningThread['auto_update_granularity'] = t
    # redirect to main
    return redirect(reverse(main))

def stop_auto_update_granularity(request):
    global Config, RunningThread
    t = RunningThread['auto_update_granularity']
    t.do_run = False
    print("waiting to break")
    # redirect to main
    return redirect(reverse(main))
#############################################################################################

# Price Visualization ######################################################################
def start_plot_price(request):

    global Config, RunningThread, PricePlotConfig

    # print(PricePlotConfig)

    t = threading.Thread(target=dv.get_price_line_chart,
                            args=(PricePlotConfig,))
    t.setDaemon(True)
    t.start()
    RunningThread['plot_price'] = t
    Config['plot_price'] = True
    # redirect to main
    return redirect(reverse(main))

def empty_plot():
    line = Line()
    line = line.set_global_opts(title_opts=opts.TitleOpts(title="Plot Generating..."))
    line = line.dump_options_with_quotes()
    line = json.loads(line)
    return dv.JsonResponse(line)

class get_price_plot(APIView):
    def get(self, request, *args, **kwargs):
        # if RunningThread['plot_price'] is None or RunningThread['plot_price'].is_alive():
        #     # print(999)
        #     return empty_plot()
        # print('222')
        # print(json.loads(dv.return_price_plot()))
        return dv.JsonResponse(json.loads(dv.return_price_plot()))

# Latency Update ######################################################################
def auto_update_latency(request):
    global Config, RunningThread

    request.GET = request.GET.copy()
    request.GET['print_update'] = "1"

    t = threading.Thread(target=dv.latency_auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    RunningThread['auto_update_latency'] = t
    # redirect to main
    return redirect(reverse(main))

def stop_auto_update_latency(request):
    global Config, RunningThread
    t = RunningThread['auto_update_latency']
    t.do_run = False
    print("waiting to break")
    # redirect to main
    return redirect(reverse(main))
#############################################################################################


# Latency Visualization ######################################################################
def start_plot_latency(request):

    global Config, RunningThread, LatencyPlotConfig

    # print(PricePlotConfig)

    t = threading.Thread(target=dv.get_latency_chart,
                            args=(LatencyPlotConfig,))
    t.setDaemon(True)
    t.start()
    RunningThread['plot_latency'] = t
    Config['plot_latency'] = True
    # redirect to main
    return redirect(reverse(main))

class get_latency_plot(APIView):
    def get(self, request, *args, **kwargs):
        # if RunningThread['plot_latency'] is None or RunningThread['plot_latency'].is_alive():
        #     return empty_plot()
        return dv.JsonResponse(json.loads(dv.return_latency_plot()))


# Lending Pool Update ######################################################################
def auto_update_lending_pool(request):
    global Config, RunningThread

    request.GET = request.GET.copy()
    request.GET['print_update'] = "1"

    t = threading.Thread(target=dm.auto_update,
                            args=(request,))
    t.setDaemon(True)
    t.start()
    RunningThread['auto_update_lending_pool'] = t
    # redirect to main
    return redirect(reverse(main))

def stop_auto_update_lending_pool(request):
    global Config, RunningThread
    t = RunningThread['auto_update_lending_pool']
    t.do_run = False
    print("waiting to break")
    # redirect to main
    return redirect(reverse(main))
#############################################################################################


# HF Visualization ######################################################################
def start_plot_hf(request):

    global Config, RunningThread, HFPlotConfig

    # print(PricePlotConfig)

    t = threading.Thread(target=dm.gen_hf_chart,
                            args=(HFPlotConfig,))
    t.setDaemon(True)
    t.start()
    RunningThread['plot_hf'] = t
    Config['plot_hf'] = True
    # redirect to main
    return redirect(reverse(main))

class get_hf_plot(APIView):
    def get(self, request, *args, **kwargs):
        # if RunningThread['plot_hf'] is None or RunningThread['plot_hf'].is_alive():
        #     return empty_plot()
        return dv.JsonResponse(json.loads(dm.return_hf_plot()))

class get_hf_previous_plot(APIView):
    def get(self, request, *args, **kwargs):
        # if RunningThread['plot_hf'] is None or RunningThread['plot_hf'].is_alive():
        #     return empty_plot()
        return dv.JsonResponse(json.loads(dm.return_hf_previous_plot()))























# import pandas as pd
# import numpy as np
# import os
# import django
# from django.db.models import Max, Min, Avg, Q, F
# from asgiref.sync import sync_to_async
# import tqdm
# from collections import defaultdict
# from pandarallel import pandarallel
# import requests
# import json
# from matplotlib import pyplot as plt
# import pickle
# import ctypes
# from ctypes import c_char_p, cdll
# GoInt64 = ctypes.c_int64
# GoInt = GoInt64
# archive_node = "http://localhost:19545"

# from etherscan.utils.parsing import ResponseParser as parser
# pandarallel.initialize(progress_bar=True)
# # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rest.settings')
# # os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
# # django.setup()

# from debtmonitor.models import *
# from datavisualization.models import *
# from datastorage.models import *
# from debtmonitor.help_function import *

# token_dict = dict(
#     usdc = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
#     usdt = '0xdac17f958d2ee523a2206206994597c13d831ec7',
#     dai =  '0x6b175474e89094c44da98b954eedeac495271d0f',
#     # common collateral asset
#     weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
# )
# decimal_dict = dict(
#     usdc = 6,
#     usdt = 6,
#     dai =  18,
#     # common collateral asset
#     weth = 18
# )

# liquidation_threshold_dict = dict(
#     usdc = 0.88,
#     usdt = None, # not allowed as collateral
#     dai =  0.8,
#     # common collateral asset
#     weth = 0.85
# )
# revert_token_dict = {v: k for k, v in token_dict.items()}


# def get_potential_target():
#     data = pd.DataFrame(
#         list(
#             LendingPoolInteraction.objects.all().values()
#         )
#     )
#     return data['on_behalf_of'].unique().tolist()


# def get_interaction_data(target):
#     data = pd.DataFrame(
#         list(
#             LendingPoolInteraction.objects.filter(
#                 on_behalf_of=target
#             ).annotate(
#                  block_num=F('block_number__number'),
#             ).all().values()
#         )
#     )
#     return data


# def get_reserves_status():
#     data = pd.DataFrame(
#         list(
#             ReservesStatus.objects.annotate(
#                  block_num=F('block_number__number'),
#             ).all().values()
#         )
#     )
#     return data


# def get_liquidation_call(target=None):
#     if target is None:
#         data = pd.DataFrame(
#             list(
#                 LiquidationCall.objects.annotate(
#                     block_num=F('block_number__number'),
#                 ).all().values()
#             )
#         )
#     else:
#         data = pd.DataFrame(
#             list(
#                 LiquidationCall.objects.filter(
#                     on_behalf_of=target
#                 ).annotate(
#                     block_num=F('block_number__number'),
#                 ).all().values()
#             )
#         )
#     return data


# def get_price_data(until_block_num, previous_block = 6424):
#     ttt = pd.DataFrame(
#         list(
#             BlockPrice.objects.filter(
#                 Q(block_number__number__lte=until_block_num) &
#                 Q(block_number__number__gte=(until_block_num - previous_block))
#             ).annotate(
#                 block_num=F('block_number__number'),
#                 oracle_name=F('token_pair__oracle__name'),
#                 token0 = F('token_pair__token0'),
#                 token1 = F('token_pair__token1'),
#             ).all().values()
#         )
#     )
#     return ttt.sort_values("block_num")

# def invert_transformation(df_train, df_forecast):
#     """Revert back the differencing to get the forecast to original scale."""
#     df_fc = df_forecast.copy()
#     columns = df_train.columns
#     for col in columns:        
#         # Roll back 1st Diff
#         df_fc[str(col)] = (df_train[col].iloc[-1] + df_fc[col].cumsum()) # np.exp(df_train[col].iloc[-1] + df_fc[col].cumsum())
#     return df_fc

# def cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict):
#     hf_list = []
#     for i in range(price_prediction.shape[0]):
#         collatearl_m_threshold_in_eth = 0
#         debt_m_threshold_in_eth = 0
#         for token_name, token_amount in token_value_dicts['collateral'].items():
#             if token_name == 'weth':
#                 collatearl_m_threshold_in_eth += token_amount * liquidation_threshold_dict[token_name]
#             else:
#                 collatearl_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]  * liquidation_threshold_dict[token_name]

#         for token_name, token_amount in token_value_dicts['var_debt'].items():
#             if token_name == 'weth':
#                 debt_m_threshold_in_eth += token_amount
#             else:
#                 debt_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]

#         for token_name, token_amount in token_value_dicts['sta_debt'].items():
#             if token_name == 'weth':
#                 debt_m_threshold_in_eth += token_amount
#             else:
#                 debt_m_threshold_in_eth += token_amount * price_prediction['chainlink_' + token_name].loc[i]
#         collatearl_m_threshold_in_eth, debt_m_threshold_in_eth

#         hf = (collatearl_m_threshold_in_eth/debt_m_threshold_in_eth)
#         hf_list.append(hf)
#     return pd.Series(hf_list)#, columns=['hf'])

# def cal_pct_be_liquidated(mc_simulation_row):
#     return (mc_simulation_row < 1).sum()/mc_simulation_row.count()

# combine_block_n_index = lambda x: int(str(x['block_num']) + str(x['index']).zfill(6))

# change_token_address_to_name = lambda x: revert_token_dict[x] if x in revert_token_dict else x



# def collect_data(liquidation_evl_df, block_before=1000, mc_amount = 300, step = 100):
#     return_data = []
#     reserves_status = get_reserves_status()
#     reserves_status = reserves_status[[
#             'reserve', 'block_num', 'index',  
#             'liquidity_rate', 'stable_borrow_rate', 'variable_borrow_rate', 
#             'liquidity_index','variable_borrow_index'
#     ]].copy()
#     reserves_status['block_n_index'] = reserves_status.apply(combine_block_n_index, axis=1)
#     reserves_status = reserves_status.sort_values('block_n_index').reset_index(drop=True)
#     reserves_status['reserve'] = reserves_status['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
#     for iii in tqdm.tqdm(liquidation_evl_df.index):
#         until_block_num = liquidation_evl_df.loc[iii, 'block_num'] - block_before
#         until_index = 9999
#         target_address = liquidation_evl_df.loc[iii, 'on_behalf_of']
#         until_block_n_index = combine_block_n_index({'block_num': until_block_num, 'index': until_index})
#         liquidation_index = until_index

#         liquidation_df = get_liquidation_call(target_address)
#         interaction_df = get_interaction_data(target_address)

#         interaction_df = interaction_df['action block_num index on_behalf_of reserve amount rate_mode rate'.split(' ')].copy()
        
#         liquidation_df = liquidation_df[[
#             'block_num', 'index', 'on_behalf_of', 
#             'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
#             'liquidator', 'receive_atoken']].copy()

#         interaction_df['block_n_index'] = interaction_df.apply(combine_block_n_index, axis=1)
        
#         liquidation_df['block_n_index'] = liquidation_df.apply(combine_block_n_index, axis=1)

#         interaction_df = interaction_df.sort_values('block_n_index').reset_index(drop=True)
        

#         # just give a random reserve address, will be swich in the following part
#         for index in interaction_df.index:
#             if interaction_df.loc[index, 'action'] == "LiquidationCall":
#                 interaction_df.loc[index, 'reserve'] = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

#         # merge
#         interaction_df['reserve'] = interaction_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
        
#         user_df = interaction_df.merge(reserves_status, on=['reserve'], how='left')
        
#         user_df['reserve'] = user_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
        

#         liquidation_df['collateral_asset'] = liquidation_df['collateral_asset'].apply(change_token_address_to_name)
#         liquidation_df['debt_asset'] = liquidation_df['debt_asset'].apply(change_token_address_to_name)
        
#         if 'usdt' in interaction_df[interaction_df['action']=='Deposit']['reserve'].to_list():
#             continue

#         def get_liquidation_data(df_row):
#             df_row = df_row.copy()
#             if df_row['action'] != 'LiquidationCall': return df_row
#             # collateral
#             block_n_index_x = df_row['block_n_index_x']
#             liquidation_row = liquidation_df[liquidation_df['block_n_index'] == block_n_index_x]
#             collateral_asset = liquidation_row['collateral_asset'].values[0]
#             tmp_reserves_status = reserves_status[\
#                 (reserves_status['reserve'] == collateral_asset) &\
#                 (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
#             tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

#             df_row['block_num_y'] = tmp_reserves_status['block_num']
#             df_row['index_y'] = tmp_reserves_status['index']
#             df_row['liquidity_rate'] = tmp_reserves_status['liquidity_rate']
#             df_row['liquidity_index'] = tmp_reserves_status['liquidity_index']
#             df_row['block_n_index_y'] = tmp_reserves_status['block_n_index']

#             debt_asset = liquidation_row['debt_asset'].values[0]
#             tmp_reserves_status = reserves_status[\
#                 (reserves_status['reserve'] == debt_asset) &\
#                 (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
#             tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

#             df_row['stable_borrow_rate'] = tmp_reserves_status['stable_borrow_rate']
#             df_row['variable_borrow_rate'] = tmp_reserves_status['variable_borrow_rate']
#             df_row['variable_borrow_index'] = tmp_reserves_status['variable_borrow_index']
            
#             return df_row

#         from_df = user_df[user_df['block_n_index_y'] <= user_df['block_n_index_x']]
#         from_df = from_df.loc[from_df.groupby('block_n_index_x').block_n_index_y.idxmax()].reset_index(drop=True)
#         from_df = from_df.apply(get_liquidation_data, axis=1)

#         collateral_dict = defaultdict(float)
#         collatearl_able_dict = defaultdict(lambda :True)
#         variable_debt_dict = defaultdict(float)
#         stable_debt_dict = defaultdict(lambda : [None, None, None]) # amount, interest, start time

#         liquidation_pool_target = [
#             "ReserveUsedAsCollateralEnabled",
#             "ReserveUsedAsCollateralDisabled", 
#             "Deposit", 
#             "Withdraw",
#             "Borrow",
#             "Repay",
#             # "LiquidationCall",
#             "Swap",
#         ]

#         SECONDS_PER_YEAR = 365 * 24 * 60 * 60
#         RAY = 1e27

#         ray_mul = lambda a,b: (a * b + RAY/2) / RAY
#         ray_div = lambda a,b: (a * RAY + b/2) / b


#         sub_interaction_df = interaction_df[interaction_df['block_n_index'] <= until_block_n_index].copy()

#         __library = cdll.LoadLibrary('../eth_crawler/library.so')

#         get_single_block_time = __library.get_single_block_time
#         get_single_block_time.argtypes = [c_char_p, GoInt]
#         get_single_block_time.restype = c_char_p

#         # Block Time
#         def get_block_time(block_num):
#             try:
#                 res = get_single_block_time(
#                     archive_node.encode(), 
#                     GoInt(int(block_num))
#                 )
#                 res = res.decode("utf-8")
#                 res = json.loads(s=res)#.items()#, columns=['BlockNum', 'Timestamp'])
                
#                 return res[str(block_num)]
#             except Exception as e: 
#                 print(e)


#         def cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p):
#             block_time = get_block_time(block_num)
#             block_time_p = get_block_time(block_num_p)
#             exp = int(block_time) - int(block_time_p)
            
#             ###### Reference #####: https://etherscan.io/address/0xc6845a5c768bf8d7681249f8927877efda425baf#code
#             expMinusOne = exp - 1
#             expMinusTwo = exp - 2 if exp > 2 else 0
#             ratePerSecond = stable_borrow_rate_p / SECONDS_PER_YEAR
#             basePowerTwo = ray_mul(ratePerSecond, ratePerSecond) # (ratePerSecond * ratePerSecond + 0.5 * RAY)/RAY
#             basePowerThree = ray_mul(basePowerTwo, ratePerSecond)#  + 0.5 * RAY)/RAY
#             secondTerm = (exp * expMinusOne * basePowerTwo) / 2
#             thirdTerm = (exp * expMinusOne * expMinusTwo * basePowerThree) / 6
#             compounded_interest = RAY + (ratePerSecond * exp) + (secondTerm) + (thirdTerm)
#             new_stable_balance = ray_mul(stable_debt_amount_p, compounded_interest)
#             balance_increase = new_stable_balance - stable_debt_amount_p
#             ########################################################################

#             return new_stable_balance, balance_increase

#         def update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
#                 rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate):
            
            
#             a_token_amount_i = ray_div(amount_i, liquidity_index)
            
#             variable_debt_amount_i = ray_div(amount_i, variable_borrow_index)

#             # For Stable Debt
#             stable_debt_amount_i = amount_i #/ stable_borrow_rate
#             stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name_i]
#             if stable_debt_amount_p != None:
#                 new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)

            
#             if action_i == "ReserveUsedAsCollateralEnabled":
#                 collatearl_able_dict[token_name_i] = True
#             elif action_i == "ReserveUsedAsCollateralDisabled":
#                 collatearl_able_dict[token_name_i] = False
#             elif action_i == "Deposit":
#                 if collatearl_able_dict[token_name_i] == False and collateral_dict[token_name_i] == 0:
#                     collatearl_able_dict[token_name_i] = True
#                 collateral_dict[token_name_i] += a_token_amount_i
#             elif action_i == 'Withdraw':
#                 if (collateral_dict[token_name_i] - a_token_amount_i) < 0:
#                     return False, np.abs(collateral_dict[token_name_i] - a_token_amount_i)
#                 collateral_dict[token_name_i] -= a_token_amount_i
#             elif action_i == "Borrow":
#                 if rate_mode_i == '1': # stable
#                     if stable_debt_dict[token_name_i][0] is None:
#                         stable_debt_dict[token_name_i] = [stable_debt_amount_i, stable_borrow_rate, block_num]
#                     else:
#                         stable_debt_dict[token_name_i] = [new_stable_balance + stable_debt_amount_i, stable_borrow_rate, block_num]
#                 elif rate_mode_i == '2': # variable
#                     variable_debt_dict[token_name_i] += variable_debt_amount_i
#                 else:
#                     assert False, "rate_mode_i error"
#             elif action_i == "Repay":
#                 if rate_mode_i == '1':
#                     if (new_stable_balance - stable_debt_amount_i) < 0:
#                         return False, np.abs(new_stable_balance - stable_debt_amount_i)
#                     stable_debt_dict[token_name_i] = [new_stable_balance - stable_debt_amount_i, stable_borrow_rate, block_num]
#                 elif rate_mode_i == '2': # variable
#                     if (variable_debt_dict[token_name_i] - variable_debt_amount_i) < 0:
#                         return False, np.abs(variable_debt_dict[token_name_i] - variable_debt_amount_i)
#                     variable_debt_dict[token_name_i] -= variable_debt_amount_i
#             elif action_i == 'RebalanceStableBorrowRate':
#                 stable_debt_dict[token_name_i] = [new_stable_balance, stable_borrow_rate, block_num]
#             else:
#                 assert False, "Interaction Data error"

#             return True, 0

#         def get_token_value(block_num, index, fix_decimal=False):
#             collateral_in_original_unit = defaultdict(float)
#             var_debt_in_original_unit = defaultdict(float)
#             sta_debt_in_original_unit = defaultdict(float)

#             block_n_index = combine_block_n_index(dict(block_num=block_num, index=index))

#             for token_name, able in collatearl_able_dict.items():
#                 decimal_fixer = 1
#                 if able:
#                     tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
#                         (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
#                     if fix_decimal:
#                         decimal_fixer = 10 ** decimal_dict[token_name]
#                     collateral_in_original_unit[token_name] = ray_mul(collateral_dict[token_name], tmp_status["liquidity_index"]) / decimal_fixer
            
#             for token_name, able in variable_debt_dict.items():
#                 decimal_fixer = 1
#                 tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
#                         (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
#                 if fix_decimal:
#                     decimal_fixer = 10 ** decimal_dict[token_name]
#                 var_debt_in_original_unit[token_name] = ray_mul(variable_debt_dict[token_name], tmp_status["variable_borrow_index"]) / decimal_fixer

#             for token_name, stable_debt in stable_debt_dict.items():
#                 decimal_fixer = 1
#                 if stable_debt[0] is not None:
#                     stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name]
#                     new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)
#                     if fix_decimal:
#                         decimal_fixer = 10 ** decimal_dict[token_name]
#                     sta_debt_in_original_unit[token_name] = new_stable_balance / decimal_fixer
            
            
            
#             return collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit


#         for index_i in sub_interaction_df.index:

#             action_i = sub_interaction_df.loc[index_i, 'action']
#             block_n_index = sub_interaction_df.loc[index_i, 'block_n_index']
#             block_num = sub_interaction_df.loc[index_i, 'block_num']
#             index = sub_interaction_df.loc[index_i, 'index']

#             # block_time = get_block_time(block_num)
#             before_data = from_df[from_df['block_n_index_x'] == block_n_index]#['amount'].values[0]
#             liquidity_index = before_data['liquidity_index'].values[0]
#             variable_borrow_index = before_data['variable_borrow_index'].values[0]
#             stable_borrow_rate = before_data['stable_borrow_rate'].values[0]
            
#             if action_i == "LiquidationCall":
#                 'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
#                 liquidation_i = liquidation_df[liquidation_df['block_n_index'] == block_n_index].copy().reset_index(drop=True)
#                 collateral_asset = liquidation_i.loc[0, 'collateral_asset']
#                 debt_asset = liquidation_i.loc[0, 'debt_asset']
#                 debt_to_cover = liquidation_i.loc[0, 'debt_to_cover']
#                 liquidated_collateral_amount = liquidation_i.loc[0, 'liquidated_collateral_amount']

#                 # a_token_amount_i = ray_div(liquidated_collateral_amount, liquidity_index)
#                 # collateral_dict[collateral_asset] -= a_token_amount_i

#                 collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit = get_token_value(block_num, index)

#                 if var_debt_in_original_unit[debt_asset] < debt_to_cover:
#                     var_debt_to_liquidate = var_debt_in_original_unit[debt_asset]
#                     sta_debt_to_repay = debt_to_cover - var_debt_to_liquidate
#                 else:
#                     var_debt_to_liquidate = debt_to_cover
#                     sta_debt_to_repay = 0

#                 success, remaining_token = update_target_debt_data(
#                     "Repay", block_num, var_debt_to_liquidate, debt_asset, 
#                     "2", liquidity_index, variable_borrow_index, stable_borrow_rate)
#                 assert success

#                 if sta_debt_to_repay > 0:
#                     success, remaining_token = update_target_debt_data(
#                         "Repay", block_num, sta_debt_to_repay, debt_asset, 
#                         "1", liquidity_index, variable_borrow_index, stable_borrow_rate)
#                     assert success
                
#                 success, remaining_token = update_target_debt_data(
#                         "Withdraw", block_num, liquidated_collateral_amount, collateral_asset, 
#                         "-1", liquidity_index, variable_borrow_index, stable_borrow_rate)
#                 assert success

#             else:
#                 amount_i = sub_interaction_df.loc[index_i, 'amount']
#                 token_name_i = sub_interaction_df.loc[index_i, 'reserve']
#                 rate_mode_i = sub_interaction_df.loc[index_i, 'rate_mode']

#                 update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
#                 rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate)
#         token_value_dicts = get_token_value(until_block_num, liquidation_index, fix_decimal=True)
#         token_value_dicts = {i:j for i,j in zip(['collateral', 'var_debt', 'sta_debt'], token_value_dicts)}


#         price_data = get_price_data(until_block_num, previous_block=6424)
#         price_data['token0'] = price_data['token0'].apply(lambda x: 'weth' if x == 'eth' else x)
#         price_data['token1'] = price_data['token1'].apply(lambda x: 'weth' if x == 'eth' else x)
#         price_data = price_data[['block_num', 'oracle_name', 'token0', 'token1', 'current']]

#         block_num_df = pd.DataFrame(
#             range(
#                 price_data.block_num.min(), 
#                 until_block_num + 1
#             ),
#             columns=['block_num']
#         )
#         block_num_df.set_index('block_num', inplace=True)

#         uniswapv3_price_dict = {}
#         for token in ['usdt', 'dai', 'usdc']:
#             sub_price_df = price_data[(price_data['oracle_name'] == 'uniswapv3') & (price_data['token1'] == token)].copy()
#             sub_price_df[f'{token}'] = 1/sub_price_df['current']
#             sub_price_df.set_index('block_num', inplace=True)
#             sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
#             sub_price_df.fillna(method='ffill', inplace=True)
#             sub_price_df.fillna(method='bfill', inplace=True)
#             uniswapv3_price_dict[token] = sub_price_df[token]
#         chainlink_price_dict ={}
#         for token in ['usdt', 'dai', 'usdc']:
#             sub_price_df = price_data[(price_data['oracle_name'] == 'chainlink') & (price_data['token0'] == token)].copy()
#             sub_price_df[f'{token}'] = sub_price_df['current']
#             sub_price_df.set_index('block_num', inplace=True)
#             sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
#             sub_price_df.fillna(method='ffill', inplace=True)
#             sub_price_df.fillna(method='bfill', inplace=True)
#             chainlink_price_dict[token] = sub_price_df[token]
    

#         collatearl_in_eth = 0
#         debt_in_eth = 0
#         for token_name, token_amount in token_value_dicts['collateral'].items():
#             if token_name == 'weth':
#                 collatearl_in_eth += token_amount
#             else:
#                 collatearl_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#         for token_name, token_amount in token_value_dicts['var_debt'].items():
#             if token_name == 'weth':
#                 debt_in_eth += token_amount
#             else:
#                 debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#         for token_name, token_amount in token_value_dicts['sta_debt'].items():
#             if token_name == 'weth':
#                 debt_in_eth += token_amount
#             else:
#                 debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#         collatearl_m_threshold_in_eth = 0
#         debt_m_threshold_in_eth = 0
#         for token_name, token_amount in token_value_dicts['collateral'].items():
#             if token_name == 'weth':
#                 collatearl_m_threshold_in_eth += token_amount * liquidation_threshold_dict[token_name]
#             else:
#                 if liquidation_threshold_dict[token_name] is None:
#                     print(123)
#                 collatearl_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]  * liquidation_threshold_dict[token_name]

#         for token_name, token_amount in token_value_dicts['var_debt'].items():
#             if token_name == 'weth':
#                 debt_m_threshold_in_eth += token_amount
#             else:
#                 debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#         for token_name, token_amount in token_value_dicts['sta_debt'].items():
#             if token_name == 'weth':
#                 debt_m_threshold_in_eth += token_amount
#             else:
#                 debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]
#         collatearl_m_threshold_in_eth, debt_m_threshold_in_eth

#         HF = (collatearl_m_threshold_in_eth/debt_m_threshold_in_eth)  


#         used_token_list = []
#         price_data_list = []
#         price_name_list = []
#         for asset_from in ['collateral', 'var_debt', 'sta_debt']:
#             for token_name in ['usdc', 'usdt', 'dai']:
#             # for token_name, token_amount in token_value_dicts[asset_from].items():
#                 if token_name == 'weth': continue
#                 if token_name not in used_token_list:
#                     used_token_list.append(token_name)
#                     price_data_list.append(chainlink_price_dict[token_name])
#                     price_name_list.append(f'chainlink_{token_name}')
#                     price_data_list.append(uniswapv3_price_dict[token_name])
#                     price_name_list.append(f'uniswapv3_{token_name}')
#         var_train_df = pd.concat(price_data_list, axis=1)
#         var_train_df.columns = price_name_list
#         var_train_df = var_train_df.reset_index(drop=False)

#         train_test_split = 1
#         train_data = var_train_df[:(int(len(var_train_df)*train_test_split)+1)].set_index('block_num')
#         test_data = var_train_df[(int(len(var_train_df)*train_test_split)+1):].set_index('block_num')
#         tmp_df = train_data.copy()#.set_index('block_num')
#         # log_df = np.log(tmp_df)
#         log_f_diff = tmp_df.diff().dropna() 
#         log_f_diff = log_f_diff.reset_index(drop=True)
#         trained_var = get_var_result(log_f_diff)              


#         def mc_simulate(df, step=240):
#             price_diff_prediction = pd.DataFrame(trained_var.simulate_var(step), columns=log_f_diff.columns)
#             price_prediction = invert_transformation(tmp_df, price_diff_prediction) 
#             hf_df = cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict)
#             return hf_df
        
        
#         mc_hf = pd.DataFrame(range(mc_amount)).apply(mc_simulate, args=(step,), axis=1).T
#         potential_liquidation = mc_hf.apply(lambda x: (x < 1).any(), axis=0)
#         mc_hf_pct = mc_hf.apply(cal_pct_be_liquidated, axis=1)

#         # mc_hf = pd.DataFrame(range(mc_amount)).parallel_apply(mc_simulate, args=(step,), axis=1).T
#         # potential_liquidation = mc_hf.parallel_apply(lambda x: (x < 1).any(), axis=0)
#         # mc_hf_pct = mc_hf.parallel_apply(cal_pct_be_liquidated, axis=1)
#         # print(tmp_df, token_value_dicts, liquidation_threshold_dict)
#         actual_hf = cal_hf(tmp_df.reset_index(), token_value_dicts, liquidation_threshold_dict)

#         return_data.append([liquidation_evl_df.loc[iii, :], mc_hf_pct, actual_hf])
#         # break
#     return return_data


# def collect_data_row(liquidation_evl_row, reserves_status, previous_block=6424, block_before=300, mc_amount = 100, step = 1000):
    
#     until_block_num = liquidation_evl_row['block_num'] - block_before
#     until_index = 9999
#     target_address = liquidation_evl_row['on_behalf_of']
#     # print(target_address, until_block_num)
#     until_block_n_index = combine_block_n_index({'block_num': until_block_num, 'index': until_index})
#     liquidation_index = until_index

#     liquidation_df = get_liquidation_call(target_address)
#     interaction_df = get_interaction_data(target_address)

#     interaction_df = interaction_df['action block_num index on_behalf_of reserve amount rate_mode rate'.split(' ')].copy()
    
#     liquidation_df = liquidation_df[[
#         'block_num', 'index', 'on_behalf_of', 
#         'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
#         'liquidator', 'receive_atoken']].copy()

#     interaction_df['block_n_index'] = interaction_df.apply(combine_block_n_index, axis=1)
    
#     liquidation_df['block_n_index'] = liquidation_df.apply(combine_block_n_index, axis=1)

#     interaction_df = interaction_df.sort_values('block_n_index').reset_index(drop=True)
    

#     # just give a random reserve address, will be swich in the following part
#     for index in interaction_df.index:
#         if interaction_df.loc[index, 'action'] == "LiquidationCall":
#             interaction_df.loc[index, 'reserve'] = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

#     # merge
#     interaction_df['reserve'] = interaction_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    
#     user_df = interaction_df.merge(reserves_status, on=['reserve'], how='left')
    
#     user_df['reserve'] = user_df['reserve'].apply(change_token_address_to_name).reset_index(drop=True)
    

#     liquidation_df['collateral_asset'] = liquidation_df['collateral_asset'].apply(change_token_address_to_name)
#     liquidation_df['debt_asset'] = liquidation_df['debt_asset'].apply(change_token_address_to_name)
    
#     if 'usdt' in interaction_df[interaction_df['action']=='Deposit']['reserve'].to_list():
#         return
    
#     if 'Swap' in interaction_df['action'].to_list():
#         return

#     def get_liquidation_data(df_row):
#         df_row = df_row.copy()
#         if df_row['action'] != 'LiquidationCall': return df_row
#         # collateral
#         block_n_index_x = df_row['block_n_index_x']
#         liquidation_row = liquidation_df[liquidation_df['block_n_index'] == block_n_index_x]
#         collateral_asset = liquidation_row['collateral_asset'].values[0]
#         tmp_reserves_status = reserves_status[\
#             (reserves_status['reserve'] == collateral_asset) &\
#             (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
#         tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

#         df_row['block_num_y'] = tmp_reserves_status['block_num']
#         df_row['index_y'] = tmp_reserves_status['index']
#         df_row['liquidity_rate'] = tmp_reserves_status['liquidity_rate']
#         df_row['liquidity_index'] = tmp_reserves_status['liquidity_index']
#         df_row['block_n_index_y'] = tmp_reserves_status['block_n_index']

#         debt_asset = liquidation_row['debt_asset'].values[0]
#         tmp_reserves_status = reserves_status[\
#             (reserves_status['reserve'] == debt_asset) &\
#             (reserves_status['block_n_index'] <= block_n_index_x)].copy().sort_values('block_n_index')
#         tmp_reserves_status = tmp_reserves_status.iloc[-1, :]

#         df_row['stable_borrow_rate'] = tmp_reserves_status['stable_borrow_rate']
#         df_row['variable_borrow_rate'] = tmp_reserves_status['variable_borrow_rate']
#         df_row['variable_borrow_index'] = tmp_reserves_status['variable_borrow_index']
        
#         return df_row

#     from_df = user_df[user_df['block_n_index_y'] <= user_df['block_n_index_x']]
#     from_df = from_df.loc[from_df.groupby('block_n_index_x').block_n_index_y.idxmax()].reset_index(drop=True)
#     from_df = from_df.apply(get_liquidation_data, axis=1)

#     collateral_dict = defaultdict(float)
#     collatearl_able_dict = defaultdict(lambda :True)
#     variable_debt_dict = defaultdict(float)
#     stable_debt_dict = defaultdict(lambda : [None, None, None]) # amount, interest, start time

#     liquidation_pool_target = [
#         "ReserveUsedAsCollateralEnabled",
#         "ReserveUsedAsCollateralDisabled", 
#         "Deposit", 
#         "Withdraw",
#         "Borrow",
#         "Repay",
#         # "LiquidationCall",
#         "Swap",
#     ]

#     SECONDS_PER_YEAR = 365 * 24 * 60 * 60
#     RAY = 1e27

#     ray_mul = lambda a,b: (a * b + RAY/2) / RAY
#     ray_div = lambda a,b: (a * RAY + b/2) / b


#     sub_interaction_df = interaction_df[interaction_df['block_n_index'] <= until_block_n_index].copy()

#     __library = cdll.LoadLibrary('../eth_crawler/library.so')

#     get_single_block_time = __library.get_single_block_time
#     get_single_block_time.argtypes = [c_char_p, GoInt]
#     get_single_block_time.restype = c_char_p

#     # Block Time
#     def get_block_time(block_num):
#         try:
#             res = get_single_block_time(
#                 archive_node.encode(), 
#                 GoInt(int(block_num))
#             )
#             res = res.decode("utf-8")
#             res = json.loads(s=res)#.items()#, columns=['BlockNum', 'Timestamp'])
            
#             return res[str(block_num)]
#         except Exception as e: 
#             print(e)


#     def cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p):
#         block_time = get_block_time(block_num)
#         block_time_p = get_block_time(block_num_p)
#         exp = int(block_time) - int(block_time_p)
        
#         ###### Reference #####: https://etherscan.io/address/0xc6845a5c768bf8d7681249f8927877efda425baf#code
#         expMinusOne = exp - 1
#         expMinusTwo = exp - 2 if exp > 2 else 0
#         ratePerSecond = stable_borrow_rate_p / SECONDS_PER_YEAR
#         basePowerTwo = ray_mul(ratePerSecond, ratePerSecond) # (ratePerSecond * ratePerSecond + 0.5 * RAY)/RAY
#         basePowerThree = ray_mul(basePowerTwo, ratePerSecond)#  + 0.5 * RAY)/RAY
#         secondTerm = (exp * expMinusOne * basePowerTwo) / 2
#         thirdTerm = (exp * expMinusOne * expMinusTwo * basePowerThree) / 6
#         compounded_interest = RAY + (ratePerSecond * exp) + (secondTerm) + (thirdTerm)
#         new_stable_balance = ray_mul(stable_debt_amount_p, compounded_interest)
#         balance_increase = new_stable_balance - stable_debt_amount_p
#         ########################################################################

#         return new_stable_balance, balance_increase

#     def update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
#             rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate):
        
        
#         a_token_amount_i = ray_div(amount_i, liquidity_index)
        
#         variable_debt_amount_i = ray_div(amount_i, variable_borrow_index)

#         # For Stable Debt
#         stable_debt_amount_i = amount_i #/ stable_borrow_rate
#         stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name_i]
#         if stable_debt_amount_p != None:
#             new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)

        
#         if action_i == "ReserveUsedAsCollateralEnabled":
#             collatearl_able_dict[token_name_i] = True
#         elif action_i == "ReserveUsedAsCollateralDisabled":
#             collatearl_able_dict[token_name_i] = False
#         elif action_i == "Deposit":
#             if collatearl_able_dict[token_name_i] == False and collateral_dict[token_name_i] == 0:
#                 collatearl_able_dict[token_name_i] = True
#             collateral_dict[token_name_i] += a_token_amount_i
#         elif action_i == 'Withdraw':
#             if (collateral_dict[token_name_i] - a_token_amount_i) < 0:
#                 assert False, np.abs(collateral_dict[token_name_i] - a_token_amount_i)
#             collateral_dict[token_name_i] -= a_token_amount_i
#         elif action_i == "Borrow":
#             if rate_mode_i == '1': # stable
#                 if stable_debt_dict[token_name_i][0] is None:
#                     stable_debt_dict[token_name_i] = [stable_debt_amount_i, stable_borrow_rate, block_num]
#                 else:
#                     stable_debt_dict[token_name_i] = [new_stable_balance + stable_debt_amount_i, stable_borrow_rate, block_num]
#             elif rate_mode_i == '2': # variable
#                 variable_debt_dict[token_name_i] += variable_debt_amount_i
#             else:
#                 assert False, "rate_mode_i error"
#         elif action_i == "Repay":
#             if rate_mode_i == '1':
#                 if (new_stable_balance - stable_debt_amount_i) < 0:
#                     assert False, np.abs(new_stable_balance - stable_debt_amount_i)
#                 stable_debt_dict[token_name_i] = [new_stable_balance - stable_debt_amount_i, stable_borrow_rate, block_num]
#             elif rate_mode_i == '2': # variable
#                 if (variable_debt_dict[token_name_i] - variable_debt_amount_i) < 0:
#                     assert False, f"{np.abs(variable_debt_dict[token_name_i] - variable_debt_amount_i)} {variable_debt_dict[token_name_i]} {variable_debt_amount_i}"
#                 variable_debt_dict[token_name_i] -= variable_debt_amount_i
#         elif action_i == 'RebalanceStableBorrowRate':
#             stable_debt_dict[token_name_i] = [new_stable_balance, stable_borrow_rate, block_num]
#         else:
#             assert False, f"Interaction Data error: {action_i}"

#         return True, 0

#     def get_token_value(block_num, index, fix_decimal=False):
#         collateral_in_original_unit = defaultdict(float)
#         var_debt_in_original_unit = defaultdict(float)
#         sta_debt_in_original_unit = defaultdict(float)

#         block_n_index = combine_block_n_index(dict(block_num=block_num, index=index))

#         for token_name, able in collatearl_able_dict.items():
#             decimal_fixer = 1
#             if able:
#                 tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
#                     (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
#                 if fix_decimal:
#                     decimal_fixer = 10 ** decimal_dict[token_name]
#                 collateral_in_original_unit[token_name] = ray_mul(collateral_dict[token_name], tmp_status["liquidity_index"]) / decimal_fixer
        
#         for token_name, able in variable_debt_dict.items():
#             decimal_fixer = 1
#             tmp_status = reserves_status[(reserves_status['reserve'] == token_name) &\
#                     (reserves_status['block_n_index'] <= block_n_index)].copy().sort_values('block_n_index').iloc[-1,:]
#             if fix_decimal:
#                 decimal_fixer = 10 ** decimal_dict[token_name]
#             var_debt_in_original_unit[token_name] = ray_mul(variable_debt_dict[token_name], tmp_status["variable_borrow_index"]) / decimal_fixer

#         for token_name, stable_debt in stable_debt_dict.items():
#             decimal_fixer = 1
#             if stable_debt[0] is not None:
#                 stable_debt_amount_p, stable_borrow_rate_p, block_num_p = stable_debt_dict[token_name]
#                 new_stable_balance, balance_increase = cal_stable_debt_change(stable_debt_amount_p, stable_borrow_rate_p, block_num, block_num_p)
#                 if fix_decimal:
#                     decimal_fixer = 10 ** decimal_dict[token_name]
#                 sta_debt_in_original_unit[token_name] = new_stable_balance / decimal_fixer
        
        
        
#         return collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit


#     for index_i in sub_interaction_df.index:

#         action_i = sub_interaction_df.loc[index_i, 'action']
#         block_n_index = sub_interaction_df.loc[index_i, 'block_n_index']
#         block_num = sub_interaction_df.loc[index_i, 'block_num']
#         index = sub_interaction_df.loc[index_i, 'index']

#         # block_time = get_block_time(block_num)
        
#         before_data = from_df[from_df['block_n_index_x'] == block_n_index]#['amount'].values[0]

#         try:
#             liquidity_index = before_data['liquidity_index'].values[0]
#         except IndexError:
#             print('**********************************************************')
#             print(block_n_index)
#             print('**********************************************************')
#         liquidity_index = before_data['liquidity_index'].values[0]

#         variable_borrow_index = before_data['variable_borrow_index'].values[0]
#         stable_borrow_rate = before_data['stable_borrow_rate'].values[0]
        
#         if action_i == "LiquidationCall":
#             'collateral_asset', 'debt_asset', 'debt_to_cover', 'liquidated_collateral_amount',
#             liquidation_i = liquidation_df[liquidation_df['block_n_index'] == block_n_index].copy().reset_index(drop=True)
#             collateral_asset = liquidation_i.loc[0, 'collateral_asset']
#             debt_asset = liquidation_i.loc[0, 'debt_asset']
#             debt_to_cover = liquidation_i.loc[0, 'debt_to_cover']
#             liquidated_collateral_amount = liquidation_i.loc[0, 'liquidated_collateral_amount']

#             # a_token_amount_i = ray_div(liquidated_collateral_amount, liquidity_index)
#             # collateral_dict[collateral_asset] -= a_token_amount_i

#             collateral_in_original_unit, var_debt_in_original_unit, sta_debt_in_original_unit = get_token_value(block_num, index)

#             if var_debt_in_original_unit[debt_asset] < debt_to_cover:
#                 var_debt_to_liquidate = var_debt_in_original_unit[debt_asset]
#                 sta_debt_to_repay = debt_to_cover - var_debt_to_liquidate
#             else:
#                 var_debt_to_liquidate = debt_to_cover
#                 sta_debt_to_repay = 0

#             success, remaining_token = update_target_debt_data(
#                 "Repay", block_num, var_debt_to_liquidate, debt_asset, 
#                 "2", liquidity_index, variable_borrow_index, stable_borrow_rate)
#             assert success

#             if sta_debt_to_repay > 0:
#                 success, remaining_token = update_target_debt_data(
#                     "Repay", block_num, sta_debt_to_repay, debt_asset, 
#                     "1", liquidity_index, variable_borrow_index, stable_borrow_rate)
#                 assert success
            
#             success, remaining_token = update_target_debt_data(
#                     "Withdraw", block_num, liquidated_collateral_amount, collateral_asset, 
#                     "-1", liquidity_index, variable_borrow_index, stable_borrow_rate)
#             assert success

#         else:
#             amount_i = sub_interaction_df.loc[index_i, 'amount']
#             token_name_i = sub_interaction_df.loc[index_i, 'reserve']
#             rate_mode_i = sub_interaction_df.loc[index_i, 'rate_mode']

#             update_target_debt_data(action_i, block_num, amount_i, token_name_i, 
#             rate_mode_i, liquidity_index, variable_borrow_index, stable_borrow_rate)
#     token_value_dicts = get_token_value(until_block_num, liquidation_index, fix_decimal=True)
#     token_value_dicts = {i:j for i,j in zip(['collateral', 'var_debt', 'sta_debt'], token_value_dicts)}


#     price_data = get_price_data(until_block_num, previous_block=previous_block)
#     price_data['token0'] = price_data['token0'].apply(lambda x: 'weth' if x == 'eth' else x)
#     price_data['token1'] = price_data['token1'].apply(lambda x: 'weth' if x == 'eth' else x)
#     price_data = price_data[['block_num', 'oracle_name', 'token0', 'token1', 'current']]

#     block_num_df = pd.DataFrame(
#         range(
#             price_data.block_num.min(), 
#             until_block_num + 1
#         ),
#         columns=['block_num']
#     )
#     block_num_df.set_index('block_num', inplace=True)

#     uniswapv3_price_dict = {}
#     for token in ['usdt', 'dai', 'usdc']:
#         sub_price_df = price_data[(price_data['oracle_name'] == 'uniswapv3') & (price_data['token1'] == token)].copy()
#         sub_price_df[f'{token}'] = 1/sub_price_df['current']
#         sub_price_df.set_index('block_num', inplace=True)
#         sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
#         sub_price_df.fillna(method='ffill', inplace=True)
#         sub_price_df.fillna(method='bfill', inplace=True)
#         uniswapv3_price_dict[token] = sub_price_df[token]
#     chainlink_price_dict ={}
#     for token in ['usdt', 'dai', 'usdc']:
#         sub_price_df = price_data[(price_data['oracle_name'] == 'chainlink') & (price_data['token0'] == token)].copy()
#         sub_price_df[f'{token}'] = sub_price_df['current']
#         sub_price_df.set_index('block_num', inplace=True)
#         sub_price_df = sub_price_df.merge(block_num_df, how='right', left_index=True, right_index=True)
#         sub_price_df.fillna(method='ffill', inplace=True)
#         sub_price_df.fillna(method='bfill', inplace=True)
#         chainlink_price_dict[token] = sub_price_df[token]


#     collatearl_in_eth = 0
#     debt_in_eth = 0
#     for token_name, token_amount in token_value_dicts['collateral'].items():
#         if token_name == 'weth':
#             collatearl_in_eth += token_amount
#         else:
#             collatearl_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#     for token_name, token_amount in token_value_dicts['var_debt'].items():
#         if token_name == 'weth':
#             debt_in_eth += token_amount
#         else:
#             debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#     for token_name, token_amount in token_value_dicts['sta_debt'].items():
#         if token_name == 'weth':
#             debt_in_eth += token_amount
#         else:
#             debt_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#     collatearl_m_threshold_in_eth = 0
#     debt_m_threshold_in_eth = 0
#     for token_name, token_amount in token_value_dicts['collateral'].items():
#         if token_name == 'weth':
#             collatearl_m_threshold_in_eth += token_amount * liquidation_threshold_dict[token_name]
#         else:
#             if liquidation_threshold_dict[token_name] is None:
#                 print(123)
#             collatearl_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]  * liquidation_threshold_dict[token_name]

#     for token_name, token_amount in token_value_dicts['var_debt'].items():
#         if token_name == 'weth':
#             debt_m_threshold_in_eth += token_amount
#         else:
#             debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]

#     for token_name, token_amount in token_value_dicts['sta_debt'].items():
#         if token_name == 'weth':
#             debt_m_threshold_in_eth += token_amount
#         else:
#             debt_m_threshold_in_eth += token_amount * chainlink_price_dict[token_name].loc[until_block_num]
#     collatearl_m_threshold_in_eth, debt_m_threshold_in_eth

#     HF = (collatearl_m_threshold_in_eth/debt_m_threshold_in_eth)  


#     used_token_list = []
#     price_data_list = []
#     price_name_list = []
#     for asset_from in ['collateral', 'var_debt', 'sta_debt']:
#         for token_name in ['usdc', 'usdt', 'dai']:
#         # for token_name, token_amount in token_value_dicts[asset_from].items():
#             if token_name == 'weth': continue
#             if token_name not in used_token_list:
#                 used_token_list.append(token_name)
#                 price_data_list.append(chainlink_price_dict[token_name])
#                 price_name_list.append(f'chainlink_{token_name}')
#                 price_data_list.append(uniswapv3_price_dict[token_name])
#                 price_name_list.append(f'uniswapv3_{token_name}')
#     var_train_df = pd.concat(price_data_list, axis=1)
#     var_train_df.columns = price_name_list
#     var_train_df = var_train_df.reset_index(drop=False)

#     train_test_split = 1
#     train_data = var_train_df[:(int(len(var_train_df)*train_test_split)+1)].set_index('block_num')
#     test_data = var_train_df[(int(len(var_train_df)*train_test_split)+1):].set_index('block_num')
#     tmp_df = train_data.copy()#.set_index('block_num')
#     # log_df = np.log(tmp_df)
#     log_f_diff = tmp_df.diff().dropna() 
#     log_f_diff = log_f_diff.reset_index(drop=True)
#     trained_var = get_var_result(log_f_diff)              


#     def mc_simulate(df, step=240):
#         price_diff_prediction = pd.DataFrame(trained_var.simulate_var(step), columns=log_f_diff.columns)
#         price_prediction = invert_transformation(tmp_df, price_diff_prediction) 
#         hf_df = cal_hf(price_prediction, token_value_dicts, liquidation_threshold_dict)
#         return hf_df
    
    
#     mc_hf = pd.DataFrame(range(mc_amount)).apply(mc_simulate, args=(step,), axis=1).T
#     potential_liquidation = mc_hf.apply(lambda x: (x < 1).any(), axis=0)
#     mc_hf_pct = mc_hf.apply(cal_pct_be_liquidated, axis=1)

#     # mc_hf = pd.DataFrame(range(mc_amount)).parallel_apply(mc_simulate, args=(step,), axis=1).T
#     # potential_liquidation = mc_hf.parallel_apply(lambda x: (x < 1).any(), axis=0)
#     # mc_hf_pct = mc_hf.parallel_apply(cal_pct_be_liquidated, axis=1)
#     # print(tmp_df, token_value_dicts, liquidation_threshold_dict)
#     actual_hf = cal_hf(tmp_df.reset_index(), token_value_dicts, liquidation_threshold_dict)

#     # print(liquidation_evl_row)
#     return [liquidation_evl_row, mc_hf_pct, actual_hf]

# def collect_evl_data(request):
#     tqdm.tqdm.pandas()

#     liquidation_evl_df = pd.read_csv('../data/evaluation_target.csv', index_col=0)

#     reserves_status = get_reserves_status()
#     reserves_status = reserves_status[[
#             'reserve', 'block_num', 'index',  
#             'liquidity_rate', 'stable_borrow_rate', 'variable_borrow_rate', 
#             'liquidity_index','variable_borrow_index'
#     ]].copy()
#     reserves_status['block_n_index'] = reserves_status.apply(combine_block_n_index, axis=1)
#     reserves_status = reserves_status.sort_values('block_n_index').reset_index(drop=True)
#     reserves_status['reserve'] = reserves_status['reserve'].apply(change_token_address_to_name).reset_index(drop=True)

    
#     # ttt = liquidation_evl_df.iloc[:10].progress_apply(collect_data_row, args=(reserves_status,), axis=1)

#     data_list = []
#     # for i in range(liquidation_evl_df.shape[0]):
    
#     # 240 block apprimate 1hr, assuming 15s/block
#     # for i in tqdm.tqdm(range(10)):

#     ver = request.GET.get("ver", '0')

#     if ver == "0":
#         previous_block=6424
#         block_before=240*3
#         mc_amount = 100
#         step = 240*3
#         vv = 0
#     elif ver == '1':
#         previous_block=6424
#         block_before=240*2
#         mc_amount = 100
#         step = 240*2
#         vv = 1
#     elif ver == '2':
#         previous_block=6424
#         block_before=240*1
#         mc_amount = 100
#         step = 240*1
#         vv = 2
#     elif ver == '3':
#         previous_block=2000
#         block_before=240*2
#         mc_amount = 100
#         step = 240*2
#         vv = 3
#     else:
#         print('ERRRRRRR')
    
#     print(vv)

#     np.random.seed(10)
#     liquidation_evl_df = liquidation_evl_df.loc[np.random.choice(liquidation_evl_df.index, 100)]

#     data_num_list = []
#     for i in tqdm.tqdm(range(liquidation_evl_df.shape[0])):
#         try:
#             data_list.append(collect_data_row(liquidation_evl_df.iloc[i,:], reserves_status, previous_block=previous_block, block_before=block_before, mc_amount = mc_amount, step = step))
#             data_num_list.append(i)
#         except Exception as e:
#             print(e)
    
#     print(data_list)
#     with open(f'../data/liquidation_evl_{ver}.pickle', 'wb') as handle:
#         pickle.dump([data_list, data_num_list], handle, protocol=pickle.HIGHEST_PROTOCOL)
    
#     return HttpResponse(f'Done')