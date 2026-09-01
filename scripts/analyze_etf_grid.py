#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析cn_etf_spot，筛选适合网格交易的ETF（波动大+成交活跃）"""
import pymysql

conn = pymysql.connect(host='localhost', user='stock', password='12345678',
                       database='instock', port=3306, charset='utf8mb4')
c = conn.cursor()

# 看表结构
c.execute('DESCRIBE cn_etf_spot')
cols = [r[0] for r in c.fetchall()]
print(f'cn_etf_spot字段: {cols}\n')

# 最新日期
c.execute('SELECT MAX(date) FROM cn_etf_spot')
latest = c.fetchone()[0]
print(f'最新日期: {latest}')

# 查最新一天的ETF：代码、名称、价格、涨跌幅、成交额、振幅、换手
# 先看字段里有哪些
c.execute("SELECT code, name FROM cn_etf_spot WHERE date=%s LIMIT 3", (latest,))
for r in c.fetchall():
    print(f' 样例: {r}')

conn.close()