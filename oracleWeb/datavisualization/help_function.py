from multiprocessing import Pool
from statsmodels.tsa.api import VAR, VECM
import statsmodels.tsa.vector_ar.util as var_tool
from statsmodels.tsa.stattools import adfuller
import statsmodels.tsa.vector_ar.vecm as vecm 
import pandas as pd
import numpy as np
import copy
from datetime import date, timedelta
import numpy as np

MAX_LAGS = 100
IC = 'aic'

def get_var_result(df, maxlags=MAX_LAGS, ic=IC):
    for col in df.columns:
        if len(set(df[col])) <= 4:
            # print('add random to avoid constant columns')
            df[col] = df[col].apply(lambda x: x + (np.random.rand()-0.5) * 0.0001 )
    model = VAR(df)
    fitted_model = model.fit(maxlags=maxlags, ic=ic)
    return fitted_model

def get_vecm_result(df, maxlags=MAX_LAGS, ic=IC):
    lag_order = vecm.select_order(df, maxlags=maxlags, deterministic="co").selected_orders[ic]
    vec_rank = vecm.select_coint_rank(df, det_order = 1, k_ar_diff = 1, method = 'trace', signif=0.05)
    model = VECM(endog = df, k_ar_diff = lag_order, coint_rank = vec_rank.rank, deterministic="co")
    fitted_model = model.fit()
    return fitted_model

def main_multi_p(log_f_diff, split_num=4, model='var'):

    with Pool(processes=None) as pool:
        # print(f'Split : {split_num}')
        splitted_df_list = np.array_split(log_f_diff, split_num)
        results = pool.map(eval(f"get_{model}_result"), splitted_df_list)
    return results

def df_split_index(df, each_range=60000):
    return [(i+1)*each_range for i in range(df.shape[0]//each_range)] +  [(df.shape[0]//each_range)*each_range + df.shape[0] % each_range]

def get_index(lst, name):
    # reference statsmodels
    try:
        result = lst.index(name)
    except Exception:
        if not isinstance(name, int):
            raise
        result = name
    return result

def get_implus_data(irf_result, implus_var, respond_var, orth=False, prune=True, alpha=0.05):
    tmp_irfs = irf_result.orth_irfs if orth else irf_result.irfs
    j = get_index(irf_result.model.names, implus_var)
    i = get_index(irf_result.model.names, respond_var)
    implus_data = tmp_irfs[:,i, j]
    if prune:
        stderr = irf_result.cov(orth=orth)
        k = len(irf_result.model.names)
        sig = np.sqrt(stderr[:, j * k + i, j * k + i])
        q = var_tool.norm_signif_level(alpha)
        upper_b = implus_data + q * sig
        lower_b = implus_data - q * sig
        for implus_i, _ in enumerate(implus_data):
            if upper_b[implus_i] > 0 and lower_b[implus_i] < 0:
                implus_data[implus_i] = 0.0
    return implus_data

def get_model_irf_df(model_i, irf_periods, columns, return_data='weighted_avg_latency'):
    assert return_data in ['weighted_avg_latency', 'cum_effect']
    irf_result = model_i.irf(irf_periods)
    data_list = []
    for implus_var in columns:
        tmp_data_list = []
        for respond_var in columns:
            implus_data = get_implus_data(irf_result, implus_var, respond_var)
            implus_data = np.array(list(map(lambda x: x if x>=0 else 0, implus_data)))
            if return_data == 'weighted_avg_latency':
                abs_implus_data = np.abs(implus_data)
                sum_abs_implus_data = np.sum(abs_implus_data)
                weight = abs_implus_data / sum_abs_implus_data if sum_abs_implus_data != 0 else 0
                implus_effect = np.sum(np.multiply(weight, np.arange(irf_periods + 1)))
                tmp_data_list.append(implus_effect)
            else:
                cum_implus_data = np.sum(implus_data)
                tmp_data_list.append(cum_implus_data)
            # print(f"{implus_var} -> {respond_var} = {implus_effect}")
        data_list.append(tmp_data_list)
    # print("---- index = implus source, column = implus to ----") 
    return pd.DataFrame(data_list, columns=columns, index=columns)

def get_latency_df(source, targets, models):
    assert type(targets) in [list, str]
    if type(targets) is str: targets = [targets]
    latency_list = []
    for target in targets:
        target_latency = list(map(lambda x:x.loc[source, target], models))
        latency_list.append(target_latency)
    latency_df = pd.DataFrame(latency_list).T
    latency_df.columns = targets
    latency_df = latency_df.applymap(lambda x: np.nan if x <= 0 else x)
    latency_df = latency_df.fillna(method="ffill")
    latency_df = latency_df.dropna()
    return latency_df

def my_adfuller_p_value(x):
	result = adfuller(x.values)
	return result[1]

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def hex2int(x):
    return int(x, 16)

def reformat_log(raw_data):
    data = copy.deepcopy(raw_data)
    for col_name in 'topic0 current roundId updatedAt'.split(' '):
        data[col_name] = raw_data[col_name].map(hex2int)
    data['updatedAt'] = pd.to_datetime(data['updatedAt'],unit='s')
    data['current'] = data['current'] / 10**8
    return data

def reformat_log_uniswap_v2(raw_data, stable_token):
    data = copy.deepcopy(raw_data)
    for col_name in 'Reserve0 Reserve1'.split(' '):
        data[col_name] = raw_data[col_name].map(hex2int)
    
    if stable_token == 'usdc':
        # USDC
        r0_base = 10**6
        # ETH
        r1_base = 10**18
    elif stable_token == 'usdt':
        # ETH
        r0_base = 10**18
        # USDT
        r1_base = 10**6
    elif stable_token == 'dai':
        # DAI
        r0_base = 10**18
        # ETH
        r1_base = 10**18

    data['Reserve0'] = data['Reserve0'] / r0_base
    data['Reserve1'] = data['Reserve1'] / r1_base


    # return data['Reserve1']/ data['Reserve0']
    return data['Reserve0'], data['Reserve1']

# USDC & DAI
def cal_price_eth_right(sqrtPriceX96):
    return (((2 ** 96) ** 2) / (sqrtPriceX96 ** 2)) * 10**(8+4)
    # return 1 / ((sqrtPriceX96 ** 2) / ((2 ** 96) ** 2) / 10**(8+4))

# USDT
def cal_price_eth_left(sqrtPriceX96):
    return ((sqrtPriceX96 ** 2) / ((2 ** 96) ** 2)) * 10**(8+4)

def get_latency_df(fitted_var_models, source_var, target_var):
    latency_list = []
    for model_i in range(len(fitted_var_models)):
        model_para = fitted_var_models[model_i].params
        lag_order = [int(i.split(".")[0][1:]) for i in model_para[target_var].index if source_var in i]
        coef = [model_para[target_var].loc[i] for i in model_para[target_var].index if source_var in i]
        coef_weight = list(map(lambda x: np.abs(x)/np.sum(np.abs(coef)), coef))
        latency_i = np.sum([i*j for i,j in zip(lag_order, coef_weight)])
        latency_list.append(latency_i)
    return pd.DataFrame(latency_list, columns=[target_var])

def str_to_dict(in_str):
    out_dict = {}
    exec(f"out_dict = {in_str}")
    return out_dict