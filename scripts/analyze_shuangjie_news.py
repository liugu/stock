#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""双杰电气消息面分析"""
import requests, re, html as h
import pymysql

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 查数据库基本信息
conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

c.execute("SELECT code, id, name FROM stock_info WHERE name LIKE '%双杰%' OR code = '300444'")
r = c.fetchone()
if r:
    code, sid, name = r
    print(f"=== {name}({code}) 技术面 ===")
    
    # 最新spot
    c.execute("SELECT MAX(date) FROM cn_stock_spot")
    sd = c.fetchone()[0]
    c.execute("SELECT new_price, change_rate, turnoverrate, open_price, high_price, low_price FROM cn_stock_spot WHERE code=%s AND date=%s", (code, sd))
    spot = c.fetchone()
    if spot:
        print(f"最新行情({sd}): 收盘{spot[0]}元 涨幅{spot[1]}% 换手{spot[2]}% 开{spot[3]} 高{spot[4]} 低{spot[5]}")
    
    # 近20日daily
    c.execute("SELECT date, close, change_percent, volume, amount FROM stock_daily WHERE stock_id=%s ORDER BY date DESC LIMIT 20", (sid,))
    rows = c.fetchall()
    if rows:
        print(f"\n近20日走势:")
        closes = []
        for d, cl, chg, vol, amt in reversed(rows):
            closes.append(float(cl))
            print(f"  {d}: 收盘{cl} 涨跌{chg}% 量{vol}")
        
        if len(closes) >= 5:
            ma5 = sum(closes[-5:])/5
            ma10 = sum(closes)/len(closes)
            ma20 = sum(closes)/len(closes)
            print(f"\nMA5={ma5:.2f} MA10={ma10:.2f} MA20={ma20:.2f}")
            print(f"短期趋势: {'↑ 多头' if ma5>ma10 else '↓ 空头'}")
            
            # 涨跌幅统计
            if len(closes) >= 10:
                chgs = [rows[i][2] for i in range(len(rows))] 
                last_5_chg = sum([float(r[2] or 0) for r in rows[:5]])
                last_10_chg = sum([float(r[2] or 0) for r in rows[:10]])
                print(f"近5日累计涨跌: {last_5_chg:.2f}%")
                print(f"近10日累计涨跌: {last_10_chg:.2f}%")

conn.close()

# 网上搜索消息
print(f"\n=== {name}({code}) 近期消息 ===")

# Bing搜索
r = requests.get(
    'https://cn.bing.com/search?q=' + requests.utils.quote(f'300444 双杰电气 公告 新闻 2026'),
    headers=headers, timeout=10
)
if r.status_code == 200:
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 15]
    for l in lines[:20]:
        clean = h.unescape(l)
        if any(kw in clean for kw in ['双杰', '300444', '电气', '电网', '配电', '充电', '新能源', '公告', '业绩', '中标', '订单']):
            print(f"  -> {clean[:200]}")

# Bing新闻搜索
r2 = requests.get(
    'https://cn.bing.com/news/search?q=' + requests.utils.quote('300444 双杰电气'),
    headers=headers, timeout=10
)
if r2.status_code == 200:
    text = re.sub(r'<script[^>]*>.*?</script>', '', r2.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 15]
    for l in lines[:20]:
        clean = h.unescape(l)
        if any(kw in clean for kw in ['双杰', '300444']):
            print(f"  📰 {clean[:200]}")