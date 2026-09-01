#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""提交雪球验证码完成登录"""
import sys, requests, json, os

phone = sys.argv[1] if len(sys.argv) > 1 else ''
code = sys.argv[2] if len(sys.argv) > 2 else ''

if not phone or not code:
    print('用法: venv/Scripts/python scripts/xueqiu_login_code.py 手机号 验证码')
    sys.exit(1)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
})

# 先访问首页
r = s.get('https://xueqiu.com/', timeout=30)
print(f'首页: {r.status_code}')

# 登录
r = s.post('https://xueqiu.com/snowman/login',
           data={'telephone': phone, 'code': code, 'remember_me': 'true'},
           timeout=15)
print(f'登录: {r.status_code}')
try:
    resp = r.json()
    print(f'结果: {json.dumps(resp, ensure_ascii=False)[:300]}')
except:
    print(f'响应: {r.text[:300]}')

# 保存 cookies
cookie_file = 'E:/量化研究/workspace/stock/output/xueqiu_cookies.txt'
os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
with open(cookie_file, 'w', encoding='utf-8') as f:
    for c in s.cookies:
        f.write(f'{c.name}={c.value}\n')
    # 额外保存 token 方便直接使用
    xq_a_token = s.cookies.get('xq_a_token', '')
    if xq_a_token:
        f.write(f'\n# xq_a_token={xq_a_token}\n')

print(f'\nCookies 已保存到: {cookie_file}')
xq_a_token = s.cookies.get('xq_a_token', '')
xq_r_token = s.cookies.get('xq_r_token', '')
print(f'xq_a_token: {xq_a_token[:15] if xq_a_token else "未获取"}')
print(f'xq_r_token: {xq_r_token[:15] if xq_r_token else "未获取"}')