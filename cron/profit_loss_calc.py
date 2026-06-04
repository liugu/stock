#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
止盈止损计算工具
基于技术分析计算止盈止损位
"""

import numpy as np
import talib as tl

__author__ = 'liugu'
__date__ = '2026/5/11'


def calculate_support_resistance(data, period=20):
    """
    计算支撑位和压力位
    
    参数:
        data: 股票历史数据DataFrame
        period: 计算周期（默认20日）
    
    返回:
        tuple: (支撑位, 压力位)
    """
    if len(data) < period:
        return None, None
    
    recent = data.tail(period)
    
    # 支撑位：近期最低点
    support = recent['low'].min()
    
    # 压力位：近期最高点
    resistance = recent['high'].max()
    
    return support, resistance


def calculate_atr_stop(data, period=14, multiplier=2.0):
    """
    基于ATR计算动态止损位
    
    参数:
        data: 股票历史数据DataFrame
        period: ATR周期（默认14）
        multiplier: ATR倍数（默认2倍）
    
    返回:
        float: 止损价位
    """
    if len(data) < period:
        return None
    
    try:
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        atr = tl.ATR(high, low, close, timeperiod=period)
        atr = np.nan_to_num(atr, nan=0.0)
        
        if len(atr) > 0 and atr[-1] > 0:
            last_close = close[-1]
            stop_loss = last_close - atr[-1] * multiplier
            return stop_loss
    except Exception as e:
        pass
    
    return None


def calculate_profit_loss_levels(data, profit_ratio=0.05, loss_ratio=0.03):
    """
    计算止盈止损建议位
    
    参数:
        data: 股票历史数据DataFrame
        profit_ratio: 止盈比例（默认5%）
        loss_ratio: 止损比例（默认3%）
    
    返回:
        dict: 止盈止损信息
    """
    if data is None or len(data) == 0:
        return {}
    
    last_close = data.iloc[-1]['close']
    
    # 计算支撑压力位
    support, resistance = calculate_support_resistance(data)
    
    # 计算ATR止损
    atr_stop = calculate_atr_stop(data)
    
    # 固定比例止盈止损
    fixed_profit = last_close * (1 + profit_ratio)
    fixed_loss = last_close * (1 - loss_ratio)
    
    result = {
        'current_price': last_close,
        'take_profit_fixed': round(fixed_profit, 2),
        'stop_loss_fixed': round(fixed_loss, 2),
        'take_profit_ratio': f"+{profit_ratio*100:.1f}%",
        'stop_loss_ratio': f"-{loss_ratio*100:.1f}%",
    }
    
    if support and resistance:
        result['support'] = round(support, 2)
        result['resistance'] = round(resistance, 2)
        result['take_profit_resistance'] = round(resistance * 1.05, 2)  # 突破压力位+5%
        result['stop_loss_support'] = round(support * 0.97, 2)  # 跌破支撑位-3%
    
    if atr_stop:
        result['stop_loss_atr'] = round(atr_stop, 2)
    
    return result


def format_profit_loss_message(pl_info, stock_name, stock_code):
    """
    格式化止盈止损消息
    
    参数:
        pl_info: 止盈止损信息字典
        stock_name: 股票名称
        stock_code: 股票代码
    
    返回:
        str: 格式化的消息
    """
    if not pl_info:
        return ""
    
    lines = [
        f"【{stock_code} {stock_name}】",
        f"当前价: {pl_info['current_price']:.2f}元",
        f"",
        f"止盈建议:",
        f"  固定止盈: {pl_info['take_profit_fixed']}元 ({pl_info['take_profit_ratio']})",
    ]
    
    if 'resistance' in pl_info:
        lines.append(f"  压力位: {pl_info['resistance']}元")
        lines.append(f"  突破止盈: {pl_info['take_profit_resistance']}元")
    
    lines.append(f"")
    lines.append(f"止损建议:")
    lines.append(f"  固定止损: {pl_info['stop_loss_fixed']}元 ({pl_info['stop_loss_ratio']})")
    
    if 'support' in pl_info:
        lines.append(f"  支撑位: {pl_info['support']}元")
        lines.append(f"  跌破止损: {pl_info['stop_loss_support']}元")
    
    if 'stop_loss_atr' in pl_info:
        lines.append(f"  ATR止损: {pl_info['stop_loss_atr']}元")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    import pandas as pd
    
    # 模拟数据
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30),
        'open': [10.0] * 30,
        'high': [10.5 + i*0.02 for i in range(30)],
        'low': [9.8 - i*0.01 for i in range(30)],
        'close': [10.2 + i*0.03 for i in range(30)],
        'volume': [1000000] * 30,
    })
    
    pl_info = calculate_profit_loss_levels(test_data)
    print(format_profit_loss_message(pl_info, "测试股票", "000001"))
