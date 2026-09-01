#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速补全指定日期的 stock_daily 数据 - 纯 baostock"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

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
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except: return 0.0

def bs_login():
    try: bs.logout()
    except: pass
    time.sleep(0.3)
    lg = bs.login()
    return lg.error_code == '0'

target = sys.argv[1] if len(sys.argv) > 1 else '2026-08-04'
print(f'补全日期: {target}')
start = (pd.Timestamp(target) - timedelta(days=5)).strftime('%Y-%m-%d')

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取全部A股
cursor.execute("""SELECT si.id, si.code FROM stock_info si
    WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
    AND si.code NOT LIKE "688%%"
    ORDER BY si.code""")
all_stocks = cursor.fetchall()

# 已有数据的跳过
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (target,))
existing = {r[0] for r in cursor.fetchall()}
to_update = [(sid, code) for sid, code in all_stocks if sid not in existing]

print(f'总股票: {len(all_stocks)}, 已有: {len(existing)}, 需更新: {len(to_update)}')

if not to_update:
    print('全部已是最新')
    conn.close(); sys.exit(0)

BATCH = 200
success = 0
failed = []
start_t = time.time()

for bi in range(0, len(to_update), BATCH):
    batch = to_update[bi:bi + BATCH]
    if not bs_login():
        time.sleep(3)
        if not bs_login():
            failed.extend(batch)
            continue

    for sid, code in batch:
        try:
            bs_code = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
            rs = bs.query_history_k_data_plus(
                bs_code, 'date,code,open,high,low,close,volume,amount,turn',
                start_date=start, end_date=target, frequency='d', adjustflag='3')
            if rs.error_code != '0':
                failed.append((sid, code))
                continue
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                continue  # 停牌退市，跳过
            d = pd.DataFrame(rows, columns=rs.fields)
            tr = d[d['date'] == target]
            if tr.empty:
                continue
            r = tr.iloc[-1]
            pr = d[d['date'] < target]
            chg = 0.0; amp = 0.0
            if not pr.empty:
                pc = sf(pr.iloc[-1]['close'])
                cc = sf(r['close'])
                if pc > 0: chg = round((cc-pc)/pc*100, 2)
                hi = sf(r['high']); lo = sf(r['low'])
                if pc > 0: amp = round((hi-lo)/pc*100, 2)
            cursor.execute("""INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                turnover_rate=VALUES(turnover_rate)""",
                (sid, target, sf(r['open']), sf(r['close']), sf(r['high']), sf(r['low']),
                 sf(r['volume']), sf(r['amount']), chg, amp, sf(r['turn'])))
            conn.commit()
            success += 1
        except Exception as e:
            failed.append((sid, code))

    elapsed = time.time() - start_t
    done = min(bi + BATCH, len(to_update))
    print(f'  批次{bi//BATCH+1}: {done}/{len(to_update)} | 成功{success} | 失败{len(failed)} | {elapsed:.0f}s')

    try: bs.logout()
    except: pass

elapsed = time.time() - start_t
print(f'\n补全完成! 成功: {success}, 失败: {len(failed)}, 用时: {elapsed:.0f}s ({elapsed/60:.1f}分)')
cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
cnt = cursor.fetchone()[0]
print(f'{target} 总计: {cnt}/{len(all_stocks)} ({cnt/len(all_stocks)*100:.1f}%)')
conn.close()
try: bs.logout()
except: pass