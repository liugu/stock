#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306)
c = conn.cursor()
today = '2026-08-19'

# 大盘情况
c.execute("""SELECT COUNT(*),
    SUM(CASE WHEN change_rate>0 THEN 1 ELSE 0 END),
    SUM(CASE WHEN change_rate<0 THEN 1 ELSE 0 END),
    AVG(change_rate),
    SUM(deal_amount)/1e8
FROM cn_stock_spot WHERE date=%s AND code NOT LIKE '688%%'""", (today,))
r = c.fetchone()
total, up, down, avg, amt = r
print(f'=== 今日 2026-08-19 真实大盘 ===')
print(f'涨:{int(up)} 跌:{int(down)} 平:{int(total-up-down)}')
print(f'涨比:{up/total*100:.1f}%')
print(f'平均涨幅:{avg:.2f}%')
print(f'成交:{amt:.0f}亿')

# 半导体
print(f'\n=== 半导体板块今日真实表现 ===')
c.execute("""SELECT si.code, si.name, sp.change_rate, sp.deal_amount
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s
    AND (si.name LIKE '%%半导体%%' OR si.name LIKE '%%芯片%%' OR si.name LIKE '%%集成%%'
         OR si.name LIKE '%%微电子%%')
    AND sp.code NOT LIKE '688%%'
    ORDER BY sp.change_rate DESC""", (today,))
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: {float(r[2] or 0):.2f}% 成交{float(r[3] or 0)/1e8:.1f}亿')

# 存储龙头
print('\n=== 存储/半导体龙头今日 ===')
c.execute("""SELECT si.code, si.name, sp.change_rate, sp.deal_amount
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND si.code IN
    ('300672','603986','300223','002371','688525','688008','600703','300661','002049')
    ORDER BY sp.change_rate DESC""", (today,))
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: {float(r[2] or 0):.2f}% 成交{float(r[3] or 0)/1e8:.1f}亿')

conn.close()