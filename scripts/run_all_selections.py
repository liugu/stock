#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股策略汇总
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'charset': 'utf8mb4'
}

def run_selection():
    conn = pymysql.connect(**DB)
    
    sql = '''
    SELECT s.code, s.name, d.date, d.open, d.close, d.high, d.low, d.volume, d.amount, d.change_percent
    FROM stock_daily d
    JOIN stock_info s ON d.stock_id = s.id
    WHERE d.date >= '2026-05-01' 
    AND (s.code LIKE '60%%' OR s.code LIKE '00%%' OR s.code LIKE '30%%')
    AND s.code NOT LIKE '688%%'
    ORDER BY s.code, d.date
    '''
    df = pd.read_sql(sql, conn)
    conn.close()
    
    print('='*60)
    print('选股策略汇总')
    print('='*60)
    print(f'数据范围: 2026-05-01 至 {df["date"].max()}')
    print(f'股票数: {df.groupby("code").size().shape[0]} 只')
    # 动态获取最新日期
    latest_date = df['date'].max()
    print(f'有{latest_date}数据: {len(df[df["date"]==latest_date])} 条')
    print()
    
    # 各策略结果
    all_results = {}
    
    for code, group in df.groupby('code'):
        if len(group) < 20:
            continue
        
        group = group.sort_values('date')
        latest = group.iloc[-1]
        
        if str(latest['date'])[:10] != str(latest_date):
            continue
        
        close = group['close'].astype(float)
        volume = group['volume'].astype(float)
        high = group['high'].astype(float)
        low = group['low'].astype(float)
        
        # 均线
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(group) >= 60 else ma20
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_val = (dif - dea).iloc[-1]
        dif_val = dif.iloc[-1]
        dea_val = dea.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1] if not loss.iloc[-1] == 0 else 50
        
        # KDJ
        low_min = low.rolling(9).min()
        high_max = high.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        k_series = rsv.ewm(com=2, adjust=False).mean()
        d_series = k_series.ewm(com=2, adjust=False).mean()
        k = k_series.iloc[-1]
        d_val = d_series.iloc[-1]
        
        # 基础数据
        change_pct = float(latest['change_percent']) if latest['change_percent'] else 0
        today_close = float(latest['close'])
        avg_vol = volume.iloc[-6:-1].mean()
        vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0
        
        info = {
            'code': code,
            'name': latest['name'],
            'close': today_close,
            'change_pct': change_pct,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'macd': macd_val,
            'dif': dif_val,
            'dea': dea_val,
            'rsi': rsi,
            'k': k,
            'd': d_val,
            'vol_ratio': vol_ratio
        }
        
        # 策略1: 放量突破 (涨幅>3%, 量比>1.5)
        if change_pct > 3 and vol_ratio > 1.5:
            if '突破' not in all_results:
                all_results['突破'] = []
            all_results['突破'].append(info)
        
        # 策略2: 均线多头 (MA5>MA10>MA20, 股价在MA5上)
        if ma5 > ma10 > ma20 and today_close > ma5:
            if '均线多头' not in all_results:
                all_results['均线多头'] = []
            all_results['均线多头'].append(info)
        
        # 策略3: MACD金叉 (DIF上穿DEA)
        if dif_val > dea_val and dif.iloc[-2] <= dea.iloc[-2]:
            if 'MACD金叉' not in all_results:
                all_results['MACD金叉'] = []
            all_results['MACD金叉'].append(info)
        
        # 策略4: KDJ金叉 (K上穿D, K<50)
        if k > d_val and k < 50 and rsv.iloc[-2] <= d_val:
            if 'KDJ金叉' not in all_results:
                all_results['KDJ金叉'] = []
            all_results['KDJ金叉'].append(info)
        
        # 策略5: 突破60日均线
        if today_close > ma60 and close.iloc[-2] <= ma60:
            if '突破60日线' not in all_results:
                all_results['突破60日线'] = []
            all_results['突破60日线'].append(info)
        
        # 策略6: 低RSI反弹 (RSI<30开始回升)
        prev_rsi = (100 - (100 / (1 + gain.iloc[-2] / loss.iloc[-2]))) if loss.iloc[-2] > 0 else 50
        if rsi > 30 and rsi < 50 and prev_rsi < 30:
            if 'RSI反弹' not in all_results:
                all_results['RSI反弹'] = []
            all_results['RSI反弹'].append(info)
    
    # 输出结果
    for strategy, stocks in all_results.items():
        print('-'*60)
        print(f'【{strategy}】 选出 {len(stocks)} 只')
        print('-'*60)
        stocks.sort(key=lambda x: x['change_pct'], reverse=True)
        for s in stocks[:10]:
            print(f"{s['name']}({s['code']}): {s['close']:.2f}元, +{s['change_pct']:.2f}%, 量比{s['vol_ratio']:.1f}")
        if len(stocks) > 10:
            print(f"... 等 {len(stocks)} 只")
        print()
    
    if not all_results:
        print('未找到符合条件的股票')

if __name__ == '__main__':
    run_selection()