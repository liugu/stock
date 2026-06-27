#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充缺失股票的历史数据
使用 Baostock 数据源
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)  # line buffering
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import baostock as bs
import time
from datetime import date, timedelta

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_baostock_code(code, market):
    """转换为 Baostock 格式"""
    if market == 'sh' or code.startswith('68'):
        return f'sh.{code}'
    else:
        return f'sz.{code}'

def safe_float(val):
    try:
        if val is None or val == '' or val == '-':
            return 0.0
        f = float(val)
        return f if f > 0 else 0.0
    except:
        return 0.0

def backfill_missing():
    """补充缺失数据"""
    print('=' * 60)
    print('补充缺失股票数据 (Baostock)')
    print('=' * 60)
    
    # 登录 Baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f'Baostock 登录失败: {lg.error_msg}')
        return
    print('Baostock 登录成功')
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取数据库最新日期
    cursor.execute('SELECT MAX(date) FROM stock_daily')
    latest_date = cursor.fetchone()[0]
    
    today = date.today()
    end_date = today.strftime('%Y-%m-%d')
    
    # 获取缺失最新数据的股票
    cursor.execute('''
        SELECT s.id, s.code, s.name, s.market
        FROM stock_info s
        WHERE s.id NOT IN (
            SELECT DISTINCT stock_id FROM stock_daily 
            WHERE date = %s
        )
        AND (s.code LIKE '60%%' OR s.code LIKE '00%%' OR s.code LIKE '30%%' OR s.code LIKE '68%%')
        ORDER BY s.code
    ''', (latest_date,))
    missing_stocks = cursor.fetchall()
    print(f'缺失最新数据({latest_date})的股票: {len(missing_stocks)} 只')
    print()
    
    success = 0
    fail = 0
    no_data = 0
    start_time = time.time()
    
    for i, (stock_id, code, name, market) in enumerate(missing_stocks, 1):
        bs_code = get_baostock_code(code, market)
        
        try:
            # 获取最近100天数据
            start_dt = (today - timedelta(days=150)).strftime('%Y-%m-%d')
            rs = bs.query_history_k_data_plus(
                bs_code,
                'date,open,close,high,low,volume,amount',
                start_date=start_dt,
                end_date=end_date,
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
            else:
                no_data += 1
            
            # 限速
            time.sleep(0.1)
            
        except Exception as e:
            fail += 1
        
        # 显示进度
        if i % 200 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(missing_stocks)} 成功:{success} 无数据:{no_data} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 无数据 {no_data}, 失败 {fail}')
    print(f'耗时: {elapsed:.1f}s')

if __name__ == '__main__':
    backfill_missing()
