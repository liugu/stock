#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""华大九天(301269) 技术分析"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import numpy as np
from datetime import date

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
conn = pymysql.connect(**DB)
c = conn.cursor()

stock_id = 496  # 华大九天
stock_code = '301269'

# === 实时行情 ===
c.execute('''SELECT cs.new_price,cs.change_rate,cs.high_price,cs.low_price,cs.open_price,
cs.pre_close_price,cs.volume,cs.deal_amount,cs.turnoverrate,cs.total_market_cap,cs.industry
FROM cn_stock_spot cs WHERE cs.code=%s ORDER BY cs.date DESC LIMIT 1''', (stock_code,))
r = c.fetchone()
print('='*50)
print(f'华大九天(301269) 技术分析 -- {date.today()}')
print('='*50)
print(f'行情: {r[0]}元 | {r[1]}% | 行业: {r[10]}')
print(f'今开: {r[4]} | 昨收: {r[5]} | 最高: {r[2]} | 最低: {r[3]}')
print(f'成交额: {r[7]/1e8:.1f}亿 | 换手: {r[8]}% | 市值: {r[9]/1e8:.0f}亿')

# === 日K数据 ===
c.execute('SELECT date,close,high,low,volume FROM stock_daily WHERE stock_id=%s ORDER BY date ASC', (stock_id,))
rows = c.fetchall()
dates = [r[0] for r in rows]
closes = [float(r[1]) for r in rows]
highs = [float(r[2]) for r in rows]
lows = [float(r[3]) for r in rows]
vols = [r[4] for r in rows]
n = len(closes)

# === 均线 ===
print('\n━━━ 均线系统 ━━━')
ma5 = np.mean(closes[-5:])
ma10 = np.mean(closes[-10:]) if n>=10 else 0
ma20 = np.mean(closes[-20:]) if n>=20 else 0
ma60 = np.mean(closes[-60:]) if n>=60 else 0
print(f'MA5:  {ma5:.2f}')
print(f'MA10: {ma10:.2f}')
print(f'MA20: {ma20:.2f}')
if n>=60: print(f'MA60: {ma60:.2f}')

# 均线排列
if n>=20:
    print(f'排列: MA5({ma5:.1f}) / MA10({ma10:.1f}) / MA20({ma20:.1f})')
    if ma5>ma10>ma20: print('→ 多头排列 ✓')
    elif ma5<ma10<ma20: print('→ 空头排列 ✗ (需观察是否反转)')
    else: print('→ 均线粘合/整理区')

# 当前价格相对均线位置
last_close = closes[-1]
print(f'股价相对均线:')
for name,ma in [('MA5',ma5),('MA10',ma10),('MA20',ma20),('MA60',ma60)]:
    if ma>0:
        pct = (last_close-ma)/ma*100
        print(f'  相对{name}: {pct:+.1f}%')

# === MACD ===
print('\n━━━ MACD(12,26,9) ━━━')
ema12 = [closes[0]]
ema26 = [closes[0]]
for i in range(1, n):
    ema12.append(closes[i]*2/13 + ema12[-1]*11/13)
    ema26.append(closes[i]*2/27 + ema26[-1]*25/27)
dif = [ema12[i]-ema26[i] for i in range(n)]
dea = [dif[0]]
for i in range(1, n):
    dea.append(dif[i]*2/10 + dea[-1]*8/10)
macd_hist = [2*(dif[i]-dea[i]) for i in range(n)]
print(f'DIF:   {dif[-1]:.2f}')
print(f'DEA:  {dea[-1]:.2f}')
print(f'柱:    {macd_hist[-1]:.2f}')
print(f'DIF交叉: {"金叉 ✓" if dif[-1]>dea[-1] else "死叉 ✗"}')
# DIF方向
if len(dif)>=3:
    if dif[-1]>dif[-2]:
        print(f'DIF: 向上 ✓ (DIF{"" if dif[-2]<=dif[-3] else "已持续"}上升)')
    else:
        print(f'DIF: 向下 ✗')

# === KDJ ===
print('\n━━━ KDJ(9,3,3) ━━━')
# 计算RSV
h9 = max(highs[-9:]) if n>=9 else max(highs)
l9 = min(lows[-9:]) if n>=9 else min(lows)
rsv = (closes[-1]-l9)/(h9-l9)*100 if h9!=l9 else 50
# K=3日平滑RSV, D=3日均K
k_vals = [50]
for i in range(1, min(60, n)):
    idx = n-1-i
    hi9 = max(highs[idx:idx+9]) if idx+9<=n else max(highs[idx:])
    lo9 = min(lows[idx:idx+9]) if idx+9<=n else min(lows[idx:])
    rsv_i = (closes[idx]-lo9)/(hi9-lo9)*100 if hi9!=lo9 else 50
    k_vals.append(k_vals[-1]*2/3 + rsv_i/3)
k = k_vals[-1]
d = np.mean(k_vals[-3:]) if len(k_vals)>=3 else k
j = 3*k - 2*d
print(f'K: {k:.1f}')
print(f'D: {d:.1f}')
print(f'J: {j:.1f}')
if k>80: print(f'K>80 → 超买区')
elif k<20: print(f'K<20 → 超卖区')
else: print(f'中性区')

if k>d:
    print(f'K>D → 金叉趋势')
else:
    print(f'K<D → 死叉趋势')

# === RSI ===
print('\n━━━ RSI(14) ━━━')
gains = []; losses = []
for i in range(n-14, n):
    if i==n-14: continue
    chg = closes[i]-closes[i-1]
    gains.append(max(0,chg))
    losses.append(max(0,-chg))
avg_gain = np.mean(gains) if gains else 0
avg_loss = np.mean(losses) if losses else 1
rsi = 100 - 100/(1+avg_gain/avg_loss) if avg_loss>0 else 100
print(f'RSI: {rsi:.1f}')
if rsi > 70: print('→ 超买 (RSI>70)')
elif rsi < 30: print('→ 超卖 (RSI<30)')
else: print('→ 中性区间')

# === 布林带 ===
print('\n━━━ 布林带(20,2) ━━━')
if n>=20:
    bb_mid = ma20
    bb_std = np.std(closes[-20:])
    bb_upper = bb_mid + 2*bb_std
    bb_lower = bb_mid - 2*bb_std
    print(f'上轨: {bb_upper:.2f}')
    print(f'中轨: {bb_mid:.2f}')
    print(f'下轨: {bb_lower:.2f}')
    bp = (last_close-bb_lower)/(bb_upper-bb_lower)*100
    print(f'带宽: {bb_upper-bb_lower:.2f}')
    if last_close > bb_upper:
        print(f'股价在 上轨之上 → 超买/突破信号')
    elif last_close < bb_lower:
        print(f'股价在 下轨之下 → 超卖/触底信号')
    else:
        print(f'股价在轨道内 (位于{bp:.0f}%位置)')

# === 成交量 ===
print('\n━━━ 成交量分析 ━━━')
avg_vol_20 = np.mean(vols[-20:-1]) if n>=20 else np.mean(vols[:-1])
last_vol = vols[-1]
print(f'今日量: {last_vol/1e4:.0f}万')
print(f'20日均: {avg_vol_20/1e4:.0f}万')
vol_ratio = last_vol/avg_vol_20 if avg_vol_20>0 else 1
print(f'量比: {vol_ratio:.2f}')
if vol_ratio > 1.5:
    print(f'→ 明显放量 ✓ ({vol_ratio:.1f}倍)')
    # 判断放量方向
    chg = (closes[-1]-closes[-2])/closes[-2]*100 if n>=2 else 0
    if chg > 0:
        print(f'  且收涨{chg:+.2f}% → 价涨量增 ✓')
    else:
        print(f'  但收跌{chg:+.2f}% → 放量下跌需警惕')
elif vol_ratio < 0.5:
    print(f'→ 明显缩量 ◐')
else:
    print(f'→ 量能正常')

# === 近期走势 ===
print('\n━━━ 近期走势 ━━━')
print(f'近5日: {" ".join(f"{c:.1f}" for c in closes[-5:])}')
print(f'近5日涨跌: {" → ".join(f"{v:+.2f}%" for v in [(closes[i]-closes[i-1])/closes[i-1]*100 for i in range(max(0,n-5), n) if i>0])}')

if n>=20:
    p20 = (closes[-1]-closes[-20])/closes[-20]*100
    print(f'近20日: {p20:+.2f}%')
if n>=60:
    p60 = (closes[-1]-closes[-60])/closes[-60]*100
    print(f'近60日: {p60:+.2f}%')

# 近期高点日期
recent30 = closes[-30:] if n>=30 else closes
recent_dates = dates[-30:] if n>=30 else dates
hi_idx = np.argmax(recent30)
lo_idx = np.argmin(recent30)
print(f'近30日最高: {recent30[hi_idx]:.2f} ({recent_dates[hi_idx]})')
print(f'近30日最低: {recent30[lo_idx]:.2f} ({recent_dates[lo_idx]})')

# === 支撑阻力 ===
print('\n━━━ 支撑/阻力位 ━━━')
print(f'上方压力:')
print(f'  整数关口 120 (前波高点附近)')
print(f'  前高 121.50 (07-07)')
print(f'  上轨 {bb_upper:.0f} (布林带上轨)' if n>=20 else '')
print(f'下方支撑:')
print(f'  MA5 {ma5:.0f}')
print(f'  整数关口 110')
print(f'  前低 109.50 (07-08盘中)')
print(f'  MA20 {ma20:.0f}' if n>=20 else '')

# === 综合评价 ===
print('\n━━━ 技术面综合评价 ━━━')
scores = []
if n>=20 and ma5>ma10>ma20: scores.append(('趋势', '多头排列', '+'))
elif n>=20 and ma5<ma10<ma20: scores.append(('趋势', '空头排列需观察', '-'))
else: scores.append(('趋势', '整理/方向不明', '~'))

if dif[-1]>dea[-1] and dif[-1]>dif[-2]: scores.append(('MACD', '金叉+DIF向上', '+'))
elif dif[-1]>dea[-1]: scores.append(('MACD', '金叉中但动能减弱', '~'))
else: scores.append(('MACD', '死叉', '-'))

if k>80: scores.append(('KDJ', '超买', '-'))
elif k<20: scores.append(('KDJ', '超卖', '+'))
elif k>d: scores.append(('KDJ', '中性偏强', '~'))
else: scores.append(('KDJ', '中性偏弱', '~'))

if rsi>70: scores.append(('RSI', '超买', '-'))
elif rsi<30: scores.append(('RSI', '超卖', '+'))
elif rsi>50: scores.append(('RSI', '偏强', '+'))
else: scores.append(('RSI', '偏弱', '-'))

if last_close>bb_upper: scores.append(('布林带', '突破上轨', '~'))
elif last_close<bb_lower: scores.append(('布林带', '跌破下轨触底', '+'))
elif bp<30: scores.append(('布林带', '下轨附近', '+'))
elif bp>70: scores.append(('布林带', '上轨附近', '-'))
else: scores.append(('布林带', '中轨附近正常', '~'))

if vol_ratio>1.5: scores.append(('成交量', '明显放量', '~'))
elif vol_ratio<0.5: scores.append(('成交量', '缩量整理', '~'))
else: scores.append(('成交量', '量能正常', '~'))

pos = sum(1 for _,_,s in scores if s=='+')
neg = sum(1 for _,_,s in scores if s=='-')
neu = sum(1 for _,_,s in scores if s=='~')

for name, desc, sig in scores:
    sym = {'+':'✓','-':'✗','~':'◐'}[sig]
    print(f'  {sym} {name}: {desc}')

total = len(scores)
print()
if pos >= neg and pos >= neu:
    print(f'总评: 偏多 ({pos}多/{neg}空/{neu}中)')
elif neg > pos:
    print(f'总评: 偏空 ({pos}多/{neg}空/{neu}中)')
else:
    print(f'总评: 中性震荡 ({pos}多/{neg}空/{neu}中)')

conn.close()