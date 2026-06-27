#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速回测工具
计算策略历史胜率和收益
"""

import os
import sys
import datetime
import pandas as pd
import numpy as np

# 添加项目路径
cpath_current = os.path.dirname(os.path.dirname(__file__))
sys.path.append(cpath_current)

__author__ = 'liugu'
__date__ = '2026/5/11'


def calculate_strategy_win_rate(signals, price_data, hold_days=5):
    """
    计算策略胜率
    
    参数:
        signals: 信号列表，每个元素包含 date, code
        price_data: 价格数据字典 {code: DataFrame}
        hold_days: 持仓天数
    
    返回:
        dict: 胜率统计
    """
    if not signals or not price_data:
        return {}
    
    wins = 0
    losses = 0
    total_return = 0
    returns = []
    
    for signal in signals:
        date = signal['date']
        code = signal['code']
        
        if code not in price_data:
            continue
        
        df = price_data[code]
        
        # 找到信号日期的索引
        try:
            signal_idx = df[df['date'] == date].index[0]
            exit_idx = signal_idx + hold_days
            
            if exit_idx >= len(df):
                continue
            
            entry_price = df.iloc[signal_idx]['close']
            exit_price = df.iloc[exit_idx]['close']
            
            ret = (exit_price - entry_price) / entry_price * 100
            returns.append(ret)
            total_return += ret
            
            if ret > 0:
                wins += 1
            else:
                losses += 1
        except (IndexError, KeyError):
            continue
    
    total_trades = wins + losses
    if total_trades == 0:
        return {}
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': wins / total_trades * 100,
        'avg_return': total_return / total_trades,
        'max_return': max(returns) if returns else 0,
        'min_return': min(returns) if returns else 0,
    }


def calculate_max_drawdown(returns):
    """
    计算最大回撤
    
    参数:
        returns: 收益率列表
    
    返回:
        float: 最大回撤百分比
    """
    if not returns:
        return 0
    
    cumulative = np.cumprod([1 + r/100 for r in returns])
    peak = cumulative[0]
    max_dd = 0
    
    for value in cumulative:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    return max_dd


def backtest_strategy(strategy_func, price_data, start_date, end_date, 
                      hold_days=5, threshold=60):
    """
    回测单个策略
    
    参数:
        strategy_func: 策略函数
        price_data: 价格数据字典 {code: DataFrame}
        start_date: 开始日期
        end_date: 结束日期
        hold_days: 持仓天数
        threshold: 策略参数
    
    返回:
        dict: 回测结果
    """
    signals = []
    
    for code, df in price_data.items():
        # 遍历每个交易日
        for _, row in df.iterrows():
            date = row['date']
            
            if date < start_date or date > end_date:
                continue
            
            # 检查策略信号
            try:
                code_name = (date, code)
                if strategy_func(code_name, df, date, threshold):
                    signals.append({
                        'date': date,
                        'code': code,
                    })
            except Exception as e:
                continue
    
    # 计算胜率
    stats = calculate_strategy_win_rate(signals, price_data, hold_days)
    
    return {
        'signals': signals,
        'stats': stats,
    }


def generate_backtest_report(strategy_name, stats, period_days):
    """
    生成回测报告
    
    参数:
        strategy_name: 策略名称
        stats: 统计数据
        period_days: 回测天数
    
    返回:
        str: 报告文本
    """
    if not stats:
        return f"【{strategy_name}】无有效数据"
    
    lines = [
        f"【{strategy_name} 回测报告】",
        f"回测周期: {period_days}天",
        f"",
        f"交易次数: {stats['total_trades']}次",
        f"盈利次数: {stats['wins']}次",
        f"亏损次数: {stats['losses']}次",
        f"胜率: {stats['win_rate']:.2f}%",
        f"平均收益: {stats['avg_return']:.2f}%",
        f"最大收益: {stats['max_return']:.2f}%",
        f"最大亏损: {stats['min_return']:.2f}%",
    ]
    
    return "\n".join(lines)


def quick_backtest_summary(strategies, date_range='30d'):
    """
    快速回测摘要
    
    参数:
        strategies: 策略列表
        date_range: 回测范围 ('30d', '60d', '90d')
    
    返回:
        str: 摘要文本
    """
    # 解析日期范围
    days_map = {'30d': 30, '60d': 60, '90d': 90}
    days = days_map.get(date_range, 30)
    
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    
    lines = [
        f"【策略回测摘要】",
        f"回测区间: {start_date} ~ {end_date}",
        f"",
    ]
    
    # 这里需要实际运行回测，暂时返回占位信息
    for strategy in strategies:
        lines.append(f"• {strategy}: 待回测")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    print(quick_backtest_summary(['放量上涨', '均线多头', '海龟交易'], '30d'))
