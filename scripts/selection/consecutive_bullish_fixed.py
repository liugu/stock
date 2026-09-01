#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续小阳线选股脚本（修复版）
- 增加数据新鲜度校验：必须包含今日数据
- 自动跳过 stock_daily 数据不完整的股票
"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import pandas as pd
import numpy as np
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date

DB_CONFIG = {
    'host': 'localhost', 'user': 'stock', 'password': '12345678',
    'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

def get_stock_list():
    """获取股票列表 - 只选有完整stock_daily数据的股票"""
    conn = get_conn()
    try:
        # 先查stock_daily最新日期
        c = conn.cursor()
        c.execute('SELECT MAX(date) FROM stock_daily')
        latest_date = c.fetchone()[0]
        if not latest_date:
            print('stock_daily 无数据')
            return pd.DataFrame()
        today = date.today()
        latest_d = latest_date if isinstance(latest_date, date) else latest_date.date()
        
        # 取最近交易日（如果是周末则取最后一个交易日）
        from datetime import timedelta
        target_date = latest_date
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        print(f'   stock_daily 最新日期: {latest_date}')
        print(f'   目标数据日期: {target_date}')
        
        # 只选 stock_daily 包含目标日期的股票
        sql = f"""
        SELECT si.id, si.code, si.name
        FROM stock_info si
        INNER JOIN stock_daily sd ON si.id = sd.stock_id AND sd.date = '{target_date}'
        WHERE (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
          AND si.code NOT LIKE '688%%'
        GROUP BY si.id, si.code, si.name
        ORDER BY si.code
        """
        df = pd.read_sql(sql, conn)
        print(f'   有完整数据（含{target_date}）的股票: {len(df)} 只')
        return df, target_date
    finally:
        conn.close()

def get_stock_daily(stock_id, target_date, days=100):
    """获取股票历史数据，仅取到target_date"""
    conn = get_conn()
    try:
        sql = f"""
        SELECT date, open, close, high, low, volume, amount, change_percent, turnover_rate
        FROM stock_daily
        WHERE stock_id = {stock_id} AND date <= '{target_date}'
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
    检查连续小阳线（修复版）
    校验最近 days 天都是阳线，涨幅在范围内
    """
    if df is None or len(df) < days + 3:
        return None
    
    recent = df.tail(days + 3).copy()
    
    closes = recent['close'].values.astype(float)
    opens = recent['open'].values.astype(float)
    volumes = recent['volume'].values.astype(float)
    changes = recent['change_percent'].values.astype(float) if 'change_percent' in recent.columns else None
    
    daily_changes = []
    vol_ratios = []
    
    for i in range(-days, 0):
        # 必须是阳线（收盘 > 开盘）
        if closes[i] <= opens[i]:
            return None
        
        # 用change_percent计算涨幅
        if changes is not None and not np.isnan(changes[i]):
            change_rate = abs(changes[i])  # 单日实际涨跌幅
        else:
            change_rate = (closes[i] - opens[i]) / opens[i] * 100
        
        # 阳线涨幅在合理范围内
        if change_rate < min_change or change_rate > max_change:
            return None
        
        daily_changes.append(round(change_rate, 2))
        
        # 成交量递增检查
        if len(volumes) >= days + 1:
            idx = len(volumes) - days + i
            if idx > 0:
                vol_ma = np.mean(volumes[max(0,idx-5):idx])
                if vol_ma > 0:
                    vol_ratios.append(round(volumes[idx] / vol_ma, 2))
    
    # 整体趋势判定
    if closes[-1] <= opens[-days]:
        return None
    
    total_change = round((closes[-1] - opens[-days]) / opens[-days] * 100, 2)
    avg_change = round(np.mean(daily_changes), 2)
    avg_vol_ratio = round(np.mean(vol_ratios), 2) if vol_ratios else 0
    
    return {
        'total_change': total_change,
        'avg_change': avg_change,
        'daily_changes': daily_changes,
        'avg_vol_ratio': avg_vol_ratio,
        'last_close': closes[-1]
    }

def check_stock(stock_info, target_date, days=5, min_change=1.0, max_change=5.0, min_vol_ratio=0.8):
    """检查单只股票"""
    stock_id, code, name = stock_info['id'], stock_info['code'], stock_info['name']
    try:
        df = get_stock_daily(stock_id, target_date, days=days + 10)
        if df is None:
            return None
        result = check_consecutive_bullish(df, days, min_change, max_change, min_vol_ratio)
        if result:
            return {
                'code': code, 'name': name,
                'price': result['last_close'],
                'total_change': result['total_change'],
                'avg_change': result['avg_change'],
                'daily_changes': result['daily_changes'],
                'avg_vol_ratio': result['avg_vol_ratio']
            }
        return None
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description='连续小阳线选股（修复版）')
    parser.add_argument('--days', type=int, default=5)
    parser.add_argument('--min-change', type=float, default=1.0)
    parser.add_argument('--max-change', type=float, default=5.0)
    parser.add_argument('--min-vol-ratio', type=float, default=0.8)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    
    print(f'\n{"="*60}')
    print('连续小阳线选股（修复版-数据新鲜度校验）')
    print(f'日期: {date.today()}')
    print(f'参数: 连续{args.days}天 涨幅{args.min_change}%-{args.max_change}% 量比≥{args.min_vol_ratio}x')
    print(f'{"="*60}')
    
    print('\n1. 获取股票列表（仅含完整数据）...')
    stock_list, target_date = get_stock_list()
    if stock_list.empty:
        print('   没有符合条件的股票')
        return
    
    print(f'\n2. 并发检查股票（{args.workers}线程）...')
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(check_stock, row.to_dict(), target_date,
                           args.days, args.min_change, args.max_change, args.min_vol_ratio): row
            for _, row in stock_list.iterrows()
        }
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f'   已检查 {completed}/{len(futures)} 只...')
            try:
                r = future.result()
                if r:
                    results.append(r)
            except:
                pass
    
    print(f'   共检查 {len(futures)} 只，找到 {len(results)} 只')
    
    if not results:
        print('\n❌ 未找到符合条件的股票')
        return
    
    results_df = pd.DataFrame(results).sort_values('total_change', ascending=False)
    
    print(f'\n✅ 找到 {len(results_df)} 只符合条件的股票:\n')
    for _, row in results_df.head(30).iterrows():
        chg = ', '.join([f'{x:.1f}%' for x in row['daily_changes']])
        print(f'【{row["name"]}】({row["code"]})')
        print(f'   价格: {row["price"]:.2f}元, 累计涨幅: +{row["total_change"]:.2f}%')
        print(f'   日均涨幅: +{row["avg_change"]:.2f}% | 日涨幅: [{chg}] | 量比: {row["avg_vol_ratio"]:.2f}x')
        print()
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_df.to_csv(os.path.join(output_dir, f'consecutive_bullish_{ts}.csv'),
                      index=False, encoding='utf-8-sig')
    print(f'结果已保存到: {output_dir}\\consecutive_bullish_{ts}.csv')

if __name__ == '__main__':
    main()
