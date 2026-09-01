#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""搜索国家六张网核心标的"""
import requests, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# 搜索 Bing
queries = [
    '国家六张网 概念 股票 标的',
    '六张网 新型电网 水网 交通网 信息网 物流网 生态网',
    '国家六张网 核心龙头股',
]

for q in queries:
    print(f'\n{"="*60}')
    print(f'搜索: {q}')
    print('='*60)
    try:
        r = requests.get(f'https://cn.bing.com/search?q={requests.utils.quote(q)}',
                        headers=headers, timeout=10, proxies={'http': '', 'https': ''})
        r.encoding = 'utf-8'
        html = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # Extract title+url pairs
        matches = re.findall(r'<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', html)
        for url, title in matches[:8]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            print(f'\n  ▸ {title}')
            print(f'    {url}')
        
        # Also print the visible result text
        text = re.sub(r'<[^>]+>', '\n', html)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 30]
        for l in lines[:10]:
            if any(kw in l for kw in ['六张网', '六网', '水网', '电网', '交通网', '信息网', '物流网', '生态']):
                print(f'  📝 {l[:200]}')
    except Exception as e:
        print(f'  Error: {e}')