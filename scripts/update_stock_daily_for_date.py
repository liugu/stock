#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新指定日期的股票历史行情数据
使用 baostock 作为数据源
"""
import sys
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

def update_stock_daily(target_date_str):
    """更新指定日期的股票历史行情数据
    
    Args:
        target_date_str: 目标日期，格式 YYYY-MM-DD 或 YYYYMMDD
    """
    # 解析日期
    if '-' in target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        target_date_yyyymmdd = target_date_str.replace('-', '')
    else:
        target_date_yyyymmdd = target_date_str
        target_date = datetime.strptime(target_date_str, '%Y%m%d').date()
    
    print('=' * 60)
    print(f'更新股票历史行情数据: {target_date}')
    print('=' * 60)
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票代码到 stock_id 的映射
    cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%" OR code LIKE "60%" OR code LIKE "00%"')
    stock_map = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
    print(f'共 {len(stock_map)} 只股票')
    
    # 获取前一天的日期（用于计算涨跌幅）
    prev_date = target_date - timedelta(days=1)
    start_date = prev_date.strftime('%Y%m%d')
    end_date = target_date_yyyymmdd
    
    print(f'获取日期范围: {start_date} - {end_date}')
    print()
    
    success = 0
    fail = 0
    skipped = 0
    start_time = time.time()
    
    for i, (code, (stock_id, name)) in enumerate(stock_map.items(), 1):
        try:
            df = get_stock_hist(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 找到目标日期的数据
                target_date_dash = target_date.strftime('%Y-%m-%d')
                target_rows = df[df['日期'].astype(str).str[:10] == target_date_dash]
                
                if len(target_rows) > 0:
                    row = target_rows.iloc[-1]
                    date_str = target_date_dash
                    
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
                        if fail <= 5:
                            print(f'  写入失败 {code}: {e}')
                else:
                    skipped += 1
            else:
                skipped += 1
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f'  获取失败 {code}: {e}')
        
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
    from datetime import datetime
    
    # 默认更新昨天
    target = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    update_stock_daily(target)
