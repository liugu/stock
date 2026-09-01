#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""狗狗币网格：准确核算盈亏（只读，不改单）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os, time, hashlib, hmac, urllib.parse, requests
from datetime import datetime

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
cfg = json.load(open(CFG, 'r', encoding='utf-8'))
KEY, SEC = cfg['binance_api_key'], cfg['binance_api_secret']
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}
BASE = 'https://api.binance.com'

def signed(params):
    params['timestamp'] = int(time.time()*1000)
    q = urllib.parse.urlencode(params)
    return q + '&signature=' + hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()

def get(path, params={}):
    return requests.get(f'{BASE}{path}?{signed(params)}', headers={'X-MBX-APIKEY': KEY}, proxies=PROX, timeout=15)

price = float(requests.get(f'{BASE}/api/v3/ticker/price?symbol=DOGEUSDT', proxies=PROX, timeout=10).json()['price'])

# 账户
acct = get('/api/v3/account').json()
bal = {b['asset']: {'free': float(b['free']), 'locked': float(b['locked'])} for b in acct['balances']}
usdt = bal.get('USDT', {}).get('free', 0) + bal.get('USDT', {}).get('locked', 0)
doge = bal.get('DOGE', {}).get('free', 0) + bal.get('DOGE', {}).get('locked', 0)
total = usdt + doge * price
print(f'DOGE现价: ${price:.4f}')
print(f'持仓: USDT {usdt:.2f} + DOGE {doge:.2f} (≈{doge*price:.2f}U)')
print(f'总资产: {total:.2f}U')
print(f'启动资金参考: 36.5U')
print(f'相对启动: {total-36.5:+.2f}U ({(total-36.5)/36.5*100:+.1f}%)')

# 所有成交（最多1000条）算真实净现金流
trades = get('/api/v3/myTrades', {'symbol':'DOGEUSDT', 'limit':1000}).json()
trades = sorted(trades, key=lambda t: t['id'])
# 找网格启动点：取08-23之后的成交
buy_spent = sell_recv = 0.0
buy_qty = sell_qty = 0.0
fee_u = 0.0
for t in trades:
    ts = datetime.fromtimestamp(t['time']/1000)
    if ts.date().isoformat() < '2026-08-23':
        continue
    qty, p, comm = float(t['qty']), float(t['price']), float(t['commission'])
    if t['isBuyer']:
        buy_qty += qty
        buy_spent += qty * p
    else:
        sell_qty += qty
        sell_recv += qty * p
    if t['commissionAsset'] == 'DOGE':
        fee_u += comm * p
    elif t['commissionAsset'] == 'USDT':
        fee_u += comm
print(f'\n=== 08-23起网格成交 ===')
print(f'买入 {buy_qty:.0f}DOGE 花 {buy_spent:.2f}U')
print(f'卖出 {sell_qty:.0f}DOGE 收 {sell_recv:.2f}U')
print(f'手续费 {fee_u:.4f}U')
# 已实现净现金流（卖收到的 - 买花的）
net = sell_recv - buy_spent - fee_u
print(f'净现金流(基于08-23后成交): {net:+.2f}U')