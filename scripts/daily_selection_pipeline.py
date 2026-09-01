#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日选股流程 - 定时任务专用
执行顺序：
1. 检查数据完整性
2. 执行修复版综合选股（12个策略）
3. 执行消息面选股
"""
import sys, os, subprocess, time
from datetime import datetime

ROOT = 'E:/量化研究/workspace/stock'
PY = ROOT + '/venv/Scripts/python'

start_t = time.time()
print('=' * 60)
print(f'每日选股流程 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 60)

# Step 1: 数据检查
print('\n[1/3] 数据完整性检查...')
import pymysql
conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()
c.execute('SELECT MAX(date), COUNT(DISTINCT stock_id) FROM stock_daily')
latest, cnt = c.fetchone()
c.execute('''SELECT COUNT(*) FROM stock_info si
    WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
    AND si.code NOT LIKE "688%%"''')
total = c.fetchone()[0]
conn.close()
pct = cnt/total*100 if total else 0
print(f'  stock_daily最新: {latest}')
print(f'  覆盖: {cnt}/{total} ({pct:.1f}%)')
if pct < 80:
    print(f'  ⚠ 数据完整度不足80%，选股结果可能不准确')
else:
    print(f'  ✅ 数据可用')

# Step 2: 综合选股
print(f'\n[2/3] 修复版综合选股 (12个策略)...')
r = subprocess.run([PY, 'scripts/run_all_strategies_fixed.py'], cwd=ROOT, timeout=300, capture_output=True, text=True)
print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)

# Step 3: 消息面选股
print(f'\n[3/3] 消息面选股...')
r2 = subprocess.run([PY, 'scripts/news_selection.py'], cwd=ROOT, timeout=120, capture_output=True, text=True)
print(r2.stdout[-2000:] if len(r2.stdout) > 2000 else r2.stdout)

elapsed = time.time() - start_t
print(f'\n{"="*60}')
print(f'每日选股完成! 用时: {elapsed:.0f}秒')
print('=' * 60)
