#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI增强选股系统 - 与现有策略整合
整合 InStock 现有策略 + AI因子评分 + Backtrader回测
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入现有策略模块
try:
    from instock.core.strategy import enter, turtle_trade, keep_increasing, breakthrough_platform
    from instock.core.strategy import new_high, parking_apron, low_backtrace_increase
    STRATEGY_MODULES = True
except ImportError:
    STRATEGY_MODULES = False
    print("警告: 无法导入现有策略模块")

# 导入AI因子模块
from ai_factor_mining import calculate_ml_features
from qlib_akshare_provider import calculate_qlib_style_factors

# ============ 整合评分系统 ============

def comprehensive_ai_score(df, include_strategies=True):
    """
    综合AI评分系统
    整合：传统策略信号 + AI因子评分 + Qlib风格因子
    """
    if df is None or len(df) < 60:
        return 0, {}
    
    scores = {}
    details = {}
    
    # ===== 1. AI因子评分 (40分) =====
    df_ai = calculate_ml_features(df)
    if df_ai is not None:
        latest = df_ai.iloc[-1]
        
        # 动量因子 (10分)
        momentum = latest.get('momentum_10d', 0)
        scores['momentum'] = min(10, max(0, momentum * 100 + 5))
        
        # 趋势因子 (10分)
        ma5 = latest.get('ma5', 0)
        ma20 = latest.get('ma20', 0)
        if ma5 > ma20:
            scores['trend'] = 10
        else:
            scores['trend'] = max(0, 10 * (ma5 / ma20 - 0.95) / 0.05) if ma20 > 0 else 0
        
        # 量能因子 (10分)
        vol_ratio = latest.get('volume_ratio', 1)
        scores['volume'] = min(10, max(0, (vol_ratio - 1) * 10))
        
        # 突破因子 (10分)
        price_pos = latest.get('price_position', 0)
        scores['breakout'] = min(10, price_pos * 10)
        
        details['ai_factors'] = {
            'momentum': round(momentum * 100, 2),
            'trend': round(ma5 / ma20 - 1, 4) if ma20 > 0 else 0,
            'volume_ratio': round(vol_ratio, 2),
            'price_position': round(price_pos, 2)
        }
    
    # ===== 2. Qlib风格因子 (30分) =====
    df_qlib = calculate_qlib_style_factors(df)
    if df_qlib is not None:
        latest = df_qlib.iloc[-1]
        
        # 收益率因子 (10分)
        ret_5d = latest.get('return_5d', 0)
        scores['return'] = min(10, max(-5, ret_5d * 50 + 5))
        
        # 波动因子 (10分)
        volatility = latest.get('volatility_10', 0)
        if 0.02 < volatility < 0.04:
            scores['volatility'] = 10
        else:
            scores['volatility'] = max(0, 10 - abs(volatility - 0.03) * 200)
        
        # RSI因子 (10分)
        rsi = latest.get('rsi_14', 50)
        if 40 < rsi < 60:
            scores['rsi'] = 10  # 中性区域最佳
        elif 30 < rsi < 70:
            scores['rsi'] = 7
        else:
            scores['rsi'] = max(0, 10 - abs(rsi - 50) / 10)
        
        details['qlib_factors'] = {
            'return_5d': round(ret_5d * 100, 2),
            'volatility': round(volatility, 4),
            'rsi': round(rsi, 2)
        }
    
    # ===== 3. 传统策略信号 (30分) =====
    if include_strategies and STRATEGY_MODULES:
        strategy_signals = {}
        
        # 准备数据格式
        df_strategy = df.copy()
        df_strategy['p_change'] = df_strategy['close'].pct_change() * 100
        df_strategy['date'] = pd.date_range(end=datetime.now(), periods=len(df_strategy))
        
        # 海龟交易信号
        try:
            turtle_signal = turtle_trade.check_enter(
                (datetime.now(),), df_strategy, threshold=20
            )
            if turtle_signal:
                scores['turtle'] = 10
                strategy_signals['turtle'] = '创20日新高'
        except:
            pass
        
        # 放量上涨信号
        try:
            enter_signal = enter.check_volume(
                (datetime.now(),), df_strategy, threshold=20
            )
            if enter_signal:
                scores['enter'] = 10
                strategy_signals['enter'] = '放量上涨'
        except:
            pass
        
        # 多周期新高
        try:
            new_high_signals = turtle_trade.check_enter_multi(
                (datetime.now(),), df_strategy, periods=[20, 60, 120]
            )
            for period, signal in new_high_signals.items():
                if signal:
                    scores[f'new_high_{period}'] = 10 / len(new_high_signals)
                    strategy_signals[f'new_high_{period}'] = f'创{period}日新高'
        except:
            pass
        
        details['strategies'] = strategy_signals
    
    # ===== 计算总分 =====
    total_score = sum(scores.values())
    details['scores'] = {k: round(v, 2) for k, v in scores.items()}
    details['total'] = round(total_score, 2)
    
    return total_score, details

# ============ 批量选股 ============

def run_ai_stock_selection(stock_data_list, top_n=10, min_score=50):
    """
    批量AI选股
    
    Args:
        stock_data_list: 股票数据列表 [(code, name, df), ...]
        top_n: 返回前N只股票
        min_score: 最低评分门槛
    """
    results = []
    
    for code, name, df in stock_data_list:
        try:
            score, details = comprehensive_ai_score(df)
            
            if score >= min_score:
                results.append({
                    'code': code,
                    'name': name,
                    'score': score,
                    'details': details
                })
        except Exception as e:
            continue
    
    # 按评分排序
    results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_n]
    
    return results

# ============ 与现有系统集成 ============

def integrate_with_instock():
    """
    与 InStock 系统集成示例
    """
    print("=" * 60)
    print("AI选股与InStock系统集成")
    print("=" * 60)
    
    # 模拟数据测试
    np.random.seed(42)
    n = 120
    
    # 创建多只股票数据
    stock_data_list = []
    for i in range(5):
        trend = np.random.choice([0.002, 0, -0.002])
        close = np.cumprod(1 + np.random.randn(n) * 0.02 + trend) * (10 + i)
        high = close * (1 + np.random.rand(n) * 0.02)
        low = close * (1 - np.random.rand(n) * 0.02)
        volume = np.random.randint(1000000, 5000000, n)
        
        df = pd.DataFrame({
            'open': close * 0.99,
            'close': close,
            'high': high,
            'low': low,
            'volume': volume,
            'amount': volume * close
        })
        
        stock_data_list.append((f'{600000+i:06d}', f'股票{i}', df))
    
    # 执行选股
    print("\n执行AI增强选股...")
    results = run_ai_stock_selection(stock_data_list, top_n=5, min_score=40)
    
    # 输出结果
    print(f"\n选出 {len(results)} 只股票:")
    for r in results:
        print(f"\n【{r['name']}】({r['code']})")
        print(f"  综合评分: {r['score']:.1f}")
        
        details = r['details']
        if 'ai_factors' in details:
            print(f"  AI因子: {details['ai_factors']}")
        if 'qlib_factors' in details:
            print(f"  Qlib因子: {details['qlib_factors']}")
        if 'strategies' in details and details['strategies']:
            print(f"  策略信号: {details['strategies']}")
    
    return results

# ============ 主程序 ============

def main():
    """主程序"""
    return integrate_with_instock()

if __name__ == '__main__':
    main()
