#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 用股票代码+完整名称搜
q = requests.utils.quote('\"300444\" \"双杰电气\" 公司 主营业务')
r = requests.get('https://cn.bing.com/search?q=' + q, headers=headers, timeout=10)
if r.status_code == 200:
    results = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', r.text, re.DOTALL)
    for item in results[:8]:
        title_m = re.search(r'<h2><a[^>]*>(.*?)</a></h2>', item, re.DOTALL)
        if title_m:
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            print(f"\n📰 {title[:200]}")
        snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
        if snip_m:
            snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
            if snip:
                print(f"   {snip[:300]}")

# 搜中标/订单/公告
print("\n\n=== 搜索: 中标 订单 公告 ===")
q2 = requests.utils.quote('300444 双杰电气 中标')
r2 = requests.get('https://cn.bing.com/search?q=' + q2, headers=headers, timeout=10)
if r2.status_code == 200:
    results = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', r2.text, re.DOTALL)
    for item in results[:8]:
        title_m = re.search(r'<h2><a[^>]*>(.*?)</a></h2>', item, re.DOTALL)
        if title_m:
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            print(f"\n📰 {title[:200]}")
        snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
        if snip_m:
            snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
            if snip:
                print(f"   {snip[:300]}")