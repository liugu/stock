#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""搜索国家六张网核心标的 - 详细版"""
import requests, re, html as htmlmod

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

proxies = {'http': '', 'https': ''}

# 搜狗微信搜索
r = requests.get(
    'https://weixin.sogou.com/weixin?type=2&query=' + requests.utils.quote('六张网概念龙头企业 新型电网 国家水网 算力网 通信网'),
    headers=headers, timeout=15, proxies=proxies
)

print(f'Status: {r.status_code}')
if r.status_code == 200:
    html = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    
    # Extract article links
    urls = re.findall(r'href="(https?://mp\.weixin\.qq\.com/s[^"]*)"', html)
    titles = re.findall(r'<h3[^>]*>.*?(?:title="([^"]*)"|>(.*?)</a>)', html)
    
    print(f'\n找到 {len(urls)} 篇文章链接')
    
    for i, url in enumerate(urls[:3]):
        url = url.replace('&amp;', '&')
        print(f'\n--- 文章 {i+1} ---')
        print(f'URL: {url}')
        try:
            ar = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            text = re.sub(r'<script[^>]*>.*?</script>', '', ar.text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', '\n', text)
            lines = [htmlmod.unescape(l.strip()) for l in text.split('\n') 
                     if l.strip() and len(l.strip()) > 15]
            for l in lines[:40]:
                print(l[:300])
        except Exception as e:
            print(f'Error fetching article: {e}')
else:
    # Fallback: print visible text anyway
    text = re.sub(r'<[^>]+>', '\n', r.text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 20]
    for l in lines[:20]:
        print(l[:200])