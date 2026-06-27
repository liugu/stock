#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速选股脚本 - 直接运行策略选股，无需数据库表
"""
import logging
import sys
import os
from datetime import datetime
import pandas as pd

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from instock.core.crawling.data_adapter import get_stock_hist, get_stock_spot
from instock.core.strategy import enter, turtle_trade, new_high
from instock.core.stockfetch import is_a_stock, is_not_st

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_stocks():
    """获取股票列表和历史数据"""
    logger.info("获取股票列表...")
    df_spot = get_stock_spot()
    if df_spot.empty:
        logger.error("获取股票列表失败")
        return None
    
    # 过滤A股
    df_spot = df_spot[df_spot['代码'].apply(is_a_stock)]
    # 过滤ST
    df_spot = df_spot[df_spot['名称'].apply(is_not_st)]
    
    logger.info(f"共 {len(df_spot)} 只A股")
    return df_spot


def run_strategy(strategy_name, strategy_func, stocks_df, date):
    """运行单个策略"""
    logger.info(f"运行策略: {strategy_name}")
    results = []
    
    for idx, row in stocks_df.iterrows():
        code = row['代码']
        name = row['名称']
        
        # 获取历史数据
        df = get_stock_hist(code)
        if df.empty or len(df) < 30:
            continue
        
        try:
            # 调用策略检查
            if strategy_func((code, name), df, date=date):
                results.append({
                    'code': code,
                    'name': name,
                    'price': row['最新价'],
                    'change': row['涨跌幅']
                })
        except Exception as e:
            pass
    
    logger.info(f"{strategy_name}: 找到 {len(results)} 只股票")
    return results


def main():
    date = datetime.now()
    logger.info(f"选股日期: {date.strftime('%Y-%m-%d')}")
    
    # 获取股票列表
    stocks_df = fetch_stocks()
    if stocks_df is None:
        return
    
    # 运行策略
    all_results = {}
    
    # 放量上涨
    results = run_strategy("放量上涨", enter.check_volume, stocks_df, date)
    all_results["放量上涨"] = results
    
    # 海龟交易
    results = run_strategy("海龟交易", turtle_trade.check_enter, stocks_df, date)
    all_results["海龟交易"] = results
    
    # 创新高
    results = run_strategy("创新高", new_high.check, stocks_df, date)
    all_results["创新高"] = results
    
    # 输出结果
    print("\n" + "="*60)
    print(f"选股结果 ({date.strftime('%Y-%m-%d')})")
    print("="*60)
    
    for strategy, stocks in all_results.items():
        if stocks:
            print(f"\n【{strategy}】({len(stocks)}只)")
            for s in stocks[:10]:  # 最多显示10只
                print(f"  {s['code']} {s['name']:8s} 价格:{s['price']:.2f} 涨幅:{s['change']:.2f}%")
            if len(stocks) > 10:
                print(f"  ... 还有 {len(stocks)-10} 只")
    
    # 统计
    total = sum(len(v) for v in all_results.values())
    print(f"\n共选出 {total} 只股票")


if __name__ == '__main__':
    main()
