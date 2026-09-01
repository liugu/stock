#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查雪球登录状态"""
import requests, re

s = requests.Session()
with open('output/xueqiu_cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            name, value = line.split('=', 1)
            s.cookies.set(name, value, domain='.xueqiu.com')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 用户主页
r = s.get('https://xueqiu.com/settings/profile', headers=headers, timeout=30)
print(f'Profile: {r.status_code}')
if r.status_code == 200:
    text = r.text[:5000]
    name = re.search(r'screen_name["\']?\s*>\s*([^<]+)', text)
    if name:
        print(f'用户昵称: {name.group(1)}')
    phone = re.search(r'手机.*?验证|验证.*?手机', text)
    if phone:
        print('需手机验证')
else:
    print(f'内容: {r.text[:300]}')

# 自己的主页
uid_cookie = None
with open('output/xueqiu_cookies.txt', 'r') as f:
    for line in f:
        if line.startswith('u='):
            uid_cookie = line.split('=', 1)[1].strip()
if uid_cookie:
    r2 = s.get(f'https://xueqiu.com/u/{uid_cookie}', headers=headers, timeout=30)
    print(f'\n个人主页: {r2.status_code}')
    if r2.status_code == 200:
        print(f'页面标题: {re.search(r"<title>([^<]+)", r2.text[:500])}')
        # 检查是否有发帖
        if 'statuses' in r2.text[:10000]:
            print('有帖子列表')