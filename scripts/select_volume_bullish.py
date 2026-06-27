#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续放量小阳线选股脚本

作者: liugu
日期: 2026/6/1

用法:
    python scripts/select_volume_bullish.py
    python scripts/select_volume_bullish.py --days 3
    python scripts/select_volume_bullish.py --conservative
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

from instock.core.strategy.volume_bullish import check, check_with_details

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
        # 去重，只保留每只股票一条记录
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
        # 按日期升序排列
        df = df.sort_values('date').reset_index(drop=True)
        return df
    finally:
        conn.close()


def check_stock(stock_info, days=5, min_change=1.0, max_change=5.0,
                min_vol_increase=1.1, min_vol_ratio=1.5):
    """检查单只股票"""
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']
    
    try:
        df = get_stock_daily(stock_id, days=days + 10)
        if df is None or len(df) < days + 5:
            return None
        
        # 使用策略检查
        result = check_with_details(
            (code, name),
            df,
            date=None,
            days=days,
            min_change=min_change,
            max_change=max_change,
            min_vol_increase=min_vol_increase,
            min_vol_ratio=min_vol_ratio
        )
        
        if result['pass']:
            return {
                'code': code,
                'name': name,
                'price': stock_info.get('new_price', df['close'].iloc[-1]) or df['close'].iloc[-1],
                'change_percent': stock_info.get('change_rate', 0) or 0,
                'turnover_rate': stock_info.get('turnoverrate', 0) or 0,
                'total_change': result['total_change'],
                'avg_change': result['avg_change'],
                'avg_vol_increase': result['avg_vol_increase'],
                'avg_vol_ratio': result['avg_vol_ratio'],
                'daily_changes': result['daily_changes'],
                'vol_increases': result['vol_increases']
            }
        return None
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser(description='连续放量小阳线选股')
    parser.add_argument('--days', type=int, default=5, help='连续阳线天数')
    parser.add_argument('--min-change', type=float, default=1.0, help='单日最小涨幅(%)')
    parser.add_argument('--max-change', type=float, default=5.0, help='单日最大涨幅(%)')
    parser.add_argument('--min-vol-increase', type=float, default=1.1, help='最小量能递增比率')
    parser.add_argument('--min-vol-ratio', type=float, default=1.5, help='最小量比')
    parser.add_argument('--conservative', action='store_true', help='保守模式（更严格的量能要求）')
    parser.add_argument('--workers', type=int, default=8, help='并发线程数')
    args = parser.parse_args()
    
    # 保守模式参数
    if args.conservative:
        args.min_vol_increase = 1.15
        args.min_vol_ratio = 2.0
        print('🔒 保守模式：量能递增 >= 15%，量比 >= 2.0')
    
    print(f'\n📊 连续放量小阳线选股')
    print(f'   参数：连续{args.days}天，涨幅 {args.min_change}%-{args.max_change}%')
    print(f'   量能：递增 >= {args.min_vol_increase}x，量比 >= {args.min_vol_ratio}x')
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
                args.min_vol_increase,
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
    
    # 格式化输出
    for i, row in results_df.head(20).iterrows():
        changes_str = ', '.join([f'{x:.1f}%' for x in row['daily_changes']])
        vol_str = ', '.join([f'{x:.1f}x' for x in row['vol_increases']])
        
        print(f"【{row['name']}】({row['code']})")
        print(f"   价格: {row['price']:.2f}元, 涨幅: +{row['change_percent']:.2f}%, 换手: {row['turnover_rate']:.2f}%")
        print(f"   累计涨幅: +{row['total_change']:.2f}%, 日均涨幅: +{row['avg_change']:.2f}%")
        print(f"   日涨幅: [{changes_str}]")
        print(f"   量能递增: [{vol_str}], 平均: {row['avg_vol_increase']:.2f}x, 量比: {row['avg_vol_ratio']:.2f}x")
        print()
    
    # 保存结果
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'volume_bullish_{timestamp}.xlsx')
    
    # 准备保存的数据
    save_df = results_df[['code', 'name', 'price', 'change_percent', 'turnover_rate',
                           'total_change', 'avg_change', 'avg_vol_increase', 'avg_vol_ratio']].copy()
    save_df.columns = ['代码', '名称', '价格', '涨幅%', '换手率%', 
                       '累计涨幅%', '日均涨幅%', '平均量能递增', '平均量比']
    save_df.to_excel(output_file, index=False)
    
    print(f'📁 结果已保存到: {output_file}')
    
    return results_df


if __name__ == '__main__':
    main()
