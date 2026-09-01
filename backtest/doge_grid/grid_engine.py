#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DOGE 现货网格交易引擎（核心逻辑，可脱离API独立测试）
- 网格状态维护：买入成交→补卖单；卖出成交→补买单
- 提供纯逻辑的 simulate() 用于验证循环闭环
"""
from datetime import datetime

GRID_LOWER = 0.075
GRID_UPPER = 0.105
GRID_COUNT = 8
ORDER_USDT = 4.0       # 每格下单金额(U)
SEED_USDT = 15.0       # 初始买入底仓金额(U)


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def grid_levels(lower, upper, count):
    """返回 count 个网格价位（不含边界，作为挂单点）"""
    levels = []
    step = (upper - lower) / count
    for i in range(1, count):
        levels.append(round(lower + step * i, 6))
    return levels


def seed_doge(usdt, price, amount=SEED_USDT):
    """初始用 amount(U) 买入底仓DOGE"""
    qty = amount / price
    return round(qty, 0)


def init_buys(levels, price, per=ORDER_USDT):
    """在价格下方每个格挂买单"""
    buys = {}
    for lvl in levels:
        if lvl < price:
            qty = round(per / lvl, 2)
            buys[lvl] = {'side': 'BUY', 'qty': qty}
    return buys


def init_sells(levels, price, doge_qty):
    """在上方每格挂卖单（用底仓DOGE，平均分配到各卖格）"""
    sells = {}
    above = [lvl for lvl in levels if lvl > price]
    if not above:
        return sells
    per_qty = int(doge_qty / len(above))
    for lvl in above:
        sells[lvl] = {'side': 'SELL', 'qty': per_qty}
    return sells


class GridState:
    """网格状态维护器"""
    def __init__(self, price):
        self.price = price
        self.levels = grid_levels(GRID_LOWER, GRID_UPPER, GRID_COUNT)
        self.orders = {}   # {price: {'side','qty','filled':bool}}
        self.doge_hold = 0
        self.pnl = 0.0
        self.trades = 0

    def init(self, usdt_balance):
        """初始化：买入底仓 + 挂初始买卖单"""
        self.doge_hold = seed_doge(usdt_balance, self.price)
        log(f'  底仓: 买入 {self.doge_hold:.0f} DOGE @ {self.price}')
        buys = init_buys(self.levels, self.price)
        sells = init_sells(self.levels, self.price, self.doge_hold)
        for lvl, o in {**buys, **sells}.items():
            self.orders[lvl] = {**o, 'filled': False}
        log(f'  初始挂单: {len(buys)}买 + {len(sells)}卖')

    def on_price(self, price):
        """价格变动到某网格价位时，检查成交并补反向单"""
        moved = False
        for lvl, o in list(self.orders.items()):
            if o['side'] == 'BUY' and not o['filled'] and price <= lvl:
                o['filled'] = True
                self.trades += 1
                upper = self._next_up(lvl)
                if upper is not None:
                    self.orders[upper] = {'side': 'SELL', 'qty': o['qty'], 'filled': False}
                log(f'  [成交] 买入 {o["qty"]:.2f}DOGE @{lvl} → 补卖单@{upper or "无"}')
                moved = True
            elif o['side'] == 'SELL' and not o['filled'] and price >= lvl:
                o['filled'] = True
                self.trades += 1
                lower = self._prev_down(lvl)
                if lower is not None:
                    self.orders[lower] = {'side': 'BUY', 'qty': o['qty'] * lvl / lower, 'filled': False}
                spread = (lvl / lower) - 1 if lower else 0
                est = o['qty'] * lvl * spread
                self.pnl += est
                log(f'  [成交] 卖出 {o["qty"]:.2f}DOGE @{lvl} 利{est:.2f}U → 补买单@{lower or "无"}')
                moved = True
        return moved

    def _idx(self, lvl):
        try:
            return self.levels.index(lvl)
        except ValueError:
            return None

    def _next_up(self, lvl):
        i = self._idx(lvl)
        if i is None or i + 1 >= len(self.levels):
            return None
        return self.levels[i + 1]

    def _prev_down(self, lvl):
        i = self._idx(lvl)
        if i is None or i - 1 < 0:
            return None
        return self.levels[i - 1]

    def summary(self):
        filled = sum(1 for o in self.orders.values() if o['filled'])
        log(f'  循环次数: {self.trades} 轮 | 套利收益: {self.pnl:.2f}U | 已触发格: {filled}')