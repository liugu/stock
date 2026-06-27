#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漏斗筛选法选股

从全市场股票开始，逐级过滤，最终筛选出优质标的

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
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def print_funnel(level, name, before, after, reason):
    """打印漏斗筛选结果"""
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
    
    # 获取最新交易日期
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM stock_daily')
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
        si.code,
        si.name,
        sd.close as price,
        sd.change_percent as pct_change,
        sd.turnover_rate as turnover,
        sd.amount,
        sd.volume
    FROM stock_info si
    INNER JOIN stock_daily sd ON si.id = sd.stock_id
    WHERE sd.date = '{latest_date}'
      AND si.code NOT LIKE '688%%'  -- 剔除科创板
      AND si.code NOT LIKE '8%%'    -- 剔除北交所
      AND si.code NOT LIKE '4%%'    -- 剔除三板
      AND si.name NOT LIKE '%%ST%%'  -- 剔除ST
      AND si.name NOT LIKE '%%*ST%%'
      AND si.name NOT LIKE '%%退%%'  -- 剔除退市
      AND sd.close > 1               -- 剔除仙股
      AND sd.close < 500             -- 剔除高价股
    """
    
    df = pd.read_sql(sql, conn)
    level1_count = len(df)
    print_funnel(1, '基础过滤', 5000, level1_count, 'ST/退市/科创板/北交所/仙股')
    
    # ============================================================
    # 第2层：流动性过滤
    # ============================================================
    before = len(df)
    df = df[
        (df['amount'] >= 20000000) &  # 成交额>=2000万（降低门槛）
        (df['turnover'] >= 0.5) &      # 换手率>=0.5%
        (df['turnover'] <= 20) &       # 换手率<=20%
        (df['price'] >= 3) &           # 价格>=3元
        (df['price'] <= 150)           # 价格<=150元
    ]
    level2_count = len(df)
    print_funnel(2, '流动性过滤', before, level2_count, '成交额<2000万/换手率异常')
    
    # ============================================================
    # 第3层：技术面过滤（需要历史数据）
    # ============================================================
    # 获取20日数据计算均线
    codes = df['code'].tolist()
    if not codes:
        print('\n无符合条件的股票')
        conn.close()
        return
    
    code_list = "','".join(codes)
    
    # 获取20日行情数据
    sql_daily = f"""
    SELECT 
        si.code,
        sd.date,
        sd.close,
        sd.high,
        sd.low,
        sd.volume
    FROM stock_info si
    INNER JOIN stock_daily sd ON si.id = sd.stock_id
    WHERE si.code IN ('{code_list}')
      AND sd.date >= DATE_SUB('{latest_date}', INTERVAL 30 DAY)
    ORDER BY si.code, sd.date
    """
    
    df_daily = pd.read_sql(sql_daily, conn)
    
    # 计算技术指标
    tech_results = []
    
    for code in codes:
        stock_data = df_daily[df_daily['code'] == code].copy()
        if len(stock_data) < 20:
            continue
        
        stock_data = stock_data.sort_values('date')
        
        # 均线
        stock_data['ma5'] = stock_data['close'].rolling(5).mean()
        stock_data['ma10'] = stock_data['close'].rolling(10).mean()
        stock_data['ma20'] = stock_data['close'].rolling(20).mean()
        
        # RSI
        delta = stock_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        stock_data['rsi'] = 100 - (100 / (1 + rs))
        
        # 获取最新一行
        latest = stock_data.iloc[-1]
        
        tech_results.append({
            'code': code,
            'price': latest['close'],
            'ma5': latest['ma5'],
            'ma10': latest['ma10'],
            'ma20': latest['ma20'],
            'rsi': latest['rsi']
        })
    
    df_tech = pd.DataFrame(tech_results)
    
    # 合并数据
    df = df.merge(df_tech, on='code', suffixes=('', '_tech'))
    
    before = len(df)
    df = df[
        (df['price'] > df['ma20'] * 0.97) &    # 股价接近或站上20日线
        (df['rsi'] >= 35) & (df['rsi'] <= 85)  # RSI合理区间
    ]
    level3_count = len(df)
    print_funnel(3, '技术面过滤', before, level3_count, '技术面弱势')
    
    # ============================================================
    # 第4层：涨幅过滤
    # ============================================================
    before = len(df)
    df = df[
        (df['pct_change'] >= -3) &   # 跌幅不超过3%
        (df['pct_change'] <= 7)      # 涨幅不超过7%
    ]
    level4_count = len(df)
    print_funnel(4, '涨跌幅过滤', before, level4_count, '涨跌幅过大/过小')
    
    # ============================================================
    # 第5层：评分排序
    # ============================================================
    print()
    print('【评分阶段】')
    print()
    
    # 计算综合得分
    df['score'] = 0
    
    # 涨幅得分（0-20分）
    df['price_score'] = df['pct_change'].apply(lambda x: min(20, max(0, x * 3)))
    
    # 换手率得分（0-20分）
    df['turnover_score'] = df['turnover'].apply(lambda x: min(20, x * 2) if x <= 10 else max(0, 20 - (x - 10) * 2))
    
    # 技术面得分（0-30分）
    df['tech_score'] = df.apply(lambda row: 
        10 if row['ma5'] > row['ma10'] > row['ma20'] else 5, axis=1)
    df['tech_score'] += df['rsi'].apply(lambda x: 10 if 50 <= x <= 70 else 5)
    
    # 成交额得分（0-30分）
    df['amount_score'] = df['amount'].apply(lambda x: 
        30 if x >= 500000000 else 
        20 if x >= 200000000 else 
        10 if x >= 100000000 else 5)
    
    df['score'] = df['price_score'] + df['turnover_score'] + df['tech_score'] + df['amount_score']
    
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
    
    # TOP 20
    print('【TOP 20 高分股票】')
    print('-'*60)
    
    for i, row in df.head(20).iterrows():
        print(f'{row["code"]} {row["name"]}')
        print(f'   价格: {row["price"]:.2f}元, 涨跌: {row["pct_change"]:+.2f}%, 换手: {row["turnover"]:.1f}%')
        print(f'   成交额: {row["amount"]/100000000:.2f}亿, 得分: {row["score"]:.0f}分')
        print(f'   MA: {row["ma5"]:.2f}/{row["ma10"]:.2f}/{row["ma20"]:.2f}, RSI: {row["rsi"]:.1f}')
        print()
    
    # 保存结果
    output_dir = 'E:/量化研究/workspace/stock/output'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'funnel_selection_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
    df[['code', 'name', 'price', 'pct_change', 'turnover', 'amount', 'score', 'rsi']].to_csv(
        output_file, index=False, encoding='utf-8-sig'
    )
    print(f'结果已保存: {output_file}')
    
    conn.close()
    
    return df

if __name__ == '__main__':
    funnel_selection()
