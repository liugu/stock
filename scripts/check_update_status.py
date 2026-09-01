#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查更新状态"""
import pymysql

conn = pymysql.connect(host='localhost',user='stock',password='12345678',
                       database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

c.execute('SELECT MAX(date) FROM cn_stock_spot')
sd = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM cn_stock_spot WHERE date = %s', (sd,))
print(f'cn_stock_spot: 日期={sd} 记录={c.fetchone()[0]}')

c.execute('SELECT MAX(date) FROM stock_daily')
dd = c.fetchone()[0]
c.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (dd,))
dc = c.fetchone()[0]
c.execute("""SELECT COUNT(*) FROM stock_info si
WHERE (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
AND si.code NOT LIKE '688%%'""")
total = c.fetchone()[0]
print(f'stock_daily: 日期={dd} 记录={dc}/{total} ({dc/total*100:.1f}%)')

# 缺哪些
c.execute("""SELECT si.code, si.name FROM stock_info si
WHERE (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
AND si.code NOT LIKE '688%%'
AND si.id NOT IN (SELECT DISTINCT stock_id FROM stock_daily WHERE date = %s)
LIMIT 10""", (dd,))
missing = c.fetchall()
if missing:
    print(f'缺少({len(missing)}只示例):')
    for code, name in missing:
        print(f'  {name}({code})')

conn.close()