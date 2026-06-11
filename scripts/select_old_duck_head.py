#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老鸭头形态选股

老鸭头是经典技术形态：
1. 5日线上穿10日线（鸭嘴张开）
2. 股价回调，5日线下穿10日线（鸭嘴闭合）
3. 60日线保持向上（鸭脖子）
4. 5日线再次上穿10日线（鸭嘴张开，买点信号）

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
    """计算均线"""
    return pd.Series(close).rolling(window=period).mean().values

def check_old_duck_head(df):
    """
    检查老鸭头形态
    
    返回: (是否形成, 形态详情)
    """
    if len(df) < 60:
        return False, None
    
    # 计算均线
    close = df['close'].astype(float).values
    ma5 = calculate_ma(close, 5)
    ma10 = calculate_ma(close, 10)
    ma60 = calculate_ma(close, 60)
    
    # 取最近30天分析
    lookback = min(30, len(df) - 60)
    recent_ma5 = ma5[-lookback:]
    recent_ma10 = ma10[-lookback:]
    recent_ma60 = ma60[-lookback:]
    recent_close = close[-lookback:]
    
    if len(recent_ma5) < 20:
        return False, None
    
    # 检查条件
    # 1. 之前有5日线上穿10日线（鸭嘴张开）
    # 2. 之后5日线下穿10日线（鸭嘴闭合）
    # 3. 60日线保持向上或平稳
    # 4. 最近5日线再次上穿10日线（买点）
    
    # 找最近的金叉（买点）
    golden_cross_idx = None
    for i in range(len(recent_ma5) - 1, 2, -1):
        if recent_ma5[i-1] <= recent_ma10[i-1] and recent_ma5[i] > recent_ma10[i]:
            golden_cross_idx = i
            break
    
    if golden_cross_idx is None or golden_cross_idx < 5:
        return False, None
    
    # 找之前的死叉（鸭嘴闭合）
    dead_cross_idx = None
    for i in range(golden_cross_idx - 1, 2, -1):
        if recent_ma5[i-1] >= recent_ma10[i-1] and recent_ma5[i] < recent_ma10[i]:
            dead_cross_idx = i
            break
    
    if dead_cross_idx is None:
        return False, None
    
    # 找最初的金叉（鸭嘴张开）
    first_golden_idx = None
    for i in range(dead_cross_idx - 1, 2, -1):
        if recent_ma5[i-1] <= recent_ma10[i-1] and recent_ma5[i] > recent_ma10[i]:
            first_golden_idx = i
            break
    
    if first_golden_idx is None:
        return False, None
    
    # 检查60日线趋势（鸭脖子向上）
    # 在死叉到金叉期间，60日线应该向上或平稳
    ma60_before = recent_ma60[dead_cross_idx]
    ma60_now = recent_ma60[golden_cross_idx]
    
    if ma60_now < ma60_before * 0.98:  # 60日线下跌超过2%，不符合
        return False, None
    
    # 检查回调幅度（鸭头高度）
    # 从第一次金叉到死叉期间的最高价，到死叉时最低价
    high_between = np.max(recent_close[first_golden_idx:dead_cross_idx])
    low_at_dead = recent_close[dead_cross_idx]
    
    pullback_pct = (high_between - low_at_dead) / high_between * 100
    
    if pullback_pct > 20:  # 回调超过20%，太深
        return False, None
    
    # 检查当前价格是否突破
    current_close = recent_close[-1]
    current_ma5 = recent_ma5[-1]
    current_ma10 = recent_ma10[-1]
    
    # 形态确认
    details = {
        '鸭嘴张开位置': first_golden_idx,
        '鸭嘴闭合位置': dead_cross_idx,
        '买点位置': golden_cross_idx,
        '回调幅度': round(pullback_pct, 2),
        '60日线趋势': '向上' if ma60_now > ma60_before else '平稳',
        '当前价': round(current_close, 2),
        'MA5': round(current_ma5, 2),
        'MA10': round(current_ma10, 2),
        'MA60': round(recent_ma60[-1], 2),
        '距买点天数': len(recent_ma5) - golden_cross_idx - 1
    }
    
    return True, details


print('=' * 60)
print('老鸭头形态选股')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

# 1. 获取历史数据
print('[1] 获取历史数据...')
sql = '''
SELECT si.id, si.code, si.name, sd.date, sd.close, sd.high, sd.low
FROM stock_info si
INNER JOIN stock_daily sd ON si.id = sd.stock_id
WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  AND si.code NOT LIKE '688%%'
  AND sd.close > 0
ORDER BY si.code, sd.date
'''
df = pd.read_sql(sql, conn)
print(f'   获取 {len(df)} 条记录')

# 2. 获取实时行情
print('[2] 获取实时行情...')
sql2 = '''
SELECT code, name, new_price, change_rate, pe, turnoverrate
FROM cn_stock_spot
WHERE date = CURDATE() AND new_price > 0 AND code NOT LIKE '688%%'
'''
spot_df = pd.read_sql(sql2, conn)
print(f'   获取 {len(spot_df)} 只股票')

conn.close()

# 3. 筛选老鸭头形态
print('[3] 筛选老鸭头形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 60:
        continue
    
    # 按日期排序
    group = group.sort_values('date')
    
    # 检查老鸭头形态
    is_duck, details = check_old_duck_head(group)
    
    if not is_duck:
        continue
    
    # 获取实时数据
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    # 只保留买点刚出现（距买点不超过5天）
    if details['距买点天数'] > 5:
        continue
    
    results.append({
        '代码': code,
        '名称': spot_row['name'],
        '最新价': float(spot_row['new_price']),
        '涨跌幅': float(spot_row['change_rate']),
        '市盈率': float(spot_row['pe']) if spot_row['pe'] else None,
        '换手率': float(spot_row['turnoverrate']) if spot_row['turnoverrate'] else None,
        'MA5': details['MA5'],
        'MA10': details['MA10'],
        'MA60': details['MA60'],
        '回调幅度': details['回调幅度'],
        '60日线趋势': details['60日线趋势'],
        '距买点天数': details['距买点天数']
    })

print(f'   筛选出 {len(results)} 只')

# 4. 输出结果
print()
print('=' * 60)
print('选股结果')
print('=' * 60)

if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('距买点天数', ascending=True)
    
    print(f'\n共找到 {len(results_df)} 只老鸭头形态股票\n')
    
    for _, row in results_df.head(20).iterrows():
        pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
        print(f'【{row["名称"]}】{row["代码"]}')
        print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
        print(f'   MA5={row["MA5"]:.2f} > MA10={row["MA10"]:.2f} > MA60={row["MA60"]:.2f}')
        print(f'   回调幅度: {row["回调幅度"]:.1f}%, 60日线: {row["60日线趋势"]}')
        print(f'   买点信号: {row["距买点天数"]}天前出现')
        print()
    
    # 保存
    output_file = f'output/old_duck_head_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)