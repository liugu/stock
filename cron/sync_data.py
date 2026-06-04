#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步脚本 - 使用新浪API同步股票数据到数据库
"""
import os
import sys

# 清除代理
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(key, None)

import requests
import pandas as pd
import pymysql
from datetime import datetime, date
import time
import random

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'instockdb',
    'charset': 'utf8mb4'
}

# 请求配置
REQUEST_DELAY = (0.3, 0.8)
TIMEOUT = 15


def get_session():
    """创建请求会话"""
    session = requests.Session()
    session.trust_env = False
    return session


def fetch_stock_list():
    """获取A股列表 - 新浪分页API"""
    print('[1/3] 获取股票列表...')
    session = get_session()
    all_data = []
    
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    
    for page in range(1, 60):
        try:
            params = {
                'page': str(page),
                'num': '100',
                'sort': 'symbol',
                'asc': '1',
                'node': 'hs_a'
            }
            r = session.get(url, params=params, timeout=TIMEOUT)
            data = r.json()
            if not data:
                break
            all_data.extend(data)
            if page % 10 == 0:
                print(f'      已获取 {len(all_data)} 只...')
            time.sleep(random.uniform(*REQUEST_DELAY))
        except Exception as e:
            print(f'      获取第{page}页失败: {e}')
            break
    
    print(f'      共获取 {len(all_data)} 只股票')
    return pd.DataFrame(all_data)


def sync_stock_spot(df, target_date):
    """同步实时行情到数据库"""
    print(f'[2/3] 同步实时行情到数据库 ({target_date})...')
    
    if df.empty:
        print('      无数据')
        return
    
    # 重命名列 - 匹配数据库字段
    df = df.rename(columns={
        'code': 'code', 'name': 'name', 'trade': 'new_price',
        'changepercent': 'change_rate', 'pricechange': 'ups_downs',
        'settlement': 'pre_close_price', 'open': 'open_price', 'high': 'high_price',
        'low': 'low_price', 'volume': 'volume', 'amount': 'deal_amount',
        'per': 'pe', 'pb': 'pbnewmrq', 'mktcap': 'total_market_cap',
        'turnoverratio': 'turnoverrate'
    })
    
    # 转换数值
    for col in ['new_price', 'change_rate', 'ups_downs', 'pre_close_price', 'open_price', 'high_price', 'low_price', 'volume', 'deal_amount', 'pe', 'pbnewmrq', 'total_market_cap', 'turnoverrate']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 添加日期列
    df['date'] = target_date
    
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 清除当天旧数据
    cursor.execute(f"DELETE FROM cn_stock_spot WHERE date = '{target_date}'")
    
    # 插入新数据 - 只插入必要字段
    insert_sql = """
    INSERT INTO cn_stock_spot 
    (date, code, name, new_price, change_rate, ups_downs, volume, deal_amount, 
     open_price, high_price, low_price, pre_close_price, pe, pbnewmrq, total_market_cap, turnoverrate)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    success = 0
    for _, row in df.iterrows():
        try:
            cursor.execute(insert_sql, (
                row['date'], row['code'], row['name'], 
                float(row.get('new_price', 0) or 0),
                float(row.get('change_rate', 0) or 0),
                float(row.get('ups_downs', 0) or 0),
                float(row.get('volume', 0) or 0),
                float(row.get('deal_amount', 0) or 0),
                float(row.get('open_price', 0) or 0),
                float(row.get('high_price', 0) or 0),
                float(row.get('low_price', 0) or 0),
                float(row.get('pre_close_price', 0) or 0),
                float(row.get('pe', 0) or 0),
                float(row.get('pbnewmrq', 0) or 0),
                float(row.get('total_market_cap', 0) or 0),
                float(row.get('turnoverrate', 0) or 0)
            ))
            success += 1
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    
    print(f'      同步完成: {success} 条记录')


def sync_stock_selection(df, target_date):
    """同步综合选股数据"""
    print(f'[3/3] 同步综合选股数据 ({target_date})...')
    
    if df.empty:
        print('      无数据')
        return
    
    # 筛选有效股票 - 使用正确的列名
    df_filtered = df[
        (pd.to_numeric(df['trade'], errors='coerce') > 0) &
        (pd.to_numeric(df['volume'], errors='coerce') > 0)
    ].copy()
    
    print(f'      筛选后 {len(df_filtered)} 条')
    
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 清除当天旧数据
    cursor.execute(f"DELETE FROM cn_stock_selection WHERE date = '{target_date}'")
    
    # 插入新数据 - 只插入必要字段，使用正确的数据库字段名
    insert_sql = """
    INSERT INTO cn_stock_selection 
    (date, code, name, new_price, change_rate, volume, deal_amount, turnoverrate, pe9, pbnewmrq, total_market_cap)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    success = 0
    for _, row in df_filtered.iterrows():
        try:
            cursor.execute(insert_sql, (
                target_date, row['code'], row['name'],
                float(row.get('trade', 0) or 0),
                float(row.get('changepercent', 0) or 0),
                float(row.get('volume', 0) or 0),
                float(row.get('amount', 0) or 0),
                float(row.get('turnoverratio', 0) or 0),
                float(row.get('per', 0) or 0),  # pe9
                float(row.get('pb', 0) or 0),   # pbnewmrq
                float(row.get('mktcap', 0) or 0)
            ))
            success += 1
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    
    print(f'      同步完成: {success} 条记录')


def main():
    """主函数"""
    target_date = date.today().strftime('%Y-%m-%d')
    
    print('=' * 60)
    print(f'数据同步 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    
    # 获取股票列表
    df = fetch_stock_list()
    
    if df.empty:
        print('获取数据失败')
        return
    
    # 同步数据
    sync_stock_spot(df, target_date)
    sync_stock_selection(df, target_date)
    
    print('=' * 60)
    print('同步完成')
    print('=' * 60)


if __name__ == '__main__':
    main()
