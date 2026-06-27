#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合选股 - 执行所有策略并汇总结果

作者: Hermes
日期: 2026-06-11
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import subprocess
from datetime import datetime, date
import json

# 策略列表
STRATEGIES = [
    ('老鸭头形态', 'scripts/select_old_duck_head.py'),
    ('金蜘蛛形态', 'scripts/select_golden_spider.py'),
    ('红三兵形态', 'scripts/select_red_three_soldiers.py'),
    ('早晨之星', 'scripts/select_morning_star.py'),
    ('突破选股', 'scripts/select_breakthrough.py'),
    ('回调买入', 'scripts/select_pullback_buy.py'),
    ('均线粘合', 'scripts/select_ma_convergence.py'),
    ('连续小阳线', 'quick_local_selection.py'),
]

def run_strategy(name, script):
    """运行单个策略"""
    print(f'\n{"="*60}')
    print(f'执行策略: {name}')
    print(f'{"="*60}')
    
    try:
        result = subprocess.run(
            ['.venv/Scripts/python', script],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='ignore'
        )
        
        output = result.stdout
        # 过滤警告
        lines = [l for l in output.split('\n') if 'UserWarning' not in l and 'pandas only supports' not in l]
        output = '\n'.join(lines)
        
        print(output[-3000:] if len(output) > 3000 else output)  # 只显示最后3000字符
        
        return True, output
    except subprocess.TimeoutExpired:
        print(f'超时')
        return False, '超时'
    except Exception as e:
        print(f'错误: {e}')
        return False, str(e)

print('=' * 60)
print('综合选股 - 执行所有策略')
print('=' * 60)
print(f'日期: {date.today()}')
print(f'策略数量: {len(STRATEGIES)}')

# 执行所有策略
results = {}
success_count = 0

for name, script in STRATEGIES:
    success, output = run_strategy(name, script)
    results[name] = {
        'success': success,
        'output': output
    }
    if success:
        success_count += 1

# 汇总结果
print('\n' + '=' * 60)
print('执行汇总')
print('=' * 60)
print(f'成功: {success_count}/{len(STRATEGIES)}')

for name, data in results.items():
    status = '✓' if data['success'] else '✗'
    print(f'  {status} {name}')

print('=' * 60)