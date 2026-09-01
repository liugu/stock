#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 搜7月下旬反弹原因
qs = [
    '300444 双杰电气 涨停 利好 2026年7月',
    '300444 双杰电气 国家电网 恢复 中标资格',
]
for q in qs:
    r = requests.get('https://cn.bing.com/search?q=' + requests.utils.quote(q), headers=headers, timeout=10)
    if r.status_code == 200:
        results = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', r.text, re.DOTALL)
        for item in results[:5]:
            title_m = re.search(r'<h2><a[^>]*>(.*?)</a></h2>', item, re.DOTALL)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
                print(f"📰 {title[:200]}")
            snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
            if snip_m:
                snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
                if snip:
                    print(f"   {snip[:300]}")
        print()