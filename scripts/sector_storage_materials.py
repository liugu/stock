#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""存储芯片 + 半导体材料板块分析"""
import pymysql

conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306)
c = conn.cursor()

today = '2026-08-17'

def query_sector(keywords, label):
    """按名称关键词查板块"""
    conditions = ' OR '.join([f"si.name LIKE '%%{k}%%'" for k in keywords])
    c.execute(f"""
        SELECT si.code, si.name, sp.new_price, sp.change_rate, 
               sp.deal_amount, sp.turnoverrate
        FROM cn_stock_spot sp
        JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
        WHERE sp.date = %s AND ({conditions})
        AND sp.code NOT LIKE '688%%'
        ORDER BY sp.change_rate DESC
    """, (today,))
    rows = c.fetchall()
    print(f'\n=== {label} ({len(rows)}只) ===')
    if not rows:
        print('  无数据')
        return
    print(f'{"代码":<8} {"名称":<12} {"最新":>8} {"涨幅":>7} {"成交额":>10} {"换手":>6}')
    
    total_chg = total_amt = 0
    up = down = 0
    names = []
    for r in rows:
        code, name, price, chg, amt, turn = r
        chg_f = float(chg or 0)
        amt_f = float(amt or 0) / 1e8
        total_chg += chg_f
        total_amt += amt_f
        if chg_f > 0: up += 1
        elif chg_f < 0: down += 1
        names.append(name)
        emoji = '🚀' if chg_f >= 5 else '📈' if chg_f > 0 else '📉' if chg_f < 0 else '➖'
        print(f'{emoji} {code:<8} {name:<12} {price:>8.2f} {chg_f:>6.2f}% {amt_f:>8.1f}亿 {turn:>5.1f}%')
    
    avg_chg = total_chg/len(rows) if rows else 0
    print(f'汇总: {up}涨/{down}跌 | 平均+{avg_chg:.2f}% | 总成交{total_amt:.0f}亿')

# 1. 存储芯片
query_sector(['存储', '闪存', '内存', 'DRAM', 'NAND', '硬盘', '固态'], '存储芯片')

# 2. 半导体材料
query_sector(['硅片', '光刻胶', '电子特气', '靶材', '抛光', '封装材料', 
              '碳化硅', '氮化镓', '衬底', '外延', '溅射'], '半导体材料')

# 3. 存储相关芯片设计
query_sector(['兆易', '北京君正', '东芯', '澜起', '聚辰', '普冉', '恒烁', 
              '复旦微', '国科微', '龙芯', '景嘉微', '寒武纪'], '存储/芯片设计')

# 4. 补充关键龙头
print('\n=== 存储+材料关键龙头 ===')
c.execute("""
    SELECT si.code, si.name, sp.new_price, sp.change_rate, sp.deal_amount
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND si.code IN (
        '603986','300672','300661','688525','688041','688008','688126',
        '688123','688019','688012','688005','688396','688200',
        '002049','002371','600703','603501','300316'
    )
    ORDER BY sp.change_rate DESC
""", (today,))
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: {float(r[3] or 0):.2f}% 成交{float(r[4] or 0)/1e8:.1f}亿')

# 5. 从 stock_info 看半导体产业链分布
print('\n=== stock_info 半导体相关行业分布 ===')
c.execute("""
    SELECT industry, COUNT(*) as cnt FROM stock_info 
    WHERE industry IS NOT NULL AND industry != ''
    AND industry LIKE '%%计算机、通信%%'
    GROUP BY industry ORDER BY cnt DESC LIMIT 5
""")
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}只')

c.execute("""
    SELECT COUNT(*) FROM stock_info
    WHERE (name LIKE '%%半导体%%' OR name LIKE '%%芯片%%' OR name LIKE '%%集成%%'
           OR name LIKE '%%微电子%%') AND code NOT LIKE '688%%'
""")
cnt = c.fetchone()[0]
print(f'\n两市半导体类公司（非科创板）: {cnt}只')

conn.close()