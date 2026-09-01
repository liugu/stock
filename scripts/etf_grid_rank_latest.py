#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用最新ETF数据筛选网格候选"""
import pymysql

conn = pymysql.connect(host='localhost', user='stock', password='12345678',
                       database='instock', port=3306, charset='utf8mb4')
c = conn.cursor()

c.execute("SELECT MAX(date) FROM cn_etf_spot")
day = c.fetchone()[0]
print(f'最新日期: {day}')

# 找512400有色金属ETF南方
c.execute("SELECT code,name,new_price,change_rate,deal_amount,turnoverrate,\n"
          "  (high_price-low_price)/pre_close_price AS amp FROM cn_etf_spot WHERE date=%s AND code='512400'", (day,))
r = c.fetchone()
if r:
    print(f'\n[候选] {r[1]} {r[0]}: 价{r[2]} 涨{r[3]}% 成交{r[4]/1e8:.1f}亿 换手{r[5]}% 振幅{r[6]*100:.1f}%')

# 按振幅排出所有ETF，看有色ETF位置
c.execute("""SELECT code,name,new_price,change_rate,deal_amount,turnoverrate,
    (high_price-low_price)/pre_close_price AS amp
    FROM cn_etf_spot WHERE date=%s AND deal_amount>=2e8 ORDER BY amp DESC""", (day,))
rows = c.fetchall()
print(f'\n=== 成交≥2亿的ETF按振幅排序 (前30) ===')
print(f'{"代码":<8}{"名称":<18}{"振幅":>6}{"涨跌":>6}{"成交亿":>8}')
for r in rows[:30]:
    if r[6] is None: continue
    print(f'{r[0]:<8}{r[1]:<16}{r[6]*100:>5.1f}%{r[3]:>5.1f}%{r[4]/1e8:>7.1f}')

conn.close()