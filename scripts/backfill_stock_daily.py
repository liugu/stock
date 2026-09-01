#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补全 stock_daily 缺失数据
从 update_failed_stocks.json 读取失败列表并重试
或由用户指定日期和股票范围
"""
import sys, os, json, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta

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

# 参数
target = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime('%Y-%m-%d')
mode = sys.argv[2] if len(sys.argv) > 2 else 'auto'

print('='*60)
print(f'补全 stock_daily - {target}')
print(f'模式: {mode}')
print('='*60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()

if mode == 'auto':
    # 自动模式：读取失败列表
    if os.path.exists(FAIL_LOG):
        with open(FAIL_LOG, 'r', encoding='utf-8') as f:
            fail_data = json.load(f)
        stocks_to_fix = [(s['sid'], s['code']) for s in fail_data.get('stocks', [])]
        print(f'从失败列表读取 {len(stocks_to_fix)} 只需补全')
    else:
        # 自动检测缺失的
        cursor.execute('''SELECT si.id, si.code FROM stock_info si
            WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
            AND si.code NOT LIKE "688%%"
            AND si.id NOT IN (
                SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s
            )''', (target,))
        stocks_to_fix = cursor.fetchall()
        print(f'数据库检测到 {len(stocks_to_fix)} 只缺失')
elif mode == 'all':
    # 全部模式：重补所有
    cursor.execute('''SELECT si.id, si.code FROM stock_info si
        WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
        AND si.code NOT LIKE "688%%"''')
    stocks_to_fix = cursor.fetchall()
    print(f'全部模式: {len(stocks_to_fix)} 只')
else:
    print(f'未知模式: {mode}')
    sys.exit(1)

if not stocks_to_fix:
    print('\n✓ 没有需要补全的股票')
    cursor.close(); conn.close(); sys.exit(0)

start = (pd.Timestamp(target) - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
BATCH = 200
success = 0
failed = []
start_t = time.time()

# 先删除目标日期的旧数据（如果有且不全的）
cursor.execute('DELETE FROM stock_daily WHERE date = %s AND stock_id IN (' +
    ','.join([str(s[0]) for s in stocks_to_fix]) + ')', (target,))
conn.commit()
print(f'已清除 {len(stocks_to_fix)} 只的旧数据（如有）')

for bi in range(0, len(stocks_to_fix), BATCH):
    batch = stocks_to_fix[bi:bi + BATCH]
    if not bs_login():
        print('登录失败，等待重试...')
        time.sleep(5)
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
                failed.append((sid, code)); continue
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())
            if not rows: failed.append((sid, code)); continue
            d = pd.DataFrame(rows, columns=rs.fields)
            tr = d[d['date'] == target]
            if tr.empty: failed.append((sid, code)); continue
            
            r = tr.iloc[-1]
            pr = d[d['date'] < target]
            chg = 0.0; amp = 0.0
            if not pr.empty:
                pc = sf(pr.iloc[-1]['close'])
                cc = sf(r['close'])
                if pc > 0: chg = round((cc-pc)/pc*100, 2)
                hi = sf(r['high']); lo = sf(r['low'])
                if pc > 0: amp = round((hi-lo)/pc*100, 2)
            
            cursor.execute('''INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (sid, target, sf(r['open']), sf(r['close']), sf(r['high']), sf(r['low']),
                 sf(r['volume']), sf(r['amount']), chg, amp, sf(r['turn'])))
            conn.commit()
            success += 1
        except:
            failed.append((sid, code))
    
    elapsed = time.time() - start_t
    done = min(bi + BATCH, len(stocks_to_fix))
    print(f'  批次{bi//BATCH+1}: {done}/{len(stocks_to_fix)} | 成功{success} 失败{len(failed)} | {elapsed:.0f}s')

elapsed = time.time() - start_t
print(f'\n{"="*60}')
print(f'补全完成!')
print(f'成功: {success} 只')
print(f'失败: {len(failed)} 只')
print(f'用时: {elapsed:.0f}s ({elapsed/60:.1f}分)')

cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
cnt = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM stock_info si WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%") AND si.code NOT LIKE "688%%"')
total = cursor.fetchone()[0]
print(f'今日总计: {cnt}/{total} ({cnt/total*100:.1f}%)')

if failed:
    print(f'\n⚠ 仍有 {len(failed)} 只失败，可再次运行补全')
    with open(FAIL_LOG, 'w', encoding='utf-8') as f:
        json.dump({'date':target, 'failed_count':len(failed), 'stocks':[{'sid':s[0],'code':s[1]} for s in failed]}, f, ensure_ascii=False, indent=2)

cursor.close(); conn.close()
try: bs.logout()
except: pass
