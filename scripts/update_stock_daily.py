#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票历史行情数据
使用 baostock 作为主要数据源
"""
import sys
import os
# 强制使用 UTF-8 编码输出
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

# 导入数据适配器
from instock.core.crawling.data_adapter_enhanced import get_stock_hist, baostock_logout

def update_stock_daily():
    """更新股票历史行情数据"""
    print('=' * 60)
    print('更新股票历史行情数据')
    print('=' * 60)
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票代码到 stock_id 的映射（包含科创板 68%）
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
    elif latest_date == today:
        # 数据库已经是今天的日期，需要获取前一天数据来计算涨跌幅
        start_date = (today - timedelta(days=1)).strftime('%Y%m%d')
    elif latest_date == today - timedelta(days=1):
        # 数据库最新是昨天，需要获取昨天和今天来计算涨跌幅
        start_date = latest_date.strftime('%Y%m%d')
    else:
        # 数据库落后超过一天，从最新日期开始获取
        start_date = latest_date.strftime('%Y%m%d')
    
    print(f'更新日期范围: {start_date} - {end_date}')
    print()
    
    success = 0
    fail = 0
    skipped = 0
    start_time = time.time()
    
    for i, (code, (stock_id, name)) in enumerate(stock_map.items(), 1):
        try:
            df = get_stock_hist(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 只写入今天的数据（最后一条）
                row = df.iloc[-1]
                date_str = str(row['日期'])[:10]
                
                # 转换为 YYYYMMDD 格式比较
                date_comp = date_str.replace('-', '')
                
                # 只处理今天的数据
                if date_comp == end_date:
                    try:
                        # 处理 NaN 值
                        def safe_float(val):
                            try:
                                if val is None:
                                    return 0.0
                                f = float(val)
                                if np.isnan(f) or np.isinf(f):
                                    return 0.0
                                return f
                            except:
                                return 0.0
                        
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
                            date_str,
                            safe_float(row['开盘']), 
                            safe_float(row['收盘']), 
                            safe_float(row['最高']), 
                            safe_float(row['最低']),
                            safe_float(row.get('成交量', 0)), 
                            safe_float(row.get('成交额', 0)),
                            safe_float(row.get('涨跌幅', 0)), 
                            safe_float(row.get('振幅', 0)), 
                            safe_float(row.get('换手率', 0))
                        ))
                        conn.commit()
                        success += 1
                    except Exception as e:
                        fail += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        except Exception as e:
            fail += 1
        
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 跳过:{skipped} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    baostock_logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}')
    print(f'耗时: {elapsed:.1f}s')

if __name__ == '__main__':
    update_stock_daily()
