#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Baostock 更新指定日期的股票历史行情数据
增强版：自动处理会话超时，分批更新
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

class BaostockUpdater:
    def __init__(self):
        self.logged_in = False
        self.login_time = 0
        self.session_timeout = 120  # 2分钟会话超时
        
    def ensure_login(self):
        """确保登录状态有效"""
        current_time = time.time()
        
        # 如果超过会话时间，先登出再重新登录
        if self.logged_in and (current_time - self.login_time) > self.session_timeout:
            try:
                bs.logout()
            except:
                pass
            self.logged_in = False
        
        if not self.logged_in:
            lg = bs.login()
            if lg.error_code != '0':
                print(f'Baostock 登录失败: {lg.error_msg}')
                return False
            self.logged_in = True
            self.login_time = current_time
            return True
        
        return True
    
    def query_with_retry(self, bs_code, start_date, end_date, max_retries=3):
        """带重试的查询"""
        for attempt in range(max_retries):
            try:
                # 确保登录
                if not self.ensure_login():
                    continue
                
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,code,open,high,low,close,volume,amount,turn",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="2"
                )
                
                if rs.error_code == '0':
                    return rs
                elif '未登录' in rs.error_msg or 'login' in rs.error_msg.lower():
                    # 会话过期，重新登录
                    self.logged_in = False
                    continue
                else:
                    return None
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logged_in = False
                    time.sleep(1)
                else:
                    return None
        
        return None
    
    def update_stock_daily(self, target_date_str):
        """更新指定日期的股票历史行情数据"""
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
        
        conn = pymysql.connect(**DB)
        cursor = conn.cursor()
        
        # 获取股票代码到 stock_id 的映射
        cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%" OR code LIKE "60%" OR code LIKE "00%"')
        stock_map = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
        print(f'共 {len(stock_map)} 只股票')
        
        # 获取前几天的日期（用于计算涨跌幅）
        prev_date = target_date - timedelta(days=5)
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
                
                # 查询数据（带重试）
                rs = self.query_with_retry(bs_code, start_date, end_date)
                
                if rs is None:
                    fail += 1
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
                
                # 计算涨跌幅
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
            
            # 进度显示
            if i % 500 == 0:
                elapsed = time.time() - start_time
                print(f'进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 无数据:{no_data} 耗时:{elapsed:.0f}s')
        
        cursor.close()
        conn.close()
        
        # 登出
        if self.logged_in:
            try:
                bs.logout()
            except:
                pass
        
        elapsed = time.time() - start_time
        print()
        print('=' * 60)
        print(f'✓ 完成: 成功 {success}, 失败 {fail}, 无数据 {no_data}')
        print(f'耗时: {elapsed:.1f}s')
        print('=' * 60)

if __name__ == '__main__':
    updater = BaostockUpdater()
    
    # 默认更新昨天
    target = sys.argv[1] if len(sys.argv) > 1 else (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
    updater.update_stock_daily(target)
