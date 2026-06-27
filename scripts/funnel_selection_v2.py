#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漏斗筛选法选股（优化版）

使用cn_stock_spot实时数据表，数据更完整

作者: Hermes
日期: 2026-06-16
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def print_funnel(level, name, before, after, reason):
    removed = before - after
    pct = (removed / before * 100) if before > 0 else 0
    print(f'  第{level}层【{name}】: {before} → {after} (剔除{removed}只, {pct:.1f}%) | {reason}')

def funnel_selection():
    """漏斗筛选主流程"""
    print('='*60)
    print('漏斗筛选法选股')
    print('='*60)
    print(f'日期: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    
    conn = get_db_connection()
    
    # 获取cn_stock_spot最新日期
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM cn_stock_spot')
    latest_date = cursor.fetchone()[0]
    cursor.close()
    
    print(f'数据日期: {latest_date}')
    print()
    
    # ============================================================
    # 第1层：基础过滤
    # ============================================================
    print('【开始筛选】')
    print()
    
    sql = f"""
    SELECT 
        code,
        name,
        new_price as price,
        change_rate as pct_change,
        turnoverrate as turnover,
        deal_amount as amount,
        pe,
        total_market_cap as market_cap,
        high_price as high,
        low_price as low
    FROM cn_stock_spot
    WHERE date = '{latest_date}'
      AND code NOT LIKE '688%%'  -- 剔除科创板
      AND code NOT LIKE '8%%'    -- 剔除北交所
      AND code NOT LIKE '4%%'    -- 剔除三板
      AND name NOT LIKE '%%ST%%'
      AND name NOT LIKE '%%*ST%%'
      AND name NOT LIKE '%%退%%'
      AND new_price > 1
      AND new_price < 500
    """
    
    df = pd.read_sql(sql, conn)
    level1_count = len(df)
    print_funnel(1, '基础过滤', 5000, level1_count, 'ST/退市/科创板/北交所')
    
    # ============================================================
    # 第2层：流动性过滤
    # ============================================================
    before = len(df)
    df = df[
        (df['amount'] >= 100000000) &  # 成交额>=1亿
        (df['turnover'] >= 1) &         # 换手率>=1%
        (df['turnover'] <= 20) &        # 换手率<=20%
        (df['price'] >= 5) &            # 价格>=5元
        (df['price'] <= 200)            # 价格<=200元
    ]
    df = df.dropna(subset=['price', 'turnover', 'amount'])
    level2_count = len(df)
    print_funnel(2, '流动性过滤', before, level2_count, '成交额<1亿/换手率异常')
    
    # ============================================================
    # 第3层：估值过滤
    # ============================================================
    before = len(df)
    df = df[
        ((df['pe'] > 0) & (df['pe'] < 80)) | (df['pe'].isna())  # PE合理或无数据
    ]
    level3_count = len(df)
    print_funnel(3, '估值过滤', before, level3_count, 'PE<0或>80')
    
    # ============================================================
    # 第4层：涨跌幅过滤
    # ============================================================
    before = len(df)
    df = df[
        (df['pct_change'] >= -5) &   # 跌幅不超过5%
        (df['pct_change'] <= 9)      # 涨幅不超过9%
    ]
    level4_count = len(df)
    print_funnel(4, '涨跌幅过滤', before, level4_count, '涨跌幅过大')
    
    # ============================================================
    # 第5层：评分排序
    # ============================================================
    print()
    print('【评分阶段】')
    print()
    
    df['score'] = 0
    
    # 涨幅得分（-20~20分）
    df['price_score'] = df['pct_change'].apply(lambda x: min(20, max(-20, x * 3)))
    
    # 换手率得分（0~20分）
    df['turnover_score'] = df['turnover'].apply(
        lambda x: min(20, x * 2) if x <= 10 else max(5, 20 - (x - 10) * 2)
    )
    
    # 成交额得分（0~30分）
    df['amount_score'] = df['amount'].apply(lambda x: 
        30 if x >= 1000000000 else 
        25 if x >= 500000000 else 
        20 if x >= 200000000 else 
        10)
    
    # 市值得分（0~15分）
    df['cap_score'] = df['market_cap'].apply(lambda x: 
        15 if x >= 20000000000 else 
        10 if x >= 10000000000 else 
        5)
    
    # PE得分（0~15分）
    df['pe_score'] = df['pe'].apply(lambda x: 
        15 if x and 0 < x < 20 else 
        10 if x and 20 <= x < 40 else 
        5 if x and 40 <= x < 60 else 0)
    
    df['score'] = df['price_score'] + df['turnover_score'] + df['amount_score'] + df['cap_score'] + df['pe_score']
    
    # 排序
    df = df.sort_values('score', ascending=False)
    
    # ============================================================
    # 输出结果
    # ============================================================
    print('='*60)
    print('筛选结果')
    print('='*60)
    print(f'\n最终筛选: {len(df)} 只')
    print()
    
    # TOP 30
    print('【TOP 30 高分股票】')
    print('-'*60)
    
    for i, row in df.head(30).iterrows():
        pe_str = f"{row['pe']:.1f}" if row['pe'] and row['pe'] > 0 else '-'
        print(f'{row["code"]} {row["name"]}')
        print(f'   价格: {row["price"]:.2f}元, 涨跌: {row["pct_change"]:+.2f}%, 换手: {row["turnover"]:.1f}%')
        print(f'   成交: {row["amount"]/100000000:.2f}亿, PE: {pe_str}, 得分: {row["score"]:.0f}')
        print()
    
    # 按板块分组（简单版）
    print('【按行业分布】')
    print('-'*60)
    
    # 保存结果
    output_dir = 'E:/量化研究/workspace/stock/output'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'funnel_selection_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
    output_cols = ['code', 'name', 'price', 'pct_change', 'turnover', 'amount', 'pe', 'market_cap', 'score']
    df[output_cols].to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'\n结果已保存: {output_file}')
    
    conn.close()
    
    return df

if __name__ == '__main__':
    funnel_selection()
