#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""半导体板块分析"""
import pymysql

conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306)
c = conn.cursor()

today = '2026-08-17'

# 半导体相关股票（名称含半导体/芯片/集成电路/微电子/晶圆/封测）
c.execute("""
    SELECT si.code, si.name, sp.new_price, sp.change_rate, 
           sp.deal_amount, sp.turnoverrate, sp.pe
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s
    AND (si.name LIKE '%%半导体%%' OR si.name LIKE '%%芯片%%' OR si.name LIKE '%%集成%%'
         OR si.name LIKE '%%微电子%%' OR si.name LIKE '%%晶圆%%' OR si.name LIKE '%%封测%%')
    AND sp.code NOT LIKE '688%%'
    ORDER BY sp.change_rate DESC
""", (today,))

rows = c.fetchall()
print(f'=== 半导体板块 ({len(rows)}只) ===')
print(f'{"代码":<8} {"名称":<12} {"最新":>8} {"涨幅":>7} {"成交额":>10} {"换手":>6}')
total_chg = 0
total_amt = 0
up = down = 0
for r in rows:
    code, name, price, chg, amt, turn, pe = r
    chg_f = float(chg or 0)
    amt_f = float(amt or 0) / 1e8
    total_chg += chg_f
    total_amt += amt_f
    if chg_f > 0: up += 1
    elif chg_f < 0: down += 1
    emoji = '🚀' if chg_f >= 5 else '📈' if chg_f > 0 else '📉' if chg_f < 0 else '➖'
    print(f'{emoji} {code:<8} {name:<12} {price:>8.2f} {chg_f:>6.2f}% {amt_f:>8.1f}亿 {turn:>5.1f}%')

avg_chg = total_chg/len(rows) if rows else 0
print(f'\n📊 汇总: {up}涨/{down}跌 | 平均涨幅{avg_chg:.2f}% | 总成交{total_amt:.0f}亿')

# 行业龙头表现
print('\n=== 半导体龙头股 ===')
c.execute("""
    SELECT si.code, si.name, sp.new_price, sp.change_rate, sp.deal_amount
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND sp.code NOT LIKE '688%%'
    AND si.code IN ('002049','603986','600703','300672','300661','603501','002371','300316')
    ORDER BY sp.change_rate DESC
""", (today,))
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: {float(r[3] or 0):.2f}% 成交{float(r[4] or 0)/1e8:.1f}亿')

print('\n=== 半导体概念板块资金流向 ===')
for concept in ['半导体', '芯片', '集成电路']:
    c.execute("""
        SELECT MAX(date) FROM cn_stock_fund_flow_concept
        WHERE concept_name LIKE %s
    """, (f'%{concept}%',))
    d = c.fetchone()[0]
    if d:
        c.execute("""
            SELECT change_rate, main_net_inflow FROM cn_stock_fund_flow_concept
            WHERE date = %s AND concept_name LIKE %s
        """, (d, f'%{concept}%'))
        r = c.fetchone()
        if r:
            print(f'  {concept}: 涨幅{r[0]}% 主力净流入{r[1]:,.0f}')

conn.close()