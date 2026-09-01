#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 搜主营业务
qs = [
    '双杰电气 主营业务 输配电 箱变 充换电',
    '双杰电气 概念 板块 所属行业',
]
for q in qs:
    r = requests.get('https://cn.bing.com/search?q=' + requests.utils.quote(q), headers=headers, timeout=10)
    if r.status_code == 200:
        results = re.findall(r'<li class=\"b_algo[^\"]*\"[^>]*>(.*?)</li>', r.text, re.DOTALL)
        for item in results[:3]:
            snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
            if snip_m:
                snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
                if snip and len(snip) > 20:
                    print(f"  {snip[:300]}")