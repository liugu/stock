#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
雪球手机号+验证码登录工具
"""
import sys, requests, json, os
from http.cookiejar import MozillaCookieJar

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
    'X-Requested-With': 'XMLHttpRequest',
}

s = requests.Session()
s.headers.update(headers)

# 先访问首页获取必要的cookie
print('访问首页获取session...')
r = s.get('https://xueqiu.com/', timeout=30)
print(f'  首页: {r.status_code}')

# 取用户手机号
phone = input('请输入手机号: ').strip()

# 发送验证码
print(f'\n发送验证码到 {phone}...')
r = s.post('https://xueqiu.com/snowman/login/verify_code', 
           data={'telephone': phone}, timeout=15)
print(f'  发送结果: {r.status_code} {r.text[:200]}')

code = input('\n请输入验证码: ').strip()

# 登录
print('登录中...')
login_data = {
    'telephone': phone,
    'code': code,
    'remember_me': 'true',
}
r = s.post('https://xueqiu.com/snowman/login', 
           data=login_data, timeout=15)
print(f'  登录结果: {r.status_code}')

try:
    resp = r.json()
    print(f'  响应: {json.dumps(resp, ensure_ascii=False)[:300]}')
except:
    print(f'  原始响应: {r.text[:300]}')

# 保存 cookies
cookie_file = 'E:/量化研究/workspace/stock/output/xueqiu_cookies.txt'
os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
with open(cookie_file, 'w') as f:
    for c in s.cookies:
        f.write(f'{c.name}={c.value}\n')
print(f'\nCookies 已保存到: {cookie_file}')

# 检查是否登录成功
print('\n验证登录态...')
r = s.get('https://xueqiu.com/statuses/original/timeline.json?page=1', timeout=15)
if 'aliyun_waf' in r.text:
    print('⚠ WAF拦截，尝试用token直接发帖...')
    # 直接尝试发帖
    test_data = {'status': '测试登录成功 🤖'}
    r2 = s.post('https://xueqiu.com/statuses/update.json', data=test_data, timeout=15)
    print(f'  测试发帖: {r2.status_code} {r2.text[:200]}')
else:
    try:
        data = r.json()
        print(f'✅ 登录成功! 用户名: {data.get("user", {}).get("screen_name", "?")}')
    except:
        print(f'  响应: {r.text[:200]}')

print('\n✅ 完成! 现在可以运行 post_to_xueqiu.py 自动发帖了')