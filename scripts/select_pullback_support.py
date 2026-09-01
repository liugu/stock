#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连续缩量回调到支撑位选股脚本

识别上升趋势中缩量回调到关键均线支撑的股票（反弹机会）

用法:
    venv/Scripts/python scripts/select_pullback_support.py
    venv/Scripts/python scripts/select_pullback_support.py --support ma60 --pullback-days 5
    venv/Scripts/python scripts/select_pullback_support.py --max-distance 2
"""

import pymysql
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instock.core.strategy.pullback_to_support import check, check_with_details

DB_CONFIG = {
    'host': 'localhost', 'user': 'stock', 'password': '12345678',
    'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def get_stock_list():
    conn = get_db_connection()
    try:
        sql = """
        SELECT si.id, si.code, 
               COALESCE(cs.name, si.name) as name,
               cs.new_price, cs.change_rate, cs.turnoverrate,
               cs.pe
        FROM stock_info si
        INNER JOIN (
            SELECT stock_id, MAX(date) as latest_date
            FROM stock_daily
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 15 DAY)
            GROUP BY stock_id
        ) sd ON si.id = sd.stock_id
        LEFT JOIN (
            SELECT cs1.* FROM cn_stock_spot cs1
            INNER JOIN (
                SELECT code, MAX(date) as max_date
                FROM cn_stock_spot
                GROUP BY code
            ) cs2 ON cs1.code = cs2.code AND cs1.date = cs2.max_date
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
        """
        df = pd.read_sql(sql, conn)
        df = df.drop_duplicates(subset=['code'], keep='first')
        print(f'   找到 {len(df)} 只有近期数据的股票')
        return df
    finally:
        conn.close()


def get_stock_daily(stock_id, days=120):
    conn = get_db_connection()
    try:
        sql = f"""
        SELECT date, open, close, high, low, volume, change_percent
        FROM stock_daily
        WHERE stock_id = {stock_id}
        ORDER BY date DESC LIMIT {days}
        """
        df = pd.read_sql(sql, conn)
        if df.empty:
            return None
        df = df.sort_values('date').reset_index(drop=True)
        return df
    finally:
        conn.close()


def check_stock(stock_info, pullback_days=3, support_ma='ma20', support_distance=3.0):
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']

    try:
        df = get_stock_daily(stock_id, days=120)
        if df is None:
            return None

        result = check_with_details((code, name), df,
                                    pullback_days=pullback_days,
                                    support_ma=support_ma,
                                    support_distance=support_distance)

        if result:
            # 过滤ST
            if name.startswith('*ST') or name.startswith('ST') or name.startswith('S'):
                return None

            last_close = df.iloc[-1]['close']
            last_change = df.iloc[-1].get('change_percent') if 'change_percent' in df.columns else None

            return {
                'code': code,
                'name': name,
                'price': stock_info.get('new_price') if pd.notna(stock_info.get('new_price')) else last_close,
                'change_percent': stock_info.get('change_rate') if pd.notna(stock_info.get('change_rate')) else (last_change if pd.notna(last_change) else 0),
                'turnover_rate': stock_info.get('turnoverrate') if pd.notna(stock_info.get('turnoverrate')) else 0,
                'pe': stock_info.get('pe') or 0,
                'total_pullback': result['total_pullback'],
                'daily_changes': result['daily_changes'],
                'avg_pullback_vol_ratio': result['avg_pullback_vol_ratio'],
                'vol_shrinking': result['vol_shrinking'],
                'ma5': result['ma5'], 'ma10': result['ma10'],
                'ma20': result['ma20'], 'ma60': result['ma60'],
                'dist_to_ma20': result['dist_to_ma20'],
                'dist_to_ma60': result['dist_to_ma60'],
                'support_ma': result['support_ma'],
                'support_value': result['support_value'],
                'distance_to_support': result['distance_to_support'],
                'uptrend_before': result['uptrend_before']
            }
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='缩量回调到支撑位选股')
    parser.add_argument('--pullback-days', type=int, default=3, help='回调天数，默认3')
    parser.add_argument('--support', type=str, default='ma20', choices=['ma20', 'ma60'],
                        help='支撑均线，ma20或ma60，默认ma20')
    parser.add_argument('--max-distance', type=float, default=3.0, help='距支撑均线最大距离%，默认3%')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    support_label = 'MA20' if args.support == 'ma20' else 'MA60'
    print(f'\n📉 连续缩量回调到{support_label}支撑位')
    print(f'   条件：连续{args.pullback_days}天回调 + 缩量 + 距{support_label}在{args.max_distance}%内')
    print()

    print('1. 获取股票列表...')
    stock_list = get_stock_list()
    if stock_list.empty:
        print('   没有找到股票数据')
        return

    print(f'2. 并发检查股票（{args.workers}线程）...')
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(check_stock, row.to_dict(), args.pullback_days, args.support, args.max_distance): row
            for _, row in stock_list.iterrows()
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f'   已检查 {completed}/{len(futures)} 只股票...')
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    print(f'   共检查 {len(futures)} 只股票')

    if not results:
        print('\n❌ 没有找到符合条件的股票')
        return

    results_df = pd.DataFrame(results)
    # 按距支撑位由近到远排序
    results_df = results_df.sort_values('distance_to_support')

    print(f'\n✅ 找到 {len(results_df)} 只缩量回调到{support_label}支撑的股票:\n')

    # 按支撑类型分组展示
    for i, row in results_df.head(20).iterrows():
        changes_str = ', '.join([f'{x:.2f}%' for x in row['daily_changes']])
        vol_str = '逐日缩量' if row['vol_shrinking'] else '量能偏低'

        print(f"【{row['name']}】({row['code']})")
        print(f"   价格: {row['price']:.2f}元 | 今日涨幅: {row['change_percent']:+.2f}% | PE: {row['pe']:.1f}")
        print(f"   累计回调: {row['total_pullback']:.2f}% | 每日涨跌: [{changes_str}]")
        print(f"   {vol_str} | 均量比: {row['avg_pullback_vol_ratio']:.2f}x")
        print(f"   距{row['support_ma'].upper()}={row['support_value']:.2f} | 距离: {row['distance_to_support']:.2f}%")
        print(f"   均线: MA5={row['ma5']:.2f} MA10={row['ma10']:.2f} MA20={row['ma20']:.2f} MA60={row['ma60']:.2f}")
        print()

    # 保存
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'pullback_support_{timestamp}.csv')

    save_df = results_df[['code', 'name', 'price', 'change_percent', 'pe',
                           'total_pullback', 'avg_pullback_vol_ratio', 'vol_shrinking',
                           'ma5', 'ma10', 'ma20', 'ma60',
                           'dist_to_ma20', 'dist_to_ma60',
                           'support_ma', 'support_value', 'distance_to_support']].copy()
    save_df.columns = ['代码', '名称', '价格', '涨幅%', 'PE',
                        '累计回调%', '均量比', '逐日缩量',
                        'MA5', 'MA10', 'MA20', 'MA60',
                        '距MA20%', '距MA60%',
                        '支撑均线', '支撑价位', '距支撑%']
    save_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f'📁 结果已保存到: {output_file}')
    print(f'📊 共 {len(results_df)} 只缩量回调支撑股')


if __name__ == '__main__':
    main()
