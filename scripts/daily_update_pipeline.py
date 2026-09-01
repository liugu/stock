#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日数据更新流程 - 定时任务专用
执行顺序：
1. 更新 cn_stock_spot（实时行情）
2. 更新 stock_daily（日K线，分批+重试）
3. 补全失败股票
"""
import sys, os, subprocess, time, json
from datetime import datetime

ROOT = 'E:/量化研究/workspace/stock'
PY = ROOT + '/venv/Scripts/python'
FAIL_LOG = ROOT + '/output/update_failed_stocks.json'

start_t = time.time()
print('=' * 60)
print(f'每日数据更新 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 60)

# Step 1: cn_stock_spot
print('\n[1/4] 更新实时行情 (cn_stock_spot)...')
subprocess.run([PY, 'scripts/update_cn_stock_spot.py'], cwd=ROOT, timeout=180)

# Step 2: stock_daily - 稳健版
print('\n[2/4] 更新日K线 (stock_daily, 分批+重试)...')
subprocess.run([PY, 'scripts/update_stock_daily_robust.py'], cwd=ROOT, timeout=600)

# Step 3: 补全失败
print('\n[3/4] 补全失败股票...')
if os.path.exists(FAIL_LOG):
    subprocess.run([PY, 'scripts/backfill_stock_daily.py', 'auto'], cwd=ROOT, timeout=600)
else:
    print('  无失败列表，跳过')

# Step 4: 检查最终状态
print('\n[4/4] 数据状态检查...')
import pymysql
conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()
c.execute('SELECT MAX(date) FROM stock_daily')
latest = c.fetchone()[0]
c.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (latest,))
avail = c.fetchone()[0]
c.execute('''SELECT COUNT(*) FROM stock_info si
    WHERE (si.code LIKE "60%%" OR si.code LIKE "00%%" OR si.code LIKE "30%%")
    AND si.code NOT LIKE "688%%"''')
total = c.fetchone()[0]
conn.close()

elapsed = time.time() - start_t
print(f'\n{"="*60}')
print(f'每日数据更新完成!')
print(f'用时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)')
print(f'stock_daily: {avail}/{total} 只 ({avail/total*100:.1f}%)')
print(f'最新日期: {latest}')
print(f'数据完整度: {"✅ 良好" if avail/total > 0.9 else "⚠ 需关注"}')
print('=' * 60)
