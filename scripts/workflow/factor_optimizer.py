#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子评估与优化模块
计算因子IC值、分组收益、因子权重优化
"""

import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

# ============ 因子评估 ============

def calculate_factor_ic(factor_values, returns):
    """
    计算因子IC值（信息系数）
    
    Args:
        factor_values: 因子值序列
        returns: 未来收益率序列
    
    Returns:
        ic: IC值
        p_value: 显著性P值
    """
    # 移除NaN
    valid_mask = ~(pd.isna(factor_values) | pd.isna(returns))
    factor_clean = factor_values[valid_mask]
    returns_clean = returns[valid_mask]
    
    if len(factor_clean) < 10:
        return 0, 1
    
    # Spearman相关系数
    ic, p_value = spearmanr(factor_clean, returns_clean)
    
    return ic, p_value

def evaluate_factors(factor_df, return_col='future_return', factor_cols=None):
    """
    批量评估多个因子
    
    Args:
        factor_df: 包含因子和收益的DataFrame
        return_col: 收益列名
        factor_cols: 因子列名列表
    
    Returns:
        DataFrame: 因子评估结果
    """
    if factor_cols is None:
        # 自动识别因子列（排除收益列和元数据列）
        exclude_cols = [return_col, 'code', 'name', 'date', 'group']
        factor_cols = [c for c in factor_df.columns if c not in exclude_cols]
    
    results = []
    for factor in factor_cols:
        if factor not in factor_df.columns:
            continue
        
        ic, p_value = calculate_factor_ic(factor_df[factor], factor_df[return_col])
        
        # 因子方向（IC>0为正向因子）
        direction = '正向' if ic > 0 else '反向'
        
        # 显著性
        significance = '显著' if p_value < 0.05 else '不显著'
        
        results.append({
            'factor': factor,
            'ic': round(ic, 4),
            'p_value': round(p_value, 4),
            'direction': direction,
            'significance': significance,
            'abs_ic': abs(ic)
        })
    
    return pd.DataFrame(results).sort_values('abs_ic', ascending=False)

# ============ 因子分组收益 ============

def calculate_group_returns(factor_df, factor_col, return_col='future_return', n_groups=5):
    """
    计算因子分组收益
    
    Args:
        factor_df: 因子数据
        factor_col: 因子列名
        return_col: 收益列名
        n_groups: 分组数量
    
    Returns:
        DataFrame: 各组平均收益
    """
    df = factor_df.copy()
    
    # 按因子分组
    df['group'] = pd.qcut(df[factor_col], n_groups, labels=False, duplicates='drop')
    
    # 计算各组收益
    group_returns = df.groupby('group')[return_col].agg(['mean', 'std', 'count'])
    group_returns['group_name'] = [f'Q{i+1}' for i in range(len(group_returns))]
    
    # 多空收益
    if len(group_returns) >= 2:
        long_return = group_returns.iloc[-1]['mean']
        short_return = group_returns.iloc[0]['mean']
        group_returns['long_short'] = long_return - short_return
    
    return group_returns

# ============ 因子权重优化 ============

def optimize_factor_weights(factor_df, factor_cols, return_col='future_return'):
    """
    基于IC值优化因子权重
    
    Args:
        factor_df: 因子数据
        factor_cols: 因子列名列表
        return_col: 收益列名
    
    Returns:
        dict: 因子权重
    """
    # 评估各因子
    factor_eval = evaluate_factors(factor_df, return_col, factor_cols)
    
    # 只使用显著因子
    significant_factors = factor_eval[factor_eval['significance'] == '显著']
    
    if len(significant_factors) == 0:
        # 如果没有显著因子，使用所有因子
        significant_factors = factor_eval.head(5)
    
    # 基于IC绝对值加权
    total_ic = significant_factors['abs_ic'].sum()
    
    weights = {}
    for _, row in significant_factors.iterrows():
        weight = row['abs_ic'] / total_ic if total_ic > 0 else 1 / len(significant_factors)
        # 考虑因子方向
        if row['ic'] < 0:
            weight = -weight
        weights[row['factor']] = weight
    
    return weights

# ============ 因子组合 ============

def combine_factors(factor_df, weights):
    """
    组合多个因子
    
    Args:
        factor_df: 因子数据
        weights: 因子权重字典
    
    Returns:
        Series: 组合因子值
    """
    combined = pd.Series(0, index=factor_df.index)
    
    for factor, weight in weights.items():
        if factor in factor_df.columns:
            # 标准化因子
            factor_std = (factor_df[factor] - factor_df[factor].mean()) / (factor_df[factor].std() + 1e-8)
            combined += factor_std * weight
    
    return combined

# ============ 因子监控 ============

def monitor_factor_decay(factor_values_history, returns_history, window=20):
    """
    监控因子IC衰减
    
    Args:
        factor_values_history: 因子历史值列表
        returns_history: 收益历史列表
        window: 滚动窗口
    
    Returns:
        DataFrame: IC时间序列
    """
    ics = []
    dates = []
    
    for i in range(window, len(factor_values_history)):
        factor_window = factor_values_history[i-window:i]
        return_window = returns_history[i-window:i]
        
        ic, _ = calculate_factor_ic(factor_window, return_window)
        
        ics.append(ic)
        dates.append(i)  # 或实际日期
    
    return pd.DataFrame({'date': dates, 'ic': ics})

# ============ 使用示例 ============

def demo_factor_evaluation():
    """演示因子评估流程"""
    print("=" * 60)
    print("因子评估与优化演示")
    print("=" * 60)
    
    # 生成模拟数据
    np.random.seed(42)
    n = 100
    
    data = {
        'code': [f'{600000+i:06d}' for i in range(n)],
        'momentum': np.random.randn(n) * 0.1,
        'vol_ratio': np.random.randn(n) * 0.5 + 1,
        'price_pos': np.random.rand(n),
        'rsi': np.random.randn(n) * 10 + 50,
        'future_return': np.random.randn(n) * 0.05
    }
    
    # 让动量和价格位置因子有预测能力
    data['future_return'] += data['momentum'] * 0.3
    data['future_return'] += (data['price_pos'] - 0.5) * 0.1
    
    df = pd.DataFrame(data)
    
    # 1. 评估因子
    print("\n[1] 因子IC评估:")
    factor_eval = evaluate_factors(df)
    print(factor_eval.to_string(index=False))
    
    # 2. 分组收益
    print("\n[2] 因子分组收益:")
    for factor in ['momentum', 'price_pos']:
        print(f"\n{factor}:")
        group_returns = calculate_group_returns(df, factor)
        print(group_returns.to_string())
    
    # 3. 优化权重
    print("\n[3] 因子权重优化:")
    weights = optimize_factor_weights(df, ['momentum', 'vol_ratio', 'price_pos', 'rsi'])
    for factor, weight in weights.items():
        print(f"  {factor}: {weight:.4f}")
    
    # 4. 组合因子
    print("\n[4] 组合因子评估:")
    df['combined'] = combine_factors(df, weights)
    combined_ic, combined_p = calculate_factor_ic(df['combined'], df['future_return'])
    print(f"  组合因子IC: {combined_ic:.4f}")
    print(f"  P值: {combined_p:.4f}")
    
    return df, weights

# ============ 主程序 ============

def main():
    """主程序"""
    return demo_factor_evaluation()

if __name__ == '__main__':
    main()
