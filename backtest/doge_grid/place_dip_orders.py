#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""加挂多档低价接货买单（摊低成本）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os, time, hashlib, hmac, urllib.parse, requests

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
cfg = json.load(open(CFG, 'r', encoding='utf-8'))
KEY, SEC = cfg['binance_api_key'], cfg['binance_api_secret']
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}
BASE = 'https://api.binance.com'
SYM = 'DOGEUSDT'

def signed(params):
    params['timestamp'] = int(time.time()*1000)
    q = urllib.parse.urlencode(params)
    return q + '&signature=' + hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()

# 查现货USDT可买量
acct = requests.get(f'{BASE}/api/v3/account?{signed({})}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15).json()
usdt = float([b for b in acct['balances'] if b['asset']=='USDT'][0]['free'])
# 加上已挂单锁定的金额（openOrders）- 查当前挂单
oo = requests.get(f'{BASE}/api/v3/openOrders?{signed({"symbol":SYM})}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15).json()
locked = sum(float(o['origQty'])*float(o['price']) for o in oo if o['side']=='BUY')
print(f'现货USDT可用: {usdt:.2f}U, 已锁定在买单: {locked:.2f}U, 净可用: {usdt-locked:.2f}U')
print(f'当前挂单数: {len(oo)}')
for o in oo:
    print(f'  [{o["side"]}] {o["price"]} x {o["origQty"]}DOGE')

# 要加的两档
new_orders = [(0.0750, 100), (0.0700, 100)]
print(f'\n待加: {[(f"@{p} x{q}") for p,q in new_orders]}')

# 计算所需
need_total = sum(p*q for p,q in new_orders)
print(f'需锁定: {need_total:.2f}U, 净可用: {usdt-locked:.2f}U')

if usdt - locked < need_total:
    print(f'❌ 资金不足! 需要{need_total:.2f}U 但净可用只有{usdt-locked:.2f}U')

for price, qty in new_orders:
    # 查重：同价位同方向是否已挂
    if any(o['side']=='BUY' and abs(float(o['price'])-price)<1e-6 for o in oo):
        print(f'  已存在 @{price} 买单，跳过')
        continue
    params = {
        'symbol': SYM, 'side': 'BUY', 'type': 'LIMIT', 'timeInForce': 'GTC',
        'quantity': str(qty), 'price': f'{price:.8f}'
    }
    r = requests.post(f'{BASE}/api/v3/order?{signed(params)}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15)
    if r.status_code == 200:
        o = r.json()
        print(f'  ✅ 挂单成功 BUY {o["origQty"]} DOGE @ ${o["price"]} (ID {o["orderId"]})')
    else:
        print(f'  ❌ 挂单失败 @{price}: {r.status_code} {r.text[:150]}')