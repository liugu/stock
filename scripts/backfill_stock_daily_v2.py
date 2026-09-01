#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补全 stock_daily 缺失数据 - v2 增强版
- 小批次(50只) + 长间隔
- 单只失败时短暂等待 + 单独重试
- 使用 baostock 最新API参数
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
    time.sleep(2)
    lg = bs.login()
    return lg.error_code == '0'

target = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime('%Y-%m-%d')
print('='*60)
print(f'补全 stock_daily v2 - {target}')
print('='*60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 读取失败列表
if os.path.exists(FAIL_LOG) and 'all' not in sys.argv:
    with open(FAIL_LOG, 'r', encoding='utf-8') as f:
        fail_data = json.load(f)
    stocks_to_fix = [(s['sid'], s['code']) for s in fail_data.get('stocks', [])]
    print(f'从失败列表读取 {len(stocks_to_fix)} 只')
else:
    cursor.execute('''SELECT si.id, si.code FROM stock_info si
        WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
        AND si.code NOT LIKE "688%%"
        AND si.id NOT IN (
            SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s
        )''', (target,))
    stocks_to_fix = cursor.fetchall()
    print(f'数据库检测到 {len(stocks_to_fix)} 只缺失')

if not stocks_to_fix:
    print('\n✓ 没有需要补全的股票')
    cursor.close(); conn.close()
    sys.exit(0)

start = (pd.Timestamp(target) - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
BATCH = 50  # 更小的批次
success = 0
failed = []
all_failed_codes = set()
start_t = time.time()

# 先清空目标日期中这批次股票的旧数据
for bi in range(0, len(stocks_to_fix), BATCH):
    batch = stocks_to_fix[bi:bi + BATCH]
    sids = [str(s[0]) for s in batch]
    if sids:
        cursor.execute(f'DELETE FROM stock_daily WHERE date = %s AND stock_id IN ({",".join(sids)})', (target,))
        conn.commit()

print(f'已清除旧数据\n')

for bi in range(0, len(stocks_to_fix), BATCH):
    batch = stocks_to_fix[bi:bi + BATCH]
    
    max_retries = 3
    for attempt in range(max_retries):
        if bs_login():
            break
        print(f'  登录失败，重试({attempt+1}/{max_retries})...')
        time.sleep(5)
    else:
        failed.extend(batch)
        print(f'  批次{bi//BATCH+1}: 登录失败，跳过')
        continue
    
    batch_failed = []
    for sid, code in batch:
        for retry in range(3):
            try:
                bs_code = f'sh.{code}' if code.startswith(('600','601','603','605')) else f'sz.{code}'
                rs = bs.query_history_k_data_plus(
                    bs_code, 'date,code,open,high,low,close,volume,amount,turn',
                    start_date=start, end_date=target, frequency='d', adjustflag='3')
                
                if rs.error_code != '0':
                    if '重复登录' in rs.error_msg or 'not login' in rs.error_msg:
                        # 重连
                        if bs_login():
                            continue
                    time.sleep(0.5)
                    continue
                
                rows = []
                while (rs.error_code == '0') and rs.next():
                    rows.append(rs.get_row_data())
                if not rows:
                    break
                d = pd.DataFrame(rows, columns=rs.fields)
                tr = d[d['date'] == target]
                if tr.empty:
                    break
                
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
                break  # 成功，退出重试循环
            except Exception as e:
                if retry < 2:
                    time.sleep(1)
                    continue
                err_str = str(e)[:60]
                batch_failed.append((sid, code, err_str))
                all_failed_codes.add(code)
                break
    
    failed.extend(batch_failed)
    elapsed = time.time() - start_t
    done = min(bi + BATCH, len(stocks_to_fix))
    rate = success / elapsed * 60 if elapsed > 0 else 0
    print(f'  批次{bi//BATCH+1}: {done}/{len(stocks_to_fix)} | 成功{success} | 本批失败{len(batch_failed)} | {elapsed:.0f}s ({rate:.0f}只/分)')

elapsed = time.time() - start_t
print(f'\n{"="*60}')
print(f'补全完成!')
print(f'成功: {success} 只')
print(f'失败: {len(failed)} 只')
print(f'失败率: {len(failed)/len(stocks_to_fix)*100:.1f}%')
print(f'用时: {elapsed:.0f}s ({elapsed/60:.1f}分)')

cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
cnt = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM stock_info si WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%") AND si.code NOT LIKE "688%%"')
total_si = cursor.fetchone()[0]
print(f'今日总计: {cnt}/{total_si} ({cnt/total_si*100:.1f}%)')

if failed:
    print(f'\n⚠ 仍有 {len(failed)} 只失败，已保存失败列表')
    fail_save = [{'sid':s[0],'code':s[1],'error':s[2][:50] if len(s) > 2 else ''} for s in failed]
    with open(FAIL_LOG, 'w', encoding='utf-8') as f:
        json.dump({'date':target, 'failed_count':len(fail_save), 'stocks':fail_save}, f, ensure_ascii=False, indent=2)
else:
    # 清理失败日志
    if os.path.exists(FAIL_LOG):
        os.remove(FAIL_LOG)

cursor.close(); conn.close()
try: bs.logout()
except: pass