#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日复盘报告自动生成
输出格式化文本，可用于雪球/公众号等平台发布
"""
import pymysql, json, os
from datetime import date, datetime, timedelta

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
OUTPUT_DIR = 'E:/量化研究/workspace/stock/output/review'

today_str = date.today().strftime('%Y-%m-%d')
# 如果今天是周末，用最近交易日
conn_tmp = pymysql.connect(**DB)
c_tmp = conn_tmp.cursor()
c_tmp.execute('SELECT MAX(date) FROM cn_stock_spot')
latest_data = c_tmp.fetchone()[0]
conn_tmp.close()
if latest_data:
    today_str = str(latest_data)
today_cn = f'{date.today().month}月{date.today().day}日'
print(f'使用数据日期: {today_str}')

conn = pymysql.connect(**DB)
c = conn.cursor()

report = []
report.append(f'📊 【{today_cn} A股复盘】')
report.append(f'日期：{today_str}')
report.append('')

# =============================================
# 1. 大盘概况
# =============================================
report.append('━━━ 一、大盘概况 ━━━')

c.execute("""
    SELECT 
        COUNT(*) as total,
        COALESCE(SUM(CASE WHEN change_rate > 0 THEN 1 ELSE 0 END), 0) as up,
        COALESCE(SUM(CASE WHEN change_rate < 0 THEN 1 ELSE 0 END), 0) as down,
        ROUND(COALESCE(AVG(change_rate), 0), 2) as avg_chg,
        ROUND(COALESCE(SUM(deal_amount), 0)/1e8, 0) as total_amt
    FROM cn_stock_spot 
    WHERE date = %s AND code NOT LIKE '688%%'
""", (today_str,))
r = c.fetchone()
total, up, down, avg_chg, amt = r
flat = total - up - down
up_ratio = round(up/total*100, 1) if total else 0

report.append(f'📈 上涨 {up} 家 | 📉 下跌 {down} 家 | ➖ 平盘 {flat} 家')
report.append(f'📊 涨跌比 {up}:{down} | 上涨占比 {up_ratio}%')
report.append(f'💰 两市成交额 {amt} 亿 | 平均涨跌幅 {avg_chg}%')
report.append('')

# =============================================
# 2. 板块排行
# =============================================
report.append('━━━ 二、板块表现 ━━━')

# 涨幅前10板块
c.execute("""
    SELECT 
        CASE 
            WHEN si.industry LIKE "C39%%" OR si.industry LIKE "计算机、通信%%" THEN "计算机/通信/电子"
            WHEN si.industry LIKE "C35%%" OR si.industry LIKE "专用设备%%" THEN "专用设备"
            WHEN si.industry LIKE "C38%%" OR si.industry LIKE "电气机械%%" THEN "电气设备"
            WHEN si.industry LIKE "C26%%" OR si.industry LIKE "化学原料%%" THEN "化学原料"
            WHEN si.industry LIKE "C27%%" OR si.industry LIKE "医药%%" THEN "医药"
            WHEN si.industry LIKE "I65%%" OR si.industry LIKE "软件%%" THEN "软件服务"
            WHEN si.industry LIKE "C36%%" OR si.industry LIKE "汽车%%" THEN "汽车"
            WHEN si.industry LIKE "%%煤炭%%" THEN "煤炭"
            WHEN si.industry LIKE "%%有色%%" OR si.industry LIKE "C32%%" THEN "有色金属"
            ELSE si.industry
        END as sector,
        COUNT(*) as cnt,
        ROUND(COALESCE(AVG(sp.change_rate), 0), 2) as avg_chg,
        COALESCE(SUM(CASE WHEN sp.change_rate > 0 THEN 1 ELSE 0 END), 0) as up,
        ROUND(COALESCE(SUM(sp.deal_amount), 0)/1e8, 0) as amt
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND si.industry IS NOT NULL AND si.industry != ''
    AND sp.code NOT LIKE '688%%'
    GROUP BY sector
    HAVING cnt >= 5
    ORDER BY avg_chg DESC LIMIT 10
""", (today_str,))
top_sectors = c.fetchall()

report.append('🔥 涨幅前十板块：')
for s in top_sectors:
    sector = s[0][:18]
    cnt = s[1]
    avg = s[2]
    up_cnt = s[3]
    amt_v = s[4]
    report.append(f'  {sector:<18} +{avg}%  {up_cnt}/{cnt}涨  成交{amt_v}亿')

report.append('')

# 跌幅前5板块
c.execute("""
    SELECT 
        CASE 
            WHEN si.industry LIKE "C39%%" OR si.industry LIKE "计算机、通信%%" THEN "计算机/通信/电子"
            WHEN si.industry LIKE "C38%%" OR si.industry LIKE "电气机械%%" THEN "电气设备"
            ELSE si.industry
        END as sector,
        COUNT(*) as cnt,
        ROUND(COALESCE(AVG(sp.change_rate), 0), 2) as avg_chg
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND si.industry IS NOT NULL AND si.industry != ''
    AND sp.code NOT LIKE '688%%'
    GROUP BY sector
    HAVING cnt >= 5
    ORDER BY avg_chg ASC LIMIT 5
""", (today_str,))
bottom_sectors = c.fetchall()

report.append('❄️ 跌幅前五板块：')
for s in bottom_sectors:
    report.append(f'  {s[0][:18]:<18} {s[2]}%')
report.append('')

# =============================================
# 3. 资金流向
# =============================================
report.append('━━━ 三、资金流向 ━━━')

c.execute("""
    SELECT 
        CASE 
            WHEN si.industry LIKE "C39%%" OR si.industry LIKE "计算机、通信%%" THEN "计算机/通信/电子"
            WHEN si.industry LIKE "C38%%" OR si.industry LIKE "电气机械%%" THEN "电气设备"
            WHEN si.industry LIKE "C35%%" OR si.industry LIKE "专用设备%%" THEN "专用设备"
            ELSE si.industry
        END as sector,
        ROUND(COALESCE(SUM(sp.deal_amount), 0)/1e8, 0) as amt,
        ROUND(COALESCE(AVG(sp.change_rate), 0), 2) as avg_chg
    FROM cn_stock_spot sp
    JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci
    WHERE sp.date = %s AND si.industry IS NOT NULL AND si.industry != ''
    AND sp.code NOT LIKE '688%%'
    GROUP BY sector
    HAVING COUNT(*) >= 5
    ORDER BY amt DESC LIMIT 8
""", (today_str,))
amt_sectors = c.fetchall()

report.append('💰 成交额最大板块：')
for s in amt_sectors:
    report.append(f'  {s[0][:18]:<18} {s[1]}亿  {"+" if float(s[2] or 0) >= 0 else ""}{s[2]}%')

report.append('')

# =============================================
# 4. 今日强势股
# =============================================
report.append('━━━ 四、今日强势股 ━━━')

c.execute("""
    SELECT sp.code, sp.name, sp.change_rate, sp.new_price, sp.deal_amount
    FROM cn_stock_spot sp
    WHERE sp.date = %s AND sp.code NOT LIKE '688%%'
    ORDER BY sp.change_rate DESC LIMIT 15
""", (today_str,))
strong_stocks = c.fetchall()

report.append('🔥 涨幅前15：')
limit_up = []
for s in strong_stocks:
    chg = float(s[2] or 0)
    amt_v = float(s[4] or 0) / 1e8
    if chg >= 9.9:
        limit_up.append(s)
        report.append(f'  🚀 {s[0]} {s[1]}  +{chg}%  {s[3]}元  成交{amt_v:.1f}亿')
    elif chg >= 5:
        report.append(f'  📈 {s[0]} {s[1]}  +{chg}%  {s[3]}元  成交{amt_v:.1f}亿')
    else:
        report.append(f'  📈 {s[0]} {s[1]}  +{chg}%  {s[3]}元  成交{amt_v:.1f}亿')

report.append('')
if limit_up:
    report.append(f'📌 涨停板：{len(limit_up)} 只')

# =============================================
# 5. 策略信号
# =============================================
report.append('')
report.append('━━━ 五、策略信号 ━━━')

# 检查连续小阳线策略结果
c.execute('SELECT MAX(date) FROM cn_stock_strategy_consecutive_small_bullish')
max_date = c.fetchone()[0]
if max_date and str(max_date) == today_str:
    c.execute("""
        SELECT si.code, si.name FROM cn_stock_strategy_consecutive_small_bullish cs
        JOIN stock_info si ON cs.code = si.code
        WHERE cs.date = %s ORDER BY cs.consecutive_days DESC LIMIT 10
    """, (today_str,))
    signals = c.fetchall()
    if signals:
        report.append('📊 连续小阳线策略信号：')
        for s in signals:
            report.append(f'  {s[0]} {s[1]}')

# 检查低位选股
c.execute("""
    SELECT MAX(date) FROM cn_stock_strategy_consecutive_bullish_at_low
""")
low_date = c.fetchone()[0]
if low_date and str(low_date) == today_str:
    c.execute("""
        SELECT si.code, si.name FROM cn_stock_strategy_consecutive_bullish_at_low cb
        JOIN stock_info si ON cb.code = si.code
        WHERE cb.date = %s LIMIT 10
    """, (today_str,))
    low_signals = c.fetchall()
    if low_signals:
        report.append('📊 低位连阳策略信号：')
        for s in low_signals:
            report.append(f'  {s[0]} {s[1]}')

if not max_date or str(max_date) != today_str:
    report.append('📊 今日策略信号：未运行选股策略')

report.append('')
report.append('━━━ ✅ 复盘完毕 ━━━')
report.append(f'📅 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}')

# 保存到文件
os.makedirs(OUTPUT_DIR, exist_ok=True)
output_path = f'{OUTPUT_DIR}/review_{today_str}.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print(f'复盘报告已保存: {output_path}')
print()
print('\n'.join(report))

conn.close()