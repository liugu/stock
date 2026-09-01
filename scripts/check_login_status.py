#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests, re

s = requests.Session()
with open('output/xueqiu_cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            name, value = line.split('=', 1)
            s.cookies.set(name, value, domain='.xueqiu.com')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

r = s.get('https://xueqiu.com/u/5806061123', headers=headers, timeout=30)
print(f'个人主页: {r.status_code}')
text = r.text[:20000]

nickname = '无情的复盘机器'
if nickname in text:
    print(f'✅ 找到昵称: {nickname}')
else:
    print('❌ 未找到昵称')
    idx = text.find('screen_name')
    if idx >= 0:
        print(f'  screen_name附近: {text[idx:idx+150]}')

for tag in ['xq_a_token', 'xq_is_login', '登录', '退出']:
    if tag in text[:5000]:
        print(f'  ✓ 含关键词: {tag}')

title = re.search(r'<title>([^<]+)', text)
if title:
    print(f'  页面标题: {title.group(1)}')