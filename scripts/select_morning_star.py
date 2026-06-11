#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早晨之星形态选股

早晨之星是底部反转信号：
1. 第一根：长阴线（下跌趋势延续）
2. 第二根：小实体（十字星或小阳/小阴），跳空低开
3. 第三根：长阳线，向上跳空，收盘进入第一根实体内

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

def check_morning_star(df):
    """检查早晨之星形态"""
    if len(df) < 20:
        return False, None
    
    close = df['close'].astype(float).values
    open_p = df['open'].astype(float).values
    high = df['high'].astype(float).values
    low = df['low'].astype(float).values
    volume = df['volume'].astype(float).values
    
    # 取最近15天
    recent_close = close[-15:]
    recent_open = open_p[-15:]
    recent_high = high[-15:]
    recent_low = low[-15:]
    recent_volume = volume[-15:]
    
    # 找早晨之星
    for i in range(len(recent_close) - 3):
        c1, c2, c3 = recent_close[i], recent_close[i+1], recent_close[i+2]
        o1, o2, o3 = recent_open[i], recent_open[i+1], recent_open[i+2]
        h1, h2, h3 = recent_high[i], recent_high[i+1], recent_high[i+2]
        l1, l2, l3 = recent_low[i], recent_low[i+1], recent_low[i+2]
        
        # 第一根：长阴线（实体占比>60%，跌幅>3%）
        body1 = abs(c1 - o1)
        total1 = h1 - l1
        if total1 == 0:
            continue
        
        is_long_bearish = (
            c1 < o1 and  # 阴线
            body1 / total1 > 0.6 and  # 长实体
            (o1 - c1) / o1 > 0.03  # 跌幅>3%
        )
        
        if not is_long_bearish:
            continue
        
        # 第二根：小实体（十字星或小阳/小阴）
        body2 = abs(c2 - o2)
        total2 = h2 - l2
        if total2 == 0:
            continue
        
        is_small_body = body2 / total2 < 0.3  # 小实体
        
        # 跳空低开（理想条件，放宽）
        gap_down = l2 < l1  # 低点低于前一日
        
        if not (is_small_body and gap_down):
            continue
        
        # 第三根：长阳线
        body3 = abs(c3 - o3)
        total3 = h3 - l3
        if total3 == 0:
            continue
        
        is_long_bullish = (
            c3 > o3 and  # 阳线
            body3 / total3 > 0.5 and  # 实体较长
            (c3 - o3) / o3 > 0.02  # 涨幅>2%
        )
        
        if not is_long_bullish:
            continue
        
        # 第三根收盘进入第一根实体内（理想）
        enters_body1 = c3 > c1 and c3 < o1
        # 放宽：至少收盘高于第一根最低点
        above_low1 = c3 > l1
        
        if not above_low1:
            continue
        
        # 成交量确认：第三根放量
        vol_avg = np.mean(recent_volume[:i+1]) if i > 0 else recent_volume[i]
        vol_confirmed = recent_volume[i+2] > vol_avg * 1.2
        
        distance = len(recent_close) - i - 3
        
        details = {
            '早晨之星位置': i,
            '距早晨之星天数': distance,
            '第一日跌幅': round((o1 - c1) / o1 * 100, 2),
            '第三日涨幅': round((c3 - o3) / o3 * 100, 2),
            '理想形态': enters_body1,
            '成交量放大': vol_confirmed,
            '反转幅度': round((c3 - c1) / c1 * 100, 2)
        }
        
        return True, details
    
    return False, None


print('=' * 60)
print('早晨之星形态选股')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

print('[1] 获取历史数据...')
sql = '''
SELECT si.id, si.code, si.name, sd.date, sd.open, sd.close, sd.high, sd.low, sd.volume
FROM stock_info si
INNER JOIN stock_daily sd ON si.id = sd.stock_id
WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
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

print('[3] 筛选早晨之星形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 20:
        continue
    
    group = group.sort_values('date')
    is_morning, details = check_morning_star(group)
    
    if not is_morning:
        continue
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    # 只保留最近5天内形成的早晨之星
    if details['距早晨之星天数'] > 5:
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
    results_df = results_df.sort_values('距早晨之星天数', ascending=True)
    
    best_df = results_df[results_df['理想形态'] & results_df['成交量放大']]
    
    print(f'\n共找到 {len(results_df)} 只早晨之星形态股票')
    print(f'其中 {len(best_df)} 只理想形态+放量\n')
    
    if len(best_df) > 0:
        print('【精选 - 理想形态+放量】')
        print('-' * 60)
        for _, row in best_df.head(10).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   反转幅度: {row["反转幅度"]:.2f}% ({row["距早晨之星天数"]}天前形成)')
            print(f'   第1日跌{row["第一日跌幅"]:.2f}%, 第3日涨{row["第三日涨幅"]:.2f}%')
            print()
    
    if len(best_df) < 10:
        other_df = results_df[~(results_df['理想形态'] & results_df['成交量放大'])]
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 反转幅度: {row["反转幅度"]:.2f}%')
            print()
    
    output_file = f'output/morning_star_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)