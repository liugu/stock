#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os; os.chdir(r'E:\量化研究\workspace\stock')
import pymysql
conn=pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c=conn.cursor()
c.execute("SELECT date,COUNT(DISTINCT stock_id) FROM stock_daily WHERE date>='2026-07-10' GROUP BY date ORDER BY date")
for r in c.fetchall():
    print('%s: %d' % (r[0], r[1]))
c.execute('SELECT MAX(date) FROM cn_stock_spot')
print('spot最新:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM stock_info WHERE (code LIKE "60%%" OR code LIKE "00%%" OR code LIKE "30%%") AND code NOT LIKE "688%%"')
print('目标总数:', c.fetchone()[0])
conn.close()