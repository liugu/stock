#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地MySQL数据库选股 - 连续小阳线策略

作者: liugu
日期: 2026/5/27
"""

import pymysql
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

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


def get_stock_list():
    """获取股票列表 - 从stock_daily和cn_stock_spot关联获取真实名称（过滤科创板688开头）"""
    conn = get_db_connection()
    try:
        sql = """
        SELECT DISTINCT si.id, si.code, 
               COALESCE(cs.name, si.name) as name
        FROM stock_info si
        INNER JOIN stock_daily sd ON si.id = sd.stock_id
        LEFT JOIN (
            SELECT cs1.* FROM cn_stock_spot cs1
            INNER JOIN (
                SELECT code, MAX(date) as max_date
                FROM cn_stock_spot
                GROUP BY code
            ) cs2 ON cs1.code = cs2.code AND cs1.date = cs2.max_date
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
          AND si.code NOT LIKE '688%%'
        """
        df = pd.read_sql(sql, conn)
        print(f'   找到 {len(df)} 只有近期数据的股票（已过滤科创板）')
        return df
    finally:
        conn.close()


def get_stock_daily(stock_id, days=300):
    """获取股票历史数据"""
    conn = get_db_connection()
    try:
        sql = f"""
        SELECT date, open, close, high, low, volume, change_percent
        FROM stock_daily
        WHERE stock_id = {stock_id}
        ORDER BY date DESC
        LIMIT {days}
        """
        df = pd.read_sql(sql, conn)
        if df.empty:
            return None
        # 按日期升序排列
        df = df.sort_values('date').reset_index(drop=True)
        return df
    finally:
        conn.close()


def check_consecutive_small_bullish(df, days=5, min_change=0.5, max_change=6.0):
    """
    检查连续小阳线
    
    参数:
        df: 历史数据DataFrame
        days: 连续阳线天数
        min_change: 单日最小涨幅(%)
        max_change: 单日最大涨幅(%)
    """
    if df is None or len(df) < days + 2:
        return False
    
    # 取最近 days 天数据
    recent = df.tail(days + 1)
    
    # 检查连续阳线
    for i in range(-days, 0):
        row = recent.iloc[i]
        open_price = float(row['open'])
        close_price = float(row['close'])
        
        # 必须是阳线
        if close_price <= open_price:
            return False
        
        # 计算涨幅（基于开盘价）
        daily_change = (close_price - open_price) / open_price * 100
        if daily_change < min_change or daily_change > max_change:
            return False
    
    return True


def check_low_position(df, lookback=250, max_price_ratio=1.3, percentile=25):
    """
    检查股价是否在低位
    
    参数:
        df: 历史数据DataFrame
        lookback: 回看天数
        max_price_ratio: 最大价格比率(当前价/期间最低价)
        percentile: 价格分位数阈值(%)
    """
    if df is None or len(df) < 60:
        return False, {}
    
    # 调整lookback
    actual_lookback = min(lookback, len(df))
    recent = df.tail(actual_lookback)
    
    current_close = float(recent.iloc[-1]['close'])
    period_low = float(recent['low'].min())
    period_high = float(recent['high'].max())
    
    # 计算价格比率
    price_ratio = current_close / period_low if period_low > 0 else 999
    
    # 计算价格分位数
    closes = recent['close'].astype(float).values
    price_pct = (np.sum(closes <= current_close) / len(closes)) * 100
    
    # 判断低位
    is_low = price_ratio <= max_price_ratio or price_pct <= percentile
    
    details = {
        'current_price': round(current_close, 2),
        'period_low': round(period_low, 2),
        'period_high': round(period_high, 2),
        'price_ratio': round(price_ratio, 2),
        'price_percentile': round(price_pct, 1),
        'distance_from_low': round((current_close - period_low) / period_low * 100, 2),
        'distance_from_high': round((period_high - current_close) / period_high * 100, 2)
    }
    
    return is_low, details


def check_stock(row, days=5, min_change=0.01, max_change=10.0):
    """
    检查单只股票
    
    参数说明 (基于回测优化):
        days: 连续阳线天数，回测显示5天最优 (胜率80%)
        min_change: 最小涨幅，放宽到0.01%
        max_change: 最大涨幅，放宽到10%
    
    返回: (是否通过, 详情)
    """
    stock_id = row['id']
    code = row['code']
    name = row['name']
    
    try:
        # 获取历史数据
        df = get_stock_daily(stock_id, days=300)
        if df is None or len(df) < 60:
            return None
        
        # 检查连续小阳线 (回测优化参数)
        is_bullish = check_consecutive_small_bullish(df, days=days, min_change=min_change, max_change=max_change)
        if not is_bullish:
            return None
        
        # 检查低位 (回测显示50%分位平衡性最好)
        is_low, low_details = check_low_position(df, percentile=50)
        if not is_low:
            return None
        
        # 获取最新价格和涨幅
        last_row = df.iloc[-1]
        latest_price = float(last_row['close'])
        change_pct = float(last_row['change_percent']) if last_row['change_percent'] is not None else 0
        
        # 构建结果
        result = {
            'stock_id': stock_id,
            '代码': code,
            '名称': name,
            '最新价': latest_price,
            '涨跌幅': round(change_pct, 2),
            '市盈率': None,  # 需要从其他表获取
            **low_details,
            '信号': f"连续{days}日小阳线+低位(距低点{low_details['distance_from_low']}%)"
        }
        
        return result
        
    except Exception as e:
        return None


def run_selection(days=5, max_workers=20):
    """
    运行选股
    
    参数:
        days: 连续阳线天数
        max_workers: 并发线程数
    """
    print(f'开始选股: 连续{days}日小阳线 + 年内低位')
    print('=' * 50)
    
    # 获取股票列表
    print('\n1. 获取股票列表...')
    stocks = get_stock_list()
    print(f'   共 {len(stocks)} 只股票')
    
    # 并发检查
    print(f'\n2. 并发检查 (线程数: {max_workers})...')
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_stock, row, days): row for _, row in stocks.iterrows()}
        
        completed = 0
        total = len(futures)
        
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f'   进度: {completed}/{total}')
            
            result = future.result()
            if result:
                results.append(result)
    
    print(f'\n3. 选股完成!')
    print(f'   符合条件: {len(results)} 只')
    
    # 排序并返回
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('distance_from_low', ascending=True)
        return df
    
    return pd.DataFrame()


def main():
    """主函数"""
    # 运行选股
    df = run_selection(days=5, max_workers=30)
    
    if df.empty:
        print('\n没有找到符合条件的股票')
        return
    
    # 打印结果
    print('\n' + '=' * 50)
    print('选股结果:')
    print('=' * 50)
    
    for i, row in df.head(20).iterrows():
        print(f'\n{i+1}. {row["代码"]} {row["名称"]}')
        print(f'   价格: {row["最新价"]}元, 涨幅: {row["涨跌幅"]}%, PE: {row["市盈率"]}')
        print(f'   期间低位: {row["period_low"]}元, 高位: {row["period_high"]}元')
        print(f'   距低点: {row["distance_from_low"]}%, 距高点: {row["distance_from_high"]}%')
        print(f'   价格分位: {row["price_percentile"]}%')
    
    # 保存结果
    output_file = f'output/selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'\n结果已保存: {output_file}')
    
    return df


if __name__ == '__main__':
    main()
