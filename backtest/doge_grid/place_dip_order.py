#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""挂限价买单: DOGE $0.08 买100 DOGE"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os, time, hashlib, hmac, urllib.parse, requests
from datetime import datetime

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
print(f'现货USDT可用: {usdt:.2f}U')

# 下单参数: 0.08 x 100 = 8U
qty, price = 100, 0.0800
need = qty * price
print(f'下单: BUY {qty} DOGE @ ${price} (需锁定 {need:.2f}U)')

if usdt < need:
    print(f'❌ USDT不足 (需要{need:.2f}U, 只有{usdt:.2f}U)')
    sys.exit(1)

params = {
    'symbol': SYM, 'side': 'BUY', 'type': 'LIMIT', 'timeInForce': 'GTC',
    'quantity': str(qty), 'price': f'{price:.8f}'
}
r = requests.post(f'{BASE}/api/v3/order?{signed(params)}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15)
if r.status_code == 200:
    o = r.json()
    print(f'✅ 挂单成功! {o.get("side")} {o.get("origQty")} DOGE @ ${o.get("price")}')
    print(f'   订单ID: {o.get("orderId")}, 状态: {o.get("status")}')
else:
    print(f'❌ 挂单失败: {r.status_code} {r.text[:200]}')