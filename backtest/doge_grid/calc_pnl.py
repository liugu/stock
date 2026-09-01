#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""计算DOGE网格已实现盈亏（扣除手续费）+ 当前总资产，换算人民币"""
import json, os
from binance_client import BinanceClient

client = BinanceClient()
price = client.get_price()
bal = client.get_balance()
usdt = bal.get('USDT', 0)
doge = bal.get('DOGE', 0)

print(f'当前DOGE价格: ${price:.4f}')
print(f'当前持仓: USDT {usdt:.4f} + DOGE {doge:.4f}')
doge_value = doge * price
total = usdt + doge_value
print(f'总资产: {total:.4f} USDT (= {total:.2f} U)')

# 拉全部成交
trades = client.my_trades(limit=500)
trades = sorted(trades, key=lambda t: t['id'])

# 汇总成交
spent_buy = 0.0      # 买入花费的USDT（quoteQty，含手续费折算复杂，用净额近似）
received_sell = 0.0  # 卖出收到的USDT
fee = 0.0            # 总手续费（折USDT）
buy_doge = 0.0
sell_doge = 0.0

for t in trades:
    qty = float(t['qty'])
    p = float(t['price'])
    comm = float(t['commission'])
    comm_asset = t['commissionAsset']
    # 折合手续费到USDT（近似用成交价折算DOGE佣金）
    if t['isBuyer']:
        buy_doge += qty
        spent_buy += qty * p
    else:
        sell_doge += qty
        received_sell += qty * p
    if comm_asset == 'DOGE':
        fee += comm * p
    elif comm_asset == 'USDT':
        fee += comm
    elif comm_asset == 'BTC':
        fee += comm * price  # 粗略
    else:
        fee += comm  # 其他情况近似

print(f'\n成交统计 (共{len(trades)}笔):')
print(f'  买入: {buy_doge:.2f} DOGE, 花费 {spent_buy:.4f} USDT')
print(f'  卖出: {sell_doge:.2f} DOGE, 收到 {received_sell:.4f} USDT')
print(f'  总手续费: {fee:.4f} USDT')

# 已实现盈亏（完整买卖闭环）：卖出所得 - 买入成本 - 手续费
# 简化：当前已卖出的DOGE对应的盈利
realized = (received_sell) - fee  # 收到的款减去费用
# 买入成本分摊：每DOGE均价
if buy_doge > 0:
    avg_cost = spent_buy / buy_doge
    print(f'  买入均价: ${avg_cost:.4f}')
    # 已卖出的105 DOGE的本金
    sell_cost = sell_doge * avg_cost
    grid_profit = received_sell - sell_cost - fee * (sell_doge / buy_doge if buy_doge else 1)
    print(f'\n网格已实现盈利(扣除手续费): {grid_profit:.4f} USDT')
else:
    print('  暂无已实现卖出')

# 汇率换算（约7.1-7.2）
for rate in (7.1, 7.15, 7.2):
    print(f'\n按汇率 {rate} 换算:')
    print(f'  总资产 ≈ {total*rate:.2f} RMB')
    if 'grid_profit' in locals():
        print(f'  已实现盈利 ≈ {grid_profit*rate:.2f} RMB')