#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import talib as tl


__author__ = 'myh '
__date__ = '2023/3/10 '


# 放量上涨
# 1.当日比前一天上涨大于等于min_change%（默认2%）
# 2.当日成交额不低于min_amount（默认2亿）
# 3.当日成交量/N日平均成交量>=vol_ratio（默认2倍）
def check_volume(code_name, data, date=None, threshold=60, min_change=2.0, min_amount=200000000, vol_ratio=2.0):
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask].copy()
    if len(data.index) < threshold:
        return False

    p_change = data.iloc[-1]['p_change']
    if p_change < min_change or data.iloc[-1]['close'] < data.iloc[-1]['open']:
        return False

    data.loc[:, 'vol_ma5'] = tl.MA(data['volume'].values, timeperiod=5)
    data.loc[:, 'vol_ma5'] = np.where(np.isnan(data['vol_ma5'].values), 0.0, data['vol_ma5'].values)

    data = data.tail(n=threshold + 1)
    if len(data) < threshold + 1:
        return False

    # 最后一天收盘价
    last_close = data.iloc[-1]['close']
    # 最后一天成交量
    last_vol = data.iloc[-1]['volume']

    amount = last_close * last_vol

    # 成交额不低于min_amount
    if amount < min_amount:
        return False

    data = data.head(n=threshold)

    mean_vol = data.iloc[-1]['vol_ma5']

    ratio = last_vol / mean_vol
    if ratio >= vol_ratio:
        return True
    else:
        return False
