#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老鸭头形态选股（增强版）

老鸭头是经典技术形态：
1. 5日线上穿10日线（鸭嘴张开）
2. 股价回调，5日线下穿10日线（鸭嘴闭合）
3. 60日线保持向上（鸭脖子）
4. 5日线再次上穿10日线（鸭嘴张开，买点信号）

增强条件：
- 成交量确认：金叉时成交量放大
- MACD金叉：DIF上穿DEA确认趋势

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

def calculate_ema(close, period):
    """计算EMA"""
    return pd.Series(close).ewm(span=period, adjust=False).mean().values

def calculate_macd(close):
    """计算MACD"""
    ema12 = calculate_ema(close, 12)
    ema26 = calculate_ema(close, 26)
    dif = ema12 - ema26
    dea = calculate_ema(dif, 9)
    macd = (dif - dea) * 2
    return dif, dea, macd

def calculate_volume_ma(volume, period):
    """计算成交量均线"""
    return pd.Series(volume).rolling(window=period).mean().values

def check_old_duck_head(df):
    """
    检查老鸭头形态（增强版：成交量+MACD确认）
    
    返回: (是否形成, 形态详情)
    """
    if len(df) < 60:
        return False, None
    
    # 计算均线
    close = df['close'].astype(float).values
    volume = df['volume'].astype(float).values
    ma5 = calculate_ma(close, 5)
    ma10 = calculate_ma(close, 10)
    ma60 = calculate_ma(close, 60)
    
    # 计算MACD
    dif, dea, macd = calculate_macd(close)
    
    # 计算成交量均线
    vol_ma5 = calculate_volume_ma(volume, 5)
    vol_ma10 = calculate_volume_ma(volume, 10)
    
    # 取最近30天分析
    lookback = min(30, len(df) - 60)
    recent_ma5 = ma5[-lookback:]
    recent_ma10 = ma10[-lookback:]
    recent_ma60 = ma60[-lookback:]
    recent_close = close[-lookback:]
    recent_volume = volume[-lookback:]
    recent_vol_ma5 = vol_ma5[-lookback:]
    recent_dif = dif[-lookback:]
    recent_dea = dea[-lookback:]
    
    if len(recent_ma5) < 20:
        return False, None
    
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
    
    # 检查60日线趋势
    ma60_before = recent_ma60[dead_cross_idx]
    ma60_now = recent_ma60[golden_cross_idx]
    
    if ma60_now < ma60_before * 0.98:
        return False, None
    
    # 检查回调幅度
    high_between = np.max(recent_close[first_golden_idx:dead_cross_idx])
    low_at_dead = recent_close[dead_cross_idx]
    pullback_pct = (high_between - low_at_dead) / high_between * 100
    
    if pullback_pct > 20:
        return False, None
    
    # === 成交量确认 ===
    # 金叉当日成交量应该放大（超过5日均量的1.2倍）
    vol_at_golden = recent_volume[golden_cross_idx]
    vol_ma5_at_golden = recent_vol_ma5[golden_cross_idx]
    
    if vol_ma5_at_golden > 0:
        vol_ratio = vol_at_golden / vol_ma5_at_golden
    else:
        vol_ratio = 1.0
    
    # 放量确认（可选，放宽到1.0倍）
    vol_confirmed = vol_ratio >= 1.0
    
    # === MACD确认 ===
    # 检查MACD是否金叉或即将金叉
    dif_at_golden = recent_dif[golden_cross_idx]
    dea_at_golden = recent_dea[golden_cross_idx]
    dif_now = recent_dif[-1]
    dea_now = recent_dea[-1]
    
    # MACD金叉：DIF > DEA 且 DIF向上
    macd_golden = False
    macd_trend = '弱势'
    
    if len(recent_dif) > golden_cross_idx + 3:
        # 检查金叉后是否有MACD金叉
        for i in range(golden_cross_idx, len(recent_dif) - 1):
            if recent_dif[i] <= recent_dea[i] and recent_dif[i+1] > recent_dea[i+1]:
                macd_golden = True
                macd_trend = '金叉确认'
                break
    
    # 当前MACD状态
    if dif_now > dea_now and dif_now > recent_dif[-2]:
        macd_trend = '多头向上'
        macd_golden = True  # 当前已是多头状态也算确认
    elif dif_now > dea_now:
        macd_trend = '多头'
        macd_golden = True
    elif dif_now > recent_dif[-3]:  # DIF开始向上
        macd_trend = '拐头向上'
    
    # 形态确认
    current_close = recent_close[-1]
    current_ma5 = recent_ma5[-1]
    current_ma10 = recent_ma10[-1]
    
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
        '距买点天数': len(recent_ma5) - golden_cross_idx - 1,
        # 成交量
        '成交量放大': vol_confirmed,
        '量比': round(vol_ratio, 2),
        # MACD
        'MACD金叉': macd_golden,
        'MACD趋势': macd_trend,
        'DIF': round(dif_now, 3),
        'DEA': round(dea_now, 3)
    }
    
    return True, details


print('=' * 60)
print('老鸭头形态选股（增强版：成交量+MACD确认）')
print('=' * 60)
print(f'日期: {date.today()}')
print()

conn = pymysql.connect(**DB)

# 1. 获取历史数据（包含成交量）
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
print('[3] 筛选老鸭头形态（成交量+MACD确认）...')

results = []
stats = {'形态': 0, '放量': 0, 'MACD': 0, '全部': 0}

for code, group in df.groupby('code'):
    if len(group) < 60:
        continue
    
    group = group.sort_values('date')
    
    is_duck, details = check_old_duck_head(group)
    
    if not is_duck:
        continue
    
    stats['形态'] += 1
    
    spot_row = spot_df[spot_df['code'] == code]
    if spot_row.empty:
        continue
    
    spot_row = spot_row.iloc[0]
    
    if details['距买点天数'] > 5:
        continue
    
    # 记录符合条件的数量
    if details['成交量放大']:
        stats['放量'] += 1
    if details['MACD金叉']:
        stats['MACD'] += 1
    if details['成交量放大'] and details['MACD金叉']:
        stats['全部'] += 1
    
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
        '距买点天数': details['距买点天数'],
        # 成交量
        '量比': details['量比'],
        '成交量放大': details['成交量放大'],
        # MACD
        'MACD趋势': details['MACD趋势'],
        'MACD金叉': details['MACD金叉'],
        'DIF': details['DIF'],
        'DEA': details['DEA']
    })

print(f'   形态符合: {stats["形态"]} 只')
print(f'   成交量放大: {stats["放量"]} 只')
print(f'   MACD金叉: {stats["MACD"]} 只')
print(f'   全部符合: {stats["全部"]} 只')

# 4. 输出结果
print()
print('=' * 60)
print('选股结果')
print('=' * 60)

if results:
    results_df = pd.DataFrame(results)
    
    # 优先排序：成交量放大 + MACD金叉 + 距买点天数
    results_df['排序权重'] = (
        results_df['成交量放大'].astype(int) * 100 +
        results_df['MACD金叉'].astype(int) * 50 +
        (5 - results_df['距买点天数'])
    )
    results_df = results_df.sort_values('排序权重', ascending=False)
    
    # 显示全部符合条件的
    best_df = results_df[results_df['成交量放大'] & results_df['MACD金叉']]
    
    print(f'\n共找到 {len(results_df)} 只老鸭头形态股票')
    print(f'其中 {len(best_df)} 只同时满足成交量放大+MACD金叉\n')
    
    if len(best_df) > 0:
        print('【精选推荐 - 成交量放大 + MACD金叉】')
        print('-' * 60)
        for _, row in best_df.head(15).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   MA5={row["MA5"]:.2f} > MA10={row["MA10"]:.2f} > MA60={row["MA60"]:.2f}')
            print(f'   量比: {row["量比"]:.2f} (放量), MACD: {row["MACD趋势"]}')
            print(f'   买点信号: {row["距买点天数"]}天前出现')
            print()
    
    # 显示其他符合条件的
    other_df = results_df[~(results_df['成交量放大'] & results_df['MACD金叉'])]
    if len(other_df) > 0:
        print()
        print('【其他候选】')
        print('-' * 60)
        for _, row in other_df.head(10).iterrows():
            pe_str = f'{row["市盈率"]:.1f}' if row['市盈率'] else '无'
            vol_str = '放量' if row['成交量放大'] else '缩量'
            macd_str = '金叉' if row['MACD金叉'] else row['MACD趋势']
            print(f'【{row["名称"]}】{row["代码"]}')
            print(f'   价格: {row["最新价"]:.2f}元, 涨跌: {row["涨跌幅"]:.2f}%, PE: {pe_str}')
            print(f'   量比: {row["量比"]:.2f} ({vol_str}), MACD: {macd_str}')
            print(f'   买点信号: {row["距买点天数"]}天前出现')
            print()
    
    # 保存全部结果
    output_file = f'output/old_duck_head_enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    os.makedirs('output', exist_ok=True)
    results_df.drop('排序权重', axis=1).to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
else:
    print('\n未找到符合条件的股票')

print('=' * 60)