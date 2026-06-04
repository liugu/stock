#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
批量下载历史K线数据
- 支持多数据源自动切换
- 支持断点续传
- 保存到缓存目录
"""
import os
import sys
import time
import pickle
import gzip
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

# 清除代理环境变量
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    if key in os.environ:
        del os.environ[key]

# 添加项目路径
sys.path.insert(0, '/home/liugu/workspace/stock')

from instock.core.crawling.data_adapter import get_stock_hist, get_stock_spot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path('/home/liugu/workspace/stock/instock/cache/hist')

def get_trade_dates(start_date: str, end_date: str) -> list:
    """获取交易日列表（简化版，排除周末）"""
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates = []
    current = start
    while current <= end:
        # 排除周末
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    return dates

def save_hist_data(symbol: str, df: pd.DataFrame, trade_date: str):
    """保存历史数据到缓存"""
    if df.empty:
        return
    
    # 确定年月子目录
    year_month = trade_date[:6]
    cache_path = CACHE_DIR / year_month / trade_date
    cache_path.mkdir(parents=True, exist_ok=True)
    
    # 保存为gzip压缩的pickle
    file_path = cache_path / f'{symbol}qfq.gzip.pickle'
    with gzip.open(file_path, 'wb') as f:
        pickle.dump(df, f)

def download_all_stocks(days: int = 100, limit: int = None):
    """
    批量下载所有股票的历史数据
    
    :param days: 下载最近多少天的数据
    :param limit: 限制下载数量（测试用）
    """
    # 获取股票列表
    logger.info('获取股票列表...')
    df_spot = get_stock_spot()
    if df_spot.empty:
        logger.error('获取股票列表失败')
        return
    
    codes = df_spot['代码'].tolist()
    if limit:
        codes = codes[:limit]
    
    logger.info(f'共 {len(codes)} 只股票需要下载')
    
    # 计算日期范围
    end_date = date.today().strftime('%Y%m%d')
    start_date = (date.today() - timedelta(days=days*2)).strftime('%Y%m%d')  # 多算一些天
    
    success = 0
    failed = 0
    
    for i, code in enumerate(codes):
        try:
            # 获取历史数据
            df = get_stock_hist(code, start_date=start_date, end_date=end_date)
            
            if df.empty:
                failed += 1
                logger.warning(f'[{i+1}/{len(codes)}] {code}: 无数据')
            else:
                # 保存到缓存
                save_hist_data(code, df, end_date)
                success += 1
                logger.info(f'[{i+1}/{len(codes)}] {code}: {len(df)} 条')
            
            # 控制请求频率
            time.sleep(0.3)
            
        except Exception as e:
            failed += 1
            logger.error(f'[{i+1}/{len(codes)}] {code}: {e}')
    
    logger.info(f'下载完成: 成功 {success}, 失败 {failed}')

def download_recent_months(months: int = 6):
    """
    下载最近几个月的数据（按月份组织）
    """
    today = date.today()
    
    for i in range(months):
        # 计算月份
        month_date = today - timedelta(days=30*i)
        year_month = month_date.strftime('%Y%m')
        
        # 计算该月的起止日期
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(day=31)
        else:
            month_end = (month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1))
        
        # 如果是当前月，结束日期为今天
        if i == 0:
            month_end = today
        
        logger.info(f'下载 {year_month} 数据: {month_start} ~ {month_end}')
        
        # 获取股票列表
        df_spot = get_stock_spot()
        if df_spot.empty:
            continue
        
        codes = df_spot['代码'].tolist()
        success = 0
        
        start_str = month_start.strftime('%Y%m%d')
        end_str = month_end.strftime('%Y%m%d')
        
        for j, code in enumerate(codes):
            try:
                df = get_stock_hist(code, start_date=start_str, end_date=end_str)
                if not df.empty:
                    # 过滤出该月的数据
                    df['日期'] = pd.to_datetime(df['日期'])
                    df_month = df[(df['日期'] >= month_start) & (df['日期'] <= month_end)]
                    
                    if not df_month.empty:
                        save_hist_data(code, df_month, end_str)
                        success += 1
                
                if (j + 1) % 100 == 0:
                    logger.info(f'  [{j+1}/{len(codes)}] 已处理')
                
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f'  {code}: {e}')
        
        logger.info(f'{year_month} 完成: {success}/{len(codes)}')

def check_cache_status():
    """检查缓存状态"""
    logger.info('=== 缓存状态检查 ===')
    
    if not CACHE_DIR.exists():
        logger.warning('缓存目录不存在')
        return
    
    for year_month in sorted(CACHE_DIR.iterdir()):
        if year_month.is_dir():
            dates = list(year_month.iterdir())
            total_files = sum(len(list(d.iterdir())) for d in dates if d.is_dir())
            logger.info(f'{year_month.name}: {len(dates)} 个交易日, {total_files} 个文件')

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='批量下载历史K线数据')
    parser.add_argument('--days', type=int, default=100, help='下载最近多少天')
    parser.add_argument('--months', type=int, help='下载最近几个月')
    parser.add_argument('--limit', type=int, help='限制下载数量（测试用）')
    parser.add_argument('--check', action='store_true', help='检查缓存状态')
    
    args = parser.parse_args()
    
    if args.check:
        check_cache_status()
    elif args.months:
        download_recent_months(args.months)
    else:
        download_all_stocks(days=args.days, limit=args.limit)
