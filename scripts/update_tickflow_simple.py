#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简化版更新脚本 - 带超时保护"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import time
from datetime import date
from tickflow import TickFlow

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def convert_code_to_symbol(code):
    if code.startswith('6'):
        return f'{code}.SH'
    elif code.startswith('0') or code.startswith('3'):
        return f'{code}.SZ'
    return None

def safe_float(val):
    try:
        if val is None:
            return 0.0
        import pandas as pd
        import numpy as np
        if pd.isna(val):
            return 0.0
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except:
        return 0.0

print('=' * 60)
print('TickFlow 数据更新（简化版）')
print('=' * 60)

tf = TickFlow.free()

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取股票列表
cursor.execute('''
    SELECT id, code, name FROM stock_info 
    WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
    ORDER BY code
    LIMIT 100
''')
stocks = cursor.fetchall()

# 过滤已更新的
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = "2026-06-26"')
existing = set(row[0] for row in cursor.fetchall())
to_update = [s for s in stocks if s[0] not in existing]

print(f'测试: 共{len(stocks)}只, 需更新{len(to_update)}只')
conn.close()

if not to_update:
    print('已是最新')
    sys.exit(0)

target_date = '2026-06-26'
success = 0
fail = 0
start_time = time.time()

for i, (stock_id, code, name) in enumerate(to_update, 1):
    symbol = convert_code_to_symbol(code)
    if not symbol:
        fail += 1
        continue
    
    print(f'[{i}/{len(to_update)}] {name}({code})...', end=' ', flush=True)
    
    try:
        df = tf.klines.get(symbol, period='1d', count=5, as_dataframe=True)
        
        if df is None or df.empty:
            print('空')
            fail += 1
            continue
        
        row = df.iloc[-1]
        trade_date = str(row['trade_date'])[:10]
        
        if trade_date != target_date:
            print(f'日期不匹配: {trade_date}')
            fail += 1
            continue
        
        import pandas as pd
        import numpy as np
        
        close = safe_float(row['close'])
        prev_close = safe_float(df.iloc[-2]['close']) if len(df) > 1 else close
        change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        high = safe_float(row['high'])
        low = safe_float(row['low'])
        amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
        
        conn = pymysql.connect(**DB)
        cursor = conn.cursor()
        sql = '''
        INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
        volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
        amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)
        '''
        cursor.execute(sql, (
            stock_id, trade_date,
            safe_float(row['open']), close, high, low,
            safe_float(row.get('volume', 0)), safe_float(row.get('amount', 0)),
            change_pct, amplitude, 0.0
        ))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'✓ {trade_date}')
        success += 1
        
    except Exception as e:
        print(f'错误: {e}')
        fail += 1
    
    # 避免触发限流
    time.sleep(0.5)

elapsed = time.time() - start_time
print()
print(f'✓ 完成: 成功{success}, 失败{fail}, 耗时{elapsed:.1f}s')
