#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
北向资金流向策略
基于主力资金数据判断北向资金流入趋势
使用已有的 stock_fund_em.py 数据接口
"""

import numpy as np
import pandas as pd

__author__ = 'liugu'
__date__ = '2026/5/11'


def check_main_inflow_continuous(code_name, data, date=None, threshold=60,
                                  inflow_days=3, min_amount=50000000):
    """
    连续N日主力资金净流入检测
    基于历史数据中的资金流向字段
    
    参数:
        code_name: 股票代码和名称元组
        data: 股票历史数据DataFrame（需包含主力资金字段）
        date: 指定日期
        threshold: 最小数据天数
        inflow_days: 连续流入天数（默认3天）
        min_amount: 最小流入金额（默认5000万）
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

    # 检查是否有主力资金数据字段
    # 如果没有，使用成交量和价格变化作为替代指标
    if 'main_inflow' in data.columns:
        # 有主力资金数据
        recent_data = data.tail(n=inflow_days)
        inflow_count = 0
        for _, row in recent_data.iterrows():
            if row['main_inflow'] >= min_amount:
                inflow_count += 1
        return inflow_count >= inflow_days
    else:
        # 无主力资金数据，使用量价关系判断
        # 连续放量上涨视为资金流入
        recent_data = data.tail(n=inflow_days + 1)
        if len(recent_data) < inflow_days + 1:
            return False
        
        inflow_count = 0
        for i in range(1, len(recent_data)):
            # 当日上涨且放量
            if (recent_data.iloc[i]['close'] > recent_data.iloc[i]['open'] and
                recent_data.iloc[i]['volume'] > recent_data.iloc[i-1]['volume']):
                inflow_count += 1
        
        return inflow_count >= inflow_days


def check_volume_price_trend(code_name, data, date=None, threshold=60):
    """
    量价趋势判断 - 替代北向资金判断
    连续3日量价齐升（资金持续流入信号）
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

    data = data.tail(n=5)
    if len(data) < 5:
        return False

    # 检查最近3日是否量价齐升
    count = 0
    for i in range(1, len(data)):
        # 收盘价上涨
        if data.iloc[i]['close'] > data.iloc[i-1]['close']:
            # 成交量放大
            if data.iloc[i]['volume'] > data.iloc[i-1]['volume']:
                count += 1
    
    return count >= 3


def check(code_name, data, date=None, threshold=60):
    """
    北向资金流向策略主函数
    由于实时北向资金API不稳定，使用主力资金和量价关系替代
    """
    return check_main_inflow_continuous(code_name, data, date, threshold) or \
           check_volume_price_trend(code_name, data, date, threshold)
