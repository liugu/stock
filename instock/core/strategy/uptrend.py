#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
趋势向上策略 v2
识别处于明显上升趋势的股票（放宽版，更实战）

核心逻辑:
1. 短期均线多头: MA5 > MA10 > MA20（短线趋势向上）
2. 股价在MA20之上（不强制在MA60之上，避免错过刚启动的）
3. MA60 走平或向上（中长期趋势不坏）
4. MACD 在0轴上方或金叉状态
5. 最近20日趋势斜率 > 0（整体向上）
"""

import numpy as np
import talib as tl

__author__ = 'hermes'
__date__ = '2026/7/1'


def check(code_name, data, date=None, max_3d_pct=10):
    """基本版：宽松条件
    max_3d_pct: 近3日涨幅上限（默认10%，超过此值排除）
    """
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'; volume_col = '成交量'
    else:
        date_col = 'date'; close_col = 'close'; volume_col = 'volume'
    
    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()
    
    if len(data) < 65:
        return False
    
    data = data.tail(65)
    closes = data[close_col].values
    
    # 条件0: 近3日涨幅不超过上限
    if len(closes) >= 4:
        pct_3d = (closes[-1] - closes[-4]) / closes[-4] * 100
        if pct_3d > max_3d_pct:
            return False
    
    ma5 = tl.MA(closes, timeperiod=5)
    ma10 = tl.MA(closes, timeperiod=10)
    ma20 = tl.MA(closes, timeperiod=20)
    ma60 = tl.MA(closes, timeperiod=60)
    
    if any(np.isnan(x[-1]) for x in [ma5, ma10, ma20, ma60]):
        return False
    
    # 条件1: 短期均线多头 MA5 > MA10 > MA20
    if not (ma5[-1] > ma10[-1] > ma20[-1]):
        return False
    
    # 条件2: 股价在MA20之上
    if closes[-1] <= ma20[-1]:
        return False
    
    # 条件3: MA60 走平或向上（比前值高）
    if len(closes) >= 65:
        if ma60[-1] < ma60[-5] * 0.99:  # 允许微跌1%
            return False
    
    # 条件4: MACD金叉或在0轴上
    dif, dea, macd = tl.MACD(closes)
    if np.isnan(dif[-1]) or np.isnan(dea[-1]):
        return False
    
    dif_ok = dif[-1] > dea[-1]        # 金叉状态
    macd_ok = dif[-1] > 0             # 在0轴上
    if not (dif_ok or macd_ok):
        return False
    
    # 条件5: 20日趋势斜率 > 0
    trend = closes[-20:]
    slope, _ = np.polyfit(np.arange(20), trend, 1)
    if slope <= 0:
        return False
    
    return True


def check_strong(code_name, data, date=None, max_3d_pct=10):
    """增强版：要求MA5>MA10>MA20>MA60 完整多头"""
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'
    else:
        date_col = 'date'; close_col = 'close'
    
    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()
    
    if len(data) < 65:
        return False
    
    data = data.tail(65)
    closes = data[close_col].values
    
    # 近3日涨幅过滤
    if len(closes) >= 4:
        pct_3d = (closes[-1] - closes[-4]) / closes[-4] * 100
        if pct_3d > max_3d_pct:
            return False
    
    ma5 = tl.MA(closes, timeperiod=5)
    ma10 = tl.MA(closes, timeperiod=10)
    ma20 = tl.MA(closes, timeperiod=20)
    ma60 = tl.MA(closes, timeperiod=60)
    
    if any(np.isnan(x[-1]) for x in [ma5, ma10, ma20, ma60]):
        return False
    
    # 完整多头排列
    if not (ma5[-1] > ma10[-1] > ma20[-1] > ma60[-1]):
        return False
    
    # 股价在MA60之上
    if closes[-1] <= ma60[-1]:
        return False
    
    dif, dea, _ = tl.MACD(closes)
    if np.isnan(dif[-1]) or np.isnan(dea[-1]):
        return False
    
    if dif[-1] <= dea[-1]:
        return False
    
    return True


def check_with_details(code_name, data, date=None, max_3d_pct=10):
    """检查并返回详细信息"""
    if '日期' in data.columns:
        date_col = '日期'; close_col = '收盘'; volume_col = '成交量'
    else:
        date_col = 'date'; close_col = 'close'; volume_col = 'volume'
    
    if date is not None:
        end_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else date
        data = data[data[date_col] <= end_date].copy()
    
    if len(data) < 65:
        return None
    
    data = data.tail(65)
    closes = data[close_col].values
    volumes = data[volume_col].values
    
    # 近3日涨幅过滤
    if len(closes) >= 4:
        pct_3d = (closes[-1] - closes[-4]) / closes[-4] * 100
        if pct_3d > max_3d_pct:
            return None
    
    ma5 = tl.MA(closes, timeperiod=5)
    ma10 = tl.MA(closes, timeperiod=10)
    ma20 = tl.MA(closes, timeperiod=20)
    ma60 = tl.MA(closes, timeperiod=60)
    
    if any(np.isnan(x[-1]) for x in [ma5, ma10, ma20, ma60]):
        return None
    
    # 核心：短期多头
    if not (ma5[-1] > ma10[-1] > ma20[-1]):
        return None
    if closes[-1] <= ma20[-1]:
        return None
    
    # MA60 走平或向上
    if ma60[-1] < ma60[-5] * 0.99:
        return None
    
    dif, dea, _ = tl.MACD(closes)
    if np.isnan(dif[-1]) or np.isnan(dea[-1]):
        return None
    if not (dif[-1] > dea[-1] or dif[-1] > 0):
        return None
    
    trend = closes[-20:]
    slope, _ = np.polyfit(np.arange(20), trend, 1)
    if slope <= 0:
        return None
    
    # 判断完整多头
    fully_bullish = (ma5[-1] > ma10[-1] > ma20[-1] > ma60[-1]) and (closes[-1] > ma60[-1])
    
    # 计算辅助指标
    pct_3d = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
    ma_spread = (ma5[-1] - ma20[-1]) / ma20[-1] * 100
    pct_60d = (closes[-1] - closes[-60]) / closes[-60] * 100 if len(closes) >= 60 else 0
    pct_20d = (closes[-1] - closes[-20]) / closes[-20] * 100
    vol_ma20_val = np.mean(volumes[-20:])
    vol_ratio = volumes[-1] / vol_ma20_val if vol_ma20_val > 0 else 0
    pct_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
    
    return {
        'ma5': round(ma5[-1], 2), 'ma10': round(ma10[-1], 2),
        'ma20': round(ma20[-1], 2), 'ma60': round(ma60[-1], 2),
        'ma_spread': round(ma_spread, 2),
        'pct_60d': round(pct_60d, 2), 'pct_20d': round(pct_20d, 2), 'pct_5d': round(pct_5d, 2),
        'pct_3d': round(pct_3d, 2),
        'vol_ratio': round(vol_ratio, 2),
        'slope': round(slope, 4),
        'fully_bullish': fully_bullish,
        'full_ma_text': f"{ma5[-1]:.2f}>{ma10[-1]:.2f}>{ma20[-1]:.2f}>{ma60[-1]:.2f}" if fully_bullish else f"{ma5[-1]:.2f}>{ma10[-1]:.2f}>{ma20[-1]:.2f}"
    }


if __name__ == '__main__':
    print("趋势向上策略 v2")
    print("  check() - 宽松版")
    print("  check_strong() - 完整多头版")
