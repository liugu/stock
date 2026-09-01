#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试雪球发帖，尝试不同方式"""
import requests, json

s = requests.Session()

with open('output/xueqiu_cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            name, value = line.split('=', 1)
            s.cookies.set(name, value, domain='.xueqiu.com')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
}

r = s.get('https://xueqiu.com/', headers=headers, timeout=30)
print(f'首页: {r.status_code}')

# 方法1: 标准 form
print('\n--- 方法1: form 短帖 ---')
r = s.post('https://xueqiu.com/statuses/update.json',
           headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
           data={'status': '测试发帖'},
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法2: 长帖（带title）
print('\n--- 方法2: 长帖 ---')
r = s.post('https://xueqiu.com/statuses/update.json',
           headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
           data={'status': '测试长帖内容', 'title': '测试'},
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法3: /api/statuses/update.json
print('\n--- 方法3: /api/ 路径 ---')
r = s.post('https://xueqiu.com/api/statuses/update.json',
           headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
           data={'status': '测试'},
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法4: v2
print('\n--- 方法4: /v2/ 路径 ---')
r = s.post('https://xueqiu.com/v2/statuses/update.json',
           headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
           data={'status': '测试'},
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法5: JSON
print('\n--- 方法5: JSON ---')
r = s.post('https://xueqiu.com/statuses/update.json',
           headers={**headers, 'Content-Type': 'application/json;charset=UTF-8'},
           data=json.dumps({'status': '测试'}),
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法6: 检查登录态
print('\n--- 方法6: 登录态验证 ---')
r = s.get('https://xueqiu.com/v4/statuses/user_timeline.json?user_id=-1',
          headers={**headers, 'Accept': 'application/json'},
          timeout=30)
print(f'  {r.status_code}')
if 'aliyun_waf' not in r.text[:200]:
    try:
        d = r.json()
        u = d.get('user', {})
        print(f'  用户: {u.get("screen_name", "?")}')
    except:
        print(f'  {r.text[:200]}')
else:
    print('  WAF拦截')

# 方法7: /api/status/create
print('\n--- 方法7: /api/status/create ---')
r = s.post('https://xueqiu.com/api/status/create',
           headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
           data={'content': '测试'},
           timeout=30)
print(f'  {r.status_code}: {r.text[:200]}')

# 方法8: 带 xq_id_token 的 Authorization
print('\n--- 方法8: Bearer token ---')
id_token = None
with open('output/xueqiu_cookies.txt', 'r') as f:
    for line in f:
        if line.startswith('xq_id_token='):
            id_token = line.split('=', 1)[1].strip()
if id_token:
    h = {**headers, 'Content-Type': 'application/x-www-form-urlencoded',
         'Authorization': f'Bearer {id_token}'}
    r = s.post('https://xueqiu.com/statuses/update.json',
               headers=h, data={'status': '测试'}, timeout=30)
    print(f'  {r.status_code}: {r.text[:200]}')
else:
    print('  未找到 xq_id_token')

# 方法9: 先获取页面，提取 CSRF token
print('\n--- 方法9: 从页面提取 token ---')
r = s.get('https://xueqiu.com/', timeout=30)
import re
# 看页面里有没有 token
tokens = re.findall(r'token[=:][\'"]?([^\'"&\s]+)', r.text[:5000])
print(f'  页面token: {tokens[:5]}')