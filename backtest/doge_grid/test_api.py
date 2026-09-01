#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试币安 API 配置（SOCKS5 代理）"""
import json, os, time, hashlib, hmac, urllib.parse, requests

CONFIG_PROXY = 'socks5h://127.0.0.1:10812'

cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
with open(cfg_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

API_KEY = cfg['binance_api_key']
API_SECRET = cfg['binance_api_secret']
BASE = 'https://api.binance.com'
PROXIES = {'http': CONFIG_PROXY, 'https': CONFIG_PROXY}

if '在此填入' in API_KEY or '在此填入' in API_SECRET:
    print('❌ 你还没填API key，去 config/api_keys.json 填一下')
    exit(1)

print(f'🔑 API Key: {API_KEY[:6]}...{API_KEY[-4:]}')
print(f'🔗 代理: {CONFIG_PROXY}')

# 1. 公开接口
try:
    r = requests.get(f'{BASE}/api/v3/ping', proxies=PROXIES, timeout=10)
    print(f'✅ 公开ping: {r.status_code} {r.text}')
except Exception as e:
    print(f'❌ 公开ping失败: {e}')

def signed_request(path, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    query = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f'{BASE}{path}?{query}&signature={signature}'
    try:
        return requests.get(url, headers={'X-MBX-APIKEY': API_KEY},
                            proxies=PROXIES, timeout=10)
    except Exception as e:
        print(f'  请求异常: {e}')
        return None

# 2. 账户接口（验证key有效性和权限）
print('\n测试账户接口...')
r = signed_request('/api/v3/account')
if r is None:
    print('❌ 连接失败')
elif r.status_code == 200:
    data = r.json()
    bal = data.get('balances', [])
    print('✅ API有效! 连接成功')
    for b in bal:
        if b['asset'] in ('USDT', 'DOGE', 'BTC', 'USDC'):
            print(f'   {b["asset"]}: 可用{b["free"]} 锁定{b["locked"]}')
else:
    print(f'❌ 账户接口: {r.status_code} {r.text[:300]}')
    if 'API-key format invalid' in r.text or 'Invalid API-key' in r.text:
        print('   → API Key 不对，检查是否有空格')
    if 'Signature for this request is not valid' in r.text:
        print('   → Secret Key 不对')
    if 'SPOT permission' in r.text:
        print('   → 没开现货交易权限')