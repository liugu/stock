#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重试更新缺失的今日数据 - 带重试机制"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta
import baostock as bs

DB = {'host': 'localhost', 'user': 'stock', 'password': '12345678',
      'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'}

today = date(2026, 7, 2)
today_str = today.strftime('%Y-%m-%d')
today_yyyymmdd = today_str.replace('-', '')

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 查询已有今日数据的股票
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (today_str,))
existing = set(r[0] for r in cursor.fetchall())
print(f'已有今日数据的股票: {len(existing)} 只')

# 获取所有股票
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%%" OR code LIKE "60%%" OR code LIKE "00%%"')
stock_map = {r[1]: (r[0], r[2]) for r in cursor.fetchall()}

# 过滤出缺少今日数据的
missing = {k: v for k, v in stock_map.items() if v[0] not in existing}
print(f'需要补充: {len(missing)} 只')

if not missing:
    print('全部已更新，无需补充')
    sys.exit(0)

# Baostock登录
lg = bs.login()
if lg.error_code != '0':
    print(f'Baostock登录失败: {lg.error_msg}')
    sys.exit(1)
print('login success!')

success = fail = 0
start_time = time.time()

for i, (code, (sid, name)) in enumerate(missing.items(), 1):
    # 尝试3次
    for attempt in range(3):
        try:
            if code.startswith(('600','601','603','605','688','689')):
                bs_code = f'sh.{code}'
            else:
                bs_code = f'sz.{code}'
            
            yesterday = (today - timedelta(days=5)).strftime('%Y-%m-%d')
            rs = bs.query_history_k_data_plus(
                bs_code, "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pbMRQ,peTTM",
                start_date=yesterday, end_date=today_str, frequency="d", adjustflag="2")
            
            if rs.error_code == '0':
                dl = []
                while rs.next():
                    dl.append(rs.get_row_data())
                if dl:
                    df = pd.DataFrame(dl, columns=rs.fields)
                    df['date'] = pd.to_datetime(df['date'])
                    for c in ['open','high','low','close','volume','amount','turn']:
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                    
                    td = df[df['date'] == pd.Timestamp(today)]
                    if not td.empty:
                        row = td.iloc[-1]
                        def sf(v):
                            if v is None: return 0.0
                            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return 0.0
                            return float(v)
                        
                        if len(df) >= 2 and not df.iloc[-2].isna().any():
                            pc = float(df.iloc[-2]['close'])
                            cc = float(row['close'])
                            cp = ((cc - pc) / pc * 100) if pc > 0 else 0.0
                            amp = ((float(row['high']) - float(row['low'])) / pc * 100) if pc > 0 else 0.0
                        else:
                            cp = amp = 0.0
                        
                        sql = """INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),low=VALUES(low),
volume=VALUES(volume),amount=VALUES(amount),change_percent=VALUES(change_percent),
amplitude=VALUES(amplitude),turnover_rate=VALUES(turnover_rate)"""
                        cursor.execute(sql, (sid, today_str, sf(row['open']), sf(row['close']),
                                            sf(row['high']), sf(row['low']), sf(row['volume']),
                                            sf(row['amount']), cp, amp, sf(row['turn'])))
                        conn.commit()
                        success += 1
                        break  # success, break retry loop
            # If failed, wait and retry
            if attempt < 2:
                time.sleep(0.5)
        except Exception as e:
            if attempt == 2:
                fail += 1
                if fail <= 5:
                    print(f'  [{i}] {code} 失败: {e}')
            else:
                time.sleep(1)
    
    if i % 200 == 0:
        elapsed = int(time.time() - start_time)
        print(f'进度: {i}/{len(missing)} 成功:{success} 失败:{fail} 耗时:{elapsed}s')

bs.logout()
cursor.close()
conn.close()
elapsed = int(time.time() - start_time)
print(f'\n✓ 补充完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed}s')
