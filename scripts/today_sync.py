#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
import time
import baostock as bs
from datetime import datetime

# 禁用缓冲
sys.stdout.flush()

DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

date_str = '2026-06-25'

# 获取股票列表
conn = pymysql.connect(**DB)
cursor = conn.cursor()
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%" ORDER BY code')
stocks = {row[1]: {'id': row[0], 'name': row[2]} for row in cursor.fetchall()}
cursor.execute('SELECT stock_id FROM stock_daily WHERE date = %s', (date_str,))
existing = set(row[0] for row in cursor.fetchall())
conn.close()

to_update = {code: info for code, info in stocks.items() if info['id'] not in existing}
print(f"日期: {date_str}, 需更新: {len(to_update)} 只", flush=True)

if not to_update:
    print("无需更新")
else:
    lg = bs.login()
    success, fail, batch_data = 0, 0, []
    start_time = time.time()
    
    for i, (code, info) in enumerate(to_update.items(), 1):
        try:
            bs_code = f'sh.{code}' if code.startswith(('6')) else f'sz.{code}'
            rs = bs.query_history_k_data_plus(bs_code, "date,open,high,low,close,volume,amount,turn",
                start_date='2026-06-18', end_date=date_str, frequency="d", adjustflag="2")
            
            if rs.error_code != '0':
                fail += 1
                continue
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                fail += 1
                continue
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            target = df[df['date'] == date_str]
            if len(target) == 0:
                fail += 1
                continue
            
            row = target.iloc[0]
            
            def sf(v):
                try:
                    if v is None or v == '' or v == '0.000':
                        return 0.0
                    f = float(v)
                    return 0.0 if np.isnan(f) or np.isinf(f) else f
                except:
                    return 0.0
            
            prev = df[df['date'] < date_str]
            pc = sf(prev.iloc[-1]['close']) if len(prev) > 0 else sf(row['close'])
            cc = sf(row['close'])
            ch = (cc - pc) / pc * 100 if pc > 0 else 0
            hi, lo = sf(row['high']), sf(row['low'])
            amp = (hi - lo) / pc * 100 if pc > 0 else 0
            
            batch_data.append((info['id'], date_str, sf(row['open']), cc, hi, lo,
                sf(row['volume']), sf(row['amount']), ch, amp, sf(row['turn'])))
            success += 1
            
            if len(batch_data) >= 100:
                conn = pymysql.connect(**DB)
                cur = conn.cursor()
                cur.executemany('INSERT INTO stock_daily VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', batch_data)
                conn.commit()
                conn.close()
                batch_data = []
                print(f"[{i}/{len(to_update)}] OK:{success} Fail:{fail}", flush=True)
        except:
            fail += 1
    
    if batch_data:
        conn = pymysql.connect(**DB)
        cur = conn.cursor()
        cur.executemany('INSERT INTO stock_daily VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', batch_data)
        conn.commit()
        conn.close()
    
    bs.logout()
    print(f"完成: OK {success}, Fail {fail}, 耗时 {time.time()-start_time:.1f}s")
