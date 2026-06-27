#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票历史行情数据（优化版）
- 支持断点续传
- 实时进度显示
- 自动重新登录
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
import json

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

# 进度文件
PROGRESS_FILE = 'E:/量化研究/workspace/stock/data/update_progress.json'

# 导入数据适配器
from instock.core.crawling.data_adapter_enhanced import get_stock_hist, baostock_logout

def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(progress):
    """保存进度"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def update_stock_daily():
    """更新股票历史行情数据"""
    print('=' * 60)
    print('更新股票历史行情数据（优化版）')
    print('=' * 60)
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票代码到 stock_id 的映射
    cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%" OR code LIKE "60%" OR code LIKE "00%"')
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
        start_date = (today - timedelta(days=1)).strftime('%Y%m%d')
    elif latest_date == today - timedelta(days=1):
        start_date = latest_date.strftime('%Y%m%d')
    else:
        start_date = latest_date.strftime('%Y%m%d')
    
    print(f'更新日期范围: {start_date} - {end_date}')
    print()
    
    # 加载进度
    progress = load_progress()
    progress_key = f'{start_date}_{end_date}'
    processed = set(progress.get(progress_key, []))
    
    if processed:
        print(f'检测到断点，已处理 {len(processed)} 只股票，继续...')
    
    success = 0
    fail = 0
    skipped = 0
    start_time = time.time()
    
    codes_to_process = [code for code in stock_map.keys() if code not in processed]
    total = len(codes_to_process)
    
    print(f'待处理: {total} 只股票')
    print()
    
    for i, code in enumerate(codes_to_process, 1):
        stock_id, name = stock_map[code]
        
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
        
        # 保存进度
        processed.add(code)
        if i % 50 == 0:
            progress[progress_key] = list(processed)
            save_progress(progress)
        
        if i % 200 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f'进度: {i}/{total} ({i*100//total}%) | 成功:{success} 失败:{fail} 跳过:{skipped} | 速度:{rate:.1f}只/秒 | 预计剩余:{eta:.0f}秒')
    
    # 清理进度文件
    if progress_key in progress:
        del progress[progress_key]
        save_progress(progress)
    
    cursor.close()
    conn.close()
    baostock_logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}')
    print(f'耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)')

if __name__ == '__main__':
    update_stock_daily()
