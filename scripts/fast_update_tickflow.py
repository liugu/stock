#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多线程更新股票日K数据 - TickFlow
并发查询，限速60次/分钟
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

TICKFLOW_API_KEY = 'tk_0cf8a26efda5479ba2e97e97d7695895'

# 全局计数器
success_count = 0
fail_count = 0
counter_lock = Lock()
last_request_time = [0]  # 用列表包装以便在函数内修改

def safe_float(val):
    try:
        if val is None or pd.isna(val):
            return 0.0
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except:
        return 0.0

def convert_code_to_symbol(code):
    if code.startswith('6'):
        return f'{code}.SH'
    elif code.startswith('0') or code.startswith('3'):
        return f'{code}.SZ'
    return None

def update_one_stock(args):
    """更新单只股票"""
    stock_id, code, name, target_date, tf = args
    
    symbol = convert_code_to_symbol(code)
    if not symbol:
        return False
    
    try:
        df = tf.klines.get(symbol, period='1d', count=5, as_dataframe=True)
        
        if df is None or df.empty:
            return False
        
        row = df.iloc[-1]
        trade_date = str(row['trade_date'])[:10]
        
        # 只写入目标日期
        if trade_date != target_date:
            return False
        
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
        return True
        
    except:
        return False

def main():
    print('=' * 60)
    print('多线程更新股票日K数据 (TickFlow)')
    print('=' * 60)
    
    from tickflow import TickFlow
    tf = TickFlow(api_key=TICKFLOW_API_KEY)
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票列表
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
        ORDER BY code
    ''')
    stocks = cursor.fetchall()
    
    # 过滤已更新的
    cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = "2026-06-25"')
    existing = set(row[0] for row in cursor.fetchall())
    to_update = [(s[0], s[1], s[2]) for s in stocks if s[0] not in existing]
    
    conn.close()
    
    print(f'总股票: {len(stocks)}, 需更新: {len(to_update)}')
    
    if not to_update:
        print('已是最新')
        return
    
    target_date = '2026-06-25'
    start_time = time.time()
    
    # 准备任务
    tasks = [(s[0], s[1], s[2], target_date, tf) for s in to_update]
    
    # 并发执行（5线程，限速）
    success = 0
    fail = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(update_one_stock, task): task for task in tasks}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                success += 1
            else:
                fail += 1
            
            if i % 100 == 0:
                elapsed = time.time() - start_time
                print(f'进度: {i}/{len(to_update)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.1f}s')

if __name__ == '__main__':
    main()
