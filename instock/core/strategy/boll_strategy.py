#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
布林带(BOLL)指标策略
1. 布林带突破（价格突破上轨）
2. 布林带收口（带宽收窄后突破）
"""

import numpy as np
import talib as tl

__author__ = 'liugu'
__date__ = '2026/5/11'


def check_boll_breakout(code_name, data, date=None, threshold=60,
                        timeperiod=20, nbdevup=2):
    """
    布林带突破检测
    价格突破布林带上轨，且成交量放大
    
    参数:
        code_name: 股票代码和名称元组
        data: 股票历史数据DataFrame
        date: 指定日期
        threshold: 最小数据天数
        timeperiod: 布林带周期（默认20）
        nbdevup: 上轨标准差倍数（默认2）
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
        close = data['close'].values
        
        # 计算布林带
        upper, middle, lower = tl.BBANDS(close,
                                          timeperiod=timeperiod,
                                          nbdevup=nbdevup,
                                          nbdevdn=nbdevup,
                                          matype=0)
        
        upper = np.nan_to_num(upper, nan=0.0)
        middle = np.nan_to_num(middle, nan=0.0)
        
        if len(upper) < 2:
            return False
        
        last_close = data.iloc[-1]['close']
        last_upper = upper[-1]
        prev_upper = upper[-2]
        
        # 条件1：收盘价突破上轨
        if last_close <= last_upper:
            return False
        
        # 条件2：成交量放大（大于5日均量）
        vol_ma5 = tl.MA(data['volume'].values, timeperiod=5)
        vol_ma5 = np.nan_to_num(vol_ma5, nan=0.0)
        
        if vol_ma5[-1] > 0:
            vol_ratio = data.iloc[-1]['volume'] / vol_ma5[-1]
            if vol_ratio < 1.5:  # 成交量至少放大1.5倍
                return False
        
        # 条件3：涨幅为正
        if data.iloc[-1]['p_change'] < 0:
            return False
        
        return True
        
    except Exception as e:
        return False


def check_boll_squeeze(code_name, data, date=None, threshold=60,
                       timeperiod=20, squeeze_threshold=0.05):
    """
    布林带收口突破检测
    布林带带宽收窄（收口）后突破，是变盘信号
    
    参数:
        code_name: 股票代码和名称元组
        data: 股票历史数据DataFrame
        date: 指定日期
        threshold: 最小数据天数
        timeperiod: 布林带周期（默认20）
        squeeze_threshold: 收口阈值（带宽/中轨 < 5%）
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
        close = data['close'].values
        
        # 计算布林带
        upper, middle, lower = tl.BBANDS(close,
                                          timeperiod=timeperiod,
                                          nbdevup=2,
                                          nbdevdn=2,
                                          matype=0)
        
        upper = np.nan_to_num(upper, nan=0.0)
        middle = np.nan_to_num(middle, nan=0.0)
        lower = np.nan_to_num(lower, nan=0.0)
        
        if len(upper) < 10:
            return False
        
        # 计算带宽 = (上轨 - 下轨) / 中轨
        bandwidth = (upper - lower) / middle
        bandwidth = np.nan_to_num(bandwidth, nan=0.1)
        
        # 检查最近10天是否有收口（带宽收窄）
        recent_bandwidth = bandwidth[-10:]
        
        # 条件1：最近几天带宽收窄（小于阈值）
        squeeze_detected = any(bw < squeeze_threshold for bw in recent_bandwidth[:-1])
        
        # 条件2：今日带宽放大（突破）
        bandwidth_expanding = bandwidth[-1] > bandwidth[-2]
        
        # 条件3：价格突破（向上突破中轨）
        price_breakout = data.iloc[-1]['close'] > middle[-1]
        
        # 条件4：涨幅为正
        price_up = data.iloc[-1]['p_change'] > 0
        
        return squeeze_detected and bandwidth_expanding and price_breakout and price_up
        
    except Exception as e:
        return False


def check(code_name, data, date=None, threshold=60):
    """
    布林带策略主函数
    返回突破或收口突破的结果
    """
    return check_boll_breakout(code_name, data, date, threshold) or \
           check_boll_squeeze(code_name, data, date, threshold)