#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健壮的 stock_daily 更新脚本
功能：
1. 断点续传 - 只更新缺失的股票
2. 自动重试失败股票（最多3次）
3. 每200只重新登录，避免连接断开
4. 停牌/退市股票直接标记永久失败，不浪费重试
5. 记录失败列表，支持后续补全
6. 每次 commit，不丢失进度
"""
import sys, os, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import baostock as bs
import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime

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
    time.sleep(0.5)
    lg = bs.login()
    return lg.error_code == '0'

print('='*60)
today = date.today()
target = today.strftime('%Y-%m-%d')
start = (today - timedelta(days=5)).strftime('%Y-%m-%d')
print(f'更新 stock_daily - {target}')
print('='*60)

# 连接数据库
conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取全部A股
cursor.execute("""SELECT si.id, si.code FROM stock_info si
WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
AND si.code NOT LIKE "688%%"
ORDER BY si.code""")
all_stocks = cursor.fetchall()
print(f'总A股: {len(all_stocks)} 只')

# 获取已有今日数据的
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (target,))
existing = {r[0] for r in cursor.fetchall()}
print(f'今日已有: {len(existing)} 只')

# 需要更新的
to_update = [(sid, code) for sid, code in all_stocks if sid not in existing]
print(f'需要更新: {len(to_update)} 只')

if not to_update:
    print('\n✓ 全部已是最新')
    cursor.close(); conn.close(); sys.exit(0)

BATCH = 200
RETRY_MAX = 3

# 失败记录
failed = []  # [(sid, code, error)] 详细日志
permanent_fail = []  # 停牌/退市，不重试
success = 0
start_t = time.time()

for retry_round in range(RETRY_MAX):
    if not to_update:
        break

    print(f'\n--- 第{retry_round+1}轮重试, 剩余{len(to_update)}只 ---')
    batch_failed = []

    for bi in range(0, len(to_update), BATCH):
        batch = to_update[bi:bi + BATCH]

        if not bs_login():
            print('登录失败，5秒后重试...')
            time.sleep(5)
            if not bs_login():
                print('登录失败，终止')
                batch_failed.extend(batch)
                break

        for sid, code in batch:
            try:
                bs_code = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
                rs = bs.query_history_k_data_plus(
                    bs_code, 'date,code,open,high,low,close,volume,amount,turn',
                    start_date=start, end_date=target, frequency='d', adjustflag='3')

                if rs.error_code != '0':
                    failed.append((sid, code, rs.error_msg))
                    batch_failed.append((sid, code))
                    continue

                rows = []
                while (rs.error_code == '0') and rs.next():
                    rows.append(rs.get_row_data())
                if not rows:
                    # 无数据 = 停牌/退市，永久失败不重试
                    failed.append((sid, code, 'no_data'))
                    permanent_fail.append((sid, code))
                    continue

                d = pd.DataFrame(rows, columns=rs.fields)
                tr = d[d['date'] == target]
                if tr.empty:
                    # 今日无数据 = 停牌/退市，永久失败不重试
                    failed.append((sid, code, 'no_today_data'))
                    permanent_fail.append((sid, code))
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
                failed.append((sid, code, str(e)[:50]))
                batch_failed.append((sid, code))

        elapsed = time.time() - start_t
        done = min(bi + BATCH, len(to_update))
        rate = success / elapsed * 60 if elapsed > 0 else 0
        print(f'  批次{bi//BATCH+1}: {done}/{len(to_update)} | 成功{success} | 本批失败{len(batch_failed)} | {rate:.0f}只/分')

    to_update = batch_failed  # 只重试网络/错误类失败

    if to_update and retry_round < RETRY_MAX - 1:
        print(f'\n  等待10秒后重试 {len(to_update)} 只失败股票...')
        time.sleep(10)

# 最终结果
elapsed = time.time() - start_t
all_failed_cnt = len(to_update) + len(permanent_fail)
print(f'\n{"="*60}')
print(f'更新完成!')
print(f'成功: {success} 只')
print(f'可重试失败: {len(to_update)} 只 | 停牌退市: {len(permanent_fail)} 只')
print(f'用时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)')

cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
final_cnt = cursor.fetchone()[0]
print(f'今日总计: {final_cnt}/{len(all_stocks)} 只 ({final_cnt/len(all_stocks)*100:.1f}%)')

# 保存失败列表
all_failed_stocks = to_update + permanent_fail
if all_failed_stocks:
    fail_data = [{'sid':sid, 'code':code, 'error':'retryable'} for sid,code in to_update] + \
                [{'sid':sid, 'code':code, 'error':'permanent_offline'} for sid,code in permanent_fail]
    with open(FAIL_LOG, 'w', encoding='utf-8') as f:
        json.dump({'date': target, 'failed_count': len(fail_data), 'stocks': fail_data}, f, ensure_ascii=False, indent=2)
    print(f'失败列表已保存: {FAIL_LOG}')
    if to_update:
        print(f'  可重试: {len(to_update)} 只')
    if permanent_fail:
        print(f'  停牌退市: {len(permanent_fail)} 只')

cursor.close(); conn.close()
try: bs.logout()
except: pass