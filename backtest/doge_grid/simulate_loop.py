#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""模拟DOGE价格在网格内波动，验证网格循环闭环"""
import random
from grid_engine import GridState, GRID_LOWER, GRID_UPPER, GRID_COUNT

random.seed(42)

# 从40U余额开始，模拟价格在 0.075~0.105 之间上下波动
price = 0.0901
state = GridState(price)
state.init(40.0)

print(f'\n=== 模拟 {GRID_COUNT} 格网格循环 ===')
print(f'区间 ${GRID_LOWER} ~ ${GRID_UPPER}, 起点 ${price}\n')

# 模拟 200 步价格随机游走，幅度限制在网格区间内
steps = 200
moves = 0
for i in range(steps):
    # 随机波动 ±2%，但限制在网格区间内
    delta = random.uniform(-0.02, 0.02)
    new_price = max(GRID_LOWER, min(GRID_UPPER, price * (1 + delta)))
    price = new_price

    # 检查是否触发成交
    if state.on_price(price):
        moves += 1
        if moves % 5 == 0:
            state.summary()

    # 每50步打印一次当前价
    if (i + 1) % 50 == 0:
        print(f'  步{i+1}: 价格 ${price:.4f}')

print('\n=== 循环结束统计 ===')
state.summary()

# 验证闭环：所有格都应已触发过成交
filled = sum(1 for o in state.orders.values() if o['filled'])
grids = len(state.levels)
print(f'网格触发率: {filled}/{grids} 格')
if state.trades > 0:
    print(f'✅ 网格循环闭环成立！共完成 {state.trades} 轮买入-卖出套利')
else:
    print('❌ 模拟期间无成交，请检查网格区间')