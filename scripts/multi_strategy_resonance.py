#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多策略共振选股 - 直接从数据库读取
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'charset': 'utf8mb4'
}

def get_data(days=100):
    """获取历史数据"""
    conn = pymysql.connect(**DB)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days+50)).strftime('%Y-%m-%d')
    
    sql = f'''
    SELECT d.stock_id, s.code, s.name, d.date, d.open, d.close, d.high, d.low, 
           d.volume, d.amount, d.change_percent, d.turnover_rate
    FROM stock_daily d
    JOIN stock_info s ON d.stock_id = s.id
    WHERE d.date >= '{start_date}'
    AND d.date <= '{end_date}'
    AND s.code NOT LIKE '688%%'  -- 排除科创板
    AND s.name NOT LIKE '%%ST%%'
    AND s.name NOT LIKE '%%*ST%%'
    AND s.name NOT LIKE '%%退%%'
    ORDER BY s.code, d.date
    '''
    
    df = pd.read_sql(sql, conn)
    conn.close()
    
    # 过滤异常数据
    df = df[df['close'] > 0]
    df = df[df['volume'] > 0]
    df = df[df['change_percent'].between(-20, 20) | df['change_percent'].isna()]
    
    return df

def calc_ma(df, periods=[5, 10, 20, 30, 60]):
    """计算均线"""
    result = df.copy()
    for p in periods:
        result[f'ma{p}'] = result.groupby('stock_id')['close'].transform(
            lambda x: x.rolling(p, min_periods=p).mean()
        )
    return result

def calc_macd(df):
    """计算MACD"""
    result = df.copy()
    for stock_id in df['stock_id'].unique():
        stock_data = df[df['stock_id'] == stock_id].copy()
        exp12 = stock_data['close'].ewm(span=12, adjust=False).mean()
        exp26 = stock_data['close'].ewm(span=26, adjust=False).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2
        
        idx = df[df['stock_id'] == stock_id].index
        df.loc[idx, 'dif'] = dif.values
        df.loc[idx, 'dea'] = dea.values
        df.loc[idx, 'macd'] = macd.values
    return df

def strategy_ma_convergence(df):
    """均线粘合策略"""
    df = calc_ma(df)
    
    # 最新数据
    latest = df.groupby('stock_id').last().reset_index()
    
    # 均线粘合：5条均线距离小于5%
    latest['ma_range'] = (
        latest[['ma5', 'ma10', 'ma20', 'ma30', 'ma60']].max(axis=1) - 
        latest[['ma5', 'ma10', 'ma20', 'ma30', 'ma60']].min(axis=1)
    ) / latest['close']
    
    # 粘合且价格在均线之上
    selected = latest[
        (latest['ma_range'] < 0.05) &  # 均线距离小于5%
        (latest['close'] > latest['ma5']) &
        (latest['ma5'] > latest['ma10'])
    ].copy()
    
    selected['strategy'] = '均线粘合'
    return selected[['code', 'name', 'close', 'change_percent', 'strategy']]

def strategy_breakthrough(df):
    """突破策略"""
    df = calc_ma(df)
    
    # 最新数据
    latest = df.groupby('stock_id').last().reset_index()
    
    # 获取前20日最高价
    high20 = df.groupby('stock_id').apply(
        lambda x: x.tail(21).head(20)['high'].max()
    ).reset_index()
    high20.columns = ['stock_id', 'high20']
    latest = latest.merge(high20, on='stock_id')
    
    # 突破：收盘价突破20日高点，成交量放大
    vol5 = df.groupby('stock_id').apply(
        lambda x: x.tail(6).head(5)['volume'].mean()
    ).reset_index()
    vol5.columns = ['stock_id', 'vol5']
    latest = latest.merge(vol5, on='stock_id')
    
    selected = latest[
        (latest['close'] > latest['high20']) &
        (latest['volume'] > latest['vol5'] * 1.5) &
        (latest['change_percent'] > 0)
    ].copy()
    
    selected['strategy'] = '突破'
    return selected[['code', 'name', 'close', 'change_percent', 'volume', 'strategy']]

def strategy_pullback(df):
    """回调买入策略"""
    df = calc_ma(df)
    
    # 获取最近30天数据
    recent = df[df.groupby('stock_id').cumcount() >= df.groupby('stock_id').size() - 30]
    
    # 计算趋势
    results = []
    for stock_id in recent['stock_id'].unique():
        stock = recent[recent['stock_id'] == stock_id].copy()
        if len(stock) < 20:
            continue
        
        latest = stock.iloc[-1]
        prev = stock.iloc[-5:]
        
        # 条件：上升趋势（MA20向上），回调到MA20附近
        ma20_trend = stock['ma20'].iloc[-5:].diff().mean() > 0  # MA20向上
        
        # 价格回调到MA20附近（±3%）
        near_ma20 = abs(latest['close'] - latest['ma20']) / latest['ma20'] < 0.03
        
        # 成交量萎缩
        vol_reduce = latest['volume'] < stock['volume'].iloc[-10:-1].mean()
        
        if ma20_trend and near_ma20 and vol_reduce:
            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'close': latest['close'],
                'change_percent': latest['change_percent'],
                'strategy': '回调买入'
            })
    
    return pd.DataFrame(results)

def strategy_golden_cross(df):
    """金叉策略（MA5上穿MA10）"""
    df = calc_ma(df)
    
    results = []
    for stock_id in df['stock_id'].unique():
        stock = df[df['stock_id'] == stock_id].copy()
        if len(stock) < 15:
            continue
        
        latest = stock.iloc[-1]
        prev = stock.iloc[-2]
        
        # MA5上穿MA10
        cross_up = (prev['ma5'] < prev['ma10']) and (latest['ma5'] > latest['ma10'])
        
        # MACD金叉或即将金叉
        df_macd = calc_macd(stock)
        if 'dif' in df_macd.columns and len(df_macd) >= 2:
            macd_latest = df_macd.iloc[-1]
            macd_prev = df_macd.iloc[-2]
            macd_cross = (macd_prev['dif'] < macd_prev['dea']) and (macd_latest['dif'] > macd_latest['dea'])
        else:
            macd_cross = False
        
        if cross_up:
            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'close': latest['close'],
                'change_percent': latest['change_percent'],
                'strategy': '金叉',
                'macd_cross': macd_cross
            })
    
    return pd.DataFrame(results)

def strategy_volume_price(df):
    """量价齐升策略"""
    df = calc_ma(df)
    
    # 最近3天数据
    results = []
    for stock_id in df['stock_id'].unique():
        stock = df[df['stock_id'] == stock_id].copy()
        if len(stock) < 10:
            continue
        
        latest = stock.iloc[-1]
        prev2 = stock.iloc[-3:]
        
        # 连续3天上涨
        up3 = (prev2['change_percent'] > 0).all()
        
        # 成交量放大
        vol5 = stock['volume'].iloc[-8:-3].mean()
        vol3 = prev2['volume'].mean()
        vol_up = vol3 > vol5 * 1.2
        
        # 价格在MA5之上
        above_ma5 = latest['close'] > latest['ma5']
        
        if up3 and vol_up and above_ma5:
            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'close': latest['close'],
                'change_percent': latest['change_percent'],
                'strategy': '量价齐升'
            })
    
    return pd.DataFrame(results)

def find_resonance(results_list):
    """多策略共振"""
    all_results = pd.concat(results_list, ignore_index=True)
    
    # 统计每只股票被多少策略选中
    resonance = all_results.groupby(['code', 'name', 'close', 'change_percent']).agg({
        'strategy': lambda x: list(x)
    }).reset_index()
    
    resonance['count'] = resonance['strategy'].apply(len)
    resonance = resonance.sort_values('count', ascending=False)
    
    return resonance

def main():
    print('=' * 60)
    print('多策略共振选股')
    print('=' * 60)
    print(f'日期: {datetime.now().strftime("%Y-%m-%d")}')
    print()
    
    # 获取数据
    print('[1] 获取历史数据...')
    df = get_data(days=100)
    print(f'   获取 {len(df):,} 条记录, {df["stock_id"].nunique()} 只股票')
    
    # 执行各策略
    print()
    print('[2] 执行选股策略...')
    
    strategies = [
        ('均线粘合', strategy_ma_convergence),
        ('突破', strategy_breakthrough),
        ('回调买入', strategy_pullback),
        ('金叉', strategy_golden_cross),
        ('量价齐升', strategy_volume_price),
    ]
    
    results = []
    for name, func in strategies:
        try:
            r = func(df.copy())
            if len(r) > 0:
                print(f'   {name}: {len(r)} 只')
                results.append(r)
            else:
                print(f'   {name}: 0 只')
        except Exception as e:
            print(f'   {name}: 错误 - {e}')
    
    # 多策略共振
    print()
    print('[3] 多策略共振分析...')
    
    if results:
        resonance = find_resonance(results)
        
        # 显示结果
        print()
        print('=' * 60)
        print('选股结果')
        print('=' * 60)
        
        # 多策略共振（2个以上策略）
        multi = resonance[resonance['count'] >= 2]
        if len(multi) > 0:
            print()
            print(f'【多策略共振】({len(multi)} 只)')
            for _, row in multi.iterrows():
                strategies_str = ', '.join(row['strategy'])
                print(f'  {row["code"]} {row["name"]}: {row["close"]:.2f}元, {row["change_percent"]:.2f}%')
                print(f'    共振策略: {strategies_str}')
        
        # 单策略结果
        single = resonance[resonance['count'] == 1]
        if len(single) > 0:
            print()
            print(f'【单策略命中】({len(single)} 只，显示前20）')
            for _, row in single.head(20).iterrows():
                print(f'  {row["code"]} {row["name"]}: {row["close"]:.2f}元, {row["change_percent"]:.2f}% [{row["strategy"][0]}]')
        
        print()
        print('=' * 60)
    else:
        print('未找到符合条件的股票')
        print('=' * 60)

if __name__ == '__main__':
    main()