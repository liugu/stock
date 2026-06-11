#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票实时行情数据（cn_stock_spot表）
包括：价格、涨跌幅、PE、PB、市值等

作者: Hermes
日期: 2026/6/11
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import requests
from datetime import datetime
import time

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_realtime_quotes():
    """获取A股实时行情"""
    print('获取A股实时行情...')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://vip.stock.finance.sina.com.cn/'
    }
    
    all_data = []
    
    # 新浪财经API
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    
    for page in range(1, 80):
        params = {
            'page': str(page),
            'num': '100',
            'sort': 'changepercent',
            'asc': '0',
            'node': 'hs_a'
        }
        
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            data = r.json()
            
            if not data:
                break
            
            all_data.extend(data)
            
            if page % 20 == 0:
                print(f'  已获取 {len(all_data)} 条...')
        except Exception as e:
            print(f'  第{page}页获取失败: {e}')
            break
    
    print(f'共获取 {len(all_data)} 条数据')
    return all_data


def update_cn_stock_spot():
    """更新cn_stock_spot表"""
    print('=' * 60)
    print('更新股票实时行情数据')
    print('=' * 60)
    print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    
    # 1. 获取实时数据
    data = get_realtime_quotes()
    
    if not data:
        print('获取数据失败')
        return
    
    # 2. 转换为DataFrame
    df = pd.DataFrame(data)
    
    # 重命名列
    column_map = {
        'code': 'code',
        'name': 'name',
        'trade': 'new_price',
        'pricechange': 'change_amount',
        'changepercent': 'change_rate',
        'buy': 'buy_price',
        'sell': 'sell_price',
        'settlement': 'yesterday_price',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'volume': 'volume',
        'amount': 'deal_amount',
        'turnoverratio': 'turnoverrate',
        'per': 'pe',
        'pb': 'pbnewmrq',
        'mktcap': 'total_market_cap',
        'nmc': 'circulation_market_cap'
    }
    
    df = df.rename(columns=column_map)
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # 3. 连接数据库
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 4. 删除今天旧数据
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(f"DELETE FROM cn_stock_spot WHERE date = '{today}'")
    conn.commit()
    print(f'删除旧数据: {cursor.rowcount} 条')
    
    # 5. 插入新数据
    insert_sql = '''
    INSERT INTO cn_stock_spot (
        date, code, name, new_price, change_rate, volume, deal_amount,
        turnoverrate, open_price, high_price, low_price, pre_close_price,
        pe, pbnewmrq, total_market_cap
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
        name=VALUES(name), new_price=VALUES(new_price), change_rate=VALUES(change_rate),
        volume=VALUES(volume), deal_amount=VALUES(deal_amount), turnoverrate=VALUES(turnoverrate),
        open_price=VALUES(open_price), high_price=VALUES(high_price), low_price=VALUES(low_price),
        pre_close_price=VALUES(pre_close_price), pe=VALUES(pe), pbnewmrq=VALUES(pbnewmrq),
        total_market_cap=VALUES(total_market_cap)
    '''
    
    success = 0
    fail = 0
    
    for _, row in df.iterrows():
        try:
            values = (
                row.get('date'),
                row.get('code'),
                row.get('name'),
                float(row.get('new_price', 0)) if row.get('new_price') else 0,
                float(row.get('change_rate', 0)) if row.get('change_rate') else 0,
                float(row.get('volume', 0)) if row.get('volume') else 0,
                float(row.get('deal_amount', 0)) if row.get('deal_amount') else 0,
                float(row.get('turnoverrate', 0)) if row.get('turnoverrate') else 0,
                float(row.get('open_price', 0)) if row.get('open_price') else 0,
                float(row.get('high_price', 0)) if row.get('high_price') else 0,
                float(row.get('low_price', 0)) if row.get('low_price') else 0,
                float(row.get('yesterday_price', 0)) if row.get('yesterday_price') else 0,
                float(row.get('pe', 0)) if row.get('pe') else None,
                float(row.get('pbnewmrq', 0)) if row.get('pbnewmrq') else None,
                float(row.get('total_market_cap', 0)) if row.get('total_market_cap') else 0
            )
            cursor.execute(insert_sql, values)
            success += 1
        except Exception as e:
            fail += 1
            if fail < 5:
                print(f'  插入失败 {row.get("code")}: {e}')
    
    conn.commit()
    
    # 6. 验证
    cursor.execute('SELECT MAX(date) FROM cn_stock_spot')
    max_date = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM cn_stock_spot WHERE date = %s', (max_date,))
    count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}')
    print(f'✓ 最新日期: {max_date}, 记录数: {count}')
    print('=' * 60)


if __name__ == '__main__':
    update_cn_stock_spot()
