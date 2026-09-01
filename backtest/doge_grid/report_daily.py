#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DOGE网格每日播报：输出状态摘要（供定时任务投递）"""
import subprocess, os
from datetime import datetime

DIR = r'E:\量化研究\workspace\stock\backtest\doge_grid'
PY = r'E:\量化研究\workspace\stock\venv\Scripts\python.exe'

try:
    r = subprocess.run([PY, 'grid_bot_live.py', '--status'],
                       capture_output=True, text=True, timeout=120, cwd=DIR)
    raw = (r.stdout + r.stderr).strip()
except Exception as e:
    raw = f'状态获取失败: {e}'

today = datetime.now().strftime('%Y-%m-%d')
print(f'📊 DOGE网格日报 {today}')
print('-' * 32)
print(raw)