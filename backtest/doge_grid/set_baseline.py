#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把网格状态基准ID设为当前最大成交ID，避免维护循环重放历史"""
import json, os
from binance_client import BinanceClient

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grid_state.json')

client = BinanceClient()
trades = client.my_trades(limit=1)
max_id = max(t['id'] for t in trades) if trades else 0
print(f'当前最大成交ID: {max_id}')

state = {}
if os.path.exists(STATE):
    with open(STATE) as f:
        state = json.load(f)
state['last_trade_id'] = max_id
with open(STATE, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(f'已写入 {STATE}: last_trade_id={max_id}')