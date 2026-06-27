#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据同步脚本 - 优先使用 TickFlow，失败回退到 Baostock
功能：
1. TickFlow 优先（速度快，稳定性好）
2. Baostock 作为备用数据源
3. 自动检测数据缺失日期
4. 进度监控和错误日志

使用方法：
    python scripts/sync_data.py                    # 自动补齐缺失数据
    python scripts/sync_data.py --date 2026-06-17 # 更新指定日期
    python scripts/sync_data.py --status           # 查看数据状态
"""

import sys
import os

# 强制UTF-8输出
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pymysql
import pandas as pd
import numpy as np
import time
import baostock as bs
from datetime import datetime, timedelta, date
import logging

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

# TickFlow API Key
TICKFLOW_API_KEY = 'tk_0cf8a26efda5479ba2e97e97d7695895'

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'sync_data.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def convert_code_to_symbol(code):
    """将6位股票代码转换为 TickFlow 格式"""
    if code.startswith('6'):
        return f'{code}.SH'
    elif code.startswith('0') or code.startswith('3'):
        return f'{code}.SZ'
    elif code.startswith('8') or code.startswith('4'):
        return f'{code}.BJ'
    return None


def safe_float(val):
    """安全转换为浮点数"""
    try:
        if val is None or pd.isna(val):
            return 0.0
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    except:
        return 0.0


def get_stock_list():
    """获取股票列表"""
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
        ORDER BY code
    ''')
    stocks = {row[1]: {'id': row[0], 'name': row[2]} for row in cursor.fetchall()}
    conn.close()
    return stocks


def get_missing_stocks(target_date):
    """获取指定日期缺失数据的股票"""
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    sql = '''
        SELECT s.id, s.code, s.name FROM stock_info s
        WHERE (s.code LIKE "60%%" OR s.code LIKE "00%%" OR s.code LIKE "30%%")
        AND s.id NOT IN (SELECT stock_id FROM stock_daily WHERE date = %s)
        ORDER BY s.code
    '''
    cursor.execute(sql, (target_date,))
    missing = cursor.fetchall()
    conn.close()
    return missing


def update_with_tickflow(target_date, stocks_to_update):
    """使用 TickFlow 更新数据"""
    try:
        from tickflow import TickFlow
        tf = TickFlow(api_key=TICKFLOW_API_KEY)
    except ImportError:
        logger.warning("TickFlow 未安装，跳过")
        return 0, len(stocks_to_update)
    
    logger.info(f"[TickFlow] 开始更新 {len(stocks_to_update)} 只股票...")
    
    success = 0
    fail = 0
    start_time = time.time()
    
    for i, (stock_id, code, name) in enumerate(stocks_to_update, 1):
        symbol = convert_code_to_symbol(code)
        if not symbol:
            fail += 1
            continue
        
        try:
            df = tf.klines.get(symbol, period='1d', count=5, as_dataframe=True)
            
            if df is None or df.empty:
                fail += 1
                continue
            
            # 获取最新数据
            row = df.iloc[-1]
            trade_date = str(row['trade_date'])[:10]
            
            # 只写入目标日期的数据
            if trade_date != target_date:
                fail += 1
                continue
            
            # 计算涨跌幅
            close = safe_float(row['close'])
            prev_close = safe_float(df.iloc[-2]['close']) if len(df) > 1 else close
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 计算振幅
            high = safe_float(row['high'])
            low = safe_float(row['low'])
            amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
            
            # 写入数据库
            conn = pymysql.connect(**DB)
            cursor = conn.cursor()
            sql = '''
            INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
            volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
            amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)
            '''
            cursor.execute(sql, (
                stock_id, trade_date,
                safe_float(row['open']), close, high, low,
                safe_float(row.get('volume', 0)), safe_float(row.get('amount', 0)),
                change_pct, amplitude, 0.0
            ))
            conn.commit()
            conn.close()
            
            success += 1
            
        except Exception as e:
            fail += 1
        
        # 显示进度（每500只）
        if i % 500 == 0:
            elapsed = time.time() - start_time
            logger.info(f"[TickFlow] 进度: {i}/{len(stocks_to_update)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s")
        
        # TickFlow 限速：60次/分钟，每次请求至少间隔1秒
        time.sleep(1.0)
    
    elapsed = time.time() - start_time
    logger.info(f"[TickFlow] 完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.0f}s")
    
    return success, fail


def update_with_baostock(target_date, stocks_to_update):
    """使用 Baostock 更新数据"""
    logger.info(f"[Baostock] 开始更新 {len(stocks_to_update)} 只股票...")
    
    # 登录
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"[Baostock] 登录失败: {lg.error_msg}")
        return 0, len(stocks_to_update)
    
    logger.info("[Baostock] 登录成功")
    
    success = 0
    fail = 0
    start_time = time.time()
    
    for i, (stock_id, code, name) in enumerate(stocks_to_update, 1):
        # 转换代码格式
        if code.startswith(('600', '601', '603', '605', '688', '689')):
            bs_code = f'sh.{code}'
        else:
            bs_code = f'sz.{code}'
        
        try:
            # 查询数据（获取前后几天用于计算涨跌幅）
            start_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,turn",
                start_date=start_date,
                end_date=target_date,
                frequency="d",
                adjustflag="2"
            )
            
            if rs.error_code != '0':
                fail += 1
                continue
            
            # 整理数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                fail += 1
                continue
            
            # 只处理目标日期的数据
            row = None
            for d in data_list:
                if d[0] == target_date:
                    row = d
                    break
            
            if not row:
                fail += 1
                continue
            
            # 计算涨跌幅
            close = safe_float(row[5])
            prev_close = 0
            if len(data_list) > 1:
                for d in reversed(data_list):
                    if d[0] != target_date:
                        prev_close = safe_float(d[5])
                        break
            
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 计算振幅
            high = safe_float(row[3])
            low = safe_float(row[4])
            amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0
            
            # 写入数据库
            conn = pymysql.connect(**DB)
            cursor = conn.cursor()
            sql = '''
            INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
            volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
            amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)
            '''
            cursor.execute(sql, (
                stock_id, row[0],
                safe_float(row[2]), close, high, low,
                safe_float(row[6]), safe_float(row[7]),
                change_pct, amplitude, safe_float(row[8]) if row[8] else 0.0
            ))
            conn.commit()
            conn.close()
            
            success += 1
            
        except Exception as e:
            fail += 1
        
        # 显示进度
        if i % 100 == 0:
            elapsed = time.time() - start_time
            logger.info(f"[Baostock] 进度: {i}/{len(stocks_to_update)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s")
        
        # Baostock 不需要限速，但避免过快
        time.sleep(0.1)
    
    # 登出
    bs.logout()
    
    elapsed = time.time() - start_time
    logger.info(f"[Baostock] 完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.0f}s")
    
    return success, fail


def show_status():
    """显示数据状态"""
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 最新日期
    cursor.execute('SELECT MAX(date) FROM stock_daily')
    latest_date = cursor.fetchone()[0]
    
    # 数据总量
    cursor.execute('SELECT COUNT(*) FROM stock_daily')
    total = cursor.fetchone()[0]
    
    print('=' * 60)
    print('数据状态')
    print('=' * 60)
    print(f'最新日期: {latest_date}')
    print(f'数据总量: {total} 条')
    print()
    
    # 最近10天数据分布
    print('最近10天数据分布:')
    cursor.execute('''
        SELECT date, COUNT(*) as count 
        FROM stock_daily 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        status = '✓ 完整' if row[1] > 4800 else f'⚠ 不完整 ({row[1]}/~5000)'
        print(f'  {row[0]}: {row[1]} 条 {status}')
    
    print('=' * 60)
    
    conn.close()


def sync_date(target_date):
    """同步指定日期的数据"""
    logger.info('=' * 60)
    logger.info(f'开始同步 {target_date} 数据')
    logger.info('=' * 60)
    
    # 获取缺失的股票
    missing = get_missing_stocks(target_date)
    
    if not missing:
        logger.info(f'{target_date} 数据已完整，无需更新')
        return
    
    logger.info(f'缺失 {len(missing)} 只股票数据')
    
    # 第一步：使用 TickFlow 更新
    tf_success, tf_fail = update_with_tickflow(target_date, missing)
    
    # 第二步：使用 Baostock 补充缺失的
    still_missing = get_missing_stocks(target_date)
    
    if still_missing:
        logger.info(f'TickFlow 完成后仍有 {len(still_missing)} 只股票缺失，尝试 Baostock...')
        bs_success, bs_fail = update_with_baostock(target_date, still_missing)
    
    # 最终统计
    final_missing = get_missing_stocks(target_date)
    
    logger.info('=' * 60)
    logger.info('同步完成')
    logger.info('=' * 60)
    logger.info(f'最新日期: {target_date}')
    logger.info(f'剩余缺失: {len(final_missing)} 只')
    
    # 显示状态
    show_status()


def main():
    parser = argparse.ArgumentParser(description='股票数据同步工具')
    parser.add_argument('--date', type=str, help='指定更新日期 (YYYY-MM-DD)')
    parser.add_argument('--range', nargs=2, type=str, help='更新日期范围')
    parser.add_argument('--status', action='store_true', help='查看数据状态')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.date:
        sync_date(args.date)
    elif args.range:
        start_date = datetime.strptime(args.range[0], '%Y-%m-%d')
        end_date = datetime.strptime(args.range[1], '%Y-%m-%d')
        
        current_date = start_date
        while current_date <= end_date:
            sync_date(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
    else:
        # 自动检测缺失日期
        show_status()


if __name__ == '__main__':
    main()
