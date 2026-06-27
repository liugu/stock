#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""多策略共振选股回测"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_stock_data():
    """获取股票数据"""
    conn = pymysql.connect(**DB)
    sql = '''
    SELECT s.code, s.name, d.date, d.open, d.close, d.high, d.low, d.volume, d.change_percent
    FROM stock_daily d
    JOIN stock_info s ON d.stock_id = s.id
    WHERE d.date >= '2026-01-01'
    AND (s.code LIKE '60%%' OR s.code LIKE '00%%' OR s.code LIKE '30%%')
    AND s.code NOT LIKE '688%%'
    ORDER BY s.code, d.date
    '''
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

def calculate_indicators(group):
    """计算技术指标"""
    close = group['close'].astype(float)
    volume = group['volume'].astype(float)
    high = group['high'].astype(float)
    low = group['low'].astype(float)
    
    # 均线
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = (dif - dea)
    
    # KDJ
    low_min = low.rolling(9).min()
    high_max = high.rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    
    # 量比
    avg_vol = volume.rolling(5).mean().shift(1)
    vol_ratio = volume / avg_vol
    
    return pd.DataFrame({
        'date': group['date'],
        'close': close,
        'change_pct': group['change_percent'].astype(float),
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'ma60': ma60,
        'dif': dif,
        'dea': dea,
        'macd': macd,
        'k': k,
        'd': d,
        'vol_ratio': vol_ratio
    })

def check_signal(row, prev_row):
    """检查买入信号"""
    score = 0
    signals = []
    
    close = row['close']
    change_pct = row['change_pct']
    vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0
    
    # 1. 均线多头
    if row['ma5'] > row['ma10'] > row['ma20'] and close > row['ma5']:
        score += 2
        signals.append('均线多头')
    
    # 2. 站上60日线
    if close > row['ma60']:
        score += 2
        signals.append('站上60日线')
    
    # 3. MACD金叉
    if row['dif'] > row['dea'] and prev_row['dif'] <= prev_row['dea']:
        score += 3
        signals.append('MACD金叉')
    elif row['dif'] > row['dea'] and row['macd'] > 0:
        score += 1
        signals.append('MACD多头')
    
    # 4. KDJ金叉
    if row['k'] > row['d'] and row['k'] < 80:
        score += 2
        signals.append('KDJ金叉')
    
    # 5. 放量突破
    if change_pct > 3 and vol_ratio > 1.5:
        score += 3
        signals.append('放量突破')
    
    return score, signals

def backtest(df, start_date, end_date, hold_days=5, min_score=10):
    """回测"""
    # 按股票分组计算指标
    all_data = []
    for code, group in df.groupby('code'):
        if len(group) < 60:
            continue
        group = group.sort_values('date')
        indicators = calculate_indicators(group)
        indicators['code'] = code
        indicators['name'] = group['name'].iloc[0]
        all_data.append(indicators)
    
    data = pd.concat(all_data, ignore_index=True)
    
    # 回测期间
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    
    results = []
    total_return = 0
    total_trades = 0
    win_count = 0
    
    for i in range(len(dates) - hold_days):
        buy_date = dates[i].strftime('%Y-%m-%d')
        sell_date = dates[i + hold_days].strftime('%Y-%m-%d')
        
        # 选股
        day_data = data[data['date'] == buy_date].copy()
        selected = []
        
        for idx, row in day_data.iterrows():
            # 获取前一天数据
            prev_data = data[(data['code'] == row['code']) & (data['date'] < buy_date)].tail(1)
            if len(prev_data) == 0:
                continue
            
            prev_row = prev_data.iloc[0]
            score, signals = check_signal(row, prev_row)
            
            if score >= min_score:
                selected.append({
                    'code': row['code'],
                    'name': row['name'],
                    'buy_price': row['close'],
                    'score': score,
                    'signals': signals
                })
        
        if not selected:
            continue
        
        # 买入后持有N天的收益
        for stock in selected[:10]:  # 最多买入10只
            sell_data = data[(data['code'] == stock['code']) & (data['date'] == sell_date)]
            if len(sell_data) == 0:
                continue
            
            sell_price = sell_data.iloc[0]['close']
            ret = (sell_price - stock['buy_price']) / stock['buy_price'] * 100
            
            total_return += ret
            total_trades += 1
            if ret > 0:
                win_count += 1
            
            results.append({
                'buy_date': buy_date,
                'sell_date': sell_date,
                'code': stock['code'],
                'name': stock['name'],
                'buy_price': stock['buy_price'],
                'sell_price': sell_price,
                'return': ret,
                'score': stock['score']
            })
    
    # 统计
    if total_trades > 0:
        avg_return = total_return / total_trades
        win_rate = win_count / total_trades * 100
        
        print('=' * 80)
        print(f'回测期间: {start_date} ~ {end_date}')
        print(f'持有天数: {hold_days}天')
        print(f'最低评分: {min_score}分')
        print('=' * 80)
        print(f'总交易次数: {total_trades}')
        print(f'胜率: {win_rate:.1f}%')
        print(f'平均收益: {avg_return:.2f}%')
        print(f'总收益: {total_return:.2f}%')
        print()
        
        # 最近5笔交易
        print('最近交易记录:')
        print('-' * 80)
        for r in results[-10:]:
            print(f'{r["buy_date"]} 买入 {r["name"]}({r["code"]}) {r["buy_price"]:.2f}元')
            print(f'  -> {r["sell_date"]} 卖出 {r["sell_price"]:.2f}元, 收益{r["return"]:+.2f}%')
    
    return results

if __name__ == '__main__':
    print('加载数据...')
    df = get_stock_data()
    print(f'数据范围: {df["date"].min()} ~ {df["date"].max()}')
    print()
    
    # 回测最近30天
    results = backtest(df, '2026-05-20', '2026-06-20', hold_days=5, min_score=10)
