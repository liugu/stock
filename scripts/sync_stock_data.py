#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据同步脚本 - 统一管理股票数据更新
功能：
1. 自动检测数据缺失日期
2. 使用 Baostock 更新历史行情（支持会话恢复）
3. 支持指定日期范围更新
4. 进度监控和错误日志

使用方法：
    python scripts/sync_stock_data.py              # 自动补齐缺失数据
    python scripts/sync_stock_data.py --date 2026-06-03  # 更新指定日期
    python scripts/sync_stock_data.py --range 2026-06-01 2026-06-05  # 更新日期范围
    python scripts/sync_stock_data.py --status     # 查看数据状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pymysql
import pandas as pd
import numpy as np
import time
import baostock as bs
from datetime import datetime, timedelta, date
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'sync_stock_data.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BaostockSession:
    """Baostock 会话管理器 - 自动处理登录超时"""
    
    def __init__(self, session_timeout=120):
        self.logged_in = False
        self.login_time = 0
        self.session_timeout = session_timeout  # 2分钟会话超时
        self.query_count = 0
        
    def ensure_login(self):
        """确保登录状态有效"""
        current_time = time.time()
        
        # 如果超过会话时间，先登出再重新登录
        if self.logged_in and (current_time - self.login_time) > self.session_timeout:
            logger.info("[Baostock] 会话超时，重新登录...")
            try:
                bs.logout()
            except:
                pass
            self.logged_in = False
        
        if not self.logged_in:
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"[Baostock] 登录失败: {lg.error_msg}")
                return False
            self.logged_in = True
            self.login_time = current_time
            self.query_count = 0
            logger.info("[Baostock] 登录成功")
        
        return True
    
    def query(self, bs_code, start_date, end_date, max_retries=3):
        """带重试的查询"""
        for attempt in range(max_retries):
            try:
                # 确保登录
                if not self.ensure_login():
                    continue
                
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,code,open,high,low,close,volume,amount,turn,peTTM,pbMRQ",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="2"  # 前复权
                )
                
                self.query_count += 1
                
                if rs.error_code == '0':
                    return rs
                elif '未登录' in rs.error_msg or 'login' in rs.error_msg.lower():
                    # 会话过期，重新登录
                    self.logged_in = False
                    logger.warning(f"[Baostock] 会话过期，重试 ({attempt+1}/{max_retries})")
                    continue
                else:
                    logger.warning(f"[Baostock] 查询失败 {bs_code}: {rs.error_msg}")
                    return None
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logged_in = False
                    time.sleep(0.5)
                else:
                    logger.error(f"[Baostock] 查询异常 {bs_code}: {e}")
                    return None
        
        return None
    
    def logout(self):
        """登出"""
        if self.logged_in:
            try:
                bs.logout()
                logger.info(f"[Baostock] 登出成功，本次查询 {self.query_count} 次")
            except:
                pass
            self.logged_in = False


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB)


def get_stock_map():
    """获取股票代码映射"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE '60%' OR code LIKE '00%' OR code LIKE '30%'
        ORDER BY code
    ''')
    
    stock_map = {row[1]: {'id': row[0], 'name': row[2]} for row in cursor.fetchall()}
    conn.close()
    
    return stock_map


def get_data_status():
    """获取数据状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取最新日期
    cursor.execute("SELECT MAX(date) FROM stock_daily")
    latest_date = cursor.fetchone()[0]
    
    # 获取最近10天的数据分布
    cursor.execute("""
        SELECT date, COUNT(*) as cnt 
        FROM stock_daily 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 10
    """)
    daily_stats = cursor.fetchall()
    
    # 获取总数据量
    cursor.execute("SELECT COUNT(*) FROM stock_daily")
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'latest_date': latest_date,
        'total_count': total_count,
        'daily_stats': daily_stats
    }


def find_missing_dates(start_date=None, end_date=None):
    """查找缺失数据的日期"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取已有数据的日期
    cursor.execute("SELECT DISTINCT date FROM stock_daily ORDER BY date DESC LIMIT 60")
    existing_dates = set(row[0] for row in cursor.fetchall())
    
    # 获取交易日列表
    today = date.today()
    if start_date is None:
        start_date = today - timedelta(days=30)
    if end_date is None:
        end_date = today
    
    # 简化的交易日判断（排除周末）
    missing_dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 周一到周五
            if current not in existing_dates:
                missing_dates.append(current)
        current += timedelta(days=1)
    
    conn.close()
    
    return missing_dates


def update_single_date(target_date, stock_map, session):
    """更新单日数据"""
    target_date_str = target_date.strftime('%Y-%m-%d')
    
    # 获取前几天的数据用于计算涨跌幅
    start_date = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
    
    logger.info(f"开始更新 {target_date_str}，共 {len(stock_map)} 只股票")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    success = 0
    fail = 0
    no_data = 0
    start_time = time.time()
    
    # 检查已有数据
    cursor.execute("SELECT COUNT(*) FROM stock_daily WHERE date = ?", (target_date_str,))
    existing = cursor.fetchone()[0]
    
    if existing >= len(stock_map) * 0.9:  # 已有90%数据
        logger.info(f"{target_date_str} 已有 {existing} 条数据，跳过更新")
        conn.close()
        return existing, 0, 0
    
    for i, (code, info) in enumerate(stock_map.items(), 1):
        try:
            # 转换股票代码格式
            if code.startswith(('600', '601', '603', '605', '688', '689')):
                bs_code = f'sh.{code}'
            else:
                bs_code = f'sz.{code}'
            
            # 查询数据
            rs = session.query(bs_code, start_date, target_date_str)
            
            if rs is None:
                fail += 1
                continue
            
            # 整理数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                no_data += 1
                continue
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 找到目标日期的数据
            target_rows = df[df['date'] == target_date_str]
            
            if len(target_rows) == 0:
                no_data += 1
                continue
            
            row = target_rows.iloc[0]
            
            # 处理数据
            def safe_float(val):
                try:
                    if val is None or val == '' or val == '0.000':
                        return 0.0
                    f = float(val)
                    if np.isnan(f) or np.isinf(f):
                        return 0.0
                    return f
                except:
                    return 0.0
            
            # 计算涨跌幅
            prev_rows = df[df['date'] < target_date_str]
            if len(prev_rows) > 0:
                prev_close = safe_float(prev_rows.iloc[-1]['close'])
                curr_close = safe_float(row['close'])
                change_pct = (curr_close - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
            else:
                change_pct = 0.0
            
            # 计算振幅
            high = safe_float(row['high'])
            low = safe_float(row['low'])
            if len(prev_rows) > 0:
                prev_close = safe_float(prev_rows.iloc[-1]['close'])
                amplitude = (high - low) / prev_close * 100 if prev_close > 0 else 0.0
            else:
                amplitude = 0.0
            
            # 写入数据库
            sql = '''
            INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
            volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
            amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)
            '''
            
            cursor.execute(sql, (
                info['id'],
                target_date_str,
                safe_float(row['open']),
                safe_float(row['close']),
                safe_float(row['high']),
                safe_float(row['low']),
                safe_float(row['volume']),
                safe_float(row['amount']),
                change_pct,
                amplitude,
                safe_float(row['turn'])
            ))
            
            success += 1
            
            # 每100条提交一次
            if success % 100 == 0:
                conn.commit()
            
        except Exception as e:
            fail += 1
            if fail <= 10:
                logger.error(f"处理失败 {code}: {e}")
        
        # 进度显示
        if i % 500 == 0:
            elapsed = time.time() - start_time
            logger.info(f"进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 无数据:{no_data} 耗时:{elapsed:.0f}s")
    
    conn.commit()
    conn.close()
    
    elapsed = time.time() - start_time
    logger.info(f"完成 {target_date_str}: 成功 {success}, 失败 {fail}, 无数据 {no_data}, 耗时 {elapsed:.1f}s")
    
    return success, fail, no_data


def main():
    parser = argparse.ArgumentParser(description='股票数据同步工具')
    parser.add_argument('--date', type=str, help='更新指定日期 (YYYY-MM-DD)')
    parser.add_argument('--range', nargs=2, type=str, metavar=('START', 'END'), help='更新日期范围')
    parser.add_argument('--status', action='store_true', help='查看数据状态')
    parser.add_argument('--missing', action='store_true', help='查找缺失日期')
    
    args = parser.parse_args()
    
    # 查看状态
    if args.status:
        status = get_data_status()
        print("\n" + "=" * 60)
        print("数据状态")
        print("=" * 60)
        print(f"最新日期: {status['latest_date']}")
        print(f"数据总量: {status['total_count']} 条")
        print("\n最近10天数据分布:")
        for d, cnt in status['daily_stats']:
            print(f"  {d}: {cnt} 条")
        print("=" * 60)
        return
    
    # 查找缺失日期
    if args.missing:
        missing = find_missing_dates()
        print("\n" + "=" * 60)
        print(f"缺失数据的日期 ({len(missing)} 个)")
        print("=" * 60)
        for d in missing:
            print(f"  {d}")
        print("=" * 60)
        return
    
    # 确定要更新的日期
    dates_to_update = []
    
    if args.date:
        dates_to_update = [datetime.strptime(args.date, '%Y-%m-%d').date()]
    elif args.range:
        start = datetime.strptime(args.range[0], '%Y-%m-%d').date()
        end = datetime.strptime(args.range[1], '%Y-%m-%d').date()
        current = start
        while current <= end:
            if current.weekday() < 5:  # 排除周末
                dates_to_update.append(current)
            current += timedelta(days=1)
    else:
        # 自动检测缺失日期
        dates_to_update = find_missing_dates()
    
    if not dates_to_update:
        logger.info("没有需要更新的日期")
        return
    
    logger.info(f"计划更新 {len(dates_to_update)} 个日期: {dates_to_update}")
    
    # 获取股票列表
    stock_map = get_stock_map()
    logger.info(f"共 {len(stock_map)} 只股票")
    
    # 创建 Baostock 会话
    session = BaostockSession()
    
    # 更新每个日期
    total_success = 0
    total_fail = 0
    
    for target_date in dates_to_update:
        success, fail, _ = update_single_date(target_date, stock_map, session)
        total_success += success
        total_fail += fail
    
    # 登出
    session.logout()
    
    # 最终状态
    status = get_data_status()
    logger.info("\n" + "=" * 60)
    logger.info("同步完成")
    logger.info("=" * 60)
    logger.info(f"总成功: {total_success}, 总失败: {total_fail}")
    logger.info(f"最新日期: {status['latest_date']}")
    logger.info(f"数据总量: {status['total_count']} 条")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()