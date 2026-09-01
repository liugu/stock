#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""币安现货 API 客户端（经 SOCKS5 代理）"""
import json, os, time, hashlib, hmac, urllib.parse, requests

BASE = 'https://api.binance.com'
PROXY = 'socks5h://127.0.0.1:10812'
PROXIES = {'http': PROXY, 'https': PROXY}
CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')


class BinanceClient:
    def __init__(self, cfg_path=CFG_PATH):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        self.api_key = cfg['binance_api_key']
        self.secret = cfg['binance_api_secret']
        self.symbol = cfg.get('symbol', 'DOGEUSDT')
        self.time_offset = self._sync_time()

    def _sync_time(self):
        """用币安服务器时间校准本地时钟偏移"""
        try:
            r = requests.get(f'{BASE}/api/v3/time', proxies=PROXIES, timeout=10)
            server_ms = r.json()['serverTime']
            local_ms = int(time.time() * 1000)
            return server_ms - local_ms
        except Exception:
            return 0

    def _signed(self, params):
        # 用校准后的时间戳 + 放宽接收窗口
        params.setdefault('recvWindow', 10000)
        params['timestamp'] = int(time.time() * 1000) + self.time_offset
        q = urllib.parse.urlencode(params)
        return q + '&signature=' + hmac.new(self.secret.encode(), q.encode(), hashlib.sha256).hexdigest()

    def _get(self, path, params=None, signed=False):
        if params is None:
            params = {}
        if signed:
            url = f'{BASE}{path}?{self._signed(params)}'
            return requests.get(url, headers={'X-MBX-APIKEY': self.api_key}, proxies=PROXIES, timeout=15)
        url = f'{BASE}{path}?{urllib.parse.urlencode(params)}'
        return requests.get(url, proxies=PROXIES, timeout=15)

    def _post(self, path, params):
        url = f'{BASE}{path}?{self._signed(params)}'
        return requests.post(url, headers={'X-MBX-APIKEY': self.api_key}, proxies=PROXIES, timeout=15)

    def _delete(self, path, params):
        url = f'{BASE}{path}?{self._signed(params)}'
        return requests.delete(url, headers={'X-MBX-APIKEY': self.api_key}, proxies=PROXIES, timeout=15)

    def get_price(self, symbol=None):
        sym = symbol or self.symbol
        r = self._get('/api/v3/ticker/price', {'symbol': sym})
        return float(r.json()['price'])

    def get_balance(self):
        r = self._get('/api/v3/account', {}, signed=True)
        if r.status_code != 200:
            raise Exception(f'balance: {r.status_code} {r.text[:200]}')
        bal = {b['asset']: float(b['free']) + float(b['locked']) for b in r.json()['balances']}
        return bal

    def open_orders(self, symbol=None):
        sym = symbol or self.symbol
        r = self._get('/api/v3/openOrders', {'symbol': sym}, signed=True)
        if r.status_code != 200:
            raise Exception(f'openOrders: {r.status_code} {r.text[:200]}')
        return r.json()

    def my_trades(self, symbol=None, limit=50, from_id=None):
        sym = symbol or self.symbol
        params = {'symbol': sym, 'limit': limit}
        if from_id:
            params['fromId'] = from_id
        r = self._get('/api/v3/myTrades', params, signed=True)
        if r.status_code != 200:
            raise Exception(f'myTrades: {r.status_code} {r.text[:200]}')
        return r.json()

    def place_limit(self, side, qty, price, symbol=None):
        """side: BUY/SELL, 限价单"""
        sym = symbol or self.symbol
        params = {
            'symbol': sym,
            'side': side,
            'type': 'LIMIT',
            'timeInForce': 'GTC',
            'quantity': f'{qty:.8f}',
            'price': f'{price:.8f}',
        }
        r = self._post('/api/v3/order', params)
        if r.status_code != 200:
            raise Exception(f'place {side} @{price}: {r.status_code} {r.text[:200]}')
        return r.json()

    def cancel_all(self, symbol=None):
        sym = symbol or self.symbol
        r = self._delete('/api/v3/openOrders', {'symbol': sym})
        if r.status_code != 200:
            raise Exception(f'cancelAll: {r.status_code} {r.text[:200]}')
        return r.json()

    def market_buy(self, quote_qty, symbol=None):
        """市价买入，quote_qty 为花费的金额(U)"""
        sym = symbol or self.symbol
        # 用市价单，按金额
        params = {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quoteOrderQty': f'{quote_qty:.8f}'}
        r = self._post('/api/v3/order', params)
        if r.status_code != 200:
            raise Exception(f'market buy {quote_qty}U: {r.status_code} {r.text[:200]}')
        return r.json()