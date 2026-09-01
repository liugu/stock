#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全面查看币安账户所有资产（现货）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os, time, hashlib, hmac, urllib.parse, requests

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
cfg = json.load(open(CFG, 'r', encoding='utf-8'))
KEY, SEC = cfg['binance_api_key'], cfg['binance_api_secret']
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}
BASE = 'https://api.binance.com'

def signed(params):
    params['timestamp'] = int(time.time()*1000)
    q = urllib.parse.urlencode(params)
    return q + '&signature=' + hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()

acct = requests.get(f'{BASE}/api/v3/account?{signed({})}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15).json()
print('=== 现货账户所有非零资产 ===')
any_asset = False
for b in acct['balances']:
    free = float(b['free'])
    locked = float(b['locked'])
    if free > 0 or locked > 0:
        any_asset = True
        print(f"  {b['asset']}: 可用{free:.6f}  锁定{locked:.6f}")
if not any_asset:
    print('  (现货账户无资产)')

# 检查是否有其他账户类型信息（资金/合约不能通过现货API直接查，但试下总资产）
print('\n=== 尝试其他账户 ===')
# 尝试合约账户（用同样的key，如果有合约权限）
try:
    fut = requests.get(f'{BASE}/fapi/v1/balance', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=10)
    if fut.status_code == 200:
        print('合约账户余额:')
        for b in fut.json():
            if float(b['balance']) > 0:
                print(f"  {b['asset']}: {b['balance']} (可用{b['availableBalance']})")
    else:
        print(f'合约账户: {fut.status_code} (可能无合约权限)')
except Exception as e:
    print(f'合约账户查询出错: {str(e).splitlines()[0][:80]}')