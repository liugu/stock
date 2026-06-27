#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import numpy as np
import time
from datetime import date, timedelta

DB = {'host': 'localhost', 'user': 'stock', 'password': '12345678', 'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'}

from instock.core.crawling.data_adapter_enhanced import get_stock_hist, baostock_logout

# 批次参数
BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 500
OFFSET = int(sys.argv[2]) if len(sys.argv) > 2 else 0

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取所有股票
cursor.execute('''
    SELECT s.id, s.code, s.name 
    FROM stock_info s
    WHERE s.code LIKE "30%" OR s.code LIKE "60%" OR s.code LIKE "00%" OR s.code LIKE "68%"
''')
all_stocks = cursor.fetchall()

# 获取已更新的股票ID
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (date.today(),))
updated_ids = set(row[0] for row in cursor.fetchall())

# 过滤未更新的
pending = [(row[0], row[1], row[2]) for row in all_stocks if row[0] not in updated_ids]
print(f'待更新总数: {len(pending)}')

# 分批处理
batch = pending[OFFSET:OFFSET+BATCH_SIZE]
print(f'本批次处理: {len(batch)} 只 (从 {OFFSET} 开始)')

today = date.today()
end_date = today.strftime('%Y%m%d')
start_date = (today - timedelta(days=5)).strftime('%Y%m%d')

success, fail = 0, 0

for i, (stock_id, code, name) in enumerate(batch, 1):
    try:
        df = get_stock_hist(code, start_date, end_date)
        if df is not None and not df.empty:
            row = df.iloc[-1]
            date_str = str(row['日期'])[:10]
            if date_str == str(today):
                def safe_float(val):
                    try:
                        f = float(val)
                        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
                    except:
                        return 0.0
                
                open_p = safe_float(row.get('开盘', 0))
                high_p = safe_float(row.get('最高', 0))
                low_p = safe_float(row.get('最低', 0))
                close_p = safe_float(row.get('收盘', 0))
                volume = safe_float(row.get('成交量', 0))
                amount = safe_float(row.get('成交额', 0))
                
                cursor.execute('''
                    INSERT INTO stock_daily (stock_id, date, open, high, low, close, volume, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE open=%s, high=%s, low=%s, close=%s, volume=%s, amount=%s
                ''', (stock_id, today, open_p, high_p, low_p, close_p, volume, amount,
                      open_p, high_p, low_p, close_p, volume, amount))
                conn.commit()
                success += 1
            else:
                fail += 1
        else:
            fail += 1
    except Exception as e:
        fail += 1
    
    if i % 50 == 0:
        print(f'进度: {i}/{len(batch)} 成功:{success} 失败:{fail}')

conn.close()
baostock_logout()
print(f'\n批次完成: 成功 {success}, 失败 {fail}')
