#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
连续小阳线 + 年内低位策略
识别在年内低位出现连续小阳线的股票形态

作者: liugu
日期: 2026/5/27

核心逻辑:
1. 连续小阳线条件（复用 consecutive_small_bullish）
2. 股价在近1年（250个交易日）低位附近
   - 当前价格 <= 近250日最低价 * 1.3（在低位30%范围内）
   - 或当前价格 <= 近250日收盘价的20%分位数

组合意义:
- 年内低位 + 连续小阳线 = 可能是底部反转信号
- 风险较低，上涨空间较大
"""

import numpy as np
from .consecutive_small_bullish import check as check_consecutive

__author__ = 'liugu'
__date__ = '2026/5/27'


def check(code_name, data, date=None, days=5, min_change=1.0, max_change=5.0,
          lookback=250, max_price_ratio=1.3, use_percentile=True, percentile=25):
    """
    检查股票是否符合"连续小阳线 + 年内低位"特征
    
    参数:
        code_name: (代码, 名称) 元组
        data: 历史K线数据 DataFrame
        date: 判断日期
        days: 连续阳线天数，默认5
        min_change: 单日最小涨幅(%)，默认1.0
        max_change: 单日最大涨幅(%)，默认5.0
        lookback: 回看天数（年化约250个交易日），默认250
        max_price_ratio: 最大价格比率（当前价/年内最低价），默认1.3
        use_percentile: 是否使用百分位数判断，默认True
        percentile: 价格分位数阈值(%)，默认25（即最低四分位）
    
    返回:
        True 如果符合条件
    """
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        close_col = '收盘'
        low_col = '最低'
    else:
        date_col = 'date'
        close_col = 'close'
        low_col = 'low'
    
    if date is None:
        end_date = code_name[0]
    else:
        if isinstance(date, str):
            end_date = date
        else:
            end_date = date.strftime("%Y-%m-%d")
    
    if end_date is not None:
        mask = (data[date_col] <= end_date)
        data = data.loc[mask].copy()
    
    # 至少需要 lookback 天的数据
    if len(data.index) < lookback:
        # 数据不足一年，用现有数据的80%，最少60天
        lookback = max(int(len(data.index) * 0.8), 60)
    
    # 如果数据太少，直接返回
    if len(data.index) < 60:
        return False
    
    # 取近 lookback 天数据
    recent_data = data.tail(n=lookback)
    
    current_close = recent_data[close_col].iloc[-1]
    
    # 条件1: 连续小阳线
    if not check_consecutive(code_name, data, date, days, min_change, max_change):
        return False
    
    # 条件2: 股价在年内低位
    year_low = recent_data[low_col].min()  # 年内最低价
    year_high = recent_data[close_col].max()  # 年内最高价
    
    # 方法1: 当前价格在年内最低价的 max_price_ratio 倍以内
    price_ratio = current_close / year_low
    if price_ratio > max_price_ratio:
        # 方法2: 使用百分位数判断
        if use_percentile:
            # 计算年内收盘价的分位数
            closes = recent_data[close_col].values
            price_percentile = (np.sum(closes <= current_close) / len(closes)) * 100
            if price_percentile > percentile:
                return False
        else:
            return False
    
    return True


def check_with_details(code_name, data, date=None, days=5, min_change=1.0, max_change=5.0,
                       lookback=250, max_price_ratio=1.3, percentile=25):
    """
    检查并返回详细信息
    
    返回:
        dict: 包含是否通过及各项指标
    """
    # 支持中文列名
    if '日期' in data.columns:
        date_col = '日期'
        close_col = '收盘'
        low_col = '最低'
        high_col = '最高'
    else:
        date_col = 'date'
        close_col = 'close'
        low_col = 'low'
        high_col = 'high'
    
    if date is None:
        end_date = code_name[0]
    else:
        if isinstance(date, str):
            end_date = date
        else:
            end_date = date.strftime("%Y-%m-%d")
    
    if end_date is not None:
        mask = (data[date_col] <= end_date)
        data = data.loc[mask].copy()
    
    if len(data.index) < lookback:
        lookback = max(int(len(data.index) * 0.8), 60)
    
    recent_data = data.tail(n=lookback)
    
    if len(recent_data.index) < 60:
        return {'pass': False, 'reason': '数据不足'}
    
    current_close = recent_data[close_col].iloc[-1]
    year_low = recent_data[low_col].min()
    year_high = recent_data[close_col].max()
    
    # 计算各项指标
    price_ratio = current_close / year_low
    closes = recent_data[close_col].values
    price_percentile = (np.sum(closes <= current_close) / len(closes)) * 100
    year_change = (current_close - recent_data[close_col].iloc[0]) / recent_data[close_col].iloc[0] * 100
    
    # 检查连续小阳线
    is_consecutive = check_consecutive(code_name, data, date, days, min_change, max_change)
    
    # 检查低位条件
    is_low_position = price_ratio <= max_price_ratio or price_percentile <= percentile
    
    result = {
        'pass': is_consecutive and is_low_position,
        'consecutive_bullish': is_consecutive,
        'low_position': is_low_position,
        'current_price': round(current_close, 2),
        'year_low': round(year_low, 2),
        'year_high': round(year_high, 2),
        'price_ratio': round(price_ratio, 2),
        'price_percentile': round(price_percentile, 1),
        'year_change_pct': round(year_change, 2),
        'distance_from_low': round((current_close - year_low) / year_low * 100, 2),
        'distance_from_high': round((year_high - current_close) / year_high * 100, 2)
    }
    
    return result


# 快捷函数：连续5天小阳线 + 年内低位
def check_5d(code_name, data, date=None):
    """连续5天小阳线 + 年内低位"""
    return check(code_name, data, date, days=5)


# 主入口测试
if __name__ == '__main__':
    print("连续小阳线 + 年内低位策略模块")
    print("用法:")
    print("  from instock.core.strategy.consecutive_bullish_at_low import check")
    print("  check(('600000', '浦发银行'), data, date='2026-05-27')")
