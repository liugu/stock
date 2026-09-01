#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补缺失的单日数据 - 小批次50只"""
import sys, time, json
sys.path.insert(0, 'E:/量化研究/workspace/stock')
import baostock as bs
import pymysql
import pandas as pd
import numpy as np

target = sys.argv[1]
DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
FAIL_LOG = 'E:/量化研究/workspace/stock/output/update_failed_stocks.json'

def sf(v):
    try:
        if v is None or v == '' or v == '0.000': return 0.0
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except: return 0.0

def bs_login():
    try: bs.logout()
    except: pass
    time.sleep(1)
    lg = bs.login()
    return lg.error_code == '0'

conn = pymysql.connect(**DB)
cur = conn.cursor()
start = (pd.Timestamp(target) - pd.Timedelta(days=5)).strftime('%Y-%m-%d')

cur.execute("""SELECT si.id, si.code FROM stock_info si
    WHERE (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
    AND si.code NOT LIKE '688%%'
    ORDER BY si.code""")
all_stocks = cur.fetchall()
print(f'{target}: 总{len(all_stocks)}只')

BATCH = 50  # 小批次
success = 0
failed = []
start_t = time.time()

for bi in range(0, len(all_stocks), BATCH):
    batch = all_stocks[bi:bi+BATCH]
    if not bs_login():
        print('  登录失败')
        failed.extend(batch)
        continue
    
    for sid, code in batch:
        try:
            bs_code = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
            rs = bs.query_history_k_data_plus(
                bs_code, 'date,code,open,high,low,close,volume,amount,turn',
                start_date=start, end_date=target, frequency='d', adjustflag='3')
            if rs.error_code != '0': continue
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())
            if not rows: continue
            d = pd.DataFrame(rows, columns=rs.fields)
            tr = d[d['date'] == target]
            if tr.empty: continue
            r = tr.iloc[-1]
            pr = d[d['date'] < target]
            chg = 0.0; amp = 0.0
            if not pr.empty:
                pc = sf(pr.iloc[-1]['close'])
                cc = sf(r['close'])
                if pc > 0: chg = round((cc-pc)/pc*100, 2)
                hi = sf(r['high']); lo = sf(r['low'])
                if pc > 0: amp = round((hi-lo)/pc*100, 2)
            cur.execute("""INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                turnover_rate=VALUES(turnover_rate)""",
                (sid, target, sf(r['open']), sf(r['close']), sf(r['high']), sf(r['low']),
                 sf(r['volume']), sf(r['amount']), chg, amp, sf(r['turn'])))
            conn.commit()
            success += 1
        except:
            pass
    
    elapsed = time.time() - start_t
    done = min(bi+BATCH, len(all_stocks))
    rate = success / elapsed * 60 if elapsed > 0 else 0
    print(f'  批次{bi//BATCH+1}: {done}/{len(all_stocks)} | 成功{success} | {rate:.0f}只/分')

cur.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
cnt = cur.fetchone()[0]
print(f'{target}完成: {cnt}/{len(all_stocks)} ({cnt/len(all_stocks)*100:.1f}%) 用时{time.time()-start_t:.0f}s')

cur.close()
conn.close()
try: bs.logout()
except: pass