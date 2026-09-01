#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试本地代理类型（HTTP vs SOCKS5）"""
import requests

target = 'https://api.binance.com/api/v3/ping'

tests = {
    'HTTP代理': {'http': 'http://127.0.0.1:10812', 'https': 'http://127.0.0.1:10812'},
    'SOCKS5代理': {'http': 'socks5://127.0.0.1:10812', 'https': 'socks5://127.0.0.1:10812'},
    'SOCKS5H代理': {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'},
}

for name, px in tests.items():
    try:
        r = requests.get(target, proxies=px, timeout=8)
        print(f'OK {name}: {r.status_code} {r.text}')
    except Exception as e:
        err = str(e).splitlines()[0][:90]
        print(f'FAIL {name}: {err}')