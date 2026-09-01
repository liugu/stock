#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""网格维护循环调用入口（供cron定时调用）
watchdog模式：无实际下单/成交/异常时静默输出；有动作时才输出。
"""
import subprocess

DIR = r'E:\量化研究\workspace\stock\backtest\doge_grid'
PY = r'E:\量化研究\workspace\stock\venv\Scripts\python.exe'

# 真实动作关键词：有成交、下单、补单、异常
ACTION_WORDS = ['成交', '补卖', '补买', '➕', '✅', '异常', '失败', 'error', 'Error']

try:
    r = subprocess.run([PY, 'grid_bot_live.py', '--run'],
                       capture_output=True, text=True, timeout=120, cwd=DIR)
    out = (r.stdout + r.stderr).strip()
    if not out:
        # 无输出：完全静默
        pass
    elif any(kw in out for kw in ACTION_WORDS):
        # 有真实动作 → 输出（cron会投递）
        print(out[-2000:])
    # else: 只有"无新成交"等常规日志 → 静默，不打印
except Exception as e:
    print(f'[cron] 维护循环异常: {e}')