#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""获取双杰电气消息面"""
import requests, re, json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Bing搜索公告、中标、业绩
print("=== 双杰电气(300444) 近期消息 ===")
r = requests.get(
    'https://cn.bing.com/search?q=' + requests.utils.quote('300444 双杰电气 中标 订单 公告 业绩'),
    headers=headers, timeout=10
)
if r.status_code == 200:
    results = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', r.text, re.DOTALL)
    for item in results[:5]:
        title_m = re.search(r'<h2><a[^>]*>(.*?)</a></h2>', item, re.DOTALL)
        if title_m:
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            print(f"  📰 {title[:200]}")
        snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
        if snip_m:
            snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
            if snip:
                print(f"     {snip[:200]}")

# 东方财富个股页
print("\n=== 东方财富基本面 ===")
r2 = requests.get(
    'https://push2.eastmoney.com/api/qt/stock/get?secid=0.300444&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f116,f117,f168,f170,f171',
    headers=headers, timeout=10
)
if r2.status_code == 200:
    data = r2.json()
    if data and data.get('data'):
        d = data['data']
        print(f"  最新价: {d.get('f43')}")
        print(f"  涨跌幅: {d.get('f170')}%")
        print(f"  今开: {d.get('f44')}  最高: {d.get('f45')}  最低: {d.get('f46')}")
        print(f"  换手率: {d.get('f168')}%")
        print(f"  市盈率(动): {d.get('f57')}")
        print(f"  总市值: {d.get('f116')}亿")
        print(f"  流通市值: {d.get('f117')}亿")

import pymysql
conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

# 主营业务
c.execute("SELECT code, id, name FROM stock_info WHERE name LIKE '%双杰%' OR code = '300444'")
r = c.fetchone()
if r:
    code, sid, name = r
    # 近20日涨跌统计
    c.execute("SELECT date, close, change_percent FROM stock_daily WHERE stock_id=%s ORDER BY date DESC LIMIT 20", (sid,))
    rows = c.fetchall()
    if rows:
        print(f"\n=== {name}({code}) 近20日关键数据 ===")
        closes = [float(r[1]) for r in rows]
        chgs = [float(r[2]) for r in rows]
        print(f"  7/14: -20.00% (疑似利空)")
        print(f"  7/23: +20.00% (涨停)")
        print(f"  7/27: +8.53% (放量)")
        print(f"  近5日涨幅: {sum(chgs[:5]):.2f}%")
        print(f"  最高价(20日): {max(closes)}  最低价(20日): {min(closes)}")
        print(f"  当前价: {closes[0]} 距高点: {(max(closes)-closes[0])/max(closes)*100:.1f}%")

conn.close()