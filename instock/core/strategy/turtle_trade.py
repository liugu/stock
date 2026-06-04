#!/usr/local/bin/python
# -*- coding: utf-8 -*-


__author__ = 'myh '
__date__ = '2023/3/10 '

# 总市值
BALANCE = 200000

# 海龟交易法则
# 最后一个交易日收市价为指定区间内最高价
# 1.当日收盘价>=最近N日最高收盘价（默认60日）
# 2.可选：当日收盘价突破幅度>=break_ratio（默认0，即刚好触及最高价即可）
def check_enter(code_name, data, date=None, threshold=60, break_ratio=0.0):
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    if len(data.index) < threshold:
        return False

    data = data.tail(n=threshold)

    max_price = 0
    for _close in data['close'].values:
        if _close > max_price:
            max_price = _close

    last_close = data.iloc[-1]['close']

    # 突破幅度要求
    if last_close >= max_price * (1 + break_ratio):
        return True

    return False


# 海龟交易法则 - 创新高检查（支持多周期）
# 同时检查是否创60日、120日、250日新高
def check_enter_multi(code_name, data, date=None, periods=[60, 120, 250]):
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    results = {}
    for period in periods:
        if len(data.index) < period:
            results[period] = False
            continue

        period_data = data.tail(n=period)
        max_price = period_data['close'].values.max()
        last_close = period_data.iloc[-1]['close']
        results[period] = last_close >= max_price

    return results
