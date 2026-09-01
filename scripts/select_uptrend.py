#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""趋势向上选股脚本 v2

宽松版（默认）: MA5 > MA10 > MA20 + 股价在MA20上 + MA60走平 + 斜率向上
增强版 (--strong): MA5 > MA10 > MA20 > MA60 完整多头排列

用法:
    venv/Scripts/python scripts/select_uptrend.py
    venv/Scripts/python scripts/select_uptrend.py --strong
    venv/Scripts/python scripts/select_uptrend.py --min-20d-pct 5 --min-vol-ratio 1.2
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

from instock.core.strategy.uptrend import check, check_strong, check_with_details

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


def check_stock(stock_info, use_strong=False, min_20d_pct=0, min_vol_ratio=0, max_3d_pct=10):
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']
    
    try:
        df = get_stock_daily(stock_id, days=120)
        if df is None:
            return None
        
        result = check_with_details((code, name), df, max_3d_pct=max_3d_pct)
        
        if result:
            # 额外过滤
            if result['pct_20d'] < min_20d_pct:
                return None
            if result['vol_ratio'] < min_vol_ratio:
                return None
            if use_strong and not result['fully_bullish']:
                return None
            
            # 过滤ST股和无效数据
            if name.startswith('*ST') or name.startswith('ST') or name.startswith('S'):
                return None
            if pd.isna(stock_info.get('new_price')) and pd.isna(df.iloc[-1]['close']):
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
                'ma5': result['ma5'], 'ma10': result['ma10'],
                'ma20': result['ma20'], 'ma60': result['ma60'],
                'ma_spread': result['ma_spread'],
                'pct_60d': result['pct_60d'],
                'pct_20d': result['pct_20d'],
                'pct_5d': result['pct_5d'],
                'pct_3d': result['pct_3d'],
                'vol_ratio': result['vol_ratio'],
                'slope': result['slope'],
                'fully_bullish': result['fully_bullish'],
                'full_ma_text': result['full_ma_text']
            }
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='趋势向上选股')
    parser.add_argument('--strong', action='store_true', help='增强版：完整多头排列 MA5>MA10>MA20>MA60')
    parser.add_argument('--min-20d-pct', type=float, default=0, help='最小20日涨幅%')
    parser.add_argument('--min-vol-ratio', type=float, default=0, help='最小量比')
    parser.add_argument('--max-3d-pct', type=float, default=10, help='近3日涨幅上限（默认10%，超过排除）')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    
    mode = '增强版' if args.strong else '宽松版'
    print(f'\n📈 趋势向上选股 [{mode}]')
    print(f'   条件：MA5>MA10>MA20 + 股价在MA20上 + 斜率向上')
    if args.strong:
        print(f'   完整多头：MA5>MA10>MA20>MA60 + 股价在MA60上')
    if args.min_20d_pct > 0:
        print(f'   20日涨幅 >= {args.min_20d_pct}%')
    if args.min_vol_ratio > 0:
        print(f'   量比 >= {args.min_vol_ratio}x')
    if args.max_3d_pct < 100:
        print(f'   过滤近3日涨幅 > {args.max_3d_pct}%')
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
            executor.submit(check_stock, row.to_dict(), args.strong, args.min_20d_pct, args.min_vol_ratio, args.max_3d_pct): row
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
    
    # 区分完整多头和普通趋势
    full_bullish_df = results_df[results_df['fully_bullish'] == True].sort_values('pct_20d', ascending=False)
    normal_df = results_df[results_df['fully_bullish'] == False].sort_values('pct_20d', ascending=False)
    
    print(f'\n✅ 找到 {len(results_df)} 只趋势向上的股票')
    print(f'   ├─ 完整多头(MA5>MA10>MA20>MA60): {len(full_bullish_df)} 只')
    print(f'   └─ 短期趋势向上: {len(normal_df)} 只')
    print()
    
    # 展示完整多头（最强信号）
    if not full_bullish_df.empty:
        print(f'━━━ 完整多头排列（最强信号）━━━\n')
        for i, row in full_bullish_df.head(15).iterrows():
            print(f"【{row['name']}】({row['code']})")
            print(f"   价格: {row['price']:.2f}元 | 涨幅: {row['change_percent']:+.2f}% | 换手: {row['turnover_rate']:.2f}% | PE: {row['pe']:.1f}")
            print(f"   {row['full_ma_text']} | 发散: {row['ma_spread']:.2f}%")
            print(f"   20日涨幅: {row['pct_20d']:+.2f}% | 60日涨幅: {row['pct_60d']:+.2f}% | 近3日: {row['pct_3d']:+.2f}% | 量比: {row['vol_ratio']:.2f}x")
            print()
    
    # 展示普通趋势
    if not normal_df.empty:
        print(f'━━━ 短期趋势向上（均线刚多头）━━━\n')
        for i, row in normal_df.head(10).iterrows():
            print(f"【{row['name']}】({row['code']})")
            print(f"   价格: {row['price']:.2f}元 | 涨幅: {row['change_percent']:+.2f}% | 换手: {row['turnover_rate']:.2f}% | PE: {row['pe']:.1f}")
            print(f"   {row['full_ma_text']} | 20日涨幅: {row['pct_20d']:+.2f}% | 近3日: {row['pct_3d']:+.2f}% | 量比: {row['vol_ratio']:.2f}x")
            print()
    
    # 保存
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'uptrend_{timestamp}.csv')
    
    save_df = results_df[['code', 'name', 'price', 'change_percent', 'turnover_rate', 'pe',
                           'ma5', 'ma10', 'ma20', 'ma60', 'ma_spread',
                           'pct_60d', 'pct_20d', 'pct_3d', 'pct_5d', 'vol_ratio', 'slope', 'fully_bullish']].copy()
    save_df.columns = ['代码', '名称', '价格', '涨幅%', '换手率%', 'PE',
                       'MA5', 'MA10', 'MA20', 'MA60', '发散度%',
                       '60日涨幅%', '20日涨幅%', '3日涨幅%', '5日涨幅%', '量比', '斜率', '完整多头']
    save_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f'📁 结果已保存到: {output_file}')
    print(f'📊 共 {len(results_df)} 只趋势向上股票')


if __name__ == '__main__':
    main()
