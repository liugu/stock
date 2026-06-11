#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红三兵形态选股

红三兵是底部反转信号：
1. 连续三根阳线
2. 每日收盘价逐步抬高
3. 每日开盘价在前一日实体内
4. 成交量温和放大

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

def check_red_three_soldiers(df):
    """检查红三兵形态"""
    if len(df) < 20:
        return False, None
    
    close = df['close'].astype(float).values
    open_p = df['open'].astype(float).values
    high = df['high'].astype(float).values
    low = df['low'].astype(float).values
    volume = df['volume'].astype(float).values
    
    # 取最近10天
    recent_close = close[-10:]
    recent_open = open_p[-10:]
    recent_high = high[-10:]
    recent_low = low[-10:]
    recent_volume = volume[-10:]
    
    # 找连续三根阳线
    for i in range(len(recent_close) - 3):
        # 检查三根阳线
        c1, c2, c3 = recent_close[i], recent_close[i+1], recent_close[i+2]
        o1, o2, o3 = recent_open[i], recent_open[i+1], recent_open[i+2]
        
        # 都是阳线
        if not (c1 > o1 and c2 > o2 and c3 > o3):
            continue
        
        # 收盘价逐步抬高
        if not (c3 > c2 > c1):
            continue
        
        # 开盘价在前一日实体内（理想形态）
        # 第二天开盘在第一天实体内
        in_body2 = o2 >= o1 and o2 <= c1
        # 第三天开盘在第二天实体内
        in_body3 = o3 >= o2 and o3 <= c2
        
        # 放宽条件：至少开盘价不低于前一日最低价
        if o2 < recent_low[i] or o3 < recent_low[i+1]:
            continue
        
        # 成交量温和放大（不是剧烈放大）
        v1, v2, v3 = recent_volume[i], recent_volume[i+1], recent_volume[i+2]
        vol_avg = np.mean(recent_volume[:i+1]) if i > 0 else v1
        
        # 成交量应该温和增加
        vol_ok = v3 >= v2 * 0.8 and v3 <= v2 * 2.5
        
        # 涨幅适中（每根阳线涨幅1-5%）
        ch1 = (c1 - o1) / o1 * 100
        ch2 = (c2 - o2) / o2 * 100
        ch3 = (c3 - o3) / o3 * 100
        
        moderate_change = all(1 <= ch <= 5 for ch in [ch1, ch2, ch3])
        
        # 计算当前位置距离红三兵的天数
        distance = len(recent_close) - i - 3
        
        details = {
            '红三兵位置': i,
            '距红三兵天数': distance,
            '三日涨幅': round((c3 - o1) / o1 * 100, 2),
            '理想形态': in_body2 and in_body3,
            '涨幅适中': moderate_change,
            '成交量配合': vol_ok,
            '第一日涨幅': round(ch1, 2),
            '第二日涨幅': round(ch2, 2),
            '第三日涨幅': round(ch3, 2)
        }
        
        return True, details
    
    return False, None


print('=' * 60)
print('红三兵形态选股')
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

print('[3] 筛选红三兵形态...')

results = []

for code, group in df.groupby('code'):
    if len(group) < 20:
        continue
    
    group = group.sort_values('date')
    is_red, details = check_red_three_soldiers(group)
    
    if not is_red:
        continue
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    # 只保留最近3天内形成的红三兵
    if details['距红三兵天数'] > 3:
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
    
    # 排序：理想形态优先
    results_df['排序权重'] = (
        results_df['理想形态'].astype(int) * 100 +
        results_df['涨幅适中'].astype(int) * 50 +
        results_df['成交量配合'].astype(int) * 30 +
        (3 - results_df['距红三兵天数'])
    )
    results_df = results_df.sort_values('排序权重', ascending=False)
    
    best_df = results_df[results_df['理想形态'] & results_df['涨幅适中']]
    
    print(f'\n共找到 {len(results_df)} 只红三兵形态股票')
    print(f'其中 {len(best_df)} 只理想形态\n')
    
    if len(best_df) > 0:
        print('【精选 - 理想形态】')
        print('-' * 60)
        for _, row in best_df.head(10).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   三日涨幅: {row["三日涨幅"]:.2f}% ({row["距红三兵天数"]}天前形成)')
            print(f'   第1日: {row["第一日涨幅"]:.2f}%, 第2日: {row["第二日涨幅"]:.2f}%, 第3日: {row["第三日涨幅"]:.2f}%')
            print()
    
    if len(best_df) < 10:
        other_df = results_df[~results_df['理想形态'] | ~results_df['涨幅适中']]
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(5).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 三日涨幅: {row["三日涨幅"]:.2f}%')
            print()
    
    output_file = f'output/red_three_soldiers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.drop('排序权重', axis=1).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)