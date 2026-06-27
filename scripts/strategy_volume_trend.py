# -*- coding: utf-8 -*-
"""
技术选股策略
"""
import os
import sys
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

os.environ['PYTHONIOENCODING'] = 'utf-8'

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'charset': 'utf8mb4'
}

def get_stock_data(days=30):
    """获取最近N天的股票数据"""
    conn = pymysql.connect(**DB_CONFIG)
    
    query = f"""
    SELECT sd.stock_id, si.code, si.name, sd.date, sd.open, sd.close, 
           sd.high, sd.low, sd.volume, sd.amount, sd.change_percent, sd.turnover_rate
    FROM stock_daily sd
    JOIN stock_info si ON sd.stock_id = si.id
    WHERE si.code NOT LIKE '688%%'
    ORDER BY sd.stock_id, sd.date DESC
    LIMIT 500000
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

def volume_up_strategy(df):
    """
    连续放量小阳线策略
    条件：
    1. 连续3天收阳（close > open）
    2. 连续3天涨幅在0.5%-7%之间（小阳线）
    3. 成交量逐步放大（今天 > 昨天 > 前天）
    """
    results = []
    
    # 按股票分组
    grouped = df.groupby('stock_id')
    
    for stock_id, group in grouped:
        if len(group) < 3:
            continue
            
        # 按日期排序
        group = group.sort_values('date', ascending=False).reset_index(drop=True)
        
        try:
            # 最近3天数据
            d0 = group.iloc[0]  # 今天
            d1 = group.iloc[1]  # 昨天
            d2 = group.iloc[2]  # 前天
            
            # 检查条件
            # 1. 连续3天收阳
            if not (d0['close'] > d0['open'] and d1['close'] > d1['open'] and d2['close'] > d2['open']):
                continue
            
            # 2. 连续3天涨幅在0.5%-7%之间
            if not (0.5 <= d0['change_percent'] <= 7 and 
                    0.5 <= d1['change_percent'] <= 7 and 
                    0.5 <= d2['change_percent'] <= 7):
                continue
            
            # 3. 成交量逐步放大
            if not (d0['volume'] > d1['volume'] > d2['volume']):
                continue
            
            # 4. 成交量放大比例
            vol_ratio = d0['volume'] / d2['volume'] if d2['volume'] > 0 else 0
            if vol_ratio < 1.2:  # 至少放大20%
                continue
            
            results.append({
                'code': d0['code'],
                'name': d0['name'],
                'close': float(d0['close']),
                'change_percent': float(d0['change_percent']),
                'turnover_rate': float(d0['turnover_rate']) if d0['turnover_rate'] else 0,
                'volume': int(d0['volume']),
                'volume_ratio': round(vol_ratio, 2),
                'date': str(d0['date'])
            })
        except:
            continue
    
    return sorted(results, key=lambda x: x['volume_ratio'], reverse=True)

def trend_up_strategy(df):
    """
    趋势向上策略
    条件：
    1. 价格在5日、10日均线之上
    2. 5日均线上穿10日均线（金叉）
    3. 近5天累计涨幅>0
    4. 今日收阳
    """
    results = []
    
    grouped = df.groupby('stock_id')
    
    for stock_id, group in grouped:
        if len(group) < 15:  # 至少需要15天数据
            continue
            
        group = group.sort_values('date', ascending=True).reset_index(drop=True)
        
        try:
            # 计算均线
            group['ma5'] = group['close'].rolling(5).mean()
            group['ma10'] = group['close'].rolling(10).mean()
            
            # 最新数据
            latest = group.iloc[-1]
            prev = group.iloc[-2]
            
            # 1. 价格在均线上方
            if not (latest['close'] > latest['ma5'] > latest['ma10']):
                continue
            
            # 2. 金叉：今天5日线 > 10日线，昨天5日线 <= 10日线
            if not (latest['ma5'] > latest['ma10'] and prev['ma5'] <= prev['ma10']):
                continue
            
            # 3. 近5天累计涨幅>0
            recent_5 = group.tail(5)
            cum_change = (recent_5['close'].iloc[-1] - recent_5['close'].iloc[0]) / recent_5['close'].iloc[0] * 100
            if cum_change <= 0:
                continue
            
            # 4. 今日收阳
            if latest['close'] <= latest['open']:
                continue
            
            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'close': float(latest['close']),
                'change_percent': float(latest['change_percent']),
                'turnover_rate': float(latest['turnover_rate']) if latest['turnover_rate'] else 0,
                'volume': int(latest['volume']),
                'ma5': round(float(latest['ma5']), 2),
                'ma10': round(float(latest['ma10']), 2),
                'cum_change_5d': round(cum_change, 2),
                'date': str(latest['date'])
            })
        except:
            continue
    
    return sorted(results, key=lambda x: x['cum_change_5d'], reverse=True)

if __name__ == '__main__':
    print("正在获取股票数据...")
    df = get_stock_data(days=20)
    print(f"获取到 {len(df)} 条数据")
    
    # 连续放量小阳线
    print("\n【连续放量小阳线策略】")
    volume_up = volume_up_strategy(df)
    print(f"共选出 {len(volume_up)} 只股票\n")
    for i, s in enumerate(volume_up[:15], 1):
        print(f"{i}. {s['name']}({s['code']}): {s['close']}元, +{s['change_percent']:.2f}%, "
              f"放量{s['volume_ratio']}倍, 换手{s['turnover_rate']:.1f}%")
    
    # 趋势向上
    print("\n" + "="*50)
    print("\n【趋势向上策略】")
    trend_up = trend_up_strategy(df)
    print(f"共选出 {len(trend_up)} 只股票\n")
    for i, s in enumerate(trend_up[:15], 1):
        print(f"{i}. {s['name']}({s['code']}): {s['close']}元, +{s['change_percent']:.2f}%, "
              f"MA5={s['ma5']}, MA10={s['ma10']}, 5日涨幅{s['cum_change_5d']:.2f}%")
