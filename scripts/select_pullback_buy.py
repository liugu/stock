#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回调买入策略

上升趋势中的缩量回调：
1. MA20/MA60向上（上升趋势）
2. 股价回调至MA20附近（距MA20<5%）
3. 回调期间缩量（量比<0.8）
4. MACD仍在多头区域

作者: Hermes
日期: 2026-06-11
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, date

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def calculate_ma(close, period):
    return pd.Series(close).rolling(window=period).mean().values

def calculate_ema(close, period):
    return pd.Series(close).ewm(span=period, adjust=False).mean().values

def calculate_macd(close):
    ema12 = calculate_ema(close, 12)
    ema26 = calculate_ema(close, 26)
    dif = ema12 - ema26
    dea = calculate_ema(dif, 9)
    return dif, dea

def check_pullback(df):
    """检查回调买入形态"""
    if len(df) < 60:
        return False, None
    
    close = df['close'].astype(float).values
    volume = df['volume'].astype(float).values
    
    ma5 = calculate_ma(close, 5)
    ma10 = calculate_ma(close, 10)
    ma20 = calculate_ma(close, 20)
    ma60 = calculate_ma(close, 60)
    vol_ma5 = calculate_ma(volume, 5)
    dif, dea = calculate_macd(close)
    
    # 取最近10天
    recent_close = close[-10:]
    recent_ma5 = ma5[-10:]
    recent_ma10 = ma10[-10:]
    recent_ma20 = ma20[-10:]
    recent_ma60 = ma60[-10:]
    recent_volume = volume[-10:]
    recent_vol_ma5 = vol_ma5[-10:]
    recent_dif = dif[-10:]
    recent_dea = dea[-10:]
    
    current_close = recent_close[-1]
    current_ma20 = recent_ma20[-1]
    current_ma60 = recent_ma60[-1]
    
    # 1. 均线向上（趋势向上）
    ma20_up = recent_ma20[-1] > recent_ma20[-5]  # MA20向上
    ma60_up = recent_ma60[-1] > recent_ma60[-10]  # MA60向上
    
    if not (ma20_up or ma60_up):
        return False, None
    
    # 2. 股价回调至MA20附近（距MA20<5%）
    distance_to_ma20 = (current_close - current_ma20) / current_ma20 * 100
    
    if distance_to_ma20 > 5 or distance_to_ma20 < -3:
        return False, None
    
    # 3. 回调期间缩量
    vol_ratio = recent_volume[-1] / recent_vol_ma5[-1] if recent_vol_ma5[-1] > 0 else 1
    shrink_volume = vol_ratio < 0.8
    
    # 放宽条件：量比<1.0即可
    if vol_ratio >= 1.0:
        return False, None
    
    # 4. MACD仍在多头区域
    macd_bullish = recent_dif[-1] > recent_dea[-1]
    
    # 5. 检查回调幅度（从高点回调）
    high_10 = np.max(recent_close)
    pullback_pct = (high_10 - current_close) / high_10 * 100
    
    # 回调幅度在3%-15%之间
    if pullback_pct < 3 or pullback_pct > 15:
        return False, None
    
    # 6. MA5开始拐头向上（买点信号）
    ma5_turning_up = recent_ma5[-1] > recent_ma5[-2]
    
    details = {
        '距MA20': round(distance_to_ma20, 2),
        '回调幅度': round(pullback_pct, 2),
        '量比': round(vol_ratio, 2),
        '缩量': shrink_volume,
        'MACD多头': macd_bullish,
        'MA20向上': ma20_up,
        'MA60向上': ma60_up,
        'MA5拐头': ma5_turning_up,
        'MA5': round(recent_ma5[-1], 2),
        'MA20': round(current_ma20, 2),
        'MA60': round(current_ma60, 2)
    }
    
    return True, details


print('=' * 60)
print('回调买入策略')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

print('[1] 获取历史数据...')
sql = '''
SELECT si.id, si.code, si.name, sd.date, sd.close, sd.high, sd.low, sd.volume
FROM stock_info si
INNER JOIN stock_daily sd ON si.id = sd.stock_id
WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  AND si.code NOT LIKE '688%%'
  AND sd.close > 0
ORDER BY si.code, sd.date
'''
df = pd.read_sql(sql, conn)
print(f'   获取 {len(df)} 条记录')

print('[2] 获取实时行情...')
sql2 = '''
SELECT code, name, new_price, change_rate, pe, turnoverrate
FROM cn_stock_spot
WHERE date = CURDATE() AND new_price > 0 AND code NOT LIKE '688%%'
'''
spot_df = pd.read_sql(sql2, conn)
print(f'   获取 {len(spot_df)} 只股票')

conn.close()

print('[3] 筛选回调买入形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 60:
        continue
    
    group = group.sort_values('date')
    is_pullback, details = check_pullback(group)
    
    if not is_pullback:
        continue
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    results.append({
        '代码': code,
        '名称': spot_row['name'],
        '最新价': float(spot_row['new_price']),
        '涨跌幅': float(spot_row['change_rate']),
        '市盈率': float(spot_row['pe']) if spot_row['pe'] else None,
        '换手率': float(spot_row['turnoverrate']) if spot_row['turnoverrate'] else None,
        **details
    })

print(f'   筛选出 {len(results)} 只')

print()
print('=' * 60)
print('选股结果')
print('=' * 60)

if results:
    results_df = pd.DataFrame(results)
    
    # 排序：缩量+MA5拐头优先
    results_df['排序权重'] = (
        results_df['缩量'].astype(int) * 100 +
        results_df['MA5拐头'].astype(int) * 50 +
        results_df['MACD多头'].astype(int) * 30 +
        (15 - results_df['回调幅度'])
    )
    results_df = results_df.sort_values('排序权重', ascending=False)
    
    best_df = results_df[results_df['缩量'] & results_df['MA5拐头'] & results_df['MACD多头']]
    
    print(f'\n共找到 {len(results_df)} 只回调买入机会')
    print(f'其中 {len(best_df)} 只缩量+MA5拐头+MACD多头\n')
    
    if len(best_df) > 0:
        print('【精选 - 缩量回调+MA5拐头】')
        print('-' * 60)
        for _, row in best_df.head(15).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   距MA20: {row["距MA20"]:.2f}%, 回调幅度: {row["回调幅度"]:.2f}%')
            print(f'   量比: {row["量比"]:.2f} (缩量), MA5拐头: {"是" if row["MA5拐头"] else "否"}')
            print()
    
    if len(best_df) < 15:
        other_df = results_df[~(results_df['缩量'] & results_df['MA5拐头'] & results_df['MACD多头'])]
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 距MA20: {row["距MA20"]:.2f}%')
            print()
    
    output_file = f'output/pullback_buy_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.drop('排序权重', axis=1).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)