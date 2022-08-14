from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from rest_framework.views import APIView 

from collections import defaultdict
import threading
import json
from pyecharts.charts import Line
import pyecharts.options as opts

import debtmonitor.views as dm
import datavisualization.views as dv
import datastorage.views as ds

from debtmonitor.models import *
from datavisualization.models import *
from datastorage.models import *


Config = dict(
    # auto_all=False,
    auto_update_datastorage=False,
    auto_update_granularity=False,
    auto_update_latency=False,

    plot_price=False,
)

RunningThread = dict(
    auto_update_datastorage=None,
    auto_update_granularity=None,
    auto_update_latency=None,

    plot_price=None,
)

summaries =BlockPriceUpdateRecord.objects.all()
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
    oracles=[]
)

# GranularityContent = dict(
#     have_data=False,
#     summaries=summaries,
#     min_block=PricePlotConfig['start_block'],
#     max_block=PricePlotConfig['end_block'],
# )

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

    # have_data = False
    # summaries =BlockPriceUpdateRecord.objects.all()
    # for summary in summaries:
    #     summary.used = False
    # min_block = max([i.min_block_number for i in summaries])
    # max_block = min([i.max_block_number for i in summaries])
    
    # granularity_content = dict(
    #     have_data=have_data,
    #     summaries=summaries,
    #     min_block=min_block,
    #     max_block=max_block,
    # )

    # Price Plot ################################################
    # price_plot_content = dict(
    #     min_block = PricePlotConfig['start_block'],
    #     max_block = PricePlotConfig['end_block'],
    #     have_data = False
    # )
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
            LatencyStartBlock = int(request.POST.get("LatencyStartBlock"))
            LatencyEndBolck = int(request.POST.get("LatencyEndBlock"))

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
        
        
    print(Config)
    content = dict(
        data_storage_summaries=Summary.objects.all(),
        price_plot_config=PricePlotConfig,
        latency_plot_config=LatencyPlotConfig,
        config=Config,
    )
    return render(request, "oracle_web/oracle_web.html", content)

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
        if RunningThread['plot_price'] is None or RunningThread['plot_price'].is_alive():
            # print(999)
            return empty_plot()
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
        if RunningThread['plot_latency'] is None or RunningThread['plot_latency'].is_alive():
            return empty_plot()
        return dv.JsonResponse(json.loads(dv.return_price_plot()))