#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金蜘蛛形态选股

金蜘蛛是强势买入信号：
1. MA5、MA10、MA20、MA30四条均线在某一点附近同时金叉
2. 均线发散向上
3. 成交量放大确认

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

def check_golden_spider(df):
    """检查金蜘蛛形态"""
    if len(df) < 40:
        return False, None
    
    close = df['close'].astype(float).values
    volume = df['volume'].astype(float).values
    
    ma5 = calculate_ma(close, 5)
    ma10 = calculate_ma(close, 10)
    ma20 = calculate_ma(close, 20)
    ma30 = calculate_ma(close, 30)
    vol_ma5 = calculate_ma(volume, 5)
    
    # 取最近15天
    lookback = min(15, len(df) - 30)
    recent_ma5 = ma5[-lookback:]
    recent_ma10 = ma10[-lookback:]
    recent_ma20 = ma20[-lookback:]
    recent_ma30 = ma30[-lookback:]
    recent_close = close[-lookback:]
    recent_volume = volume[-lookback:]
    recent_vol_ma5 = vol_ma5[-lookback:]
    
    if len(recent_ma5) < 10:
        return False, None
    
    # 找金蜘蛛点：四线交叉汇聚
    spider_idx = None
    
    for i in range(2, len(recent_ma5) - 2):
        # 检查均线是否在狭窄范围内汇聚（差距<2%）
        ma_vals = [recent_ma5[i], recent_ma10[i], recent_ma20[i], recent_ma30[i]]
        max_ma = max(ma_vals)
        min_ma = min(ma_vals)
        
        if max_ma > 0 and (max_ma - min_ma) / max_ma < 0.02:
            # 检查是否从下向上穿越（金叉）
            # MA5应该穿越其他均线
            if recent_ma5[i-1] < recent_ma10[i-1] and recent_ma5[i] > recent_ma10[i]:
                spider_idx = i
                break
    
    if spider_idx is None:
        return False, None
    
    # 检查均线发散向上
    current_idx = len(recent_ma5) - 1
    if spider_idx > current_idx - 3:
        return False, None
    
    # 均线应该向上发散
    ma5_trend = recent_ma5[current_idx] > recent_ma5[spider_idx]
    ma10_trend = recent_ma10[current_idx] > recent_ma10[spider_idx]
    
    if not (ma5_trend and ma10_trend):
        return False, None
    
    # 当前均线排列：MA5 > MA10 > MA20 > MA30
    ma_aligned = (
        recent_ma5[current_idx] > recent_ma10[current_idx] and
        recent_ma10[current_idx] > recent_ma20[current_idx] and
        recent_ma20[current_idx] > recent_ma30[current_idx]
    )
    
    if not ma_aligned:
        return False, None
    
    # 成交量放大
    vol_ratio = recent_volume[current_idx] / recent_vol_ma5[current_idx] if recent_vol_ma5[current_idx] > 0 else 1
    vol_confirmed = vol_ratio >= 1.2
    
    details = {
        '蜘蛛点位置': spider_idx,
        '距蜘蛛点天数': current_idx - spider_idx,
        'MA5': round(recent_ma5[current_idx], 2),
        'MA10': round(recent_ma10[current_idx], 2),
        'MA20': round(recent_ma20[current_idx], 2),
        'MA30': round(recent_ma30[current_idx], 2),
        '均线发散': '向上' if ma5_trend else '平稳',
        '量比': round(vol_ratio, 2),
        '成交量放大': vol_confirmed
    }
    
    return True, details


print('=' * 60)
print('金蜘蛛形态选股')
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

print('[3] 筛选金蜘蛛形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 40:
        continue
    
    group = group.sort_values('date')
    is_spider, details = check_golden_spider(group)
    
    if not is_spider:
        continue
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    # 只保留最近5天内形成金蜘蛛
    if details['距蜘蛛点天数'] > 5:
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
    results_df = results_df.sort_values('距蜘蛛点天数', ascending=True)
    
    # 优先显示放量确认的
    best_df = results_df[results_df['成交量放大']]
    other_df = results_df[~results_df['成交量放大']]
    
    print(f'\n共找到 {len(results_df)} 只金蜘蛛形态股票')
    print(f'其中 {len(best_df)} 只成交量放大确认\n')
    
    if len(best_df) > 0:
        print('【精选 - 成交量放大】')
        print('-' * 60)
        for _, row in best_df.head(10).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   MA5={row["MA5"]:.2f} > MA10={row["MA10"]:.2f} > MA20={row["MA20"]:.2f} > MA30={row["MA30"]:.2f}')
            print(f'   量比: {row["量比"]:.2f}, 金蜘蛛: {row["距蜘蛛点天数"]}天前形成')
            print()
    
    if len(other_df) > 0 and len(best_df) < 10:
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   MA排列已形成, 量比: {row["量比"]:.2f}')
            print()
    
    output_file = f'output/golden_spider_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)