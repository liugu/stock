#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""高效更新今日 stock_daily - Baostock 直连 + 分批"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import baostock as bs
import numpy as np
from datetime import date, timedelta

def sf(v):
    if v is None or v == '' or v == '0.000': return 0.0
    try:
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except: return 0.0

def login():
    try: bs.logout()
    except: pass
    time.sleep(0.3)
    lg = bs.login()
    return lg.error_code == '0'

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

print('='*60)
print('高效更新今日 stock_daily (Baostock 直连 + 每300只重登)')
print('='*60)

today = date.today()
target = today.strftime('%Y-%m-%d')
start = (today - timedelta(days=5)).strftime('%Y-%m-%d')
print(f'目标日期: {target}')

conn = pymysql.connect(**DB)
cursor = conn.cursor()
cursor.execute('''SELECT si.id, si.code FROM stock_info si
WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
AND si.code NOT LIKE "688%%"
ORDER BY si.code''')
stocks = cursor.fetchall()

cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (target,))
existing = {r[0] for r in cursor.fetchall()}
to_update = [(sid, code) for sid, code in stocks if sid not in existing]
print(f'总股票: {len(stocks)}, 今日已有: {len(existing)}, 需更新: {len(to_update)}')

if not to_update:
    print('\n✓ 全部已完成')
    cursor.close(); conn.close(); sys.exit(0)

BATCH = 300
success = fail = 0
start_t = time.time()

for bi in range(0, len(to_update), BATCH):
    batch = to_update[bi:bi + BATCH]
    if not login():
        print('登录失败，终止'); break
    
    batch_start = time.time()
    for sid, code in batch:
        try:
            bs_code = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
            rs = bs.query_history_k_data_plus(
                bs_code, 'date,code,open,high,low,close,volume,amount,turn',
                start_date=start, end_date=target, frequency='d', adjustflag='3'
            )
            if rs.error_code != '0':
                fail += 1; continue
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())
            if not rows: fail += 1; continue
            
            d = pd.DataFrame(rows, columns=rs.fields)
            tr = d[d['date'] == target]
            if tr.empty: fail += 1; continue
            r = tr.iloc[-1]
            
            pr = d[d['date'] < target]
            chg = 0.0; amp = 0.0
            if not pr.empty:
                pc = sf(pr.iloc[-1]['close'])
                cc = sf(r['close'])
                if pc > 0: chg = round((cc-pc)/pc*100, 2)
                hi = sf(r['high']); lo = sf(r['low'])
                if pc > 0: amp = round((hi-lo)/pc*100, 2)
            
            cursor.execute('''INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                turnover_rate=VALUES(turnover_rate)''',
                (sid, target, sf(r['open']), sf(r['close']), sf(r['high']), sf(r['low']),
                 sf(r['volume']), sf(r['amount']), chg, amp, sf(r['turn'])))
            conn.commit()
            success += 1
        except Exception as e:
            fail += 1
    
    elapsed = time.time() - start_t
    batch_t = time.time() - batch_start
    done = min(bi + BATCH, len(to_update))
    rate = success / elapsed * 60 if elapsed > 0 else 0
    print(f'批次{bi//BATCH+1}: {done}/{len(to_update)} | 成功{success} 失败{fail} | {batch_t:.0f}s批 | {rate:.0f}只/分 | 总{elapsed:.0f}s')

bt = time.time() - start_t
print(f'\n=== 完成 === 成功{success} 失败{fail} 用时{bt:.0f}s({bt/60:.1f}分)')

cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
final = cursor.fetchone()[0]
pct = final/len(stocks)*100
print(f'今日总计: {final}/{len(stocks)} ({pct:.1f}%)')
cursor.close(); conn.close()
try: bs.logout()
except: pass
