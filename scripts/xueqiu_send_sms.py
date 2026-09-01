#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发送雪球登录验证码"""
import sys, requests, json

phone = sys.argv[1] if len(sys.argv) > 1 else ''
if not phone:
    print('用法: venv/Scripts/python scripts/xueqiu_send_sms.py 手机号')
    sys.exit(1)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
}

s = requests.Session()
s.headers.update(headers)

# 先访问首页
r = s.get('https://xueqiu.com/', timeout=30)
print(f'首页: {r.status_code}')

# 发送验证码
r = s.post('https://xueqiu.com/snowman/login/verify_code',
           data={'telephone': phone}, timeout=15)
print(f'发送验证码: {r.status_code}')
try:
    resp = r.json()
    print(f'结果: {json.dumps(resp, ensure_ascii=False)}')
except:
    print(f'响应: {r.text[:200]}')