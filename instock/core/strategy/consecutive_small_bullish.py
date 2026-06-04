#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
连续小阳线策略
识别连续小阳线、稳步上涨的股票形态

作者: liugu
日期: 2026/5/25

核心逻辑:
1. 最近 N 天每天收阳（收盘价 > 开盘价）
2. 每天涨幅在 1%-5% 之间（排除大阳线和涨停）
3. 最后一天收盘 > 第一天开盘（整体趋势向上）
4. 成交量温和：当日成交量 >= 5日均量 * 0.8
5. 排除停牌股（成交量 > 0）
"""

import numpy as np
import talib as tl

__author__ = 'liugu '
__date__ = '2026/5/25 '


def check(code_name, data, date=None, days=5, min_change=1.0, max_change=5.0,
          vol_ma_period=5, min_vol_ratio=0.8):
    """
    检查股票是否符合连续小阳线特征
    
    参数:
        code_name: (代码, 名称) 元组
        data: 历史K线数据 DataFrame
        date: 判断日期
        days: 连续阳线天数，默认5
        min_change: 单日最小涨幅(%)，默认1.0
        max_change: 单日最大涨幅(%)，默认5.0
        vol_ma_period: 成交量均线周期，默认5
        min_vol_ratio: 最小量比（当日/均量），默认0.8
    
    返回:
        True 如果符合连续小阳线特征
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
        end_date = code_name[0]
    else:
        if isinstance(date, str):
            end_date = date
        else:
            end_date = date.strftime("%Y-%m-%d")
    
    if end_date is not None:
        mask = (data[date_col] <= end_date)
        data = data.loc[mask].copy()
    
    # 至少需要 days 天的数据
    if len(data.index) < days + 2:
        return False
    
    # 取最近 days+1 天（days天连续 + 前一天用来比较成交量）
    data = data.tail(n=days + 1)
    
    closes = data[close_col].values
    opens = data[open_col].values
    volumes = data[volume_col].values
    
    # 排除停牌：当天成交量为0
    if volumes[-1] <= 0:
        return False
    
    # 检查连续阳线 + 涨幅在范围内
    for i in range(1, days + 1):
        change_rate = (closes[i] - opens[i]) / opens[i] * 100
        
        # 必须是阳线
        if closes[i] <= opens[i]:
            return False
        
        # 涨幅在 min_change ~ max_change 之间
        if change_rate < min_change or change_rate > max_change:
            return False
    
    # 整体趋势向上：最后一天收盘 > 第一天开盘
    if closes[-1] <= opens[-days]:
        return False
    
    # 成交量条件：当日成交量 >= 5日均量 * min_vol_ratio
    # 用倒数第二天到前面的数据算均线（排除当天的成交量干扰）
    vol_values = volumes[:days]  # 不包括当天
    vol_ma = np.mean(vol_values)
    if vol_ma > 0 and volumes[-1] < vol_ma * min_vol_ratio:
        return False
    
    return True


# 快捷函数：连续5天小阳线
def check_5d(code_name, data, date=None):
    """连续5天小阳线"""
    return check(code_name, data, date, days=5)


# 快捷函数：连续8天小阳线
def check_8d(code_name, data, date=None):
    """连续8天小阳线（更保守）"""
    return check(code_name, data, date, days=8)


# 主入口测试
if __name__ == '__main__':
    print("连续小阳线策略模块")
    print("用法:")
    print("  from instock.core.strategy.consecutive_small_bullish import check")
    print("  check(('600000', '浦发银行'), data, date='2026-05-25')")
