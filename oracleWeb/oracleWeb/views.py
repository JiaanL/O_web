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

        
    print(Config)
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

    global Config, RunningThread, PricePlotConfig

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