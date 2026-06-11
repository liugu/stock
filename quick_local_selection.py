#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速选股 - 单次查询获取所有数据，内存筛选

策略：连续小阳线 + 低位
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

print('=' * 60)
print('快速选股 - 连续小阳线 + 低位')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

# 1. 获取所有股票最近30天数据（单次查询）
print('[1] 获取历史数据...')
sql = '''
SELECT si.id, si.code, si.name, sd.date, sd.open, sd.close, sd.high, sd.low, sd.change_percent
FROM stock_info si
INNER JOIN stock_daily sd ON si.id = sd.stock_id
WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  AND si.code NOT LIKE '688%%'
  AND sd.close > 0
ORDER BY si.code, sd.date
'''
df = pd.read_sql(sql, conn)
print(f'   获取 {len(df)} 条记录')

# 2. 获取实时行情（PE、换手率）
print('[2] 获取实时行情...')
sql2 = '''
SELECT code, name, new_price, change_rate, pe, turnoverrate
FROM cn_stock_spot
WHERE date = CURDATE() AND new_price > 0 AND code NOT LIKE '688%%'
'''
spot_df = pd.read_sql(sql2, conn)
print(f'   获取 {len(spot_df)} 只股票')

conn.close()

# 3. 内存筛选
print('[3] 筛选连续小阳线...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 10:
        continue
    
    # 按日期排序
    group = group.sort_values('date')
    
    # 取最近5天
    recent = group.tail(5)
    
    if len(recent) < 5:
        continue
    
    # 检查连续阳线
    all_bullish = True
    changes = []
    
    for _, row in recent.iterrows():
        open_p = float(row['open'])
        close_p = float(row['close'])
        
        if close_p <= open_p:  # 不是阳线
            all_bullish = False
            break
        
        change = (close_p - open_p) / open_p * 100
        if change < 0.5 or change > 6:  # 涨幅不在范围
            all_bullish = False
            break
        changes.append(change)
    
    if not all_bullish:
        continue
    
    # 检查低位（价格分位数 < 30%）
    closes = group['close'].astype(float).values
    current_close = float(recent.iloc[-1]['close'])
    
    price_pct = np.sum(closes <= current_close) / len(closes) * 100
    
    if price_pct > 30:  # 不是低位
        continue
    
    # 获取实时数据
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
        '连续阳线': len(changes),
        '平均涨幅': round(np.mean(changes), 2),
        '价格分位': round(price_pct, 1),
        '期间最低': round(float(group['low'].min()), 2),
        '期间最高': round(float(group['high'].max()), 2)
    })

print(f'   筛选出 {len(results)} 只')

# 4. 输出结果
print()
print('=' * 60)
print('选股结果')
print('=' * 60)

if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('价格分位', ascending=True)
    
    for i, row in results_df.head(15).iterrows():
        pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
        print(f'【{row["名称"]}】{row["代码"]}')
        print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
        print(f'   连续阳线: {row["连续阳线"]}天, 平均涨幅: {row["平均涨幅"]:.2f}%')
        print(f'   价格分位: {row["价格分位"]}% (低位), 换手率: {row["换手率"]:.2f}%')
        print()
    
    # 保存
    output_file = f'output/selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('未找到符合条件的股票')

print('=' * 60)