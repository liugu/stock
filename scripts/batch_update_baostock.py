#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量更新股票日K数据 - 使用 Baostock
支持批量查询，速度快
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def safe_float(val):
    try:
        if val is None or pd.isna(val) or val == '':
            return 0.0
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except:
        return 0.0

def update_stock_daily():
    print('=' * 60)
    print('批量更新股票日K数据 (Baostock)')
    print('=' * 60)
    
    # 登录 baostock
    lg = bs.login()
    print(f'Baostock 登录: {lg.error_msg}')
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票列表
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
        ORDER BY code
    ''')
    stocks = cursor.fetchall()
    print(f'共 {len(stocks)} 只股票')
    
    # 检查今天已更新数量
    cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = "2026-06-25"')
    already_updated = cursor.fetchone()[0]
    print(f'今天已更新: {already_updated} 只')
    
    # 获取已有数据的股票ID
    cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = "2026-06-25"')
    existing_ids = set(row[0] for row in cursor.fetchall())
    
    # 过滤出需要更新的股票
    to_update = [(s[0], s[1], s[2]) for s in stocks if s[0] not in existing_ids]
    print(f'需要更新: {len(to_update)} 只')
    
    if not to_update:
        print('所有股票已是最新')
        bs.logout()
        conn.close()
        return
    
    today = '2026-06-25'
    start_date = '2026-06-24'
    end_date = '2026-06-25'
    
    success = 0
    fail = 0
    
    # 批量查询（每次50只）
    batch_size = 50
    for batch_start in range(0, len(to_update), batch_size):
        batch = to_update[batch_start:batch_start + batch_size]
        
        for stock_id, code, name in batch:
            # 转换代码格式
            if code.startswith('6'):
                symbol = f'sh.{code}'
            else:
                symbol = f'sz.{code}'
            
            try:
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,code,open,high,low,close,volume,amount,turn",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != '0':
                    fail += 1
                    continue
                
                data = []
                while rs.next():
                    data.append(rs.get_row_data())
                
                if not data:
                    fail += 1
                    continue
                
                row = data[-1]  # 取最新一条
                trade_date = row[0]
                
                # 计算涨跌幅（需要前一天数据）
                close = safe_float(row[5])
                prev_close = close
                if len(data) > 1:
                    prev_close = safe_float(data[-2][5])
                change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
                
                # 计算振幅
                high = safe_float(row[3])
                low = safe_float(row[4])
                amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
                
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
                    safe_float(row[2]), close, high, low,
                    safe_float(row[6]), safe_float(row[7]),
                    change_pct, amplitude, safe_float(row[8])
                ))
                conn.commit()
                success += 1
                
            except Exception as e:
                fail += 1
        
        # 显示进度
        progress = min(batch_start + batch_size, len(to_update))
        print(f'进度: {progress}/{len(to_update)} 成功:{success} 失败:{fail}')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}')

if __name__ == '__main__':
    update_stock_daily()
