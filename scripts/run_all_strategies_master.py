#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量运行所有选股策略并输出结果"""
import sys, os, subprocess, time
from datetime import date
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'E:/量化研究/workspace/stock'
VENV_PY = ROOT + '/venv/Scripts/python'

STRATEGIES = [
    ('老鸭头形态', 'scripts/select_old_duck_head.py'),
    ('金蜘蛛形态', 'scripts/select_golden_spider.py'),
    ('红三兵形态', 'scripts/select_red_three_soldiers.py'),
    ('早晨之星', 'scripts/select_morning_star.py'),
    ('突破选股', 'scripts/select_breakthrough.py'),
    ('回调买入', 'scripts/select_pullback_buy.py'),
    ('均线粘合', 'scripts/select_ma_convergence.py'),
    ('回调支撑', 'scripts/select_pullback_support.py'),
    ('稳健长牛', 'scripts/select_stable_longterm.py'),
    ('趋势向上', 'scripts/select_uptrend.py'),
    ('放量上涨', 'scripts/select_volume_bullish.py'),
    ('连续小阳线', 'scripts/select_consecutive_bullish.py'),
]

def extract_results(name, output):
    """从输出中提取选股结果"""
    lines = output.split('\n')
    stocks = []
    in_result = False
    for line in lines:
        line = line.strip()
        if '选股结果' in line or '最终结果' in line:
            in_result = True
            continue
        if in_result and line and not line.startswith('=') and not line.startswith('日期'):
            # 匹配股票格式：代码 名称 价格 涨跌幅
            parts = line.split()
            if len(parts) >= 2:
                stocks.append(line)
    return stocks

print(f'{"="*60}')
print(f'综合选股 - {date.today()}')
print(f'策略数: {len(STRATEGIES)}')
print(f'{"="*60}')

all_results = {}

for name, script in STRATEGIES:
    full_path = os.path.join(ROOT, script)
    if not os.path.exists(full_path):
        print(f'\n✗ {name}: 脚本不存在({script})')
        continue
    
    print(f'\n▶ {name}...', end=' ', flush=True)
    try:
        r = subprocess.run([VENV_PY, full_path], capture_output=True, text=True, timeout=120, cwd=ROOT)
        out = r.stdout
        # 提取股票代码行
        stock_lines = []
        for line in out.split('\n'):
            line = line.strip()
            # 匹配类似 "000001  平安银行  10.28  0.59%" 的格式
            if line and len(line) > 5 and line[0].isdigit():
                stock_lines.append(line)
        
        if stock_lines:
            print(f'✓ {len(stock_lines)}只')
            all_results[name] = stock_lines
        else:
            print('无结果')
    except subprocess.TimeoutExpired:
        print('超时')
    except Exception as e:
        print(f'错: {str(e)[:30]}')

# 输出汇总
print(f'\n\n{"="*60}')
print(f'选股结果汇总 ({date.today()})')
print(f'{"="*60}')

total = 0
for name, stocks in all_results.items():
    print(f'\n【{name}】({len(stocks)}只)')
    for s in stocks[:8]:
        print(f'  {s}')
    if len(stocks) > 8:
        print(f'  ... 还有 {len(stocks)-8} 只')
    total += len(stocks)

print(f'\n{"="*60}')
print(f'共 {len(all_results)} 个策略选出 {total} 只股票')
