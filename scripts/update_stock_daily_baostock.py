#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Baostock 更新指定日期的股票历史行情数据
纯 Baostock 实现，不依赖外部网络API
"""
import sys
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
import time
import baostock as bs
from datetime import datetime, timedelta

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def update_stock_daily_baostock(target_date_str):
    """使用 Baostock 更新指定日期的股票历史行情数据
    
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
    
    target_date_dash = target_date.strftime('%Y-%m-%d')
    
    print('=' * 60)
    print(f'[Baostock] 更新股票历史行情数据: {target_date}')
    print('=' * 60)
    
    # 登录 Baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f'Baostock 登录失败: {lg.error_msg}')
        return
    print('Baostock 登录成功')
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取股票代码到 stock_id 的映射
    cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%" OR code LIKE "60%" OR code LIKE "00%"')
    stock_map = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
    print(f'共 {len(stock_map)} 只股票')
    
    # 获取前一天的日期（用于计算涨跌幅）
    prev_date = target_date - timedelta(days=3)  # 多获取几天确保有数据
    start_date = prev_date.strftime('%Y-%m-%d')
    end_date = target_date_dash
    
    print(f'获取日期范围: {start_date} - {end_date}')
    print()
    
    success = 0
    fail = 0
    no_data = 0
    start_time = time.time()
    
    for i, (code, (stock_id, name)) in enumerate(stock_map.items(), 1):
        try:
            # 转换股票代码格式
            if code.startswith(('600', '601', '603', '605', '688', '689')):
                bs_code = f'sh.{code}'
            else:
                bs_code = f'sz.{code}'
            
            # 查询数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,turn",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"  # 前复权
            )
            
            if rs.error_code != '0':
                fail += 1
                if fail <= 5:
                    print(f'  查询失败 {code}: {rs.error_msg}')
                continue
            
            # 整理数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                no_data += 1
                continue
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 找到目标日期的数据
            target_rows = df[df['date'] == target_date_dash]
            
            if len(target_rows) == 0:
                no_data += 1
                continue
            
            row = target_rows.iloc[0]
            
            # 处理数据
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
            
            # 计算涨跌幅（需要前一天数据）
            prev_rows = df[df['date'] < target_date_dash]
            if len(prev_rows) > 0:
                prev_close = safe_float(prev_rows.iloc[-1]['close'])
                curr_close = safe_float(row['close'])
                if prev_close > 0:
                    change_pct = (curr_close - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0
            else:
                change_pct = 0.0
            
            # 计算振幅
            high = safe_float(row['high'])
            low = safe_float(row['low'])
            if len(prev_rows) > 0:
                prev_close = safe_float(prev_rows.iloc[-1]['close'])
                if prev_close > 0:
                    amplitude = (high - low) / prev_close * 100
                else:
                    amplitude = 0.0
            else:
                amplitude = 0.0
            
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
                stock_id,
                target_date_dash,
                safe_float(row['open']),
                safe_float(row['close']),
                safe_float(row['high']),
                safe_float(row['low']),
                safe_float(row['volume']),
                safe_float(row['amount']),
                change_pct,
                amplitude,
                safe_float(row['turn'])
            ))
            conn.commit()
            success += 1
            
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f'  处理失败 {code}: {e}')
        
        # 进度显示
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 无数据:{no_data} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    elapsed = time.time() - start_time
    print()
    print('=' * 60)
    print(f'✓ 完成: 成功 {success}, 失败 {fail}, 无数据 {no_data}')
    print(f'耗时: {elapsed:.1f}s')
    print('=' * 60)

if __name__ == '__main__':
    from datetime import date
    
    # 默认更新昨天，可指定日期
    target = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    update_stock_daily_baostock(target)