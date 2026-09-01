#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证API key是否有效（只读测试，不修改任何订单）"""
import json, time, hashlib, hmac, urllib.parse, requests, shutil, os

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')

# 先备份config（防止再次丢失）
backup = CFG + '.bak'
shutil.copy2(CFG, backup)
print(f'已备份配置 → {backup}')

cfg = json.load(open(CFG, 'r', encoding='utf-8'))
KEY = cfg['binance_api_key']
SEC = cfg['binance_api_secret']
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}
BASE = 'https://api.binance.com'

if '在此填入' in KEY or '在此填入' in SEC:
    print('❌ 仍未填写key')
    exit(1)

print(f'🔑 Key: {KEY[:4]}...{KEY[-4:]}')
print(f'🔑 Secret: {SEC[:2]}...{SEC[-2:]}')

# 时钟同步
r = requests.get(f'{BASE}/api/v3/time', proxies=PROX, timeout=10)
offset = r.json()['serverTime'] - int(time.time() * 1000)

def signed(path, params=None):
    params = params or {}
    params['timestamp'] = int(time.time()*1000) + offset
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    return f'{BASE}{path}?{q}&signature={sig}'

# 只读测试：账户余额
r = requests.get(signed('/api/v3/account', {}), headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=10)
if r.status_code == 200:
    bal = {b['asset']: float(b['free']) for b in r.json()['balances']}
    print(f'✅ API有效')
    print(f'   USDT: {bal.get("USDT", 0):.4f}')
    print(f'   DOGE: {bal.get("DOGE", 0):.4f}')
else:
    print(f'❌ API失败: {r.status_code} {r.text[:200]}')

# 读当前网格配置
g = cfg.get('grid_lower'), cfg.get('grid_upper'), cfg.get('grid_count')
print(f'当前网格配置: 区间 {g[0]}~{g[1]}, {g[2]}格')