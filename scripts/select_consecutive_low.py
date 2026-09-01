#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连续小阳线+低位筛选"""
import pymysql
from datetime import date

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

# 42只连续5日小阳线股票（来自上一轮选股结果）
BULLISH_CODES = [
    ('603990','麦迪科技'),('600133','东湖高新'),('002698','博实股份'),('300082','奥克股份'),
    ('002703','浙江世宝'),('002369','卓翼科技'),('300879','大叶股份'),('002749','国光股份'),
    ('002214','大立科技'),('002003','伟星股份'),('603578','三星新材'),('601798','蓝科高新'),
    ('603889','新澳股份'),('301565','中仑新材'),('001234','泰慕士'),('300923','研奥股份'),
    ('300241','瑞丰光电'),('603183','建研院'),('603177','德创环保'),('600130','波导股份'),
    ('001332','锡装股份'),('601598','中国外运'),('603335','迪生力'),('603869','ST智知'),
    ('300326','凯利泰'),('300691','联合光电'),('603344','星德胜'),('002241','歌尔股份'),
    ('300198','纳川股份'),('300708','聚灿光电'),('600869','远东股份'),('300042','朗科科技'),
    ('002437','誉衡药业'),('002445','中南文化'),('600008','首创环保'),('600227','赤天化'),
    ('002051','中工国际'),('605090','九丰能源'),('002130','沃尔核材'),('600992','贵绳股份'),
    ('600884','杉杉股份'),('000536','华映科技'),
]

today = date.today()
print(f'=== 连续小阳线+低位筛选 ({today}) ===\n')

conn = pymysql.connect(**DB)
c = conn.cursor()

results = []
for code_str, name in BULLISH_CODES:
    # 获取日K数据
    c.execute("""
        SELECT sd.date, sd.close, sd.open, sd.low, sd.change_percent
        FROM stock_daily sd
        JOIN stock_info si ON sd.stock_id = si.id
        WHERE si.code = %s
        ORDER BY sd.date DESC LIMIT 260
    """, (code_str,))
    rows = list(c.fetchall())
    if not rows or len(rows) < 60:
        continue
    
    rows.reverse()
    closes = [float(r[1]) for r in rows]
    opens = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    chgs = [float(r[4] or 0) for r in rows]
    n = len(closes)
    
    # 连续5天小阳线确认
    daily_chgs = []
    ok = True
    for i in range(-5, 0):
        if closes[i] <= opens[i]:
            ok = False; break
        pct = (closes[i] - opens[i]) / opens[i] * 100
        if pct < 0.5 or pct > 5.0:
            ok = False; break
        daily_chgs.append(round(pct, 2))
    if not ok:
        continue
    if closes[-1] <= opens[-5]:
        continue
    total_chg = round((closes[-1] - opens[-5]) / opens[-5] * 100, 2)
    
    # --- 低位判断 ---
    lb = min(250, n)
    yr_low = min(lows[-lb:])
    yr_high = max(closes[-lb:])
    dist = (closes[-1] / yr_low - 1) * 100
    
    if dist > 30:
        continue
    
    all_c = closes[-lb:]
    pctl = sum(1 for c in all_c if c <= closes[-1]) / len(all_c) * 100
    if pctl > 40:
        continue
    
    # 获取今日行情
    c.execute("""
        SELECT new_price, change_rate, turnoverrate, pe, pbnewmrq, total_market_cap
        FROM cn_stock_spot WHERE code = %s AND date = %s
    """, (code_str, today))
    spot = c.fetchone()
    
    mcap = round(float(spot[5]) / 10000, 1) if spot and spot[5] else None
    chg_pct = float(spot[1]) if spot and spot[1] else 0
    turn = float(spot[2]) if spot and spot[2] else 0
    pe_val = round(float(spot[3]), 1) if spot and spot[3] else None
    pb_val = round(float(spot[4]), 2) if spot and spot[4] else None
    
    chgs_str = ', '.join([f'{x:.1f}%' for x in daily_chgs])
    
    results.append({
        'code': code_str, 'name': name,
        'price': round(closes[-1], 2),
        'change_pct': round(chg_pct, 2),
        'turnover': turn,
        'total_chg': total_chg,
        'daily_chgs': chgs_str,
        'dist_low': round(dist, 1),
        'yr_low': round(yr_low, 2),
        'yr_high': round(yr_high, 2),
        'pctl': round(pctl, 1),
        'pe': pe_val,
        'pb': pb_val,
        'mcap': mcap,
    })

conn.close()

# 距低点由近到远排序
results.sort(key=lambda x: x['dist_low'])

print(f'从42只连续小阳线中，筛选出 {len(results)} 只低位股\n')

for i, r in enumerate(results, 1):
    tag = '🟢' if r['dist_low'] < 10 else '🟡'
    pe_str = f'{r["pe"]}' if r['pe'] else 'N/A'
    pb_str = f'{r["pb"]}' if r['pb'] else 'N/A'
    mc_str = f'{r["mcap"]}亿' if r['mcap'] else 'N/A'
    
    print(f'{i}. {r["name"]}({r["code"]})')
    print(f'   价格:{r["price"]}  今日:{r["change_pct"]:+.2f}%  换手:{r["turnover"]:.2f}%')
    print(f'   累计涨幅:{r["total_chg"]:+.2f}%  日涨幅:[{r["daily_chgs"]}]')
    print(f'   {tag} 距年低:{r["dist_low"]:+.1f}%  年低:{r["yr_low"]}  年高:{r["yr_high"]}')
    print(f'   年低位百分位:{r["pctl"]}%  PE:{pe_str}  PB:{pb_str}  市值:{mc_str}')
    print()

print(f'=== 完成 ===')