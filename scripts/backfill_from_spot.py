#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 cn_stock_spot 补全 stock_daily 缺失数据
用于 baostock 不可用时的替代方案
"""
import sys, os, json, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

# 字段映射: spot -> daily
FIELD_MAP = {
    'new_price': 'close',
    'open_price': 'open',
    'high_price': 'high',
    'low_price': 'low',
    'volume': 'volume',
    'deal_amount': 'amount',
    'change_rate': 'change_percent',
    'amplitude': 'amplitude',
    'turnoverrate': 'turnover_rate',
}

target = sys.argv[1] if len(sys.argv) > 1 else '2026-07-16'
print('='*60)
print(f'从 cn_stock_spot 补全 stock_daily - {target}')
print('='*60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取spor中今日数据，且没有daily数据的股票
cursor.execute('''
SELECT si.id, si.code, sp.new_price, sp.change_rate, sp.turnoverrate,
       sp.open_price, sp.high_price, sp.low_price, sp.volume, sp.deal_amount,
       sp.amplitude
FROM cn_stock_spot sp
JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
WHERE sp.date = %s
AND si.code NOT LIKE '688%%'
AND (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
AND si.id NOT IN (SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s)
ORDER BY sp.code
''', (target, target))

stocks = cursor.fetchall()
print(f'待补全: {len(stocks)} 只')

if not stocks:
    print('✓ 没有需要补全的')
    cursor.close(); conn.close()
    sys.exit(0)

success = 0
failed = []
start_t = time.time()

for sid, code, close, chg, turn, open_p, high, low, vol, amt, amp in stocks:
    try:
        # 安全转换数值
        def sf(v):
            if v is None or v == '':
                return 0.0
            try:
                f = float(v)
                return 0.0 if (f != f or abs(f) > 1e20) else f
            except:
                return 0.0
        
        cursor.execute('''INSERT INTO stock_daily(stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),
            low=VALUES(low),volume=VALUES(volume),amount=VALUES(amount),
            change_percent=VALUES(change_percent),amplitude=VALUES(amplitude),
            turnover_rate=VALUES(turnover_rate)''',
            (sid, target, sf(open_p), sf(close), sf(high), sf(low),
             int(sf(vol)), int(sf(amt)), sf(chg), sf(amp), sf(turn)))
        conn.commit()
        success += 1
    except Exception as e:
        failed.append((sid, code, str(e)[:60]))

    if success % 500 == 0 and success > 0:
        print(f'  已处理 {success}/{len(stocks)} ...')

elapsed = time.time() - start_t
print(f'\\n{"="*60}')
print(f'补全完成!')
print(f'成功: {success} 只')
if failed:
    print(f'失败: {len(failed)} 只')
    for s in failed[:5]:
        print(f'  {s[1]}: {s[2]}')

cursor.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (target,))
cnt = cursor.fetchone()[0]
cursor.execute('''SELECT COUNT(*) FROM stock_info si
    WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
    AND si.code NOT LIKE "688%%"''')
total = cursor.fetchone()[0]
print(f'今日总计: {cnt}/{total} ({cnt/total*100:.1f}%)')

cursor.close(); conn.close()