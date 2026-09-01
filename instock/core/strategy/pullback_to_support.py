#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
连续缩量回调到支撑位策略
识别上升趋势中缩量回调到关键均线支撑的股票（反弹机会）

核心逻辑:
1. 前期处于上升趋势（MA5 > MA10 > MA20 或 MA60向上）
2. 最近N天连续回调（每日收跌或累计跌幅超阈值）
3. 回调过程持续缩量（成交量逐日递减或低于均值）
4. 股价回调到MA20或MA60支撑位附近（如距MA20在±3%内）
5. 支撑均线仍然向上（趋势未破）
"""

import numpy as np
import talib as tl

__author__ = 'hermes'
__date__ = '2026/7/1'


def check(code_name, data, date=None,
          pullback_days=3, max_pullback_pct=-2.0,
          support_ma='ma20', support_distance=3.0,
          vol_shrink_ratio=0.8):
    """
    检查股票是否符合缩量回调到支撑位特征

    参数:
        code_name: (代码, 名称) 元组
        data: 历史K线数据 DataFrame
        date: 判断日期
        pullback_days: 回调天数，默认3
        max_pullback_pct: 回调期间最大允许单日涨幅（负数代表下跌），默认-2%
        support_ma: 支撑均线 'ma20' 或 'ma60'
        support_distance: 距支撑均线的距离阈值%，默认3%
        vol_shrink_ratio: 回调期间量能/20日均量的最大比值，默认0.8

    返回:
        True 如果符合缩量回调到支撑位特征
    """
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'; open_col = '开盘'
        high_col = '最高'; low_col = '最低'; volume_col = '成交量'
    else:
        date_col = 'date'; close_col = 'close'; open_col = 'open'
        high_col = 'high'; low_col = 'low'; volume_col = 'volume'

    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()

    if len(data) < 65:
        return False

    data = data.tail(65)
    closes = data[close_col].values
    opens = data[open_col].values
    volumes = data[volume_col].values

    # 计算均线
    ma5 = tl.MA(closes, timeperiod=5)
    ma10 = tl.MA(closes, timeperiod=10)
    ma20 = tl.MA(closes, timeperiod=20)
    ma60 = tl.MA(closes, timeperiod=60)

    if any(np.isnan(x[-1]) for x in [ma5, ma10, ma20, ma60]):
        return False

    # ---- 条件1: 前期处于上升趋势 ----
    # 标准：MA5 > MA10 > MA20（短期多头）
    uptrend = ma5[-pullback_days-1] > ma10[-pullback_days-1] > ma20[-pullback_days-1]
    # 或者：MA60 向上
    ma60_up = ma60[-1] > ma60[-5] * 0.995  # 允许微跌0.5%

    if not (uptrend or ma60_up):
        return False

    # ---- 条件2: 最近N天连续回调 ----
    pullback_volumes = volumes[-pullback_days:]
    pullback_closes = closes[-pullback_days:]
    pullback_opens = opens[-pullback_days:]

    # 检查每日是否收跌
    for i in range(pullback_days):
        day_change = (pullback_closes[i] - opens[-pullback_days+i]) / opens[-pullback_days+i] * 100
        if day_change > 0:  # 不能收阳
            return False

    # 累计跌幅：回调起点 vs 当前
    if pullback_days < len(closes):
        start_idx = -(pullback_days + 1)
        total_pullback = (closes[-1] - closes[start_idx]) / closes[start_idx] * 100
        # 起码是跌的（累计为负或平）
        if total_pullback >= 0:
            return False

    # ---- 条件3: 缩量 ----
    # 3a: 量能逐日递减
    vol_shrinking = True
    for i in range(1, pullback_days):
        if pullback_volumes[i] > pullback_volumes[i-1] * 1.05:  # 允许5%的波动
            vol_shrinking = False
            break

    # 3b: 或 回调期平均量 < 20日均量 * vol_shrink_ratio
    vol_ma20_val = np.mean(volumes[-20:])
    avg_pullback_vol = np.mean(pullback_volumes)
    vol_below_ma = avg_pullback_vol < vol_ma20_val * vol_shrink_ratio if vol_ma20_val > 0 else False

    if not (vol_shrinking or vol_below_ma):
        return False

    # ---- 条件4: 股价在支撑位附近 ----
    if support_ma == 'ma20':
        support_line = ma20[-1]
    else:  # ma60
        support_line = ma60[-1]

    # 股价距支撑均线的距离百分比
    distance_to_support = (closes[-1] - support_line) / support_line * 100
    
    # 在支撑线附近（允许在支撑线上方或下方一点）
    if abs(distance_to_support) > support_distance:
        return False

    # ---- 条件5: 支撑均线趋势向上 ----
    if support_ma == 'ma20':
        # MA20 走平或向上
        if ma20[-1] < ma20[-5] * 0.99:
            return False
    else:
        # MA60 走平或向上
        if ma60[-1] < ma60[-5] * 0.99:
            return False

    return True


def check_with_details(code_name, data, date=None,
                       pullback_days=3, support_ma='ma20', support_distance=3.0):
    """检查并返回详细信息"""
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'; open_col = '开盘'
        high_col = '最高'; low_col = '最低'; volume_col = '成交量'
    else:
        date_col = 'date'; close_col = 'close'; open_col = 'open'
        high_col = 'high'; low_col = 'low'; volume_col = 'volume'

    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()

    if len(data) < 65:
        return None

    data = data.tail(65)
    closes = data[close_col].values
    opens = data[open_col].values
    volumes = data[volume_col].values

    ma5 = tl.MA(closes, timeperiod=5)
    ma10 = tl.MA(closes, timeperiod=10)
    ma20 = tl.MA(closes, timeperiod=20)
    ma60 = tl.MA(closes, timeperiod=60)

    if any(np.isnan(x[-1]) for x in [ma5, ma10, ma20, ma60]):
        return None

    # 前趋上升趋势
    uptrend = ma5[-pullback_days-1] > ma10[-pullback_days-1] > ma20[-pullback_days-1]
    ma60_up = ma60[-1] > ma60[-5] * 0.995
    if not (uptrend or ma60_up):
        return None

    # 连续回调
    pullback_volumes = volumes[-pullback_days:]
    pullback_closes = closes[-pullback_days:]

    for i in range(pullback_days):
        day_change = (pullback_closes[i] - opens[-pullback_days+i]) / opens[-pullback_days+i] * 100
        if day_change > 0:  # 不收阳（可微跌或平）
            return None

    start_idx = -(pullback_days + 1)
    total_pullback = (closes[-1] - closes[start_idx]) / closes[start_idx] * 100
    if total_pullback >= 0:
        return None

    # 缩量
    vol_shrinking = all(pullback_volumes[i] <= pullback_volumes[i-1] * 1.05 for i in range(1, pullback_days))
    vol_ma20_val = np.mean(volumes[-20:])
    avg_pullback_vol = np.mean(pullback_volumes)
    vol_below_ma = avg_pullback_vol < vol_ma20_val * 0.8 if vol_ma20_val > 0 else False
    if not (vol_shrinking or vol_below_ma):
        return None

    # 支撑位
    support_line = ma20[-1] if support_ma == 'ma20' else ma60[-1]
    distance_to_support = (closes[-1] - support_line) / support_line * 100

    # 到MA20的距离
    dist_to_ma20 = (closes[-1] - ma20[-1]) / ma20[-1] * 100
    # 到MA60的距离
    dist_to_ma60 = (closes[-1] - ma60[-1]) / ma60[-1] * 100

    if abs(distance_to_support) > support_distance:
        return None

    # 支撑趋势
    if (support_ma == 'ma20' and ma20[-1] < ma20[-5] * 0.99) or \
       (support_ma == 'ma60' and ma60[-1] < ma60[-5] * 0.99):
        return None

    # 计算各日跌幅
    daily_changes = []
    for i in range(pullback_days):
        chg = (pullback_closes[i] - opens[-pullback_days+i]) / opens[-pullback_days+i] * 100
        daily_changes.append(round(chg, 2))

    # 量比序列
    vol_ratios = []
    for v in pullback_volumes:
        vol_ratios.append(round(v / vol_ma20_val, 2) if vol_ma20_val > 0 else 0)

    return {
        'total_pullback': round(total_pullback, 2),
        'daily_changes': daily_changes,
        'vol_ratios': vol_ratios,
        'avg_pullback_vol_ratio': round(avg_pullback_vol / vol_ma20_val, 2) if vol_ma20_val > 0 else 0,
        'ma5': round(ma5[-1], 2), 'ma10': round(ma10[-1], 2),
        'ma20': round(ma20[-1], 2), 'ma60': round(ma60[-1], 2),
        'dist_to_ma20': round(dist_to_ma20, 2),
        'dist_to_ma60': round(dist_to_ma60, 2),
        'support_ma': support_ma,
        'support_value': round(support_line, 2),
        'distance_to_support': round(distance_to_support, 2),
        'vol_shrinking': vol_shrinking,
        'uptrend_before': uptrend
    }


if __name__ == '__main__':
    print("缩量回调到支撑位策略")
    print("用法:")
    print("  from instock.core.strategy.pullback_to_support import check")
    print("  check(('600000', '浦发银行'), data, date='2026-07-01')")
