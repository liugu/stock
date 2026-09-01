#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量更新今日 stock_daily - 验证可行的分批方案"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

def sf(v):
    try:
        if v is None or v == '' or v == '0.000': return 0.0
        f = float(v)
        return 0.0 if np.isnan(f) or np.isinf(f) else f
    except: return 0.0

print('=' * 60)
today = date.today()
target = today.strftime('%Y-%m-%d')
start = (today - timedelta(days=5)).strftime('%Y-%m-%d')
print(f'更新 stock_daily - {target}')
print('=' * 60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()
cursor.execute('''SELECT i.id,i.code FROM stock_info i
WHERE (i.code LIKE "60%%" OR i.code LIKE "00%%" OR i.code LIKE "30%%")
AND i.code NOT LIKE "688%%" ORDER BY i.code''')
stocks = cursor.fetchall()

cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (target,))
existing = {r[0] for r in cursor.fetchall()}
to_update = [(sid,code) for sid,code in stocks if sid not in existing]
print(f'总{len(stocks)}只, 今日已有{len(existing)}, 需更新{len(to_update)}')

if not to_update:
    print('\n✓ 全部最新')
    cursor.close(); conn.close(); sys.exit(0)

lg = bs.login()
if lg.error_code != '0':
    print(f'登录失败: {lg.error_msg}')
    sys.exit(1)
print('登录成功')

success = fail = 0
start_t = time.time()
batch_size = 50

for bi in range(0, len(to_update), batch_size):
    batch = to_update[bi:bi+batch_size]
    for sid, code in batch:
        try:
            sym = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
            rs = bs.query_history_k_data_plus(
                sym, 'date,code,open,high,low,close,volume,amount,turn',
                start_date=start, end_date=target, frequency='d', adjustflag='3')
            if rs.error_code != '0': fail+=1; continue
            rows = []
            while rs.next(): rows.append(rs.get_row_data())
            if not rows: fail+=1; continue
            
            d = pd.DataFrame(rows, columns=rs.fields)
            tr = d[d['date']==target]
            if tr.empty: fail+=1; continue
            r = tr.iloc[-1]
            
            pr = d[d['date']<target]
            chg=0.0; amp=0.0
            if not pr.empty:
                pc = sf(pr.iloc[-1]['close'])
                cc = sf(r['close'])
                if pc>0: chg = round((cc-pc)/pc*100,2)
                hi=sf(r['high']); lo=sf(r['low'])
                if pc>0: amp = round((hi-lo)/pc*100,2)
            
            cursor.execute('''INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                turnover_rate=VALUES(turnover_rate)''',
                (sid,target,sf(r['open']),sf(r['close']),sf(r['high']),sf(r['low']),
                 sf(r['volume']),sf(r['amount']),chg,amp,sf(r['turn'])))
            conn.commit()
            success+=1
        except: fail+=1
    
    elapsed = time.time()-start_t
    done = min(bi+batch_size, len(to_update))
    rate = success/elapsed*60 if elapsed>0 else 0
    print(f'批次{bi//batch_size+1}: {done}/{len(to_update)} | 成功{success} 失败{fail} | {elapsed:.0f}s | {rate:.0f}只/分')

elapsed = time.time()-start_t
print(f'\n=== 完成 === 成功{success} 失败{fail} 用时{elapsed:.0f}s({elapsed/60:.1f}分)')
cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date=%s', (target,))
print(f'今日总计: {cursor.fetchone()[0]}只')
cursor.close(); conn.close()
try: bs.logout()
except: pass
