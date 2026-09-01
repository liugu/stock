#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DOGE网格守护进程：每2分钟自动跑一次维护循环"""
import time, subprocess

DIR = r'E:\量化研究\workspace\stock\backtest\doge_grid'
PY = r'E:\量化研究\workspace\stock\venv\Scripts\python.exe'

INTERVAL = 120  # 秒

def maintain():
    try:
        r = subprocess.run([PY, 'grid_bot_live.py', '--run'],
                           capture_output=True, text=True, timeout=100, cwd=DIR)
        out = (r.stdout + r.stderr).strip()
        if out:
            # 只打印真实动作
            if any(k in out for k in ['成交', '补', '✅', '异常', '失败']):
                print(out[-1500:])
    except Exception as e:
        print(f'[守护] 维护异常: {e}')

if __name__ == '__main__':
    print('[守护] DOGE网格维护进程启动，每2分钟一次', flush=True)
    while True:
        try:
            maintain()
        except Exception as e:
            print(f'[守护] 异常: {e}', flush=True)
        time.sleep(INTERVAL)