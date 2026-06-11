#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
均线粘合选股策略

均线粘合后发散：
1. MA5/MA10/MA20/MA30四线粘合（差距<3%）
2. 粘合后开始发散
3. 成交量放大确认
4. MACD金叉配合

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

def check_ma_convergence(df):
    """检查均线粘合形态"""
    if len(df) < 40:
        return False, None
    
    close = df['close'].astype(float).values
    volume = df['volume'].astype(float).values
    
    ma5 = calculate_ma(close, 5)
    ma10 = calculate_ma(close, 10)
    ma20 = calculate_ma(close, 20)
    ma30 = calculate_ma(close, 30)
    vol_ma5 = calculate_ma(volume, 5)
    dif, dea = calculate_macd(close)
    
    # 取最近20天
    lookback = min(20, len(df) - 30)
    recent_ma5 = ma5[-lookback:]
    recent_ma10 = ma10[-lookback:]
    recent_ma20 = ma20[-lookback:]
    recent_ma30 = ma30[-lookback:]
    recent_close = close[-lookback:]
    recent_volume = volume[-lookback:]
    recent_vol_ma5 = vol_ma5[-lookback:]
    recent_dif = dif[-lookback:]
    recent_dea = dea[-lookback:]
    
    # 找粘合点
    convergence_idx = None
    min_spread = 999
    
    for i in range(2, len(recent_ma5) - 3):
        ma_vals = [recent_ma5[i], recent_ma10[i], recent_ma20[i], recent_ma30[i]]
        max_ma = max(ma_vals)
        min_ma = min(ma_vals)
        
        if max_ma > 0:
            spread = (max_ma - min_ma) / max_ma * 100
            if spread < min_spread:
                min_spread = spread
                if spread < 3:  # 粘合度<3%
                    convergence_idx = i
    
    if convergence_idx is None:
        return False, None
    
    # 检查当前是否开始发散
    current_idx = len(recent_ma5) - 1
    distance = current_idx - convergence_idx
    
    if distance > 5:  # 粘合太久
        return False, None
    
    # 均线发散：MA5向上穿越
    diverging = (
        recent_ma5[current_idx] > recent_ma10[current_idx] and
        recent_ma10[current_idx] > recent_ma20[current_idx]
    )
    
    # 或者刚刚开始发散
    just_starting = (
        recent_ma5[current_idx] > recent_ma5[convergence_idx] * 1.02 and
        recent_ma5[current_idx-1] > recent_ma5[current_idx-2]
    )
    
    if not (diverging or just_starting):
        return False, None
    
    # 成交量放大
    vol_ratio = recent_volume[current_idx] / recent_vol_ma5[current_idx] if recent_vol_ma5[current_idx] > 0 else 1
    vol_confirmed = vol_ratio >= 1.3
    
    # MACD金叉
    macd_golden = recent_dif[current_idx] > recent_dea[current_idx]
    
    # 价格突破
    price_breakout = recent_close[current_idx] > max(recent_close[convergence_idx:current_idx])
    
    details = {
        '粘合位置': convergence_idx,
        '粘合度': round(min_spread, 2),
        '距粘合天数': distance,
        '均线发散': diverging,
        '量比': round(vol_ratio, 2),
        '成交量放大': vol_confirmed,
        'MACD金叉': macd_golden,
        '价格突破': price_breakout,
        'MA5': round(recent_ma5[current_idx], 2),
        'MA10': round(recent_ma10[current_idx], 2),
        'MA20': round(recent_ma20[current_idx], 2),
        'MA30': round(recent_ma30[current_idx], 2)
    }
    
    return True, details


print('=' * 60)
print('均线粘合选股策略')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

print('[1] 获取历史数据...')
sql = '''
SELECT si.id, si.code, si.name, sd.date, sd.close, sd.high, sd.low, sd.volume
FROM stock_info si
INNER JOIN stock_daily sd ON si.id = sd.stock_id
WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
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

print('[3] 筛选均线粘合形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 40:
        continue
    
    group = group.sort_values('date')
    is_converge, details = check_ma_convergence(group)
    
    if not is_converge:
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
    
    # 排序：放量+MACD金叉+价格突破优先
    results_df['排序权重'] = (
        results_df['成交量放大'].astype(int) * 100 +
        results_df['MACD金叉'].astype(int) * 50 +
        results_df['价格突破'].astype(int) * 30 +
        (5 - results_df['距粘合天数'])
    )
    results_df = results_df.sort_values('排序权重', ascending=False)
    
    best_df = results_df[results_df['成交量放大'] & results_df['MACD金叉'] & results_df['价格突破']]
    
    print(f'\n共找到 {len(results_df)} 只均线粘合股票')
    print(f'其中 {len(best_df)} 只放量+MACD金叉+价格突破\n')
    
    if len(best_df) > 0:
        print('【精选 - 放量突破】')
        print('-' * 60)
        for _, row in best_df.head(15).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   粘合度: {row["粘合度"]:.2f}%, {row["距粘合天数"]}天前粘合后发散')
            print(f'   MA5={row["MA5"]:.2f} > MA10={row["MA10"]:.2f} > MA20={row["MA20"]:.2f}')
            print(f'   量比: {row["量比"]:.2f} (放量), MACD: {"金叉" if row["MACD金叉"] else "弱势"}')
            print()
    
    if len(best_df) < 15:
        other_df = results_df[~(results_df['成交量放大'] & results_df['MACD金叉'] & results_df['价格突破'])]
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 粘合度: {row["粘合度"]:.2f}%')
            print()
    
    output_file = f'output/ma_convergence_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.drop('排序权重', axis=1).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)