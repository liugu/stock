#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TickFlow 补全今日数据 - 限流控制 + 批量写入"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
import re
from datetime import date
from tickflow import TickFlow

DB = {'host':'localhost','user':'stock','password':'12345678',
      'database':'instock','port':3306,'charset':'utf8mb4'}

today = date(2026, 7, 2)
today_str = str(today)

tf = TickFlow.free()

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 查询已有数据
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date=%s', (today_str,))
existing = set(r[0] for r in cursor.fetchall())

# 获取所有股票
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "60%%" OR code LIKE "00%%" OR code LIKE "30%%"')
stocks = [(r[1], r[0], r[2]) for r in cursor.fetchall() if r[0] not in existing]
cursor.close()
conn.close()

print(f'已有: {len(existing)}, 需补充: {len(stocks)}')

def sf(v):
    if v is None: return 0.0
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return 0.0
    return float(v)

def parse_wait(msg):
    m = re.search(r'(\d+)\s*ms', str(msg))
    return int(m.group(1))/1000 + 1 if m else 60

success = fail = 0
start = time.time()
batch = []
last_req = 0

for i, (code, sid, name) in enumerate(stocks, 1):
    symbol = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
    
    # 限流: 每秒最多1次
    now = time.time()
    wait = 1.1 - (now - last_req)
    if wait > 0:
        time.sleep(wait)
    last_req = time.time()
    
    # 重试3次
    for retry in range(3):
        try:
            df = tf.klines.get(symbol, period='1d', count=5, as_dataframe=True)
            if df is None or df.empty:
                fail += 1
                break  # 空数据不重试
            row = df.iloc[-1]
            td = str(row['trade_date'])[:10]
            if td != today_str:
                fail += 1
                break
            close = sf(row['close'])
            if len(df) >= 2:
                pc = sf(df.iloc[-2]['close'])
                cp = ((close - pc) / pc * 100) if pc > 0 else 0.0
                amp = ((sf(row['high']) - sf(row['low'])) / pc * 100) if pc > 0 else 0.0
            else:
                cp = amp = 0.0
            batch.append((sid, td, sf(row['open']), close, sf(row['high']),
                        sf(row['low']), sf(row.get('volume',0)), sf(row.get('amount',0)),
                        cp, amp, 0.0))
            success += 1
            break  # 成功，跳出重试
        except Exception as e:
            if '频率超限' in str(e) or '10543' in str(e):
                wt = parse_wait(str(e))
                print(f'限流等待{wt:.0f}s...', end=' ', flush=True)
                time.sleep(wt)
            elif retry < 2:
                time.sleep(2)
            else:
                fail += 1
                if fail <= 3:
                    print(f'[{i}] {code} 失败: {str(e)[:60]}')
    
    # 每60只批量写入
    if i % 60 == 0:
        if batch:
            conn = pymysql.connect(**DB)
            cur = conn.cursor()
            sql = """INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),low=VALUES(low),
volume=VALUES(volume),amount=VALUES(amount),change_percent=VALUES(change_percent),
amplitude=VALUES(amplitude),turnover_rate=VALUES(turnover_rate)"""
            cur.executemany(sql, batch)
            conn.commit()
            cur.close()
            conn.close()
            batch = []
        elapsed = int(time.time() - start)
        print(f'进度: {i}/{len(stocks)} 成功:{success} 失败:{fail} 耗时:{elapsed}s')

# 写入剩余批次
if batch:
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    sql = """INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),low=VALUES(low),
volume=VALUES(volume),amount=VALUES(amount),change_percent=VALUES(change_percent),
amplitude=VALUES(amplitude),turnover_rate=VALUES(turnover_rate)"""
    cur.executemany(sql, batch)
    conn.commit()
    cur.close()
    conn.close()

elapsed = int(time.time() - start)
print(f'\n✓ 完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed}s')
