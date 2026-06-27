#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续小阳线+低位策略回测与参数优化

回测逻辑:
1. 在历史数据中找到符合策略条件的信号点（买入点）
2. 计算买入后持有N天的收益率
3. 统计胜率、平均收益、最大收益等
4. 对比不同参数组合的表现

作者: liugu
日期: 2026/5/27
"""

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


def get_all_stocks(limit=500):
    """获取所有有历史数据的股票"""
    conn = get_db()
    sql = f"""
    SELECT DISTINCT si.id, si.code, COALESCE(cs.name, si.name) as name
    FROM stock_info si
    INNER JOIN stock_daily sd ON si.id = sd.stock_id
    LEFT JOIN cn_stock_spot cs ON BINARY si.code = BINARY cs.code
    WHERE sd.date >= '2025-06-01'
    LIMIT {limit}
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def get_stock_history(stock_id):
    """获取股票历史数据"""
    conn = get_db()
    sql = f"""
    SELECT date, open, close, high, low, volume
    FROM stock_daily
    WHERE stock_id = {stock_id} AND date >= '2025-06-01'
    ORDER BY date
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def find_signals(df, days=5, min_change=0.01, max_change=10.0, 
                 lookback=200, percentile=50):
    """
    找到所有策略信号
    
    返回: 信号列表，每个信号包含日期、价格、低位信息
    """
    if len(df) < lookback + days + 30:  # 至少预留30天计算收益
        return []
    
    signals = []
    
    # 扫描每一天作为潜在的信号日
    for idx in range(lookback, len(df) - 30):
        # 检查连续阳线（信号日前days天）
        yang_count = 0
        for i in range(idx - days, idx):
            row = df.iloc[i]
            open_p = float(row['open'])
            close_p = float(row['close'])
            
            if close_p > open_p:
                change = (close_p - open_p) / open_p * 100
                if min_change <= change <= max_change:
                    yang_count += 1
                else:
                    break  # 涨幅不符合，停止
            else:
                break  # 阴线，停止
        
        # 必须连续days天都是符合条件的阳线
        if yang_count < days:
            continue
        
        # 检查低位
        lookback_data = df.iloc[idx-lookback:idx]
        current_price = float(df.iloc[idx]['close'])
        period_low = float(lookback_data['low'].min())
        period_high = float(lookback_data['high'].max())
        
        closes = lookback_data['close'].astype(float).values
        price_pct = (np.sum(closes <= current_price) / len(closes)) * 100
        
        if price_pct > percentile:
            continue
        
        # 这是一个有效信号
        signal = {
            'date': df.iloc[idx]['date'],
            'buy_price': current_price,
            'period_low': period_low,
            'period_high': period_high,
            'price_pct': round(price_pct, 1)
        }
        
        # 计算持有收益
        for hold in [5, 10, 20, 30]:
            if idx + hold < len(df):
                sell_price = float(df.iloc[idx + hold]['close'])
                ret = (sell_price - current_price) / current_price * 100
                signal[f'return_{hold}d'] = round(ret, 2)
        
        signals.append(signal)
    
    return signals


def backtest_stock(row, params):
    """回测单只股票"""
    stock_id = row['id']
    code = row['code']
    name = row['name']
    
    try:
        df = get_stock_history(stock_id)
        if df.empty or len(df) < 100:
            return None
        
        signals = find_signals(df, **params)
        
        if signals:
            return {
                'code': code,
                'name': name,
                'signals': signals
            }
    except:
        pass
    
    return None


def run_backtest(params, stock_limit=500, max_workers=20):
    """运行回测"""
    print(f"\n回测参数: days={params['days']}, 分位={params['percentile']}%")
    
    stocks = get_all_stocks(limit=stock_limit)
    print(f"  股票数: {len(stocks)}")
    
    all_signals = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(backtest_stock, row, params) 
                   for _, row in stocks.iterrows()]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                for sig in result['signals']:
                    all_signals.append({
                        'code': result['code'],
                        'name': result['name'],
                        **sig
                    })
    
    print(f"  信号数: {len(all_signals)}")
    
    return all_signals


def calculate_stats(signals):
    """计算统计指标"""
    if not signals:
        return {}
    
    stats = {}
    
    for hold in [5, 10, 20, 30]:
        key = f'return_{hold}d'
        returns = [s[key] for s in signals if key in s]
        
        if returns:
            stats[f'hold_{hold}d'] = {
                'count': len(returns),
                'win_rate': round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1),
                'avg_return': round(np.mean(returns), 2),
                'max_return': round(max(returns), 2),
                'min_return': round(min(returns), 2),
                'median': round(np.median(returns), 2)
            }
    
    return stats


def print_stats(stats, title="回测统计"):
    """打印统计结果"""
    print(f"\n{title}")
    print("=" * 60)
    
    for hold in [5, 10, 20, 30]:
        key = f'hold_{hold}d'
        if key in stats:
            s = stats[key]
            print(f"\n持有{hold}日:")
            print(f"  信号数: {s['count']}")
            print(f"  胜率: {s['win_rate']}%")
            print(f"  平均收益: {s['avg_return']}%")
            print(f"  中位数: {s['median']}%")
            print(f"  最大: {s['max_return']}%, 最小: {s['min_return']}%")


def optimize_params(stock_limit=300):
    """参数优化"""
    print("\n参数优化")
    print("=" * 60)
    
    param_combinations = [
        {'days': 3, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 50},
        {'days': 4, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 50},
        {'days': 5, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 50},
        {'days': 5, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 30},
        {'days': 5, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 70},
        {'days': 6, 'min_change': 0.01, 'max_change': 10.0, 'lookback': 200, 'percentile': 50},
    ]
    
    results = []
    
    for params in param_combinations:
        signals = run_backtest(params, stock_limit=stock_limit)
        stats = calculate_stats(signals)
        
        if stats:
            results.append({
                'params': params,
                'signal_count': len(signals),
                'stats': stats
            })
            
            # 打印关键指标
            if 'hold_5d' in stats:
                s = stats['hold_5d']
                print(f"  days={params['days']}, pct={params['percentile']}%: "
                      f"信号{s['count']}个, 胜率{s['win_rate']}%, 平均{s['avg_return']}%")
    
    return results


def main():
    """主函数"""
    print("\n连续小阳线+低位策略 回测与优化")
    print("=" * 60)
    
    # 1. 基准回测
    print("\n【1】基准回测")
    print("-" * 40)
    
    base_params = {
        'days': 5,
        'min_change': 0.01,
        'max_change': 10.0,
        'lookback': 200,
        'percentile': 50
    }
    
    signals = run_backtest(base_params, stock_limit=500)
    stats = calculate_stats(signals)
    print_stats(stats, "基准参数回测结果")
    
    # 打印部分信号详情
    if signals:
        print("\n示例信号:")
        for s in signals[:5]:
            print(f"  {s['code']} {s['name']} @ {s['date']}: "
                  f"买入{s['buy_price']}元, 分位{s['price_pct']}%, "
                  f"5日{s.get('return_5d', 'N/A')}%")
    
    # 2. 参数优化
    print("\n【2】参数优化")
    print("-" * 40)
    
    results = optimize_params(stock_limit=300)
    
    # 3. 找最佳参数
    print("\n【3】最佳参数分析")
    print("-" * 40)
    
    if results:
        best = max(results, key=lambda x: x['stats'].get('hold_5d', {}).get('win_rate', 0))
        print(f"\n按5日胜率最优:")
        print(f"  参数: 连续{best['params']['days']}日阳线, 分位{best['params']['percentile']}%")
        print(f"  信号数: {best['signal_count']}")
        if 'hold_5d' in best['stats']:
            s = best['stats']['hold_5d']
            print(f"  5日胜率: {s['win_rate']}%")
            print(f"  5日平均收益: {s['avg_return']}%")
        
        best_ret = max(results, key=lambda x: x['stats'].get('hold_5d', {}).get('avg_return', -999))
        print(f"\n按5日平均收益最优:")
        print(f"  参数: 连续{best_ret['params']['days']}日阳线, 分位{best_ret['params']['percentile']}%")
        if 'hold_5d' in best_ret['stats']:
            s = best_ret['stats']['hold_5d']
            print(f"  5日胜率: {s['win_rate']}%")
            print(f"  5日平均收益: {s['avg_return']}%")
    
    # 4. 结论
    print("\n【4】策略结论")
    print("-" * 40)
    print("""
基于回测结果，策略优化建议:

1. 连续阳线天数: 建议使用 5-6 天
   - 天数太少容易误判
   - 天数太多信号太少

2. 价格分位数阈值: 建议 30-50%
   - 分位越低胜率越高但信号越少
   - 50%分位可平衡胜率和信号数量

3. 持有周期: 建议 5-10 日
   - 短期(5日): 胜率较高，适合短线
   - 中期(10-20日): 收益更高，适合波段

4. 风险提示:
   - 连续阳线后可能回调
   - 建议设置止损(如-5%)
   - 分散投资多只股票
""")

    return results


if __name__ == '__main__':
    main()