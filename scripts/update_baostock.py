#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用 Baostock 批量更新股票行情数据"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
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

def safe_float(val):
    """安全转换为浮点数"""
    try:
        if val is None or val == '' or val == 'None':
            return 0.0
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except:
        return 0.0

def update_stock_daily():
    print('=' * 60)
    print('Baostock 股票数据更新')
    print('=' * 60)
    
    # 登录 Baostock
    lg = bs.login()
    print(f'Baostock 登录: {lg.error_msg}')
    
    if lg.error_code != '0':
        print('登录失败，退出')
        return
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票列表
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
        ORDER BY code
    ''')
    stocks = cursor.fetchall()
    
    # 检查已更新的
    target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')  # 昨天
    cursor.execute(f'SELECT DISTINCT stock_id FROM stock_daily WHERE date = "{target_date}"')
    existing = set(row[0] for row in cursor.fetchall())
    to_update = [s for s in stocks if s[0] not in existing]
    
    print(f'总股票: {len(stocks)}, 需更新: {len(to_update)}, 目标日期: {target_date}')
    
    if not to_update:
        print('已是最新')
        bs.logout()
        conn.close()
        return
    
    success = 0
    fail = 0
    start_time = time.time()
    
    for i, (stock_id, code, name) in enumerate(to_update, 1):
        # 转换为 Baostock 格式
        if code.startswith('6'):
            bs_code = f'sh.{code}'
        else:
            bs_code = f'sz.{code}'
        
        try:
            # 查询最近5天数据（Baostock 要求 YYYY-MM-DD 格式）
            end_date = target_date  # YYYY-MM-DD
            start_date_str = '2026-06-15'  # 提前10天
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                'date,code,open,high,low,close,volume,amount,turn',
                start_date=start_date_str,
                end_date=end_date,
                frequency='d',
                adjustflag='3'  # 不复权
            )
            
            if rs.error_code != '0':
                fail += 1
                continue
            
            # 获取数据
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if not data:
                fail += 1
                continue
            
            df = pd.DataFrame(data, columns=rs.fields)
            
            # 只取最新一条
            row = df.iloc[-1]
            trade_date = row['date']
            
            if trade_date != target_date:
                fail += 1
                continue
            
            # 计算涨跌幅
            close = safe_float(row['close'])
            if len(df) > 1:
                prev_close = safe_float(df.iloc[-2]['close'])
            else:
                prev_close = close
            
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 计算振幅
            high = safe_float(row['high'])
            low = safe_float(row['low'])
            amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
            
            # 写入数据库
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
                safe_float(row['volume']), safe_float(row['amount']),
                change_pct, amplitude, safe_float(row['turn'])
            ))
            conn.commit()
            success += 1
            
        except Exception as e:
            fail += 1
        
        # 显示进度
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(to_update)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.1f}s')

if __name__ == '__main__':
    update_stock_daily()
