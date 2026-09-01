#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用已保存的雪球 cookie 自动发帖"""
import sys, os, json, glob, requests
from datetime import datetime

today_str = datetime.now().strftime('%Y-%m-%d')
out_dir = 'E:/量化研究/workspace/stock/output/review'
cookie_file = 'E:/量化研究/workspace/stock/output/xueqiu_cookies.txt'

# 读取复盘报告
report_file = f'{out_dir}/review_{today_str}.txt'
if not os.path.exists(report_file):
    files = sorted(glob.glob(f'{out_dir}/review_*.txt'), reverse=True)
    if not files:
        print('❌ 没有复盘报告')
        sys.exit(1)
    report_file = files[0]

with open(report_file, 'r', encoding='utf-8') as f:
    content = f.read()
print(f'📄 报告: {len(content)} 字')

# 读取 cookie
if not os.path.exists(cookie_file):
    print(f'❌ 未找到 cookie 文件: {cookie_file}')
    print('   请先运行 xueqiu_login_code.py 完成登录')
    sys.exit(1)

s = requests.Session()
with open(cookie_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            name, value = line.split('=', 1)
            s.cookies.set(name, value, domain='.xueqiu.com')

xq_a_token = s.cookies.get('xq_a_token', '')
if not xq_a_token:
    print('❌ cookie 中无 xq_a_token，请重新登录')
    sys.exit(1)

print(f'🔑 token: {xq_a_token[:10]}...')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# 访问首页
r = s.get('https://xueqiu.com/', headers=headers, timeout=30)
print(f'🏠 首页: {r.status_code}')

# 发帖
r = s.post('https://xueqiu.com/statuses/update.json',
           headers=headers, data={'status': content}, timeout=30)
print(f'📤 发帖: {r.status_code}')

if r.status_code == 200:
    print('✅ 发帖成功！')
    try:
        resp = r.json()
        pid = resp.get('id', '?')
        uid = resp.get('user_id', '?')
        print(f'  链接: https://xueqiu.com/{uid}/{pid}')
    except Exception:
        print(f'  响应: {r.text[:200]}')
else:
    print(f'❌ 失败: {r.text[:300]}')