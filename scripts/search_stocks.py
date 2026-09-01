#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""搜索国家六张网核心标的 - Bing版"""
import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# Bing search for 六张网
r = requests.get(
    'https://cn.bing.com/search?q=' + requests.utils.quote('"六张网" 概念股 龙头 标的'),
    headers=headers, timeout=10
)
print(f'Bing Status: {r.status_code}')

# Try to extract <li class="b_algo"> results
results = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', r.text, re.DOTALL)
print(f'Found {len(results)} search results')

for i, item in enumerate(results[:15]):
    title_m = re.search(r'<h2><a[^>]*>(.*?)</a></h2>', item, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else 'N/A'
    
    snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
    snippet = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()[:200] if snip_m else ''
    
    url_m = re.search(r'<a[^>]*href="([^"]+)"', item)
    url = url_m.group(1) if url_m else ''
    
    print(f'\n{i+1}. {title}')
    print(f'   {url}')
    if snippet:
        print(f'   {snippet}')

# Also print anything that contains "六" in the page
text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
lines = [l.strip() for l in text.split('\n') if '六' in l and len(l.strip()) > 15]
print('\n\n=== 包含"六"的文本 ===')
for l in lines[:10]:
    print(l[:200])