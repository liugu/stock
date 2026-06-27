#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI因子挖掘模块
整合 Microsoft Qlib 进行因子生成与机器学习选股
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============ 1. 传统技术因子 ============

def calculate_technical_factors(df):
    """计算传统技术因子"""
    if df is None or len(df) < 60:
        return None
    
    df = df.copy()
    
    # 价格因子
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    df['return_20d'] = df['close'].pct_change(20)
    
    # 均线因子
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    df['ma5_ma20'] = df['ma5'] / df['ma20'] - 1  # 短期均线相对位置
    df['price_ma20'] = df['close'] / df['ma20'] - 1  # 价格相对均线位置
    
    # 波动因子
    df['volatility_10d'] = df['return_1d'].rolling(10).std()
    df['volatility_20d'] = df['return_1d'].rolling(20).std()
    
    # 成交量因子
    df['volume_ma5'] = df['volume'].rolling(5).mean()
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma5']
    
    # 动量因子
    df['momentum_5d'] = df['close'] / df['close'].shift(5) - 1
    df['momentum_10d'] = df['close'] / df['close'].shift(10) - 1
    df['momentum_20d'] = df['close'] / df['close'].shift(20) - 1
    
    # 价格位置因子
    df['high_20d'] = df['high'].rolling(20).max()
    df['low_20d'] = df['low'].rolling(20).min()
    df['price_position'] = (df['close'] - df['low_20d']) / (df['high_20d'] - df['low_20d'])
    
    # 振幅因子
    df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1)
    df['amplitude_ma5'] = df['amplitude'].rolling(5).mean()
    
    return df

# ============ 2. Qlib 因子接口 ============

def init_qlib():
    """初始化 Qlib"""
    try:
        import qlib
        from qlib.config import REG_CN
        
        # 初始化 Qlib（使用内置数据）
        qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region=REG_CN)
        print("✓ Qlib 初始化成功")
        return True
    except ImportError:
        print("✗ Qlib 未安装，请运行: pip install pyqlib")
        return False
    except Exception as e:
        print(f"✗ Qlib 初始化失败: {e}")
        return False

def get_qlib_factors(stock_code, start_date, end_date):
    """使用 Qlib 获取因子数据"""
    try:
        from qlib.data import D
        from qlib.data.dataset import DatasetH
        from qlib.contrib.data.handler import Alpha360
        
        # 获取股票数据
        instruments = [stock_code]
        
        # 使用 Alpha360 因子集（360个技术因子）
        dataset = DatasetH(
            handler={
                "class": "Alpha360",
                "module_path": "qlib.contrib.data.handler",
                "kwargs": {
                    "start_time": start_date,
                    "end_time": end_date,
                    "instruments": instruments,
                },
            }
        )
        
        # 获取因子数据
        factor_data = dataset.prepare("train")
        return factor_data
        
    except Exception as e:
        print(f"Qlib 因子获取失败: {e}")
        return None

# ============ 3. 机器学习因子 ============

def calculate_ml_features(df):
    """计算机器学习特征"""
    if df is None or len(df) < 60:
        return None
    
    df = df.copy()
    
    # 技术指标特征
    df = calculate_technical_factors(df)
    
    # 滞后特征（过去N天的数据）
    for lag in [1, 2, 3, 5, 10]:
        df[f'close_lag{lag}'] = df['close'].shift(lag)
        df[f'volume_lag{lag}'] = df['volume'].shift(lag)
        df[f'return_lag{lag}'] = df['return_1d'].shift(lag)
    
    # 滚动统计特征
    for window in [5, 10, 20]:
        df[f'return_mean_{window}'] = df['return_1d'].rolling(window).mean()
        df[f'return_std_{window}'] = df['return_1d'].rolling(window).std()
        df[f'return_skew_{window}'] = df['return_1d'].rolling(window).skew()
        df[f'volume_mean_{window}'] = df['volume'].rolling(window).mean()
    
    # 交互特征
    df['price_volume_corr'] = df['close'].rolling(10).corr(df['volume'])
    df['return_volume_corr'] = df['return_1d'].rolling(10).corr(df['volume'])
    
    return df

# ============ 4. 因子评估 ============

def evaluate_factor_ic(factor_values, returns):
    """
    评估因子的IC值（信息系数）
    IC = corr(因子值, 未来收益率)
    """
    from scipy.stats import spearmanr
    
    # 移除 NaN
    valid_mask = ~(factor_values.isna() | returns.isna())
    factor_clean = factor_values[valid_mask]
    returns_clean = returns[valid_mask]
    
    if len(factor_clean) < 10:
        return None
    
    # 计算 Spearman 相关系数
    ic, p_value = spearmanr(factor_clean, returns_clean)
    
    return {
        'ic': ic,
        'p_value': p_value,
        'sample_size': len(factor_clean)
    }

# ============ 5. 因子筛选 ============

def select_stocks_by_factors(stock_list, factor_func, top_n=10):
    """
    基于因子选股
    factor_func: 因子计算函数，返回因子值
    """
    results = []
    
    for stock in stock_list:
        try:
            # 计算因子
            factor_value = factor_func(stock)
            if factor_value is not None:
                results.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'factor_value': factor_value
                })
        except Exception as e:
            continue
    
    # 按因子值排序
    results = sorted(results, key=lambda x: x['factor_value'], reverse=True)
    
    return results[:top_n]

# ============ 6. 示例策略 ============

def strategy_ml_enhanced(df, lookback=20):
    """
    机器学习增强策略
    综合多个因子进行选股
    """
    if df is None or len(df) < lookback + 10:
        return False, {}
    
    df = calculate_ml_features(df)
    if df is None:
        return False, {}
    
    # 获取最新因子值
    latest = df.iloc[-1]
    
    # 因子评分
    scores = []
    
    # 因子1: 动量
    if latest['momentum_10d'] > 0.05:
        scores.append(1)
    elif latest['momentum_10d'] > 0:
        scores.append(0.5)
    
    # 因子2: 价格位置
    if latest['price_position'] > 0.8:
        scores.append(1)
    elif latest['price_position'] > 0.5:
        scores.append(0.5)
    
    # 因子3: 量比
    if latest['volume_ratio'] > 1.5:
        scores.append(1)
    elif latest['volume_ratio'] > 1:
        scores.append(0.5)
    
    # 因子4: 均线多头
    if latest['ma5'] > latest['ma20'] and latest['ma10'] > latest['ma20']:
        scores.append(1)
    
    # 因子5: 波动率适中
    if 0.02 < latest['volatility_10d'] < 0.05:
        scores.append(0.5)
    
    total_score = sum(scores)
    
    # 综合判断
    is_buy = total_score >= 3
    
    info = {
        'score': total_score,
        'momentum_10d': round(latest['momentum_10d'] * 100, 2),
        'price_position': round(latest['price_position'], 2),
        'volume_ratio': round(latest['volume_ratio'], 2),
        'ma5_ma20': round(latest['ma5_ma20'] * 100, 2),
        'volatility': round(latest['volatility_10d'], 4)
    }
    
    return is_buy, info

# ============ 7. 主程序 ============

def main():
    """测试因子模块"""
    print("=" * 60)
    print("AI因子挖掘模块测试")
    print("=" * 60)
    
    # 测试 Qlib
    print("\n[1] 检查 Qlib 状态...")
    qlib_ready = init_qlib()
    
    if qlib_ready:
        print("\n[2] 测试 Qlib 因子...")
        factors = get_qlib_factors('000001.SZ', '2024-01-01', '2024-12-31')
        if factors is not None:
            print(f"获取到 {factors.shape[1]} 个因子")
    
    print("\n[3] 测试传统因子计算...")
    import akshare as ak
    try:
        df = ak.stock_zh_a_hist(symbol='000001', period='daily', adjust='qfq')
        df = df.tail(100)
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover']
        
        # 计算因子
        df_with_factors = calculate_ml_features(df)
        
        if df_with_factors is not None:
            print(f"✓ 计算了 {len(df_with_factors.columns)} 个特征")
            
            # 测试策略
            is_buy, info = strategy_ml_enhanced(df_with_factors)
            print(f"\n策略信号: {'买入' if is_buy else '观望'}")
            print(f"因子评分: {info}")
    except Exception as e:
        print(f"测试失败: {e}")
    
    return True

if __name__ == '__main__':
    main()
