#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
长线稳定盈利选股策略 v2
识别适合长期持有的优质股票（价值投资风格）

核心逻辑（允许优质股回调，左侧布局）:
1. 估值合理: PE在5~25之间，PB在0.5~3之间
2. 大中盘股: 总市值 >= 100亿
3. 低波动: 过去60日收益率标准差 <= 3.5%
4. 长期趋势没坏: MA120趋势向上（120日线仍在走高）
5. 不过度远离MA120: 股价在MA120的-15%~+30%之间
6. 回撤可控: 过去120日最大回撤 <= 30%
7. 稳定性: 正收益天数占比 >= 48%
8. 近期不暴涨: 近3日涨幅 <= 8%
"""

import numpy as np
import talib as tl

__author__ = 'hermes'
__date__ = '2026/7/1'


def check_with_details(code_name, data, date=None):
    """检查股票是否符合长线稳定盈利特征"""
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'; volume_col = '成交量'
    else:
        date_col = 'date'; close_col = 'close'; volume_col = 'volume'

    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()

    if len(data) < 125:
        return None

    data = data.tail(200)
    closes = data[close_col].values

    ma60 = tl.MA(closes, timeperiod=60)
    ma120 = tl.MA(closes, timeperiod=120)

    if np.isnan(ma60[-1]) or np.isnan(ma120[-1]):
        return None

    last_close = closes[-1]

    # ---- 条件1: MA120趋势向上（长期趋势没坏） ----
    if len(ma120) >= 60 and not np.isnan(ma120[-60]):
        if ma120[-1] <= ma120[-60] * 0.97:  # 允许微跌3%
            return None

    # ---- 条件2: 股价不离MA120太远（允许回调到下方，但不能太远）----
    deviation_120 = (last_close - ma120[-1]) / ma120[-1] * 100
    if deviation_120 < -15 or deviation_120 > 30:
        return None

    # ---- 条件3: 低波动率 ----
    log_returns = np.diff(np.log(closes[-61:]))
    volatility = np.std(log_returns) * 100
    if volatility > 3.5:
        return None

    # ---- 条件4: 最大回撤控制 ----
    high_prices = np.maximum.accumulate(closes[-120:])
    drawdowns = (high_prices - closes[-120:]) / high_prices * 100
    max_dd = np.max(drawdowns)
    if max_dd > 30:
        return None

    # ---- 条件5: 稳定性评分 ----
    returns_120 = np.diff(closes[-121:])
    positive_days = np.sum(returns_120 > 0)
    stability = positive_days / len(returns_120) * 100
    if stability < 48:
        return None

    # ---- 条件6: 近3日涨幅过滤 ----
    if len(closes) >= 4:
        pct_3d = (closes[-1] - closes[-4]) / closes[-4] * 100
        if pct_3d > 8:
            return None

    # ---- 计算辅助指标 ----
    # 均线
    ma5 = tl.MA(closes, 5)[-1] if len(closes) >= 5 else None
    ma10 = tl.MA(closes, 10)[-1] if len(closes) >= 10 else None
    ma20 = tl.MA(closes, 20)[-1] if len(closes) >= 20 else None
    
    # 判断均线多头
    bullish_ma = False
    if all(x is not None and not np.isnan(x) for x in [ma5, ma10, ma20, ma60[-1]]):
        bullish_ma = ma5 > ma10 > ma20 > ma60[-1]

    # 到MA60的距离
    deviation_60 = (last_close - ma60[-1]) / ma60[-1] * 100

    # 各周期涨幅
    pct_120d = (closes[-1] - closes[-120]) / closes[-120] * 100
    pct_60d = (closes[-1] - closes[-60]) / closes[-60] * 100 if len(closes) >= 60 else 0
    pct_20d = (closes[-1] - closes[-20]) / closes[-20] * 100
    pct_3d_val = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0

    # 年化波动率
    annual_vol = volatility * np.sqrt(244)

    return {
        'last_close': round(last_close, 2),
        'ma60': round(ma60[-1], 2),
        'ma120': round(ma120[-1], 2),
        'deviation_60': round(deviation_60, 2),
        'deviation_120': round(deviation_120, 2),
        'volatility': round(volatility, 2),
        'annual_vol': round(annual_vol, 2),
        'max_drawdown': round(max_dd, 2),
        'stability': round(stability, 1),
        'pct_120d': round(pct_120d, 2),
        'pct_60d': round(pct_60d, 2),
        'pct_20d': round(pct_20d, 2),
        'pct_3d': round(pct_3d_val, 2),
        'bullish_ma': bullish_ma
    }


if __name__ == '__main__':
    print("长线稳定盈利选股策略 v2")
