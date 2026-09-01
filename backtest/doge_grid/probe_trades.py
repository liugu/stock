#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探测币安 myTrades 返回结构"""
import json, os, time, hashlib, hmac, urllib.parse, requests
from datetime import datetime

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
cfg = json.load(open(CFG, 'r', encoding='utf-8'))
KEY = cfg['binance_api_key']
SECRET = cfg['binance_api_secret']
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}
BASE = 'https://api.binance.com'

def signed(params):
    params['timestamp'] = int(time.time() * 1000)
    q = urllib.parse.urlencode(params)
    return q + '&signature=' + hmac.new(SECRET.encode(), q.encode(), hashlib.sha256).hexdigest()

# 查成交历史
params = {'symbol': 'DOGEUSDT', 'limit': 10}
url = f'{BASE}/api/v3/myTrades?{signed(params)}'
r = requests.get(url, headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=10)
print(f'myTrades: {r.status_code}')
if r.status_code == 200:
    trades = r.json()
    print(f'成交条数: {len(trades)}')
    for t in trades:
        side = 'BUY ' if t['isBuyer'] else 'SELL'
        ts = datetime.fromtimestamp(t['time'] / 1000).strftime('%m-%d %H:%M')
        print(f'  [{side}] {t["qty"]} DOGE @ {t["price"]} | 佣金{t["commission"]}{t["commissionAsset"]} | {ts}')
else:
    print(f'  {r.text[:300]}')

# openOrders
params2 = {'symbol': 'DOGEUSDT'}
url2 = f'{BASE}/api/v3/openOrders?{signed(params2)}'
r2 = requests.get(url2, headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=10)
print(f'\nopenOrders: {r2.status_code}')
if r2.status_code == 200:
    oo = r2.json()
    print(f'挂单数: {len(oo)}')
    for o in oo:
        print(f'  [{o["side"]}] {o["type"]} {o["price"]} x {o["origQty"]} 状态:{o["status"]}')