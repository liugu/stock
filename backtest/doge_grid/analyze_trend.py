#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析DOGE走势 + 输出优化建议"""
import requests
from datetime import datetime

BASE = 'https://data-api.binance.vision'
# 用代理（与交易一致的网络环境）
PROX = {'http': 'socks5h://127.0.0.1:10812', 'https': 'socks5h://127.0.0.1:10812'}

def get_klines(interval, limit):
    r = requests.get(f'{BASE}/api/v3/klines?symbol=DOGEUSDT&interval={interval}&limit={limit}',
                     proxies=PROX, timeout=15)
    return r.json()

cur = float(requests.get(f'{BASE}/api/v3/ticker/price?symbol=DOGEUSDT', proxies=PROX, timeout=10).json()['price'])
print(f'DOGE 现价: ${cur:.4f}')

# 日线
daily = get_klines('1d', 30)
dh = [float(k[2]) for k in daily]
dl = [float(k[3]) for k in daily]
dc = [float(k[4]) for k in daily]
print(f'\n=== 日线(30天) ===')
print(f'最高: ${max(dh):.4f}  最低: ${min(dl):.4f}')
print(f'近7日收盘: {[f"{c:.4f}" for c in dc[-7:]]}')
print(f'30日均价: ${sum(dc)/len(dc):.4f}')

# 小时线
h1 = get_klines('1h', 24)
hc = [float(k[4]) for k in h1]
print(f'\n=== 小时线(24h) ===')
print(f'近24h最高: ${max(float(k[2]) for k in h1):.4f}  最低: ${min(float(k[3]) for k in h1):.4f}')
print(f'24h均价: ${sum(hc)/len(hc):.4f}')
print(f'近12小时趋势: {hc[0]:.4f} → {hc[-1]:.4f} ({"上升" if hc[-1]>hc[0] else "下跌"})')

# 判断当前网格区间是否合适
print(f'\n=== 当前网格区间: $0.075 ~ $0.105 ===')
lo30, hi30 = min(dl), max(dh)
print(f'  30天实际区间: ${lo30:.4f} ~ ${hi30:.4f}')
print(f'  当前价格相对30天高低位: {(cur-lo30)/(hi30-lo30)*100:.0f}%')

# 波动率估算（用小时线）
from statistics import pstdev
vol = pstdev([(hc[i]-hc[i-1])/hc[i-1] for i in range(1,len(hc))]) * 100
print(f'\n小时线波动率(标准差): {vol:.2f}%')