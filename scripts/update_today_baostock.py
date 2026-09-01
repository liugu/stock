#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速更新今日 stock_daily - Baostock 分批重登录"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
import baostock as bs
from datetime import date, timedelta, datetime

def safe_float(v):
    try:
        if v is None or v == '' or v == '0.000': return 0.0
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    except: return 0.0

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

print('='*60)
print('快速更新今日 stock_daily (Baostock 不复权 + 每300只重登)')
print('='*60)

# 目标日期
today = date.today()
target = today.strftime('%Y-%m-%d')
target_ymd = today.strftime('%Y-%m-%d')
prev_ymd = (today - timedelta(days=5)).strftime('%Y-%m-%d')
print(f'目标日期: {target}')

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取所有A股
cursor.execute('''SELECT si.id, si.code, si.name FROM stock_info si
WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
AND si.code NOT LIKE "688%%"
ORDER BY si.code''')
stocks = cursor.fetchall()
print(f'共 {len(stocks)} 只正常A股')

# 获取今日已更新的股票ID
cursor.execute('SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s', (target,))
existing = {r[0] for r in cursor.fetchall()}
print(f'今日已有: {len(existing)} 只')

# 需要更新的
to_update = [s for s in stocks if s[0] not in existing]
print(f'需要更新: {len(to_update)} 只')

if not to_update:
    print('\n✓ 所有股票已是最新')
    cursor.close(); conn.close(); sys.exit(0)

def login_bs():
    bs.logout()
    time.sleep(0.5)
    lg = bs.login()
    if lg.error_code != '0':
        print(f'登录失败: {lg.error_msg}')
        return False
    return True

# 分批处理，每300只重新登录
batch_size = 300
success = fail = 0
start_time = time.time()

for batch_i in range(0, len(to_update), batch_size):
    batch = to_update[batch_i:batch_i + batch_size]
    
    # 重新登录
    if not login_bs():
        print('登录失败，终止')
        break
    
    for sid, code, name in batch:
        try:
            bs_code = f'sh.{code}' if code.startswith(('600','601','603','605','688','689')) else f'sz.{code}'
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                'date,code,open,high,low,close,volume,amount,turn',
                start_date=prev_ymd, end_date=target_ymd,
                frequency='d', adjustflag='3'
            )
            
            if rs.error_code != '0':
                fail += 1
                continue
            
            rows = []
            while (rs.error_code == '0') and rs.next():
                rows.append(rs.get_row_data())
            
            if not rows:
                fail += 1
                continue
            
            df = pd.DataFrame(rows, columns=rs.fields)
            target_rows = df[df['date'] == target]
            
            if target_rows.empty:
                fail += 1
                continue
            
            r = target_rows.iloc[-1]
            
            # 计算涨跌幅
            prev_rows = df[df['date'] < target]
            change_pct = 0.0
            amplitude = 0.0
            if not prev_rows.empty:
                pc = safe_float(prev_rows.iloc[-1]['close'])
                cc = safe_float(r['close'])
                if pc > 0:
                    change_pct = round((cc - pc) / pc * 100, 2)
                hi = safe_float(r['high'])
                lo = safe_float(r['low'])
                if pc > 0:
                    amplitude = round((hi - lo) / pc * 100, 2)
            
            sql = '''INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                     ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
                     low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
                     change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
                     turnover_rate=VALUES(turnover_rate)'''
            
            cursor.execute(sql, (
                sid, target,
                safe_float(r['open']), safe_float(r['close']),
                safe_float(r['high']), safe_float(r['low']),
                safe_float(r['volume']), safe_float(r['amount']),
                change_pct, amplitude, safe_float(r['turn'])
            ))
            conn.commit()
            success += 1
        except Exception as e:
            fail += 1
    
    elapsed = time.time() - start_time
    done = batch_i + len(batch)
    print(f'  批次完成: {done}/{len(to_update)} | 成功{success} 失败{fail} | {elapsed:.0f}s')

elapsed = time.time() - start_time
print(f'\n=== 完成 ===')
print(f'成功: {success}, 失败: {fail}')
print(f'用时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)')

# 检查结果
cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
final = cursor.fetchone()[0]
print(f'今日总计: {final}/{len(stocks)} 只')

cursor.close(); conn.close()
try: bs.logout()
except: pass
