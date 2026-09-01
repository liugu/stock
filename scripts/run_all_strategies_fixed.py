#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""综合选股（修复版）- 先校验数据完整性，再执行策略"""
import sys, os, subprocess, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

from datetime import date
import pymysql

ROOT = 'E:/量化研究/workspace/stock'
VENV_PY = ROOT + '/venv/Scripts/python'
DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

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
    ('连续小阳线', 'scripts/selection/consecutive_bullish_fixed.py'),
]

def check_data_status():
    conn = pymysql.connect(**DB)
    c = conn.cursor()
    c.execute('SELECT MAX(date) FROM stock_daily')
    latest = c.fetchone()[0]
    if latest:
        c.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (latest,))
        avail = c.fetchone()[0]
        c.execute('''SELECT COUNT(*) FROM stock_info si WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%") AND si.code NOT LIKE "688%%"''')
        total = c.fetchone()[0]
        pct = avail/total*100
    else:
        avail = 0; total = 0; pct = 0
    conn.close()
    return {'latest': str(latest) if latest else '无', 'avail': avail, 'total': total, 'pct': round(pct,1)}

today_str = str(date.today())

print('='*60)
print(f'综合选股 - {today_str}（修复版）')
print('='*60)

# 数据校验
print('\n数据完整性校验:')
status = check_data_status()
print(f'  stock_daily 最新: {status["latest"]}')
print(f'  完整数据A股: {status["avail"]}/{status["total"]} ({status["pct"]}%)')

if status['pct'] < 50:
    print('  ⚠ 完整度过低，结果可能不准确')
elif status['pct'] < 80:
    print('  ⚠ 数据部分缺失，结果可能不完整')
else:
    print('  ✅ 数据可用')

# 执行策略
print(f'\n执行策略 ({len(STRATEGIES)}个)...')
all_results = {}

for name, script in STRATEGIES:
    full_path = os.path.join(ROOT, script)
    if not os.path.exists(full_path):
        print(f'  ✗ {name}: 脚本不存在')
        continue
    print(f'  ▶ {name}...', end=' ', flush=True)
    try:
        r = subprocess.run([VENV_PY, full_path], capture_output=True, text=True, timeout=120, cwd=ROOT)
        lines = r.stdout.split('\n')
        stocks = [l.strip() for l in lines if '【' in l and '】' in l]
        if stocks:
            print(f'✓ {len(stocks)}只')
            all_results[name] = stocks
        else:
            print('无结果')
    except subprocess.TimeoutExpired:
        print('超时')
    except Exception as e:
        print(f'错: {str(e)[:30]}')

# 汇总
print(f'\n{"="*60}')
print(f'选股结果汇总 ({today_str})')
print(f'数据: stock_daily {status["latest"]} 完整度{status["pct"]}%')
print(f'{"="*60}')

if not all_results:
    print('\n所有策略均未选出股票')
else:
    total = 0
    for name, stocks in all_results.items():
        print(f'\n【{name}】({len(stocks)}只)')
        for s in stocks[:10]:
            print(f'  {s}')
        if len(stocks) > 10:
            print(f'  ... 还有 {len(stocks)-10} 只')
        total += len(stocks)
    print(f'\n共 {len(all_results)} 个策略选出 {total} 只股票')
print('='*60)
