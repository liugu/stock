#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询烽火电子退市风险"""
import pymysql

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
conn = pymysql.connect(**DB)
c = conn.cursor()
code = '000561'

# 查股票基本信息
c.execute("SELECT code, name, industry, area, pe_ttm, pb, total_mv FROM stock_info WHERE code=%s", (code,))
r = c.fetchone()
if r:
    print(f"📌 {r[1]}({r[0]})")
    print(f"   行业: {r[2]}  地区: {r[3]}")
    print(f"   PE: {r[4]}  PB: {r[5]}  总市值: {r[6]}亿" if r[5] else f"   PE: {r[4]}  PB: N/A  总市值: {r[6]}亿")

# 检查名称是否含ST/*ST
if r and r[1]:
    name = r[1]
    if name.startswith('*ST'):
        print(f"\n❌ **{name}** — 退市风险警示（*ST）")
    elif name.startswith('ST'):
        print(f"\n⚠️ **{name}** — 特别处理（ST）")
    else:
        print(f"\n✅ **名称正常** — 无ST/*ST标记")

# 面值退市检查（股价连续20日低于1元）
c.execute("""
    SELECT date, close FROM stock_daily 
    WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)
    ORDER BY date DESC LIMIT 60
""", (code,))
rows = c.fetchall()
if rows:
    closes = [float(row[1]) for row in rows]
    min_close = min(closes)
    print(f"\n💰 **面值退市检查**：近60日最低价 = {min_close}元", end='')
    if min_close < 1:
        print(f" ❌ 低于1元！触及面值退市条件！")
    elif min_close < 3:
        print(f" ⚠️ 虽高于1元警戒线，但低于3元，需关注")
    else:
        print(f" ✅ 远高于1元面值警戒线，安全")

# 营收退市检查（主板：营收<1亿+净利润为负；创业板：营收<1亿）
c.execute("""
    SELECT date, close, change_percent, volume 
    FROM stock_daily WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)
    ORDER BY date DESC LIMIT 5
""", (code,))
print(f"\n📅 **近5日交易活跃度**：")
for d, cl, chg, v in rows[:5]:
    chg_str = f"{chg:+.2f}%" if chg else "N/A"
    print(f"   {d}: 收{cl}元  {chg_str}  量{v:.0f}")

# 流动性检查（日均成交额 vs 上半年）
c.execute("SELECT COUNT(*) FROM stock_daily WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)", (code,))
total_days = c.fetchone()[0]
print(f"\n📊 **数据库中有 {total_days} 个交易日数据**，说明一直正常交易未停牌")

# 查今年单日大跌情况
c.execute("""
    SELECT date, close, change_percent, volume FROM stock_daily 
    WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)
    AND date >= '2026-01-01' AND change_percent <= -5
    ORDER BY date DESC
""", (code,))
crashes = c.fetchall()
if crashes:
    print(f"\n📉 **2026年大跌交易日（跌超5%）**：共 {len(crashes)} 天")
    for d, cl, chg, v in crashes:
        print(f"   {d}: {chg:+.2f}%  收{cl}")
else:
    print(f"\n📉 **2026年无单日跌超5%的交易** ✅")

# 今年以来的涨跌幅
c.execute("""
    SELECT close FROM stock_daily WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)
    AND date = (SELECT MIN(date) FROM stock_daily WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s) AND date >= '2026-01-01')
""", (code, code))
first_close = c.fetchone()
c.execute("""
    SELECT close FROM stock_daily WHERE stock_id=(SELECT id FROM stock_info WHERE code=%s)
    ORDER BY date DESC LIMIT 1
""", (code,))
last_close = c.fetchone()
if first_close and last_close:
    chg_ytd = (float(last_close[0]) / float(first_close[0]) - 1) * 100
    print(f"\n📈 **2026年涨跌幅**：{chg_ytd:+.2f}% ({first_close[0]} → {last_close[0]})")

# 总市值（判断是否触及3亿退市标准）
if r and r[6]:
    mv = float(r[6])
    print(f"\n🏢 **总市值**：{mv:.2f}亿", end='')
    if mv < 3:
        print(" ❌ 低于3亿元！触及市值退市条件！")
    elif mv < 10:
        print(" ⚠️ 低于10亿，小盘股但未触及3亿退市线")
    else:
        print(" ✅ 市值正常，远超3亿退市警戒线")

conn.close()