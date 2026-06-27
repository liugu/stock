#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI增强选股系统
整合：传统因子 + 机器学习特征 + 策略评分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入因子模块
from ai_factor_mining import (
    calculate_technical_factors,
    calculate_ml_features,
    strategy_ml_enhanced
)

# ============ 配置 ============

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'charset': 'utf8mb4',
    'port': 3306
}

# 选股配置
STOCK_FILTER = {
    'min_amount': 100000000,  # 最小成交额 1亿
    'min_turnover': 3,        # 最小换手率 3%
    'pe_range': (0, 100),     # PE 范围
}

# ============ 数据获取 ============

def get_stock_list_akshare():
    """使用 akshare 获取股票列表"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        df = df[['代码', '名称', '最新价', '涨跌幅', '换手率', '成交量', '成交额', '市盈率-动态']]
        df.columns = ['code', 'name', 'price', 'pct_change', 'turnover', 'volume', 'amount', 'pe']
        
        # 应用筛选条件
        df = df[
            (df['turnover'] > STOCK_FILTER['min_turnover']) &
            (df['amount'] > STOCK_FILTER['min_amount']) &
            (df['pe'] > STOCK_FILTER['pe_range'][0]) &
            (df['pe'] < STOCK_FILTER['pe_range'][1])
        ]
        
        return df
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return None

def get_stock_history_akshare(code, days=120):
    """使用 akshare 获取历史数据"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
        df = df.tail(days)
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover']
        return df
    except Exception as e:
        return None

# ============ 综合评分策略 ============

def comprehensive_score(df):
    """
    综合评分系统
    返回：总分, 各项得分详情
    """
    if df is None or len(df) < 60:
        return 0, {}
    
    # 计算因子
    df = calculate_ml_features(df)
    if df is None:
        return 0, {}
    
    latest = df.iloc[-1]
    scores = {}
    
    # 1. 动量得分 (0-20分)
    momentum = latest.get('momentum_10d', 0)
    if momentum > 0.1:
        scores['momentum'] = 20
    elif momentum > 0.05:
        scores['momentum'] = 15
    elif momentum > 0:
        scores['momentum'] = 10
    elif momentum > -0.05:
        scores['momentum'] = 5
    else:
        scores['momentum'] = 0
    
    # 2. 趋势得分 (0-20分)
    ma5 = latest.get('ma5', 0)
    ma10 = latest.get('ma10', 0)
    ma20 = latest.get('ma20', 0)
    ma60 = latest.get('ma60', 0)
    
    trend_score = 0
    if ma5 > ma20:
        trend_score += 10
    if ma10 > ma20:
        trend_score += 5
    if ma20 > ma60:
        trend_score += 5
    scores['trend'] = trend_score
    
    # 3. 量能得分 (0-15分)
    volume_ratio = latest.get('volume_ratio', 0)
    if volume_ratio > 2:
        scores['volume'] = 15
    elif volume_ratio > 1.5:
        scores['volume'] = 12
    elif volume_ratio > 1:
        scores['volume'] = 8
    else:
        scores['volume'] = 0
    
    # 4. 位置得分 (0-15分)
    price_position = latest.get('price_position', 0)
    if price_position > 0.8:
        scores['position'] = 15
    elif price_position > 0.6:
        scores['position'] = 10
    elif price_position > 0.4:
        scores['position'] = 5
    else:
        scores['position'] = 0
    
    # 5. 波动得分 (0-10分)
    volatility = latest.get('volatility_10d', 0)
    if 0.02 < volatility < 0.04:
        scores['volatility'] = 10
    elif 0.015 < volatility < 0.05:
        scores['volatility'] = 7
    else:
        scores['volatility'] = 3
    
    # 6. 突破得分 (0-20分)
    high_20d = latest.get('high_20d', 0)
    close = latest.get('close', 0)
    
    if close >= high_20d * 0.98:
        scores['breakout'] = 20
    elif close >= high_20d * 0.95:
        scores['breakout'] = 15
    elif close >= high_20d * 0.90:
        scores['breakout'] = 10
    else:
        scores['breakout'] = 0
    
    # 总分
    total = sum(scores.values())
    
    return total, scores

# ============ 选股主流程 ============

def run_stock_selection(limit=50, top_n=10):
    """
    执行选股
    limit: 筛选股票数量上限
    top_n: 返回前N只股票
    """
    print("=" * 60)
    print(f"AI增强选股系统 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 1. 获取股票列表
    print("\n[1/3] 获取股票列表...")
    stocks = get_stock_list_akshare()
    if stocks is None or len(stocks) == 0:
        print("✗ 无法获取股票数据")
        return []
    
    stocks = stocks.head(limit)
    print(f"筛选出 {len(stocks)} 只股票")
    
    # 2. 计算因子和评分
    print("\n[2/3] 计算AI因子评分...")
    results = []
    
    for idx, row in stocks.iterrows():
        code = row['code']
        name = row['name']
        
        # 获取历史数据
        hist = get_stock_history_akshare(code, days=80)
        if hist is None or len(hist) < 60:
            continue
        
        # 计算评分
        total_score, detail_scores = comprehensive_score(hist)
        
        if total_score >= 40:  # 最低40分入选
            results.append({
                'code': code,
                'name': name,
                'price': row['price'],
                'pct_change': row['pct_change'],
                'turnover': row['turnover'],
                'pe': row['pe'],
                'score': total_score,
                'detail': detail_scores
            })
    
    # 3. 排序输出
    print("\n[3/3] 选股完成")
    results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_n]
    
    return results

# ============ 结果输出 ============

def format_results(results):
    """格式化输出结果"""
    if not results:
        return "今日无符合条件的股票"
    
    output = []
    output.append("\n" + "=" * 60)
    output.append("【AI增强选股结果】")
    output.append("=" * 60)
    
    for i, r in enumerate(results, 1):
        output.append(f"\n【{i}. {r['name']}】({r['code']})")
        output.append(f"  价格: {r['price']}元, 涨幅: +{r['pct_change']}%, 换手率: {r['turnover']}%")
        output.append(f"  综合评分: {r['score']}/100")
        
        detail = r['detail']
        output.append(f"  因子详情:")
        output.append(f"    动量: {detail.get('momentum', 0)}/20")
        output.append(f"    趋势: {detail.get('trend', 0)}/20")
        output.append(f"    量能: {detail.get('volume', 0)}/15")
        output.append(f"    位置: {detail.get('position', 0)}/15")
        output.append(f"    波动: {detail.get('volatility', 0)}/10")
        output.append(f"    突破: {detail.get('breakout', 0)}/20")
    
    return "\n".join(output)

# ============ 主程序 ============

def main():
    """主程序"""
    results = run_stock_selection(limit=100, top_n=10)
    print(format_results(results))
    return results

if __name__ == '__main__':
    main()
