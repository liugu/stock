#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看DOGE当前行情，为网格设计提供参数"""
import requests, json

# 公开行情接口
base = 'https://data-api.binance.vision'

# 最新价
r = requests.get(f'{base}/api/v3/ticker/price?symbol=DOGEUSDT', timeout=10)
price = float(r.json()['price'])
print(f'DOGE 现价: ${price:.4f}')

# 24hr 统计
r = requests.get(f'{base}/api/v3/ticker/24hr?symbol=DOGEUSDT', timeout=10)
d = r.json()
high = float(d['highPrice'])
low = float(d['lowPrice'])
chg = float(d['priceChangePercent'])
vol = float(d['quoteVolume']) / 1e8
print(f'24h高: ${high:.4f}  低: ${low:.4f}')
print(f'24h涨幅: {chg:.2f}%')
print(f'24h成交额: {vol:.0f}亿U')

# 近30天日K，确定波动区间
r = requests.get(f'{base}/api/v3/klines?symbol=DOGEUSDT&interval=1d&limit=30', timeout=10)
klines = r.json()
highs = [float(k[2]) for k in klines]
lows = [float(k[3]) for k in klines]
print(f'\n近30天最高: ${max(highs):.4f}  最低: ${min(lows):.4f}')

# 计算网格区间建议
cur = price
print(f'\n=== 网格设计参考 (当前价 ${cur:.4f}) ===')
for pct in [0.10, 0.15, 0.20, 0.25]:
    lo = cur * (1 - pct)
    hi = cur * (1 + pct)
    print(f'区间 ±{pct*100:.0f}%:  ${lo:.4f} ~ ${hi:.4f} (跨度 ${hi-lo:.4f})')

# 资金分配参考
print(f'\n=== 资金分配参考 (总资金 70U) ===')
for n in [7, 8, 10, 12]:
    per = 70 / n
    print(f'{n}格: 每格约 {per:.1f}U')