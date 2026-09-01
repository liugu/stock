#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DOGE 现货网格交易机器人
- 通过 SOCKS5 代理连接币安
- 网格参数从 config/api_keys.json 读取
- SIMULATION 模式下不产生真实订单（复盘/验证用）
"""
import json, os, time, hashlib, hmac, urllib.parse, requests
from datetime import datetime

# ============ 配置 ============
CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
BASE = 'https://api.binance.com'
PROXY = 'socks5h://127.0.0.1:10812'
PROXIES = {'http': PROXY, 'https': PROXY}

# 模拟模式开关：True 只算不真实下单
SIMULATION = True

SYMBOL = 'DOGEUSDT'
# 网格参数（将从配置读取，这里为默认）
GRID_LOWER = 0.075
GRID_UPPER = 0.105
GRID_COUNT = 8
# 单格下单金额（U）
ORDER_AMOUNT = 4.0


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def load_config():
    with open(CFG_PATH, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    return cfg


def signed(params, secret):
    query = urllib.parse.urlencode(params)
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return query + '&signature=' + sig


def api_get(path, api_key, secret, params=None, base=None):
    base = base or BASE
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    url = f'{base}{path}?{signed(params, secret)}'
    return requests.get(url, headers={'X-MBX-APIKEY': api_key}, proxies=PROXIES, timeout=15)


def api_post(path, api_key, secret, data, base=None):
    base = base or BASE
    data['timestamp'] = int(time.time() * 1000)
    url = f'{base}{path}?{signed(data, secret)}'
    return requests.post(url, headers={'X-MBX-APIKEY': api_key}, proxies=PROXIES, timeout=15)


def api_delete(path, api_key, secret, params, base=None):
    base = base or BASE
    params['timestamp'] = int(time.time() * 1000)
    url = f'{base}{path}?{signed(params, secret)}'
    return requests.delete(url, headers={'X-MBX-APIKEY': api_key}, proxies=PROXIES, timeout=15)


def get_price(symbol=SYMBOL):
    r = requests.get(f'{BASE}/api/v3/ticker/price?symbol={symbol}',
                     proxies=PROXIES, timeout=10)
    return float(r.json()['price'])


def get_balance(api_key, secret):
    r = api_get('/api/v3/account', api_key, secret)
    if r.status_code != 200:
        log(f'获取账户失败: {r.status_code} {r.text[:200]}')
        return None, None
    bal = r.json()['balances']
    usdt = doge = 0.0
    for b in bal:
        if b['asset'] == 'USDT':
            usdt = float(b['free']) + float(b['locked'])
        elif b['asset'] == 'DOGE':
            doge = float(b['free']) + float(b['locked'])
    return usdt, doge


def grid_levels(lower, upper, count):
    """把区间分成 count 段，返回 count+1 个价位（含上下界）"""
    levels = []
    step = (upper - lower) / count
    for i in range(count + 1):
        levels.append(round(lower + step * i, 6))
    return levels


def get_open_orders(api_key, secret):
    r = api_get('/api/v3/openOrders', api_key, secret, {'symbol': SYMBOL})
    if r.status_code != 200:
        log(f'获取挂单失败: {r.status_code} {r.text[:150]}')
        return []
    return r.json()


def cancel_all(api_key, secret):
    r = api_delete('/api/v3/openOrders', api_key, secret, {'symbol': SYMBOL})
    if r.status_code != 200:
        log(f'撤单失败: {r.status_code} {r.text[:150]}')
        return False
    return True


def place_order(api_key, secret, side, quantity, price, sim=SIMULATION):
    """side: BUY/SELL, 限价单"""
    data = {
        'symbol': SYMBOL,
        'side': side,
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': str(quantity),
        'price': f'{price:.6f}',
    }
    if sim:
        log(f'  [模拟] {side} {quantity} DOGE @ {price} ({side == "BUY" and "买" or "卖"})')
        return {'sim': True}
    r = api_post('/api/v3/order', api_key, secret, data)
    if r.status_code != 200:
        log(f'下单失败 {side} @{price}: {r.text[:150]}')
        return None
    return r.json()


def main():
    cfg = load_config()
    api_key = cfg['binance_api_key']
    secret = cfg['binance_api_secret']

    if '在此填入' in api_key or '在此填入' in secret:
        log('❌ 请先填 API key')
        return

    # 获取参数（支持config覆盖）
    global GRID_LOWER, GRID_UPPER, GRID_COUNT
    GRID_LOWER = cfg.get('grid_lower', GRID_LOWER)
    GRID_UPPER = cfg.get('grid_upper', GRID_UPPER)
    GRID_COUNT = cfg.get('grid_count', GRID_COUNT)

    log(f'网格: ${GRID_LOWER} ~ ${GRID_UPPER}, {GRID_COUNT}格, 模拟模式={SIMULATION}')

    # 当前价 & 余额
    price = get_price()
    usdt, doge = get_balance(api_key, secret)
    log(f'当前DOGE: ${price:.4f} | 余额: {usdt:.2f}U / {doge:.0f}DOGE')
    if usdt is None:
        return

    # 网格价位
    levels = grid_levels(GRID_LOWER, GRID_UPPER, GRID_COUNT)
    log(f'网格价位: {[f"{l:.4f}" for l in levels]}')

    if SIMULATION:
        # 落在当前价下方 buy，上方 sell（不含当前价所在格）
        for lvl in levels:
            if lvl < price * 0.999:
                place_order(api_key, secret, 'BUY', ORDER_AMOUNT / lvl, lvl)
            elif lvl > price * 1.001:
                place_order(api_key, secret, 'SELL', 100, lvl)  # 数量放DOGE，模拟
        log(f'✅ 模拟网格布置完成（未实际下单）')
        return

    # ---- 真实模式 ----
    # 先撤掉所有旧挂单，避免重复
    cancel_all(api_key, secret)
    time.sleep(1)

    # 每个价位的下单金额
    per = usdt / (GRID_COUNT * 0.6)  # 留40%现金缓冲
    log(f'每格下单金额: {per:.2f}U')

    for lvl in levels:
        if lvl < price:  # 下方挂买单
            qty = round(per / lvl, 0)
            if qty >= 1:
                place_order(api_key, secret, 'BUY', qty, lvl, sim=False)
        elif lvl > price:  # 上方挂卖单（用DOGE）
            # 需要已有DOGE才能卖，这里简化假设有足够DOGE
            place_order(api_key, secret, 'SELL', 50, lvl, sim=False)

    log('✅ 真实网格挂单完成')


if __name__ == '__main__':
    main()