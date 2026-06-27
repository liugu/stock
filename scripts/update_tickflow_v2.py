#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TickFlow 数据更新 - 支持限流重试"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import time
import re
from datetime import date, timedelta
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

def parse_retry_time(msg):
    """从错误消息提取等待秒数"""
    m = re.search(r'(\d+)\s*ms', msg)
    if m:
        return int(m.group(1)) / 1000 + 1
    return 60  # 默认等60秒

print('=' * 60)
print('TickFlow 数据更新')
print('=' * 60)

tf = TickFlow.free()

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取股票列表
cursor.execute('''
    SELECT id, code, name FROM stock_info 
    WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
    ORDER BY code
''')
stocks = cursor.fetchall()

# 查询已有最新日期
cursor.execute('SELECT MAX(date) FROM stock_daily')
latest = cursor.fetchone()[0]
print(f'数据库最新日期: {latest}')

# 目标日期：数据库最新日期的下一天，或今天
target_date = '2026-06-25'  # TickFlow 最新数据日期

# 过滤已更新的
cursor.execute(f'SELECT DISTINCT stock_id FROM stock_daily WHERE date = "{target_date}"')
existing = set(row[0] for row in cursor.fetchall())
to_update = [s for s in stocks if s[0] not in existing]

conn.close()

print(f'总股票: {len(stocks)}, 需更新: {len(to_update)}')

if not to_update:
    print('已是最新')
    sys.exit(0)

import pandas as pd
import numpy as np

success = 0
fail = 0
start_time = time.time()
last_request_time = 0

for i, (stock_id, code, name) in enumerate(to_update, 1):
    symbol = convert_code_to_symbol(code)
    if not symbol:
        fail += 1
        continue
    
    # 限流控制：每秒最多1次请求
    elapsed_since_last = time.time() - last_request_time
    if elapsed_since_last < 1.0:
        time.sleep(1.0 - elapsed_since_last)
    
    if i % 100 == 0:
        elapsed = time.time() - start_time
        print(f'进度: {i}/{len(to_update)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    # 重试逻辑
    max_retries = 3
    for retry in range(max_retries):
        try:
            last_request_time = time.time()
            df = tf.klines.get(symbol, period='1d', count=5, as_dataframe=True)
            
            if df is None or df.empty:
                fail += 1
                break  # 数据为空，不重试
            
            row = df.iloc[-1]
            trade_date = str(row['trade_date'])[:10]
            
            if trade_date != target_date:
                fail += 1
                break  # 日期不匹配，不重试
            
            close = safe_float(row['close'])
            prev_close = safe_float(df.iloc[-2]['close']) if len(df) > 1 else close
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            high = safe_float(row['high'])
            low = safe_float(row['low'])
            amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
            
            conn = pymysql.connect(**DB)
            cur = conn.cursor()
            sql = '''
            INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
            volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
            amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)
            '''
            cur.execute(sql, (
                stock_id, trade_date,
                safe_float(row['open']), close, high, low,
                safe_float(row.get('volume', 0)), safe_float(row.get('amount', 0)),
                change_pct, amplitude, 0.0
            ))
            conn.commit()
            cur.close()
            conn.close()
            success += 1
            break  # 成功，退出重试
            
        except Exception as e:
            err_msg = str(e)
            if '请求频率超限' in err_msg and retry < max_retries - 1:
                wait_time = parse_retry_time(err_msg)
                print(f'限流，等待{wait_time:.0f}s后重试...')
                time.sleep(wait_time)
            else:
                fail += 1
                break

elapsed = time.time() - start_time
print()
print(f'✓ 完成: 成功{success}, 失败{fail}, 耗时{elapsed:.1f}s')