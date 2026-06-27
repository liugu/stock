#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
后台更新今日数据 - 使用 baostock 多线程
"""
import sys, os, time, threading
sys.path.insert(0, 'E:/量化研究/workspace/stock')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import baostock as bs
import pymysql
from datetime import date, timedelta

bs.login()

today_str = '2026-06-24'
prev_date = '2026-06-23'

# 获取待更新股票
conn = pymysql.connect(host='localhost', user='stock', password='12345678', database='instock', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute('''SELECT id, code, name FROM stock_info 
WHERE code REGEXP "^(600|601|603|605|000|001|002|003|300|301)" 
AND id NOT IN (SELECT stock_id FROM stock_daily WHERE date = "2026-06-24")''')
stocks = cursor.fetchall()
cursor.close()
conn.close()

print(f'待更新: {len(stocks)} 只股票', flush=True)

if len(stocks) == 0:
    print('已完成，无需更新', flush=True)
    bs.logout()
    sys.exit(0)

success, fail = 0, 0
lock = threading.Lock()

def update_stock(s):
    global success, fail
    stock_id, code, name = s
    bs_code = f'sh.{code}' if code.startswith('6') else f'sz.{code}'
    
    try:
        rs = bs.query_history_k_data_plus(bs_code, 'date,open,high,low,close,volume,amount,turn',
            start_date=today_str, end_date=today_str, frequency='d', adjustflag='3')
        rows = []
        while rs.next(): rows.append(rs.get_row_data())
        if not rows: return
        
        r = rows[0]
        close = float(r[4]) if r[4] else 0
        if close <= 0: return
        
        open_p = float(r[1]) if r[1] else 0
        high = float(r[2]) if r[2] else 0
        low = float(r[3]) if r[3] else 0
        vol = float(r[5]) if r[5] else 0
        amt = float(r[6]) if r[6] else 0
        turn = float(r[7]) if r[7] else 0
        
        rs2 = bs.query_history_k_data_plus(bs_code, 'close', start_date=prev_date, end_date=prev_date, frequency='d', adjustflag='3')
        prev_c = 0
        while rs2.next(): 
            if rs2.get_row_data()[0]: prev_c = float(rs2.get_row_data()[0])
        
        chg = ((close - prev_c) / prev_c * 100) if prev_c > 0 else 0
        amp = ((high - low) / prev_c * 100) if prev_c > 0 else 0
        
        c = pymysql.connect(host='localhost', user='stock', password='12345678', database='instock', charset='utf8mb4')
        cur = c.cursor()
        cur.execute('''INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
            volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent), amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)''',
            (stock_id, r[0], open_p, close, high, low, vol, amt, chg, amp, turn))
        c.commit()
        cur.close()
        c.close()
        with lock: success += 1
    except:
        with lock: fail += 1

from concurrent.futures import ThreadPoolExecutor, as_completed
t0 = time.time()

with ThreadPoolExecutor(max_workers=30) as ex:
    futures = [ex.submit(update_stock, s) for s in stocks]
    for i, f in enumerate(as_completed(futures), 1):
        if i % 500 == 0:
            print(f'进度: {i}/{len(stocks)} 成功:{success} 失败:{fail} 耗时:{time.time()-t0:.0f}s', flush=True)

bs.logout()
print(f'完成: 成功 {success}, 失败 {fail}, 耗时 {time.time()-t0:.1f}s', flush=True)

# 最终统计
conn = pymysql.connect(host='localhost', user='stock', password='12345678', database='instock', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM stock_daily WHERE date = "2026-06-24"')
cnt = cursor.fetchone()[0]
print(f'2026-06-24 数据总数: {cnt}', flush=True)
cursor.close()
conn.close()