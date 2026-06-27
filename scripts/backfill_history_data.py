#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充股票历史数据（2023-06-01至今）
使用 Baostock 数据源
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import baostock as bs
import time
from datetime import date, timedelta

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

START_DATE = '2023-06-01'
END_DATE = '2025-05-21'  # 补充到现有数据开始之前

def safe_float(val):
    try:
        if val is None or val == '' or val == '-':
            return 0.0
        f = float(val)
        return f if f > 0 else 0.0
    except:
        return 0.0

def backfill_history():
    print('=' * 60)
    print('补充股票历史数据 (2023-06-01 ~ 2025-05-21)')
    print('=' * 60)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f'Baostock 登录失败: {lg.error_msg}')
        return
    print('Baostock 登录成功')
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取所有股票
    cursor.execute('''
        SELECT id, code, name, market FROM stock_info
        WHERE code LIKE '60%%' OR code LIKE '00%%' OR code LIKE '30%%' OR code LIKE '68%%'
        AND name NOT LIKE '%%退%%'
        AND name NOT LIKE '%%ST%%'
        AND name NOT LIKE '%%*ST%%'
        ORDER BY code
    ''')
    stocks = cursor.fetchall()
    print(f'需要补充的股票: {len(stocks)} 只')
    print(f'日期范围: {START_DATE} ~ {END_DATE}')
    print()
    
    success = 0
    fail = 0
    no_data = 0
    total_records = 0
    start_time = time.time()
    
    # 分批处理
    batch_size = 100
    for batch_idx in range(0, len(stocks), batch_size):
        batch = stocks[batch_idx:batch_idx + batch_size]
        
        for stock_id, code, name, market in batch:
            # 转换代码格式
            if market == 'sh' or code.startswith('68'):
                bs_code = f'sh.{code}'
            else:
                bs_code = f'sz.{code}'
            
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    'date,open,close,high,low,volume,amount',
                    start_date=START_DATE,
                    end_date=END_DATE,
                    frequency='d',
                    adjustflag='3'
                )
                
                if rs.error_code != '0':
                    fail += 1
                    continue
                
                data = []
                while rs.next():
                    data.append(rs.get_row_data())
                
                if not data:
                    no_data += 1
                    continue
                
                # 写入数据库
                records = 0
                for row in data:
                    trade_date = row[0]
                    open_p = safe_float(row[1])
                    close = safe_float(row[2])
                    high = safe_float(row[3])
                    low = safe_float(row[4])
                    volume = safe_float(row[5])
                    amount = safe_float(row[6])
                    
                    if close <= 0:
                        continue
                    
                    sql = '''
                    INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
                    volume=VALUES(volume), amount=VALUES(amount)
                    '''
                    cursor.execute(sql, (stock_id, trade_date, open_p, close, high, low, volume, amount))
                    records += 1
                
                if records > 0:
                    conn.commit()
                    success += 1
                    total_records += records
                else:
                    no_data += 1
                
                time.sleep(0.05)  # 限速
                
            except Exception as e:
                fail += 1
        
        # 显示进度
        elapsed = time.time() - start_time
        processed = min(batch_idx + batch_size, len(stocks))
        rate = total_records / elapsed if elapsed > 0 else 0
        print(f'进度: {processed}/{len(stocks)} 成功:{success} 记录:{total_records:,} 耗时:{elapsed:.0f}s 速率:{rate:.0f}条/秒')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 无数据 {no_data}, 失败 {fail}')
    print(f'✓ 新增记录: {total_records:,}')
    print(f'耗时: {elapsed:.1f}s')

if __name__ == '__main__':
    backfill_history()