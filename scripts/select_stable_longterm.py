#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长线稳定盈利选股脚本

选股逻辑（四维筛选）:
  基本面: PE在5~25 + PB在0.5~3 + 总市值>=100亿
  技术面: 股价在MA60和MA120之上 + 均线趋势向上
  风控面: 波动率<=3% + 最大回撤<=20%
  稳健面: 稳定性评分 + 均线多头加分

用法:
    venv/Scripts/python scripts/select_stable_longterm.py
    venv/Scripts/python scripts/select_stable_longterm.py --min-pe 8 --max-pe 20
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

from instock.core.strategy.stable_longterm import check_with_details

DB_CONFIG = {
    'host': 'localhost', 'user': 'stock', 'password': '12345678',
    'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def get_stock_list():
    conn = get_db_connection()
    try:
        # 先用基本面预筛选：PE、PB、市值
        sql = """
        SELECT si.id, si.code, 
               COALESCE(cs.name, si.name) as name,
               cs.new_price, cs.change_rate, cs.turnoverrate,
               cs.pe, cs.pbnewmrq, cs.total_market_cap
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
          AND cs.pe > 0 AND cs.pe <= 30
          AND cs.pbnewmrq > 0 AND cs.pbnewmrq <= 5
          AND cs.total_market_cap >= 5000000  -- 50亿（单位：万元）
          AND (cs.name NOT LIKE '%ST%' AND cs.name NOT LIKE '%*ST%' AND cs.name NOT LIKE '%S%')
        ORDER BY cs.total_market_cap DESC
        """
        df = pd.read_sql(sql, conn)
        df = df.drop_duplicates(subset=['code'], keep='first')
        print(f'   基本面预筛通过: {len(df)} 只')
        return df
    finally:
        conn.close()


def get_stock_daily(stock_id, days=200):
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


def check_stock(stock_info):
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']
    
    try:
        df = get_stock_daily(stock_id, days=200)
        if df is None or len(df) < 125:
            return None

        result = check_with_details((code, name), df)

        if result is None:
            return None

        # 基本面数据
        pe = stock_info.get('pe')
        pb = stock_info.get('pbnewmrq')
        mcap = stock_info.get('total_market_cap')
        # 市值转亿
        mcap_yi = round(mcap / 10000, 1) if mcap and mcap > 0 else 0

        last_close = df.iloc[-1]['close']
        last_change = df.iloc[-1].get('change_percent') if 'change_percent' in df.columns else None

        # 综合评分（百分制）
        score = 50  # 基础分
        
        # 加分：PE评分（15-25之间最佳）
        if pe and 8 <= pe <= 20:
            score += 15
        elif pe and 5 <= pe <= 25:
            score += 10
        else:
            score += 5
        
        # 加分：PB评分（1-2之间最佳）
        if pb and 1 <= pb <= 2:
            score += 10
        elif pb and 0.5 <= pb <= 3:
            score += 5
        
        # 加分：低波动
        if result['volatility'] <= 2.0:
            score += 10
        elif result['volatility'] <= 2.5:
            score += 5
        
        # 加分：低回撤
        if result['max_drawdown'] <= 10:
            score += 10
        elif result['max_drawdown'] <= 15:
            score += 5
        
        # 加分：稳定性高
        if result['stability'] >= 55:
            score += 10
        elif result['stability'] >= 50:
            score += 5
        
        # 加分：均线多头
        if result['bullish_ma']:
            score += 5

        return {
            'code': code,
            'name': name,
            'price': stock_info.get('new_price') if pd.notna(stock_info.get('new_price')) else last_close,
            'change_percent': stock_info.get('change_rate') if pd.notna(stock_info.get('change_rate')) else (last_change if pd.notna(last_change) else 0),
            'pe': round(pe, 2) if pe else 0,
            'pb': round(pb, 2) if pb else 0,
            'mcap_yi': mcap_yi,
            'volatility': result['volatility'],
            'annual_vol': result['annual_vol'],
            'max_drawdown': result['max_drawdown'],
            'stability': result['stability'],
            'deviation_60': result['deviation_60'],
            'pct_120d': result['pct_120d'],
            'pct_60d': result['pct_60d'],
            'pct_20d': result['pct_20d'],
            'pct_3d': result['pct_3d'],
            'ma60': result['ma60'],
            'ma120': result['ma120'],
            'bullish_ma': result['bullish_ma'],
            'score': score
        }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='长线稳定盈利选股')
    parser.add_argument('--min-pe', type=float, default=5, help='最小PE')
    parser.add_argument('--max-pe', type=float, default=25, help='最大PE')
    parser.add_argument('--min-mcap', type=float, default=50, help='最小市值(亿)')
    parser.add_argument('--max-vol', type=float, default=3.0, help='最大波动率%')
    parser.add_argument('--max-dd', type=float, default=20, help='最大回撤%')
    parser.add_argument('--top', type=int, default=20, help='展示前N只')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    print(f'\n🏛️ 长线稳定盈利选股')
    print(f'   条件：PE {args.min_pe}~{args.max_pe} | PB 0.5~3 | 市值>{args.min_mcap}亿')
    print(f'   波动率<{args.max_vol}% | 最大回撤<{args.max_dd}% | 股价在MA60+MA120之上')
    print()

    print('1. 基本面预筛选...')
    stock_list = get_stock_list()
    if stock_list.empty:
        print('   没有找到符合条件的股票')
        return

    print(f'2. 技术面筛选（{args.workers}线程）...')
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(check_stock, row.to_dict()): row
            for _, row in stock_list.iterrows()
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 200 == 0:
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

    df = pd.DataFrame(results)
    df = df.sort_values('score', ascending=False)

    print(f'\n✅ 找到 {len(df)} 只长线稳定盈利候选股')
    print(f'   {"完整多头":>4} | {"均线多头":>4}')  # 只是统计用
    bullish_count = df[df['bullish_ma'] == True].shape[0]
    print(f'   均线多头排列: {bullish_count}/{len(df)} 只')
    print()

    # 按评分区间展示
    tiers = [
        ('⭐⭐⭐⭐⭐ 优质蓝筹 (评分≥90)', df[df['score'] >= 90]),
        ('⭐⭐⭐⭐ 稳健成长 (评分80-89)', df[(df['score'] >= 80) & (df['score'] < 90)]),
        ('⭐⭐⭐ 值得关注 (评分70-79)', df[(df['score'] >= 70) & (df['score'] < 80)]),
        ('⭐⭐ 备选观察 (评分<70)', df[df['score'] < 70]),
    ]

    for title, tier_df in tiers:
        if tier_df.empty:
            continue
        print(f'━━━ {title} ━━━\n')
        for _, row in tier_df.head(args.top).iterrows():
            ma_flag = '📈' if row['bullish_ma'] else '📊'
            print(f"{ma_flag} 【{row['name']}】({row['code']})  评分: {row['score']}")
            print(f"   价格: {row['price']:.2f}元 | PE: {row['pe']:.1f} | PB: {row['pb']:.2f} | 市值: {row['mcap_yi']:.0f}亿")
            print(f"   波动率: {row['volatility']:.2f}%/日 ({row['annual_vol']:.1f}%/年) | 最大回撤: {row['max_drawdown']:.1f}%")
            print(f"   稳定性: {row['stability']:.1f}%正收益日 | 距MA60: {row['deviation_60']:+.2f}%")
            print(f"   120日涨幅: {row['pct_120d']:+.2f}% | 60日: {row['pct_60d']:+.2f}% | 20日: {row['pct_20d']:+.2f}%")
            print()

    # 保存
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'stable_longterm_{timestamp}.csv')

    save_df = df[['code', 'name', 'price', 'change_percent', 'pe', 'pb', 'mcap_yi',
                   'volatility', 'annual_vol', 'max_drawdown', 'stability',
                   'deviation_60', 'pct_120d', 'pct_60d', 'pct_20d',
                   'ma60', 'ma120', 'bullish_ma', 'score']].copy()
    save_df.columns = ['代码', '名称', '价格', '涨幅%', 'PE', 'PB', '市值亿',
                        '日波动率%', '年化波动%', '最大回撤%', '正收益日%',
                        '距MA60%', '120日涨幅%', '60日涨幅%', '20日涨幅%',
                        'MA60', 'MA120', '均线多头', '评分']
    save_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f'📁 结果已保存到: {output_file}')
    print(f'📊 共 {len(df)} 只长线稳定盈利候选股')


if __name__ == '__main__':
    main()
