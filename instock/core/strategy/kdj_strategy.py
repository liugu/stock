#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
KDJ指标策略
1. KDJ金叉检测（K线上穿D线）
2. KDJ超卖反弹（J值低于阈值后回升）
"""

import numpy as np
import talib as tl

__author__ = 'liugu'
__date__ = '2026/5/11'


def check_kdj_golden_cross(code_name, data, date=None, threshold=60):
    """
    KDJ金叉检测
    K线上穿D线，且处于低位（超卖区）
    
    参数:
        code_name: 股票代码和名称元组
        data: 股票历史数据DataFrame
        date: 指定日期
        threshold: 最小数据天数
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

    # 计算KDJ指标
    # 使用TA-Lib的STOCH函数计算KDJ
    # fastk_period=9, slowk_period=3, slowd_period=3
    try:
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        # 计算K和D值
        slowk, slowd = tl.STOCH(high, low, close, 
                                fastk_period=9,
                                slowk_period=3,
                                slowk_matype=0,
                                slowd_period=3,
                                slowd_matype=0)
        
        # 计算J值 = 3K - 2D
        j = 3 * slowk - 2 * slowd
        
        # 替换NaN值
        slowk = np.nan_to_num(slowk, nan=50.0)
        slowd = np.nan_to_num(slowd, nan=50.0)
        j = np.nan_to_num(j, nan=50.0)
        
        # 获取最近两天的数据
        if len(slowk) < 2:
            return False
        
        k_today = slowk[-1]
        k_yesterday = slowk[-2]
        d_today = slowd[-1]
        d_yesterday = slowd[-2]
        
        # 金叉条件：
        # 1. 昨日K < D，今日K > D（K线上穿D线）
        # 2. K值和D值处于相对低位（< 50）
        if (k_yesterday < d_yesterday and k_today > d_today and
            k_today < 50 and d_today < 50):
            return True
        
        return False
    except Exception as e:
        return False


def check_kdj_oversold_bounce(code_name, data, date=None, threshold=60,
                               j_threshold=20):
    """
    KDJ超卖反弹检测
    J值低于阈值后回升，是买入信号
    
    参数:
        code_name: 股票代码和名称元组
        data: 股票历史数据DataFrame
        date: 指定日期
        threshold: 最小数据天数
        j_threshold: J值超卖阈值（默认20）
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

    try:
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        # 计算KDJ
        slowk, slowd = tl.STOCH(high, low, close,
                                fastk_period=9,
                                slowk_period=3,
                                slowk_matype=0,
                                slowd_period=3,
                                slowd_matype=0)
        
        j = 3 * slowk - 2 * slowd
        j = np.nan_to_num(j, nan=50.0)
        
        if len(j) < 5:
            return False
        
        # 检查最近5天内是否有J值低于阈值
        recent_j = j[-5:]
        
        # 条件1：最近5天内J值曾低于阈值（超卖）
        oversold = any(j_val < j_threshold for j_val in recent_j[:-1])
        
        # 条件2：当前J值回升（今日J值 > 昨日J值）
        bouncing = j[-1] > j[-2] and j[-1] > j_threshold
        
        # 条件3：股价上涨
        price_up = data.iloc[-1]['close'] > data.iloc[-2]['close']
        
        return oversold and bouncing and price_up
        
    except Exception as e:
        return False


def check(code_name, data, date=None, threshold=60):
    """
    KDJ策略主函数
    返回金叉或超卖反弹的结果
    """
    return check_kdj_golden_cross(code_name, data, date, threshold) or \
           check_kdj_oversold_bounce(code_name, data, date, threshold)
