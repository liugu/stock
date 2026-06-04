#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import talib as tl

__author__ = 'liugu '
__date__ = '2026/5/10 '


# 创新高策略
# 股价创N日新高（支持60日、120日、250日）
# 1.当日收盘价>=最近N日最高收盘价
# 2.可选：成交量放大确认（当日成交量>=N日平均成交量*vol_ratio）
def check(code_name, data, date=None, period=60, vol_ratio=1.0, require_volume=False):
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        close_col = '收盘'
        volume_col = '成交量'
    else:
        date_col = 'date'
        close_col = 'close'
        volume_col = 'volume'
    
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")
    if end_date is not None:
        mask = (data[date_col] <= end_date)
        data = data.loc[mask].copy()
    if len(data.index) < period:
        return False

    data = data.tail(n=period)

    # 计算区间最高价（不含当日）
    front_data = data.head(n=period - 1)
    max_price = front_data[close_col].values.max()

    last_close = data.iloc[-1][close_col]

    # 创新高条件
    if last_close < max_price:
        return False

    # 成交量确认（可选）
    if require_volume:
        data.loc[:, 'vol_ma'] = tl.MA(data[volume_col].values, timeperiod=period)
        data.loc[:, 'vol_ma'] = np.where(np.isnan(data['vol_ma'].values), 0.0, data['vol_ma'].values)
        last_vol = data.iloc[-1][volume_col]
        mean_vol = data.iloc[-1]['vol_ma']
        if mean_vol > 0 and last_vol < mean_vol * vol_ratio:
            return False

    return True


# 创60日新高
def check_60(code_name, data, date=None):
    return check(code_name, data, date, period=60)


# 创120日新高
def check_120(code_name, data, date=None):
    return check(code_name, data, date, period=120)


# 创250日新高（一年新高）
def check_250(code_name, data, date=None):
    return check(code_name, data, date, period=250)


# 创历史新高
# 当日收盘价>=历史最高收盘价
def check_all_time(code_name, data, date=None):
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        close_col = '收盘'
    else:
        date_col = 'date'
        close_col = 'close'
    
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")
    if end_date is not None:
        mask = (data[date_col] <= end_date)
        data = data.loc[mask]

    if len(data.index) < 10:
        return False

    # 历史最高价（不含当日）
    front_data = data.head(n=len(data) - 1)
    max_price = front_data[close_col].values.max()
    last_close = data.iloc[-1][close_col]

    return last_close >= max_price
