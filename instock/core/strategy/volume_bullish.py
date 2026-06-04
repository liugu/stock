#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
连续放量小阳线策略
识别连续放量上涨的小阳线形态

作者: liugu
日期: 2026/6/1

核心逻辑:
1. 最近 N 天每天收阳（收盘价 > 开盘价）
2. 每天涨幅在 1%-5% 之间（排除大阳线和涨停）
3. 成交量连续放大：
   - 当日成交量 >= 前一日成交量 * min_vol_increase（量能递增）
   - 且当日成交量 >= 5日均量 * min_vol_ratio（相对放量）
4. 最后一天收盘 > 第一天开盘（整体趋势向上）
5. 排除停牌股（成交量 > 0）

技术含义:
- 连续小阳线 + 放量 = 主力吸筹或温和拉升
- 量能递增显示买盘持续增强
- 涨幅温和避免追高风险
"""

import numpy as np
import pandas as pd

__author__ = 'liugu'
__date__ = '2026/6/1'


def check(code_name, data, date=None, days=5, min_change=1.0, max_change=5.0,
          min_vol_increase=1.1, min_vol_ratio=1.5, vol_ma_period=5):
    """
    检查股票是否符合连续放量小阳线特征
    
    参数:
        code_name: (代码, 名称) 元组
        data: 历史K线数据 DataFrame
        date: 判断日期
        days: 连续阳线天数，默认5
        min_change: 单日最小涨幅(%)，默认1.0
        max_change: 单日最大涨幅(%)，默认5.0
        min_vol_increase: 最小量能递增比率（当日/前日），默认1.1（放大10%）
        min_vol_ratio: 最小量比（当日/均量），默认1.5（放大50%）
        vol_ma_period: 成交量均线周期，默认5
    
    返回:
        True 如果符合连续放量小阳线特征
    """
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        open_col = '开盘'
        close_col = '收盘'
        high_col = '最高'
        low_col = '最低'
        volume_col = '成交量'
    else:
        date_col = 'date'
        open_col = 'open'
        close_col = 'close'
        high_col = 'high'
        low_col = 'low'
        volume_col = 'volume'
    
    if date is None:
        end_date = None  # 不限制日期，使用全部数据
    else:
        if isinstance(date, str):
            end_date = date
        else:
            end_date = date.strftime("%Y-%m-%d")
    
    if end_date is not None:
        # 转换日期列类型以便比较
        data[date_col] = pd.to_datetime(data[date_col])
        end_date_dt = pd.to_datetime(end_date)
        mask = (data[date_col] <= end_date_dt)
        data = data.loc[mask].copy()
    
    # 至少需要 days + vol_ma_period 天的数据
    min_data = days + vol_ma_period
    if len(data.index) < min_data:
        return False
    
    # 取最近 days + vol_ma_period 天数据
    data = data.tail(n=min_data)
    
    closes = data[close_col].values
    opens = data[open_col].values
    volumes = data[volume_col].values
    
    # 排除停牌：当天成交量为0
    if volumes[-1] <= 0:
        return False
    
    # 检查连续阳线 + 涨幅在范围内 + 量能放大
    for i in range(min_data - days, min_data):
        change_rate = (closes[i] - opens[i]) / opens[i] * 100
        
        # 必须是阳线
        if closes[i] <= opens[i]:
            return False
        
        # 涨幅在 min_change ~ max_change 之间
        if change_rate < min_change or change_rate > max_change:
            return False
        
        # 量能放大条件（从第二天开始检查，第一天只检查相对均量）
        if i > min_data - days:
            # 条件1: 当日成交量 >= 前一日 * min_vol_increase
            if volumes[i] < volumes[i-1] * min_vol_increase:
                return False
        
        # 条件2: 当日成交量 >= 5日均量 * min_vol_ratio
        vol_ma_start = max(0, i - vol_ma_period)
        vol_ma = np.mean(volumes[vol_ma_start:i])
        if vol_ma > 0 and volumes[i] < vol_ma * min_vol_ratio:
            return False
    
    # 整体趋势向上：最后一天收盘 > 第一天开盘
    if closes[-1] <= opens[-days]:
        return False
    
    return True


def check_with_details(code_name, data, date=None, days=5, min_change=1.0, max_change=5.0,
                       min_vol_increase=1.1, min_vol_ratio=1.5, vol_ma_period=5):
    """
    检查并返回详细信息
    
    返回:
        dict: 包含是否通过及各项指标
    """
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        open_col = '开盘'
        close_col = '收盘'
        high_col = '最高'
        low_col = '最低'
        volume_col = '成交量'
    else:
        date_col = 'date'
        open_col = 'open'
        close_col = 'close'
        high_col = 'high'
        low_col = 'low'
        volume_col = 'volume'
    
    if date is None:
        end_date = None
    else:
        if isinstance(date, str):
            end_date = date
        else:
            end_date = date.strftime("%Y-%m-%d")
    
    if end_date is not None:
        data[date_col] = pd.to_datetime(data[date_col])
        end_date_dt = pd.to_datetime(end_date)
        mask = (data[date_col] <= end_date_dt)
        data = data.loc[mask].copy()
    
    min_data = days + vol_ma_period
    if len(data.index) < min_data:
        return {'pass': False, 'reason': '数据不足'}
    
    data = data.tail(n=min_data)
    
    closes = data[close_col].values
    opens = data[open_col].values
    volumes = data[volume_col].values
    
    if volumes[-1] <= 0:
        return {'pass': False, 'reason': '停牌或无成交'}
    
    # 计算各项指标
    daily_changes = []
    vol_increases = []
    vol_ratios = []
    
    all_bullish = True
    all_in_range = True
    all_vol_increasing = True
    all_vol_above_ma = True
    
    for i in range(min_data - days, min_data):
        change_rate = (closes[i] - opens[i]) / opens[i] * 100
        daily_changes.append(change_rate)
        
        if closes[i] <= opens[i]:
            all_bullish = False
        
        if change_rate < min_change or change_rate > max_change:
            all_in_range = False
        
        if i > min_data - days:
            vol_inc = volumes[i] / volumes[i-1]
            vol_increases.append(vol_inc)
            if volumes[i] < volumes[i-1] * min_vol_increase:
                all_vol_increasing = False
        else:
            vol_increases.append(1.0)
        
        vol_ma_start = max(0, i - vol_ma_period)
        vol_ma = np.mean(volumes[vol_ma_start:i])
        if vol_ma > 0:
            vol_ratio = volumes[i] / vol_ma
            vol_ratios.append(vol_ratio)
            if volumes[i] < vol_ma * min_vol_ratio:
                all_vol_above_ma = False
        else:
            vol_ratios.append(1.0)
    
    total_change = (closes[-1] - opens[-days]) / opens[-days] * 100
    trend_up = closes[-1] > opens[-days]
    
    result = {
        'pass': all_bullish and all_in_range and all_vol_increasing and all_vol_above_ma and trend_up,
        'all_bullish': all_bullish,
        'all_in_range': all_in_range,
        'all_vol_increasing': all_vol_increasing,
        'all_vol_above_ma': all_vol_above_ma,
        'trend_up': trend_up,
        'daily_changes': [round(x, 2) for x in daily_changes],
        'avg_change': round(np.mean(daily_changes), 2),
        'total_change': round(total_change, 2),
        'vol_increases': [round(x, 2) for x in vol_increases],
        'avg_vol_increase': round(np.mean(vol_increases), 2),
        'vol_ratios': [round(x, 2) for x in vol_ratios],
        'avg_vol_ratio': round(np.mean(vol_ratios), 2),
        'first_open': round(opens[-days], 2),
        'last_close': round(closes[-1], 2),
        'last_volume': int(volumes[-1])
    }
    
    return result


# 快捷函数：连续3天放量小阳线
def check_3d(code_name, data, date=None):
    """连续3天放量小阳线"""
    return check(code_name, data, date, days=3)


# 快捷函数：连续5天放量小阳线
def check_5d(code_name, data, date=None):
    """连续5天放量小阳线"""
    return check(code_name, data, date, days=5)


# 快捷函数：连续放量小阳线（保守版，量能要求更高）
def check_conservative(code_name, data, date=None, days=5):
    """保守版：量能递增15%，量比2.0"""
    return check(code_name, data, date, days=days, min_vol_increase=1.15, min_vol_ratio=2.0)


# 主入口测试
if __name__ == '__main__':
    print("连续放量小阳线策略模块")
    print("用法:")
    print("  from instock.core.strategy.volume_bullish import check")
    print("  check(('600000', '浦发银行'), data, date='2026-06-01')")
