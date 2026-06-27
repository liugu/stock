#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票历史行情数据
使用 TickFlow 批量接口 (https://tickflow.org)
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
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

def convert_code_to_symbol(code):
    """将6位股票代码转换为 TickFlow 格式"""
    if code.startswith('6'):
        return f"{code}.SH"
    elif code.startswith('0') or code.startswith('3'):
        return f"{code}.SZ"
    elif code.startswith('8') or code.startswith('4'):
        return f"{code}.BJ"
    return None

def update_stock_daily():
    """更新股票历史行情数据"""
    print('=' * 60)
    print('更新股票历史行情数据 (TickFlow 批量接口)')
    print('=' * 60)
    
    from tickflow import TickFlow
    tf = TickFlow.free()  # 使用免费API（无需注册，仅历史日K）
    print("[TickFlow] 使用免费服务")
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票代码到 stock_id 的映射
    cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%" OR code LIKE "60%" OR code LIKE "00%" OR code LIKE "68%"')
    stock_map = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
    print(f'共 {len(stock_map)} 只股票')
    
    # 获取最新日期
    cursor.execute('SELECT MAX(date) FROM stock_daily')
    latest_date = cursor.fetchone()[0]
    
    today = date.today()
    end_date = today.strftime('%Y%m%d')
    
    if latest_date is None:
        start_date = '20260101'
    else:
        start_date = latest_date.strftime('%Y%m%d')
    
    print(f'更新日期范围: {start_date} - {end_date}')
    print()
    
    # 构建股票代码列表
    symbols = []
    code_to_id = {}
    for code, (stock_id, name) in stock_map.items():
        symbol = convert_code_to_symbol(code)
        if symbol:
            symbols.append(symbol)
            code_to_id[symbol] = (stock_id, code, name)
    
    print(f'需要更新 {len(symbols)} 只股票')
    
    success = 0
    fail = 0
    start_time = time.time()
    
    # 单个查询（当前套餐不支持批量）
    for i, (code, (stock_id, name)) in enumerate(stock_map.items(), 1):
        symbol = convert_code_to_symbol(code)
        if not symbol:
            continue
        
        # 每100只显示进度
        if i % 100 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
        
        try:
            df = tf.klines.get(symbol, period="1d", count=5, as_dataframe=True)
            
            if df is None or df.empty:
                continue
            
            # 只处理最新一条数据
            row = df.iloc[-1]
            trade_date = str(row['trade_date'])[:10]
            date_comp = trade_date.replace('-', '')
            
            # 只写入今天的数据
            if date_comp != end_date:
                continue
            
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
            
            # 计算涨跌幅
            close = safe_float(row['close'])
            prev_close = safe_float(df.iloc[-2]['close']) if len(df) > 1 else close
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 计算振幅
            high = safe_float(row['high'])
            low = safe_float(row['low'])
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
                stock_id,
                trade_date,
                safe_float(row['open']), 
                close,
                high, 
                low,
                safe_float(row.get('volume', 0)), 
                safe_float(row.get('amount', 0)),
                change_pct, 
                amplitude, 
                0.0
            ))
            conn.commit()
            success += 1
            
        except Exception as e:
            fail += 1
        
        # 显示进度
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}')
    print(f'耗时: {elapsed:.1f}s')

if __name__ == '__main__':
    update_stock_daily()
