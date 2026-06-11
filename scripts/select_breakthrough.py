#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
突破选股策略

放量突破前期高点：
1. 突破20日/60日前高
2. 成交量放大（量比>1.5）
3. 突破幅度>3%
4. MACD多头确认

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

def check_breakthrough(df):
    """检查突破形态"""
    if len(df) < 60:
        return False, None
    
    close = df['close'].astype(float).values
    high = df['high'].astype(float).values
    volume = df['volume'].astype(float).values
    
    # 计算MACD
    dif, dea = calculate_macd(close)
    
    # 计算成交量均线
    vol_ma5 = calculate_ma(volume, 5)
    vol_ma10 = calculate_ma(volume, 10)
    
    # 取最近5天和前60天对比
    recent_close = close[-5:]
    recent_high = high[-5:]
    recent_volume = volume[-5:]
    recent_vol_ma5 = vol_ma5[-5:]
    recent_dif = dif[-5:]
    recent_dea = dea[-5:]
    
    # 前60天的高点（排除最近5天）
    history_high = np.max(high[-60:-5])
    history_high_20 = np.max(high[-25:-5])
    
    # 当前价格
    current_close = recent_close[-1]
    current_high = recent_high[-1]
    
    # 检查突破
    # 1. 突破20日高点
    break_20 = current_close > history_high_20
    # 2. 突破60日高点
    break_60 = current_close > history_high
    
    if not (break_20 or break_60):
        return False, None
    
    # 突破幅度
    if break_60:
        break_level = history_high
        break_type = '60日'
    else:
        break_level = history_high_20
        break_type = '20日'
    
    break_pct = (current_close - break_level) / break_level * 100
    
    if break_pct < 1:  # 突破幅度不足
        return False, None
    
    # 成交量放大
    vol_ratio = recent_volume[-1] / recent_vol_ma5[-1] if recent_vol_ma5[-1] > 0 else 1
    vol_confirmed = vol_ratio >= 1.5
    
    # MACD多头
    macd_bullish = recent_dif[-1] > recent_dea[-1] and recent_dif[-1] > recent_dif[-2]
    
    # 检查是否有效突破（收盘价站稳）
    stable_break = current_close > break_level * 1.01  # 站稳1%以上
    
    details = {
        '突破类型': break_type,
        '突破幅度': round(break_pct, 2),
        '突破价位': round(break_level, 2),
        '量比': round(vol_ratio, 2),
        '成交量放大': vol_confirmed,
        'MACD多头': macd_bullish,
        '有效突破': stable_break
    }
    
    return True, details


print('=' * 60)
print('突破选股策略')
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

print('[3] 筛选突破形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 60:
        continue
    
    group = group.sort_values('date')
    is_break, details = check_breakthrough(group)
    
    if not is_break:
        continue
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    # 只保留突破幅度>2%的
    if details['突破幅度'] < 2:
        continue
    
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
    
    # 排序：60日突破优先，放量+MACD确认优先
    results_df['排序权重'] = (
        (results_df['突破类型'] == '60日').astype(int) * 200 +
        results_df['成交量放大'].astype(int) * 50 +
        results_df['MACD多头'].astype(int) * 30 +
        results_df['突破幅度']
    )
    results_df = results_df.sort_values('排序权重', ascending=False)
    
    best_df = results_df[results_df['成交量放大'] & results_df['MACD多头']]
    
    print(f'\n共找到 {len(results_df)} 只突破股票')
    print(f'其中 {len(best_df)} 只放量+MACD确认\n')
    
    # 分开显示60日和20日突破
    break_60 = results_df[results_df['突破类型'] == '60日']
    break_20 = results_df[results_df['突破类型'] == '20日']
    
    if len(break_60) > 0:
        print('【60日新高突破】')
        print('-' * 60)
        for _, row in break_60.head(10).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            vol_str = '放量' if row['成交量放大'] else '缩量'
            macd_str = '多头' if row['MACD多头'] else '弱势'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   突破幅度: {row["突破幅度"]:.2f}%, 突破价位: {row["突破价位"]:.2f}元')
            print(f'   量比: {row["量比"]:.2f} ({vol_str}), MACD: {macd_str}')
            print()
    
    if len(break_20) > 0 and len(break_60) < 10:
        print('【20日新高突破】')
        print('-' * 60)
        for _, row in break_20.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 突破幅度: {row["突破幅度"]:.2f}%')
            print()
    
    output_file = f'output/breakthrough_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.drop('排序权重', axis=1).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)