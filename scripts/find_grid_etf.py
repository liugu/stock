#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查常见A股场内ETF代码是否在数据库"""
import pymysql

conn = pymysql.connect(host='localhost', user='stock', password='12345678',
                       database='instock', port=3306, charset='utf8mb4')
c = conn.cursor()

# 常见场内ETF代码
etfs = ['512880','512660','515790','159995','512480','159915','588000',
        '512010','512200','515030','159992','588080','512690','159948',
        '516160','515220','512400','159869','588200','515700']

# 查这些代码在stock_info和cn_stock_spot是否有数据
for code in etfs:
    c.execute('SELECT code, name FROM stock_info WHERE code=%s', (code,))
    info = c.fetchone()
    if info:
        c.execute('SELECT MAX(date), COUNT(*) FROM cn_stock_spot WHERE code=%s', (code,))
        spot = c.fetchone()
        print(f'  {info[0]} {info[1]} | spot最新{spot[0]}, {spot[1]}条')
    else:
        print(f'  {code} (不在stock_info)')

# 检查股票表里是否有基金/证券类型数据
c.execute("SHOW TABLES")
tables = [r[0] for r in c.fetchall()]
print(f'\n数据库表: {tables[:40]}')

conn.close()