#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析今日板块表现"""
import pymysql
from collections import defaultdict

conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

today = '2026-08-06'

# 从 stock_company 获取行业分类，与 cn_stock_spot 关联
c.execute('''SELECT sc.industry, sp.code, sp.name, sp.new_price, sp.change_rate, 
    sp.open_price, sp.high_price, sp.low_price, sp.volume, sp.deal_amount, sp.turnoverrate
    FROM cn_stock_spot sp
    JOIN stock_company sc ON sp.code = sc.code COLLATE utf8mb4_0900_ai_ci
    WHERE sp.date = %s AND sc.industry IS NOT NULL AND sc.industry != ''
    ORDER BY sp.change_rate DESC''', (today,))
rows = c.fetchall()

# 按行业汇总
industry_data = defaultdict(lambda: {'stocks': [], 'total_chg': 0.0, 'up': 0, 'down': 0, 
                                       'total_vol': 0.0, 'total_amt': 0.0, 'count': 0})

for row in rows:
    industry = row[0]
    d = industry_data[industry]
    d['count'] += 1
    d['total_chg'] += float(row[4] or 0)
    d['total_vol'] += float(row[8] or 0)
    d['total_amt'] += float(row[9] or 0)
    if float(row[4] or 0) > 0:
        d['up'] += 1
    else:
        d['down'] += 1
    d['stocks'].append(row)

# 计算行业平均涨幅并排序
industry_stats = []
for ind, d in industry_data.items():
    avg_chg = round(d['total_chg'] / d['count'], 2) if d['count'] > 0 else 0
    top5 = sorted(d['stocks'], key=lambda x: float(x[4] or 0), reverse=True)[:5]
    industry_stats.append({
        'industry': ind,
        'count': d['count'],
        'avg_chg': avg_chg,
        'up': d['up'],
        'down': d['down'],
        'up_ratio': round(d['up']/d['count']*100, 1),
        'total_amt': d['total_amt'],
        'top5': top5
    })

industry_stats.sort(key=lambda x: x['avg_chg'], reverse=True)

print(f'=== {today} 板块表现分析 ===')
print()

# 涨幅前15行业
print('━━━ 涨幅前15板块 ━━━')
print(f'{"板块":<10} {"涨幅%":>7} {"涨/跌":>8} {"涨比":>6} {"个股":>5}')
for s in industry_stats[:15]:
    ind = s['industry'][:10]
    print(f'{ind:<10} {s["avg_chg"]:>7.2f} {s["up"]}/{s["down"]:>4} {s["up_ratio"]:>5.1f}% {s["count"]:>5}')

print()

# 每个热板块的领涨股
print('━━━ 领涨板块龙头股 ━━━')
for s in industry_stats[:8]:
    ind = s['industry'][:12]
    print(f'【{ind}】涨幅{s["avg_chg"]:.2f}% 涨比{s["up_ratio"]:.1f}%')
    for stk in s['top5'][:3]:
        code = stk[1]
        name = stk[2]
        chg = stk[4]
        amt = stk[9]
        print(f'  {code} {name}: {chg}% 成交{amt/1e8:.1f}亿')
    print()

# 成交额最大的板块（资金聚集）
print('━━━ 成交额前10板块（资金热点）━━━')
industry_stats_by_amt = sorted(industry_stats, key=lambda x: x['total_amt'], reverse=True)
print(f'{"板块":<10} {"成交额":>8} {"涨幅%":>7} {"涨比":>6}')
for s in industry_stats_by_amt[:10]:
    ind = s['industry'][:10]
    print(f'{ind:<10} {s["total_amt"]/1e8:>7.1f}亿 {s["avg_chg"]:>6.2f}% {s["up_ratio"]:>5.1f}%')

print()

# 从cn_stock_spot直接找最强势个股（排除688）
print('━━━ 今日强势个股（涨幅前20）━━━')
c.execute('''SELECT sp.code, sp.name, sp.new_price, sp.change_rate, sp.deal_amount, sc.industry
    FROM cn_stock_spot sp
    LEFT JOIN stock_company sc ON sp.code = sc.code COLLATE utf8mb4_0900_ai_ci
    WHERE sp.date = %s AND sp.code NOT LIKE '688%%'
    ORDER BY sp.change_rate DESC LIMIT 20''', (today,))
strong = c.fetchall()
print(f'{"代码":<8} {"名称":<8} {"最新":>6} {"涨幅":>7} {"成交额":>10} {"行业":<10}')
for s in strong:
    code = s[0]
    name = s[1]
    price = s[2]
    chg = s[3]
    amt = s[4] or 0
    ind = (s[5] or '')[:10]
    print(f'{code:<8} {name:<8} {price:>6.2f} {chg:>6.2f}% {amt/1e8:>8.1f}亿 {ind:<10}')

conn.close()