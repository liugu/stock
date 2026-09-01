#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""更新今日 stock_daily - 200只重连 + 3轮重试"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
BATCH_SIZE = 200

def sf(v):
    try:
        if v is None or v == '' or v == '0.000': return 0.0
        f = float(v)
        return 0.0 if np.isnan(f) or np.isinf(f) else f
    except: return 0.0

today = date.today().strftime('%Y-%m-%d')
start = (date.today() - timedelta(5)).strftime('%Y-%m-%d')

conn = pymysql.connect(**DB)
c = conn.cursor()
c.execute('''SELECT i.id,i.code FROM stock_info i
WHERE (i.code LIKE "60%%" OR i.code LIKE "00%%" OR i.code LIKE "30%%")
AND i.code NOT LIKE "688%%" ORDER BY i.code''')
stocks = c.fetchall()
c.close(); conn.close()

c = pymysql.connect(**DB).cursor()
c.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date=%s', (today,))
existing = {r[0] for r in c.fetchall()}
c.close()
to_update = [(sid,code) for sid,code in stocks if sid not in existing]

print(f'{today} | 总{len(stocks)}只 已有{len(existing)} 需更新{len(to_update)}')
if not to_update: print('✓ 全部完成'); sys.exit(0)

def do_login():
    try: bs.logout()
    except: pass
    lg = bs.login()
    return lg.error_code == '0'

total_ok = 0
total_fail = 0
t0 = time.time()

for retry_round in range(3):
    if not to_update: break
    do_login()
    print(f'\n--- 第{retry_round+1}轮重试, 剩余{len(to_update)}只 ---')
    
    for bi in range(0, len(to_update), BATCH_SIZE):
        batch = to_update[bi:bi+BATCH_SIZE]
        for sid, code in batch:
            try:
                sym = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
                rs = bs.query_history_k_data_plus(
                    sym, 'date,code,open,high,low,close,volume,amount,turn',
                    start_date=start, end_date=today, frequency='d', adjustflag='3')
                if rs.error_code != '0': total_fail += 1; continue
                rows = []
                while rs.next(): rows.append(rs.get_row_data())
                if not rows: total_fail += 1; continue
                
                d = pd.DataFrame(rows, columns=rs.fields)
                tr = d[d['date']==today]
                if tr.empty: total_fail += 1; continue
                r = tr.iloc[-1]
                
                pr = d[d['date']<today]
                chg = 0.0; amp = 0.0
                if not pr.empty:
                    pc = sf(pr.iloc[-1]['close'])
                    cc = sf(r['close'])
                    if pc > 0: chg = round((cc-pc)/pc*100, 2)
                    hi = sf(r['high']); lo = sf(r['low'])
                    if pc > 0: amp = round((hi-lo)/pc*100, 2)
                
                conn = pymysql.connect(**DB)
                cc = conn.cursor()
                cc.execute('''INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                    low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                    change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                    turnover_rate=VALUES(turnover_rate)''',
                    (sid,today,sf(r['open']),sf(r['close']),sf(r['high']),sf(r['low']),
                     sf(r['volume']),sf(r['amount']),chg,amp,sf(r['turn'])))
                conn.commit()
                cc.close(); conn.close()
                total_ok += 1
            except:
                total_fail += 1
        
        elapsed = time.time() - t0
        done = min(bi+BATCH_SIZE, len(to_update))
        rate = total_ok/elapsed*60 if elapsed>0 else 0
        print(f'  B{bi//BATCH_SIZE+1}: {done}/{len(to_update)} | OK{total_ok} FAIL{total_fail} | {elapsed:.0f}s | {rate:.0f}/min')
    
    # re-login before next round
    do_login()
    # rebuild to_update: missing stocks only
    conn = pymysql.connect(**DB)
    c = conn.cursor()
    c.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date=%s', (today,))
    now_exist = {r[0] for r in c.fetchall()}
    c.close(); conn.close()
    to_update = [(sid,code) for sid,code in stocks if sid not in now_exist]

elapsed = time.time() - t0
print(f'\n=== 完成 === OK{total_ok} FAIL{total_fail} 用时{elapsed:.0f}s({elapsed/60:.1f}分)')

conn = pymysql.connect(**DB)
c = conn.cursor()
c.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date=%s', (today,))
print(f'今日stock_daily总计: {c.fetchone()[0]}只')
c.close(); conn.close()
try: bs.logout()
except: pass