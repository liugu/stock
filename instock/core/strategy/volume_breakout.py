#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
成交量异动检测策略
1. 放量突破：当日成交量 > 5日均量 * 2，涨幅 > 3%
2. 缩量回调：连续3日缩量回调，但未跌破支撑位
"""

import numpy as np
import talib as tl

__author__ = 'liugu'
__date__ = '2026/5/11'


# 放量突破检测
# 1. 当日成交量 >= 5日均量 * vol_ratio（默认2倍）
# 2. 当日涨幅 >= min_change%（默认3%）
# 3. 当日成交额 >= min_amount（默认1亿）
def check_volume_breakout(code_name, data, date=None, threshold=60,
                          vol_ratio=2.0, min_change=3.0, min_amount=100000000):
    """
    放量突破检测
    当日成交量显著放大且股价上涨
    """
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask].copy()

    if len(data.index) < threshold:
        return False

    # 检查当日涨幅
    p_change = data.iloc[-1]['p_change']
    if p_change < min_change:
        return False

    # 检查当日是否阳线
    if data.iloc[-1]['close'] < data.iloc[-1]['open']:
        return False

    # 计算5日均量
    data.loc[:, 'vol_ma5'] = tl.MA(data['volume'].values, timeperiod=5)
    data.loc[:, 'vol_ma5'] = np.where(np.isnan(data['vol_ma5'].values), 0.0, data['vol_ma5'].values)

    data = data.tail(n=threshold + 1)
    if len(data) < threshold + 1:
        return False

    # 最后一天数据
    last_close = data.iloc[-1]['close']
    last_vol = data.iloc[-1]['volume']
    mean_vol = data.iloc[-1]['vol_ma5']

    # 成交额检查
    amount = last_close * last_vol
    if amount < min_amount:
        return False

    # 成交量放大检查
    if mean_vol > 0 and last_vol >= mean_vol * vol_ratio:
        return True

    return False


# 缩量回调检测
# 1. 连续3日缩量回调
# 2. 回调未跌破支撑位（前一波段低点或重要均线）
# 3. 整体趋势向上
def check_volume_shrink(code_name, data, date=None, threshold=60,
                        shrink_days=3, support_ratio=0.95):
    """
    缩量回调检测
    连续缩量回调但未跌破支撑，可能是买入机会
    """
    if date is None:
        end_date = code_name[0]
    else:
        end_date = date.strftime("%Y-%m-%d")

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask].copy()

    if len(data.index) < threshold:
        return False

    data = data.tail(n=threshold)
    if len(data) < threshold:
        return False

    # 计算成交量均线
    data.loc[:, 'vol_ma5'] = tl.MA(data['volume'].values, timeperiod=5)
    data.loc[:, 'vol_ma5'] = np.where(np.isnan(data['vol_ma5'].values), 0.0, data['vol_ma5'].values)

    # 计算收盘价均线
    data.loc[:, 'close_ma20'] = tl.MA(data['close'].values, timeperiod=20)
    data.loc[:, 'close_ma20'] = np.where(np.isnan(data['close_ma20'].values), 0.0, data['close_ma20'].values)

    # 检查最近shrink_days天是否连续缩量回调
    recent_data = data.tail(n=shrink_days + 1)
    if len(recent_data) < shrink_days + 1:
        return False

    # 检查连续缩量
    for i in range(1, len(recent_data)):
        if recent_data.iloc[i]['volume'] >= recent_data.iloc[i - 1]['volume']:
            return False

    # 检查是否回调（收盘价下跌）
    for i in range(1, len(recent_data)):
        if recent_data.iloc[i]['close'] >= recent_data.iloc[i - 1]['close']:
            return False

    # 检查是否跌破支撑位（20日均线或前低）
    last_close = data.iloc[-1]['close']
    ma20 = data.iloc[-1]['close_ma20']

    if ma20 > 0:
        # 以20日均线作为支撑
        support_level = ma20 * support_ratio
        if last_close < support_level:
            return False
    else:
        # 如果没有20日均线，检查前低
        front_data = data.head(n=threshold - shrink_days)
        if len(front_data) > 0:
            low_support = front_data['close'].values.min() * support_ratio
            if last_close < low_support:
                return False

    # 检查整体趋势向上（最近20日涨幅为正）
    if len(data) >= 20:
        close_20_ago = data.iloc[-20]['close']
        if last_close <= close_20_ago:
            return False

    return True


# 主检查函数 - 同时检测放量突破和缩量回调
def check(code_name, data, date=None, threshold=60):
    """
    成交量异动检测
    返回放量突破或缩量回调的结果
    """
    return check_volume_breakout(code_name, data, date, threshold) or \
           check_volume_shrink(code_name, data, date, threshold)