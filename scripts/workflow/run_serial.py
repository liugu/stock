#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串行执行数据更新和策略选股
避免 Windows 上的多线程问题
"""
import time
import datetime
import logging
import os.path
import sys

print('启动数据更新和策略选股...')

# 添加项目路径
cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
log_path = os.path.join(cpath_current, 'log')
if not os.path.exists(log_path):
    os.makedirs(log_path)
logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.join(log_path, 'stock_execute_job.log'))
logging.getLogger().setLevel(logging.INFO)

import instock.job.init_job as bj
import instock.job.basic_data_daily_job as hdj
import instock.job.basic_data_other_daily_job as hdtj
import instock.job.basic_data_after_close_daily_job as acdj
import instock.job.indicators_data_daily_job as gdj
import instock.job.strategy_data_daily_job as sdj
import instock.job.backtest_data_daily_job as bdj
import instock.job.klinepattern_data_daily_job as kdj
import instock.job.selection_data_daily_job as sddj
import instock.job.cpbd_data_daily_job as cdj

def main():
    start = time.time()
    _start = datetime.datetime.now()
    logging.info("######## 任务执行时间: %s #######" % _start.strftime("%Y-%m-%d %H:%M:%S.%f"))
    
    print("\n=== 第1步: 初始化数据库 ===")
    try:
        bj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第2.1步: 创建股票基础数据表 ===")
    try:
        hdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第2.2步: 创建综合股票数据表 ===")
    try:
        sddj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第3.1步: 创建股票其它基础数据表 ===")
    try:
        hdtj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第3.2步: 创建股票指标数据表 ===")
    try:
        gdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第4步: 创建股票K线形态表 ===")
    try:
        kdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第5步: 创建股票策略数据表（选股）===")
    try:
        sdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第6步: 创建股票回测 ===")
    try:
        bdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第7步: 创建操盘必读数据 ===")
    try:
        cdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n=== 第8步: 创建股票闭盘后数据 ===")
    try:
        acdj.main()
        print("✓ 完成")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    elapsed = time.time() - start
    logging.info("######## 完成任务, 使用时间: %s 秒 #######" % elapsed)
    print(f"\n{'='*60}")
    print(f"全部完成！总耗时: {elapsed:.1f} 秒")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
