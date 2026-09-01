#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""筛选适合网格交易的ETF：波动率(振幅)+成交额(流动性)"""
import pymysql

conn = pymysql.connect(host='localhost', user='stock', password='12345678',
                       database='instock', port=3306, charset='utf8mb4')
c = conn.cursor()

# 找出有数据的最新日期（按日期聚合，取记录最多的那天，代表正常交易日）
c.execute("""
    SELECT date, COUNT(*) FROM cn_etf_spot GROUP BY date ORDER BY date DESC LIMIT 15
""")
dates = c.fetchall()
print(f'最近15个交易日数据量:')
for d in dates:
    print(f'  {d[0]}: {d[1]}只ETF')

# 取最近一个完整交易日（记录量最大的一天）
c.execute("""
    SELECT date FROM cn_etf_spot GROUP BY date ORDER BY COUNT(*) DESC LIMIT 1
""")
day = c.fetchone()[0]
print(f'\n使用交易日: {day}')

# 计算振幅 = (high-low)/pre_close，并与成交额一起评估网格适用性
c.execute("""
    SELECT code, name, new_price, change_rate, deal_amount, turnoverrate,
           (high_price - low_price) / pre_close_price AS amplitude
    FROM cn_etf_spot WHERE date = %s
""", (day,))
rows = c.fetchall()

print(f'\n=== 适合网格的ETF：波动大 + 成交活跃 ===')
print(f'{"代码":<8}{"名称":<16}{"振幅":>7}{"涨跌":>7}{"成交额亿":>9}{"换手":>6}')
print('-' * 55)

# 筛选条件：成交额>=1亿(流动性OK)，按振幅排序
liquids = [r for r in rows if r[4] and r[4] >= 1e8]
liquids.sort(key=lambda r: r[5], reverse=True)  # 按振幅降序

for r in liquids[:40]:
    code, name, price, chg, amt, turn, amp = r
    if price is None:
        continue
    amp_f = float(amp or 0) * 100
    chg_f = float(chg or 0)
    amt_yi = float(amt or 0) / 1e8
    turn_f = float(turn or 0)
    print(f'{code:<8}{name:<14}{amp_f:>6.1f}%{chg_f:>6.1f}%{amt_yi:>8.1f}{turn_f:>6.1f}%')

conn.close()