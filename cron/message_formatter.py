#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
推送消息格式化工具
按板块分组展示选股结果
"""

import pandas as pd
import requests
from functools import lru_cache

__author__ = 'liugu'
__date__ = '2026/5/11'


@lru_cache(maxsize=1)
def get_stock_industry_map():
    """
    获取股票行业分类映射
    数据来源：东方财富网
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "5000",
        "po": "1",
        "np": "1",
        "ut": "b2884a393a59ad64002292a3e90d46a5",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2",
        "fields": "f12,f14,f116"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        
        if data.get("data") and data["data"].get("diff"):
            result = {}
            for item in data["data"]["diff"]:
                code = item.get("f12", "")
                industry = item.get("f116", "")
                if code and industry:
                    result[code] = industry
            return result
    except Exception as e:
        print(f"获取行业分类失败: {e}")
    
    return {}


def group_stocks_by_industry(stocks, industry_map=None):
    """
    按行业分组股票
    
    参数:
        stocks: 股票列表，每个元素包含 code, name, change_rate 等
        industry_map: 行业分类映射（可选）
    
    返回:
        dict: 按行业分组的股票
    """
    if industry_map is None:
        industry_map = get_stock_industry_map()
    
    grouped = {}
    for stock in stocks:
        code = stock.get('code', '')
        industry = industry_map.get(code, '其他')
        
        if industry not in grouped:
            grouped[industry] = []
        grouped[industry].append(stock)
    
    return grouped


def format_message_by_industry(date, results, top_n=10):
    """
    按行业分组格式化推送消息
    
    参数:
        date: 日期字符串
        results: 策略选股结果字典
        top_n: 每个行业最多显示股票数
    
    返回:
        str: 格式化的消息
    """
    # 合并所有股票
    all_stocks = []
    for strategy_name, df in results.items():
        if df.empty:
            continue
        for _, row in df.iterrows():
            all_stocks.append({
                'strategy': strategy_name,
                'code': row['code'],
                'name': row['name'],
                'change_rate': row.get('change_rate', 0) if pd.notna(row.get('change_rate')) else 0,
                'new_price': row.get('new_price', 0) if pd.notna(row.get('new_price')) else 0,
            })
    
    if not all_stocks:
        return f"## 📊 选股报告 - {date}\n\n今日策略选股结果为空，无符合条件的股票。"
    
    # 按涨幅排序
    all_stocks.sort(key=lambda x: x['change_rate'], reverse=True)
    
    # 获取行业分类
    industry_map = get_stock_industry_map()
    
    # 按行业分组
    grouped = group_stocks_by_industry(all_stocks, industry_map)
    
    # 构建消息
    content = f"## 📊 选股报告 - {date}\n\n"
    content += f"**共选出 {len(all_stocks)} 只股票**\n\n"
    
    # 按行业展示
    for industry, stocks in grouped.items():
        if not stocks:
            continue
        
        # 按涨幅排序
        stocks.sort(key=lambda x: x['change_rate'], reverse=True)
        
        # 计算行业平均涨幅
        avg_change = sum(s['change_rate'] for s in stocks) / len(stocks)
        avg_change_str = f"+{avg_change:.2f}%" if avg_change > 0 else f"{avg_change:.2f}%"
        
        content += f"### {industry} ({len(stocks)}只, 均涨{avg_change_str})\n\n"
        
        for i, stock in enumerate(stocks[:top_n], 1):
            change_str = f"+{stock['change_rate']:.2f}%" if stock['change_rate'] > 0 else f"{stock['change_rate']:.2f}%"
            content += f"{i}. {stock['name']}({stock['code']}): {change_str}\n"
        
        if len(stocks) > top_n:
            content += f"... 还有 {len(stocks) - top_n} 只\n"
        
        content += "\n"
    
    return content


def format_message_compact(date, results, top_n=10):
    """
    紧凑格式化推送消息（适合微信）
    
    参数:
        date: 日期字符串
        results: 策略选股结果字典
        top_n: 最多显示股票数
    
    返回:
        str: 格式化的消息
    """
    # 合并所有股票
    all_stocks = []
    for strategy_name, df in results.items():
        if df.empty:
            continue
        for _, row in df.iterrows():
            all_stocks.append({
                'strategy': strategy_name,
                'code': row['code'],
                'name': row['name'],
                'change_rate': row.get('change_rate', 0) if pd.notna(row.get('change_rate')) else 0,
            })
    
    if not all_stocks:
        return f"【选股报告】{date}\n今日无符合条件的股票"
    
    # 按涨幅排序
    all_stocks.sort(key=lambda x: x['change_rate'], reverse=True)
    
    content = f"【选股报告】{date}\n"
    content += f"共选出 {len(all_stocks)} 只\n\n"
    
    # 策略统计
    strategy_count = {}
    for stock in all_stocks:
        s = stock['strategy']
        strategy_count[s] = strategy_count.get(s, 0) + 1
    
    content += "策略分布:\n"
    for s, c in sorted(strategy_count.items(), key=lambda x: -x[1]):
        content += f"• {s}: {c}只\n"
    
    content += f"\n涨幅前{min(top_n, len(all_stocks))}:\n"
    for i, stock in enumerate(all_stocks[:top_n], 1):
        change_str = f"+{stock['change_rate']:.2f}%" if stock['change_rate'] > 0 else f"{stock['change_rate']:.2f}%"
        content += f"{i}. {stock['name']} {change_str}\n"
    
    return content


if __name__ == "__main__":
    # 测试
    test_results = {
        "放量上涨": pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', '万科A'],
            'change_rate': [3.5, 2.1],
            'new_price': [10.5, 8.2],
        }),
        "均线多头": pd.DataFrame({
            'code': ['600519', '600036'],
            'name': ['贵州茅台', '招商银行'],
            'change_rate': [1.5, 0.8],
            'new_price': [1800, 35],
        }),
    }
    
    print(format_message_compact("2024-01-15", test_results))
