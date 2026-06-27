#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI量化选股系统 - 统一入口
快速使用各类功能

使用方法:
  python main.py --mode select        # 执行选股
  python main.py --mode backtest      # 执行回测
  python main.py --mode factor        # 因子分析
  python main.py --mode demo          # 演示模式
"""

import argparse
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_selection():
    """执行AI增强选股"""
    print("=" * 60)
    print("AI增强选股系统")
    print("=" * 60)
    
    from ai_integrated_selection import integrate_with_instock
    results = integrate_with_instock()
    
    return results

def run_backtest():
    """执行回测"""
    print("=" * 60)
    print("Backtrader回测系统")
    print("=" * 60)
    
    from backtest_professional import run_backtest
    
    # 演示回测
    print("\n回测演示 (使用模拟数据):")
    
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # 创建模拟数据
    np.random.seed(42)
    n = 250
    dates = pd.date_range(start='2023-01-01', periods=n)
    close = np.cumprod(1 + np.random.randn(n) * 0.02) * 10
    
    data = pd.DataFrame({
        'date': dates,
        'open': close * 0.99,
        'high': close * 1.02,
        'low': close * 0.98,
        'close': close,
        'volume': np.random.randint(1000000, 5000000, n)
    })
    
    print(f"数据范围: {data['date'].min().date()} ~ {data['date'].max().date()}")
    print(f"数据量: {len(data)} 条")
    
    # 简单回测统计
    total_return = (close[-1] / close[0] - 1) * 100
    max_drawdown = np.min(close / np.maximum.accumulate(close)) - 1
    
    print(f"\n回测结果:")
    print(f"  总收益率: {total_return:.2f}%")
    print(f"  最大回撤: {max_drawdown*100:.2f}%")
    
    return data

def run_factor_analysis():
    """执行因子分析"""
    print("=" * 60)
    print("因子分析与优化")
    print("=" * 60)
    
    from factor_optimizer import demo_factor_evaluation
    df, weights = demo_factor_evaluation()
    
    return df

def run_demo():
    """运行完整演示"""
    print("=" * 60)
    print("AI量化选股系统 - 完整演示")
    print("=" * 60)
    
    # 1. 因子计算演示
    print("\n[1] AI因子计算演示...")
    from ai_factor_mining import calculate_technical_factors, calculate_ml_features
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    n = 100
    close = np.cumprod(1 + np.random.randn(n) * 0.02 + 0.001) * 10
    df = pd.DataFrame({
        'close': close,
        'high': close * 1.02,
        'low': close * 0.98,
        'volume': np.random.randint(1000000, 5000000, n)
    })
    
    df_tech = calculate_technical_factors(df)
    df_ml = calculate_ml_features(df)
    print(f"   技术因子: 23个")
    print(f"   ML特征: {len(df_ml.columns) - len(df.columns)}个")
    
    # 2. Qlib因子演示
    print("\n[2] Qlib风格因子演示...")
    from qlib_akshare_provider import calculate_qlib_style_factors
    df_qlib = calculate_qlib_style_factors(df)
    print(f"   Qlib因子: {len(df_qlib.columns) - len(df.columns)}个")
    
    # 3. 因子评估演示
    print("\n[3] 因子IC评估...")
    from factor_optimizer import evaluate_factors
    
    # 创建带收益的数据
    df_eval = pd.DataFrame({
        'code': [f'{600000+i:06d}' for i in range(50)],
        'momentum': np.random.randn(50) * 0.1,
        'vol_ratio': np.random.randn(50) * 0.5 + 1,
        'price_pos': np.random.rand(50),
        'future_return': np.random.randn(50) * 0.05
    })
    
    factor_eval = evaluate_factors(df_eval)
    print(f"   评估因子: {len(factor_eval)}个")
    print(f"   显著因子: {len(factor_eval[factor_eval['significance'] == '显著'])}个")
    
    # 4. 选股演示
    print("\n[4] AI增强选股演示...")
    from ai_stock_selection import comprehensive_score
    
    score, details = comprehensive_score(df)
    print(f"   综合评分: {score}/100")
    print(f"   因子详情: {details}")
    
    # 5. 总结
    print("\n" + "=" * 60)
    print("系统功能总结:")
    print("  • AI因子: 75个 (技术23 + ML52)")
    print("  • Qlib因子: 45个")
    print("  • TA-Lib指标: 32个")
    print("  • 策略数量: 18种")
    print("  • 总因子数: 152个")
    print("=" * 60)
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI量化选股系统')
    parser.add_argument('--mode', type=str, default='demo',
                       choices=['select', 'backtest', 'factor', 'demo'],
                       help='运行模式')
    
    args = parser.parse_args()
    
    if args.mode == 'select':
        run_selection()
    elif args.mode == 'backtest':
        run_backtest()
    elif args.mode == 'factor':
        run_factor_analysis()
    else:
        run_demo()

if __name__ == '__main__':
    main()
