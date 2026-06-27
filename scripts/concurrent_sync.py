#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""并发数据同步 - 使用多线程加速"""
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
import time
import baostock as bs
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

date_str = '2026-06-25'
results = []
results_lock = threading.Lock()
progress = {'success': 0, 'fail': 0}
progress_lock = threading.Lock()

def sf(v):
    try:
        if v is None or v == '' or v == '0.000':
            return 0.0
        f = float(v)
        return 0.0 if np.isnan(f) or np.isinf(f) else f
    except:
        return 0.0

def fetch_stock(code_info):
    """获取单只股票数据"""
    code, info = code_info
    try:
        # 每个线程独立登录
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        bs_code = f'sh.{code}' if code.startswith(('6')) else f'sz.{code}'
        rs = bs.query_history_k_data_plus(
            bs_code, "date,open,high,low,close,volume,amount,turn",
            start_date='2026-06-18', end_date=date_str, frequency="d", adjustflag="2"
        )
        
        if rs.error_code != '0':
            bs.logout()
            return None
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        bs.logout()
        
        if not data_list:
            return None
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        target = df[df['date'] == date_str]
        if len(target) == 0:
            return None
        
        row = target.iloc[0]
        prev = df[df['date'] < date_str]
        pc = sf(prev.iloc[-1]['close']) if len(prev) > 0 else sf(row['close'])
        cc = sf(row['close'])
        ch = (cc - pc) / pc * 100 if pc > 0 else 0
        hi, lo = sf(row['high']), sf(row['low'])
        amp = (hi - lo) / pc * 100 if pc > 0 else 0
        
        return (info['id'], date_str, sf(row['open']), cc, hi, lo,
                sf(row['volume']), sf(row['amount']), ch, amp, sf(row['turn']))
    except:
        return None

# 获取股票列表
conn = pymysql.connect(**DB)
cursor = conn.cursor()
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%" ORDER BY code')
stocks = {row[1]: {'id': row[0], 'name': row[2]} for row in cursor.fetchall()}
cursor.execute('SELECT stock_id FROM stock_daily WHERE date = %s', (date_str,))
existing = set(row[0] for row in cursor.fetchall())
conn.close()

to_update = [(code, info) for code, info in stocks.items() if info['id'] not in existing]
print(f"日期: {date_str}, 需更新: {len(to_update)} 只, 使用5线程并发", flush=True)

if to_update:
    start_time = time.time()
    all_data = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_stock, item): item[0] for item in to_update}
        
        for future in as_completed(futures):
            code = futures[future]
            result = future.result()
            
            with progress_lock:
                if result:
                    all_data.append(result)
                    progress['success'] += 1
                else:
                    progress['fail'] += 1
                
                total = progress['success'] + progress['fail']
                if total % 200 == 0:
                    elapsed = time.time() - start_time
                    speed = total / elapsed
                    print(f"[{total}/{len(to_update)}] OK:{progress['success']} Fail:{progress['fail']} 速度:{speed:.1f}股/秒", flush=True)
    
    # 批量写入
    if all_data:
        conn = pymysql.connect(**DB)
        cursor = conn.cursor()
        cursor.executemany('INSERT INTO stock_daily VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', all_data)
        conn.commit()
        conn.close()
        
        elapsed = time.time() - start_time
        print(f"\n完成: OK {progress['success']}, Fail {progress['fail']}, 耗时 {elapsed:.1f}s", flush=True)
        
        # 验证
        conn = pymysql.connect(**DB)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM stock_daily WHERE date = %s', (date_str,))
        count = cursor.fetchone()[0]
        conn.close()
        print(f"数据库中 {date_str} 共 {count} 条数据", flush=True)
