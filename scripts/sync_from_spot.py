#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从cn_stock_spot同步今日数据到stock_daily
解决外部API连接中断问题

作者: Hermes
日期: 2026/6/11
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
from datetime import datetime

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def sync_today_data():
    """从cn_stock_spot同步今日数据到stock_daily"""
    print('=' * 60)
    print('从cn_stock_spot同步今日数据到stock_daily')
    print('=' * 60)
    print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 1. 获取cn_stock_spot最新日期
    cursor.execute('SELECT MAX(date) FROM cn_stock_spot')
    spot_date = cursor.fetchone()[0]
    print(f'cn_stock_spot 最新日期: {spot_date}')
    
    if not spot_date:
        print('cn_stock_spot 无数据')
        cursor.close()
        conn.close()
        return
    
    # 2. 检查stock_daily是否已有该日期数据
    cursor.execute('SELECT COUNT(*) FROM stock_daily WHERE date = %s', (spot_date,))
    existing = cursor.fetchone()[0]
    
    if existing > 0:
        print(f'stock_daily 已有 {spot_date} 数据 {existing} 条')
        print('跳过同步')
        cursor.close()
        conn.close()
        return
    
    # 3. 同步数据
    print(f'开始同步 {spot_date} 数据...')
    
    sync_sql = '''
    INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, turnover_rate)
    SELECT 
        si.id,
        cs.date,
        cs.open_price,
        cs.new_price,
        cs.high_price,
        cs.low_price,
        cs.volume,
        cs.deal_amount,
        cs.change_rate,
        cs.turnoverrate
    FROM cn_stock_spot cs
    INNER JOIN stock_info si ON BINARY si.code = BINARY cs.code
    WHERE cs.date = %s
      AND cs.new_price > 0
      AND si.id IS NOT NULL
    '''
    
    cursor.execute(sync_sql, (spot_date,))
    inserted = cursor.rowcount
    conn.commit()
    
    # 4. 验证
    cursor.execute('SELECT MAX(date) FROM stock_daily')
    max_date = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM stock_daily WHERE date = %s', (max_date,))
    count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print()
    print(f'✓ 同步完成: 插入 {inserted} 条记录')
    print(f'✓ stock_daily 最新日期: {max_date}, 记录数: {count}')
    print('=' * 60)


if __name__ == '__main__':
    sync_today_data()
