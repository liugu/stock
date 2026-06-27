#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续小阳线选股脚本

作者: liugu
日期: 2026/6/1

用法:
    python scripts/select_consecutive_bullish.py
    python scripts/select_consecutive_bullish.py --days 5
    python scripts/select_consecutive_bullish.py --days 3 --min-change 0.5
"""

import pymysql
import pandas as pd
import numpy as np
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    """获取股票列表"""
    conn = get_db_connection()
    try:
        sql = """
        SELECT si.id, si.code, 
               COALESCE(cs.name, si.name) as name,
               cs.new_price, cs.change_rate, cs.turnoverrate
        FROM stock_info si
        INNER JOIN (
            SELECT stock_id, MAX(date) as latest_date
            FROM stock_daily
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
            GROUP BY stock_id
        ) sd ON si.id = sd.stock_id
        LEFT JOIN cn_stock_spot cs ON BINARY si.code = BINARY cs.code
        WHERE si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
        """
        df = pd.read_sql(sql, conn)
        df = df.drop_duplicates(subset=['code'], keep='first')
        print(f'   找到 {len(df)} 只有近期数据的股票')
        return df
    finally:
        conn.close()


def get_stock_daily(stock_id, days=100):
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
        df = df.sort_values('date').reset_index(drop=True)
        return df
    finally:
        conn.close()


def check_consecutive_bullish(df, days=5, min_change=1.0, max_change=5.0, min_vol_ratio=0.8):
    """
    检查连续小阳线
    
    参数:
        df: 历史数据DataFrame
        days: 连续阳线天数
        min_change: 单日最小涨幅(%)
        max_change: 单日最大涨幅(%)
        min_vol_ratio: 最小量比（当日/均量）
    """
    if df is None or len(df) < days + 5:
        return None
    
    # 取最近数据
    recent = df.tail(days + 5).copy()
    
    closes = recent['close'].values
    opens = recent['open'].values
    volumes = recent['volume'].values
    
    # 检查连续阳线
    daily_changes = []
    vol_ratios = []
    
    for i in range(-days, 0):
        # 必须是阳线
        if closes[i] <= opens[i]:
            return None
        
        # 计算涨幅
        change_rate = (closes[i] - opens[i]) / opens[i] * 100
        daily_changes.append(round(change_rate, 2))
        
        # 涨幅在范围内
        if change_rate < min_change or change_rate > max_change:
            return None
        
        # 量比计算
        vol_start = max(0, i - 5)
        vol_ma = np.mean(volumes[vol_start:i])
        if vol_ma > 0:
            vol_ratios.append(round(volumes[i] / vol_ma, 2))
    
    # 整体趋势向上
    if closes[-1] <= opens[-days]:
        return None
    
    total_change = round((closes[-1] - opens[-days]) / opens[-days] * 100, 2)
    avg_change = round(np.mean(daily_changes), 2)
    avg_vol_ratio = round(np.mean(vol_ratios), 2) if vol_ratios else 0
    
    return {
        'total_change': total_change,
        'avg_change': avg_change,
        'daily_changes': daily_changes,
        'vol_ratios': vol_ratios,
        'avg_vol_ratio': avg_vol_ratio,
        'last_close': closes[-1],
        'last_volume': int(volumes[-1])
    }


def check_stock(stock_info, days=5, min_change=1.0, max_change=5.0, min_vol_ratio=0.8):
    """检查单只股票"""
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']
    
    try:
        df = get_stock_daily(stock_id, days=days + 10)
        if df is None:
            return None
        
        result = check_consecutive_bullish(df, days, min_change, max_change, min_vol_ratio)
        
        if result:
            return {
                'code': code,
                'name': name,
                'price': stock_info.get('new_price') or result['last_close'],
                'change_percent': stock_info.get('change_rate') or 0,
                'turnover_rate': stock_info.get('turnoverrate') or 0,
                'total_change': result['total_change'],
                'avg_change': result['avg_change'],
                'daily_changes': result['daily_changes'],
                'vol_ratios': result['vol_ratios'],
                'avg_vol_ratio': result['avg_vol_ratio']
            }
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='连续小阳线选股')
    parser.add_argument('--days', type=int, default=5, help='连续阳线天数')
    parser.add_argument('--min-change', type=float, default=1.0, help='单日最小涨幅(%)')
    parser.add_argument('--max-change', type=float, default=5.0, help='单日最大涨幅(%)')
    parser.add_argument('--min-vol-ratio', type=float, default=0.8, help='最小量比')
    parser.add_argument('--workers', type=int, default=8, help='并发线程数')
    args = parser.parse_args()
    
    print(f'\n📊 连续小阳线选股')
    print(f'   参数：连续{args.days}天，涨幅 {args.min_change}%-{args.max_change}%')
    print(f'   量能：量比 >= {args.min_vol_ratio}x')
    print()
    
    # 获取股票列表
    print('1. 获取股票列表...')
    stock_list = get_stock_list()
    
    if stock_list.empty:
        print('   没有找到股票数据')
        return
    
    # 并发检查
    print(f'2. 并发检查股票（{args.workers}线程）...')
    results = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                check_stock,
                row.to_dict(),
                args.days,
                args.min_change,
                args.max_change,
                args.min_vol_ratio
            ): row
            for _, row in stock_list.iterrows()
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f'   已检查 {completed}/{len(futures)} 只股票...')
            
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass
    
    print(f'   共检查 {len(futures)} 只股票')
    
    if not results:
        print('\n❌ 没有找到符合条件的股票')
        return
    
    # 排序结果
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_change', ascending=False)
    
    # 显示结果
    print(f'\n✅ 找到 {len(results_df)} 只符合条件的股票:\n')
    
    for i, row in results_df.head(30).iterrows():
        changes_str = ', '.join([f'{x:.1f}%' for x in row['daily_changes']])
        
        print(f"【{row['name']}】({row['code']})")
        print(f"   价格: {row['price']:.2f}元, 涨幅: +{row['change_percent']:.2f}%, 换手: {row['turnover_rate']:.2f}%")
        print(f"   累计涨幅: +{row['total_change']:.2f}%, 日均涨幅: +{row['avg_change']:.2f}%")
        print(f"   日涨幅: [{changes_str}], 量比: {row['avg_vol_ratio']:.2f}x")
        print()
    
    # 保存结果
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'consecutive_bullish_{timestamp}.xlsx')
    
    save_df = results_df[['code', 'name', 'price', 'change_percent', 'turnover_rate',
                           'total_change', 'avg_change', 'avg_vol_ratio']].copy()
    save_df.columns = ['代码', '名称', '价格', '涨幅%', '换手率%', 
                       '累计涨幅%', '日均涨幅%', '平均量比']
    save_df.to_excel(output_file, index=False)
    
    print(f'📁 结果已保存到: {output_file}')
    
    return results_df


if __name__ == '__main__':
    main()
