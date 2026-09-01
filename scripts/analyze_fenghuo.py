#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""烽火电子专业分析"""
import pymysql
from datetime import date, timedelta
import requests, re

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
conn = pymysql.connect(**DB)
c = conn.cursor()

# 查股票基本信息
c.execute("SELECT code, id, name FROM stock_info WHERE name LIKE '%烽火电子%' OR code = '000561'")
r = c.fetchone()
if not r:
    c.execute("SELECT code, id, name FROM stock_info WHERE name LIKE '%烽火%'")
    r = c.fetchone()

if r:
    code, sid, name = r
    print(f"=== {name}({code}) ===")
    
    # 最新行情
    c.execute("SELECT MAX(date) FROM cn_stock_spot")
    sd = c.fetchone()[0]
    c.execute("SELECT new_price, change_rate, turnoverrate, open_price, high_price, low_price, volume, deal_amount, amplitude FROM cn_stock_spot WHERE code=%s AND date=%s", (code, sd))
    spot = c.fetchone()
    if spot:
        print(f"\n📊 行情({sd}):")
        print(f"   收盘: {spot[0]}元  涨幅: {spot[1]}%")
        print(f"   今开: {spot[3]}  最高: {spot[4]}  最低: {spot[5]}")
        print(f"   换手: {spot[2]}%  量: {spot[6]}  额: {spot[7]}")
    
    # 近60日K线
    c.execute("SELECT date, close, change_percent, volume, amount FROM stock_daily WHERE stock_id=%s ORDER BY date ASC LIMIT 60", (sid,))
    rows = c.fetchall()
    if rows:
        closes = [float(r[1]) for r in rows]
        chgs = [float(r[2] or 0) for r in rows]
        vols = [float(r[3]) for r in rows]
        
        print(f"\n📈 技术指标:")
        if len(closes) >= 20:
            ma5 = sum(closes[-5:])/5
            ma10 = sum(closes[-10:])/10
            ma20 = sum(closes[-20:])/20
            ma60_val = sum(closes[-min(60,len(closes)):])/min(60,len(closes))
            print(f"   MA5={ma5:.2f}  MA10={ma10:.2f}  MA20={ma20:.2f}  MA60={ma60_val:.2f}")
            trend = "↑多头" if ma5 > ma10 > ma20 else ("↓空头" if ma5 < ma10 < ma20 else "→震荡")
            print(f"   趋势: {trend}")
        
        if len(chgs) >= 20:
            week_chg = sum(chgs[-5:])
            month_chg = sum(chgs[-20:])
            print(f"   近5日涨跌: {week_chg:+.2f}%")
            print(f"   近20日涨跌: {month_chg:+.2f}%")
        
        if len(closes) >= 20:
            max_c = max(closes[-20:])
            min_c = min(closes[-20:])
            print(f"   20日最高: {max_c}  最低: {min_c}  波幅: {(max_c-min_c)/min_c*100:.1f}%")
        
        if len(vols) >= 20:
            avg_vol_5 = sum(vols[-5:])/5
            avg_vol_20 = sum(vols[-20:])/20
            vol_ratio = avg_vol_5/avg_vol_20 if avg_vol_20 > 0 else 0
            desc = '放量' if vol_ratio>1.5 else ('缩量' if vol_ratio<0.7 else '正常')
            print(f"   量能: 近5日均量/近20日均量={vol_ratio:.2f}倍 {desc}")

    # 近20日明细(倒序)
    c.execute("SELECT date, open, close, high, low, change_percent, volume FROM stock_daily WHERE stock_id=%s ORDER BY date DESC LIMIT 20", (sid,))
    detail = c.fetchall()
    if detail:
        print(f"\n📋 近20日明细:")
        for d, o, cl, h, l, chg, v in reversed(detail):
            marker = ""
            chg_val = float(chg or 0)
            if chg_val >= 9.5: marker = " 🔥涨停"
            elif chg_val <= -9.5: marker = " 💥跌停"
            elif chg_val >= 5: marker = " ⚡大涨"
            print(f"   {d} 开{o} 收{cl} 高{h} 低{l} 涨跌{chg}% 量{v}{marker}")

conn.close()

# 网上搜索公司概况
print(f"\n🌐 公司概况:")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
try:
    r = requests.get(f'https://cn.bing.com/search?q={requests.utils.quote("000561 烽火电子 主营业务 概念")}', 
                     headers=headers, timeout=10)
    snippets = re.findall(r'<p[^>]*>(.*?)</p>', r.text, re.DOTALL)
    for s in snippets[:10]:
        clean = re.sub(r'<[^>]+>', '', s).strip()
        if clean and len(clean) > 20 and any(kw in clean for kw in ['通信','电子','军工','主营','概念','公司','烽火']):
            print(f"   {clean[:300]}")
except Exception as e:
    print(f"   搜索异常: {e}")