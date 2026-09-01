#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 Chrome 读取雪球登录态，自动发帖
"""
import os, sys, json, glob, requests
from datetime import datetime

today_str = datetime.now().strftime('%Y-%m-%d')
out_dir = 'E:/量化研究/workspace/stock/output/review'
report_file = f'{out_dir}/review_{today_str}.txt'

# 读取复盘报告
if not os.path.exists(report_file):
    files = sorted(glob.glob(f'{out_dir}/review_*.txt'), reverse=True)
    if not files:
        print('❌ 没有复盘报告，请先运行 daily_review.py')
        sys.exit(1)
    report_file = files[0]
    print(f'使用最近报告: {report_file}')

with open(report_file, 'r', encoding='utf-8') as f:
    content = f.read()
print(f'📄 报告内容: {len(content)} 字')

# === 从 Chrome 读取雪球 cookies ===
try:
    import browser_cookie3
    cj = browser_cookie3.chrome(domain_name='xueqiu.com')
    cookies = {c.name: c.value for c in cj}
    print(f'🔑 已获取雪球 cookie: {len(cookies)} 个')
except Exception as e:
    print(f'❌ 读取 cookie 失败: {e}')
    print('   请先在 Chrome 登录雪球 (确保 Chrome 已关闭再运行)')
    sys.exit(1)

xq_a_token = cookies.get('xq_a_token', '')
xq_r_token = cookies.get('xq_r_token', '')

if not xq_a_token:
    print('❌ 未找到 xq_a_token')
    print('   请先在 Chrome 登录雪球')
    sys.exit(1)

print(f'🔑 xq_a_token: {xq_a_token[:10]}...')

# === 发帖 ===
s = requests.Session()
s.cookies.set('xq_a_token', xq_a_token, domain='.xueqiu.com')
s.cookies.set('xq_r_token', xq_r_token, domain='.xueqiu.com')
s.cookies.set('xq_is_login', '1', domain='.xueqiu.com')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# 先访问首页
r = s.get('https://xueqiu.com/', headers=headers, timeout=30)
print(f'🏠 访问首页: {r.status_code}')

# 发帖
data = {'status': content}
r = s.post('https://xueqiu.com/statuses/update.json',
           headers=headers, data=data, timeout=30)
print(f'📤 发帖结果: {r.status_code}')

if r.status_code == 200:
    print('✅ 发帖成功！')
    try:
        resp = r.json()
        pid = resp.get('id', '?')
        uid = resp.get('user_id', '?')
        print(f'  帖子ID: {pid}')
        print(f'  链接: https://xueqiu.com/{uid}/{pid}')
    except Exception:
        print(f'  响应: {r.text[:200]}')
else:
    print(f'❌ 发帖失败: {r.text[:300]}')