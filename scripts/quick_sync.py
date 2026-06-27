#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速同步脚本 - 批量收集数据，一次性写入
优化：实时进度、超时处理、错误日志
"""

import sys
import os

# 强制UTF-8输出
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import pandas as pd
import numpy as np
import baostock as bs
from datetime import datetime, date, timedelta
import time
import signal

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_stock_list():
    """获取股票列表"""
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE '60%' OR code LIKE '00%' OR code LIKE '30%'
        ORDER BY code
    ''')
    stocks = {row[1]: {'id': row[0], 'name': row[2]} for row in cursor.fetchall()}
    conn.close()
    return stocks

def fetch_data_from_baostock(date_str):
    """从 Baostock 获取单日数据"""
    print(f"登录 Baostock...")
    sys.stdout.flush()
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return None
    
    stocks = get_stock_list()
    print(f"获取 {len(stocks)} 只股票数据...")
    sys.stdout.flush()
    
    all_data = []
    success = 0
    fail = 0
    errors = []  # 记录错误
    
    start_time = time.time()
    last_print_time = start_time
    
    for i, (code, info) in enumerate(stocks.items(), 1):
        try:
            # 转换代码格式
            if code.startswith(('600', '601', '603', '605', '688', '689')):
                bs_code = f'sh.{code}'
            else:
                bs_code = f'sz.{code}'
            
            # 查询数据（获取前后几天用于计算涨跌幅）
            start_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,turn,peTTM,pbMRQ",
                start_date=start_date,
                end_date=date_str,
                frequency="d",
                adjustflag="2"
            )
            
            if rs.error_code != '0':
                fail += 1
                if fail <= 20:  # 只记录前20个错误
                    errors.append(f"{code}: {rs.error_msg}")
                continue
            
            # 整理数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                fail += 1
                continue
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            target_rows = df[df['date'] == date_str]
            
            if len(target_rows) == 0:
                fail += 1
                continue
            
            row = target_rows.iloc[0]
            
            # 处理数值
            def safe_float(val):
                try:
                    if val is None or val == '' or val == '0.000':
                        return 0.0
                    f = float(val)
                    if np.isnan(f) or np.isinf(f):
                        return 0.0
                    return f
                except:
                    return 0.0
            
            # 计算涨跌幅
            prev_rows = df[df['date'] < date_str]
            if len(prev_rows) > 0:
                prev_close = safe_float(prev_rows.iloc[-1]['close'])
                curr_close = safe_float(row['close'])
                change_pct = (curr_close - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
                high = safe_float(row['high'])
                low = safe_float(row['low'])
                amplitude = (high - low) / prev_close * 100 if prev_close > 0 else 0.0
            else:
                change_pct = 0.0
                amplitude = 0.0
            
            all_data.append({
                'stock_id': info['id'],
                'date': date_str,
                'open': safe_float(row['open']),
                'close': safe_float(row['close']),
                'high': safe_float(row['high']),
                'low': safe_float(row['low']),
                'volume': safe_float(row['volume']),
                'amount': safe_float(row['amount']),
                'change_percent': change_pct,
                'amplitude': amplitude,
                'turnover_rate': safe_float(row['turn'])
            })
            
            success += 1
        
        except Exception as e:
            fail += 1
            if len(errors) < 20:
                errors.append(f"{code}: {str(e)[:50]}")
        
        # 每50只股票或每3秒输出一次进度（更频繁）
        current_time = time.time()
        if i % 50 == 0 or (current_time - last_print_time) >= 3:
            elapsed = current_time - start_time
            speed = i / elapsed if elapsed > 0 else 0
            remaining = (len(stocks) - i) / speed if speed > 0 else 0
            print(f"[{i}/{len(stocks)}] 成功:{success} 失败:{fail} 速度:{speed:.1f}股/秒 剩余:{remaining:.0f}秒")
            sys.stdout.flush()
            last_print_time = current_time
    
    bs.logout()
    
    elapsed = time.time() - start_time
    print(f"\n完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.1f}秒")
    
    if errors:
        print(f"\n前 {len(errors)} 个错误:")
        for err in errors[:10]:
            print(f"  - {err}")
    
    sys.stdout.flush()
    
    return all_data

def save_to_database(data, date_str):
    """批量写入数据库"""
    if not data:
        print("没有数据需要保存")
        return
    
    print(f"写入 {len(data)} 条数据到数据库...")
    sys.stdout.flush()
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 先删除已有数据
    cursor.execute("DELETE FROM stock_daily WHERE date = %s", (date_str,))
    print(f"删除已有数据: {cursor.rowcount} 条")
    sys.stdout.flush()
    
    # 批量插入
    sql = '''
    INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    
    values = [
        (d['stock_id'], d['date'], d['open'], d['close'], d['high'], d['low'],
         d['volume'], d['amount'], d['change_percent'], d['amplitude'], d['turnover_rate'])
        for d in data
    ]
    
    start_time = time.time()
    cursor.executemany(sql, values)
    conn.commit()
    
    elapsed = time.time() - start_time
    print(f"写入成功: {cursor.rowcount} 条, 耗时 {elapsed:.2f}秒")
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM stock_daily WHERE date = %s", (date_str,))
    final_count = cursor.fetchone()[0]
    print(f"数据库中 {date_str} 共有 {final_count} 条数据")
    
    conn.close()
    sys.stdout.flush()

def main():
    date_str = datetime.now().strftime('%Y-%m-%d')
    print(f"开始同步 {date_str} 数据...")
    
    # 获取数据
    data = fetch_data_from_baostock(date_str)
    
    # 写入数据库
    if data:
        save_to_database(data, date_str)
    
    print("同步完成!")

if __name__ == '__main__':
    main()
