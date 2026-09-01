#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""左侧买点选股：超跌+底部企稳+价值支撑"""
import pymysql, numpy as np, pandas as pd
from datetime import date

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
today = date.today()
print(f'=== 左侧买点选股 ({today}) ===\n')

conn = pymysql.connect(**DB)
sql = """
SELECT si.code, si.name, cs.new_price, cs.change_rate, cs.turnoverrate,
       cs.pe, cs.pbnewmrq, cs.total_market_cap, cs.industry
FROM cn_stock_spot cs
JOIN stock_info si ON BINARY si.code = BINARY cs.code
WHERE cs.date = %s
  AND si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
  AND (cs.pe > 0 OR cs.pbnewmrq < 1.5)
  AND cs.change_rate > -10
ORDER BY cs.code
"""
df = pd.read_sql(sql, conn, params=(today,))
print(f'基础池: {len(df)} 只\n')
conn.close()

results = []

for _, row in df.iterrows():
    code = row['code']; name = row['name']

    conn2 = pymysql.connect(**DB)
    c2 = conn2.cursor()
    try:
        c2.execute("""
            SELECT sd.date, sd.close, sd.open, sd.low, sd.high, sd.change_percent, sd.volume
            FROM stock_daily sd JOIN stock_info si ON sd.stock_id = si.id
            WHERE si.code = %s
            ORDER BY sd.date DESC LIMIT 260
        """, (code,))
        rows = list(c2.fetchall())
    finally:
        c2.close(); conn2.close()

    if not rows or len(rows) < 60: continue

    rows.reverse()
    n = len(rows)
    closes = [float(r[1]) for r in rows]
    opens = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    highs = [float(r[4]) for r in rows]
    chgs = [float(r[5] or 0) for r in rows]
    vols = [float(r[6]) for r in rows]

    last = closes[-1]

    # 年内低点判断
    lb = min(250, n)
    yr_low = min(lows[-lb:])
    yr_high = max(highs[-lb:])

    if yr_low <= 0 or last <= 0: continue

    dist_low = (last / yr_low - 1) * 100

    # 条件1：距年内低点 < 15%（左侧底部区域）
    if dist_low > 15: continue

    # 条件2：超跌（60日跌超8%）
    chg_60 = sum(chgs[-60:]) if len(chgs) >= 60 else sum(chgs)
    if chg_60 > -8: continue  # 跌幅不够大

    # 条件3：底部止跌信号
    last3 = rows[-3:]
    yang_cnt = sum(1 for r in last3 if float(r[1]) > float(r[2]))
    last_chg = chgs[-1]

    if not (yang_cnt >= 2 or last_chg > 1.5):
        # 或者连续5天小阳线企稳
        small_yang = True
        if n >= 5:
            for i in range(-5, 0):
                if closes[i] <= opens[i] or (closes[i]-opens[i])/opens[i]*100 > 5:
                    small_yang = False; break
        else: small_yang = False
        if not small_yang: continue

    # 条件4：基本面
    pe = float(row['pe']) if row['pe'] else 0
    pb = float(row['pbnewmrq']) if row['pbnewmrq'] else 0
    mcap = float(row['total_market_cap']) / 10000 if row['total_market_cap'] else 0
    turn = float(row['turnoverrate']) if row['turnoverrate'] else 0
    ind = row['industry'] or ''

    # 量能变化
    vol_5 = np.mean(vols[-5:]) if len(vols) >= 5 else 0
    vol_20 = np.mean(vols[-25:-5]) if len(vols) >= 25 else 1
    vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 1

    # 评分系统
    score = 0
    if dist_low < 8: score += 3
    elif dist_low < 12: score += 2
    else: score += 1

    if chg_60 < -20: score += 3
    elif chg_60 < -15: score += 2
    else: score += 1

    if last_chg > 2: score += 1

    if pe > 0 and pe < 20: score += 3
    elif pe > 0 and pe < 40: score += 2
    elif pe > 0: score += 1

    if pb < 1 and pe > 0: score += 2
    if vol_ratio > 1.2: score += 1
    if 30 < mcap < 300: score += 1
    if 'ST' not in name: score += 1

    results.append({
        'code': code, 'name': name,
        'price': round(last, 2),
        'chg%': round(last_chg, 2),
        'dist_low%': round(dist_low, 1),
        'yr_low': round(yr_low, 2),
        'yr_high': round(yr_high, 2),
        'chg60d%': round(chg_60, 1),
        'yang3d': f'{yang_cnt}/3',
        'vol_ratio': round(vol_ratio, 2),
        'pe': round(pe, 1) if pe > 0 else '亏损',
        'pb': round(pb, 2),
        'mcap': round(mcap, 1),
        'turnover': round(turn, 2),
        'industry': ind,
        'score': score,
    })

results.sort(key=lambda x: x['score'], reverse=True)

print(f'筛选出 {len(results)} 只左侧买点标的\n')

for i, r in enumerate(results[:25], 1):
    tag = '🔴' if r['dist_low%'] < 8 else ('🟠' if r['dist_low%'] < 12 else '🟡')
    pe_str = f'{r["pe"]}' if isinstance(r['pe'], float) else r['pe']
    print(f'{i}. {tag} {r["name"]}({r["code"]})  [得分:{r["score"]}]')
    print(f'   价格:{r["price"]}  今日:{r["chg%"]:+.2f}%  换手:{r["turnover"]}%')
    print(f'   距年低:{r["dist_low%"]:+.1f}%  年低:{r["yr_low"]}  60日跌:{r["chg60d%"]:+.1f}%')
    print(f'   近3日阳线:{r["yang3d"]}  量比:{r["vol_ratio"]}x')
    print(f'   PE:{pe_str}  PB:{r["pb"]}  市值:{r["mcap"]}亿  {r["industry"]}')
    print()

print(f'=== 完成，共 {len(results)} 只 ===')