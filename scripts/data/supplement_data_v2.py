#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据补充脚本V2 - 带重试机制和延时

作者: Hermes
日期: 2026/5/29
"""

import sys
import os
import time
import pymysql
import pandas as pd
from datetime import datetime
import random

PROJECT_DIR = r'E:\量化研究\workspace\stock'
sys.path.insert(0, PROJECT_DIR)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def retry_call(func, max_retries=3, delay=2):
    """带重试的调用"""
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i < max_retries - 1:
                wait = delay * (i + 1) + random.uniform(0, 1)
                print(f"  重试 {i+1}/{max_retries}，等待 {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise e
    return None

def update_industry_info():
    """更新行业信息 - 分批次"""
    print("\n【更新行业信息】")
    print("-" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        import akshare as ak
        
        # 获取行业列表
        df_industries = retry_call(lambda: ak.stock_board_industry_name_em())
        
        if df_industries is None or df_industries.empty:
            print("✗ 获取行业列表失败")
            return
        
        print(f"共 {len(df_industries)} 个行业")
        
        updated = 0
        for idx, row in df_industries.iterrows():
            industry_name = row['板块名称']
            
            try:
                # 获取行业成分股
                df_stocks = retry_call(lambda: ak.stock_board_industry_cons_em(symbol=industry_name))
                
                if df_stocks is None or df_stocks.empty:
                    continue
                
                for _, stock in df_stocks.iterrows():
                    code = stock['代码']
                    
                    cur.execute("""
                        UPDATE stock_info SET industry = %s WHERE code = %s
                    """, (industry_name, code))
                    
                    if cur.rowcount > 0:
                        updated += 1
                
                conn.commit()
                
                # 随机延时，避免被封
                time.sleep(random.uniform(0.3, 0.8))
                
                if updated % 200 == 0:
                    print(f"  已更新 {updated} 条...")
                    
            except Exception as e:
                print(f"  行业 {industry_name} 失败: {e}")
                continue
        
        print(f"✓ 行业更新完成: {updated} 条")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def update_concept_info():
    """更新概念题材"""
    print("\n【更新概念题材】")
    print("-" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    
    # 清空旧数据
    cur.execute("TRUNCATE TABLE stock_concept")
    conn.commit()
    
    try:
        import akshare as ak
        
        # 获取概念列表
        df_concepts = retry_call(lambda: ak.stock_board_concept_name_em())
        
        if df_concepts is None or df_concepts.empty:
            print("✗ 获取概念列表失败")
            return
        
        print(f"共 {len(df_concepts)} 个概念")
        
        total = 0
        for idx, row in df_concepts.iterrows():
            concept_name = row['板块名称']
            
            try:
                # 获取概念成分股
                df_stocks = retry_call(lambda: ak.stock_board_concept_cons_em(symbol=concept_name))
                
                if df_stocks is None or df_stocks.empty:
                    continue
                
                for _, stock in df_stocks.iterrows():
                    cur.execute("""
                        INSERT INTO stock_concept (code, name, concept, concept_name)
                        VALUES (%s, %s, %s, %s)
                    """, (stock['代码'], stock['名称'], concept_name, concept_name))
                    total += 1
                
                conn.commit()
                
                time.sleep(random.uniform(0.2, 0.5))
                
                if total % 500 == 0:
                    print(f"  已插入 {total} 条...")
                    
            except Exception as e:
                continue
        
        print(f"✓ 概念题材完成: {total} 条")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def update_realtime_with_volume_ratio():
    """更新实时行情（包含量比）"""
    print("\n【更新实时行情】")
    print("-" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        import akshare as ak
        
        df = retry_call(lambda: ak.stock_zh_a_spot_em())
        
        if df is None or df.empty:
            print("✗ 获取实时行情失败")
            return
        
        latest_date = datetime.now().strftime('%Y-%m-%d')
        
        # 删除当日旧数据
        cur.execute("DELETE FROM cn_stock_spot WHERE date = %s", (latest_date,))
        
        insert_count = 0
        for _, row in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO cn_stock_spot 
                    (date, code, name, new_price, change_rate, turnoverrate, 
                     volume_ratio, deal_amount, amplitude, pe, total_market_cap)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    latest_date,
                    row['代码'],
                    row['名称'],
                    row['最新价'],
                    row['涨跌幅'],
                    row['换手率'],
                    row.get('量比', 0),
                    row['成交额'],
                    row['振幅'],
                    row.get('市盈率-动态', None),
                    row.get('总市值', None)
                ))
                insert_count += 1
            except:
                pass
        
        conn.commit()
        print(f"✓ 实时行情更新: {insert_count} 条")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def verify():
    """验证"""
    print("\n【验证结果】")
    print("-" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    
    # 行业
    cur.execute("SELECT COUNT(*) FROM stock_info WHERE industry IS NOT NULL AND industry != ''")
    has_industry = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stock_info")
    total = cur.fetchone()[0]
    print(f"stock_info 行业: {has_industry}/{total} ({has_industry/total*100:.1f}%)")
    
    # 概念
    cur.execute("SELECT COUNT(*) FROM stock_concept")
    cnt = cur.fetchone()[0]
    print(f"stock_concept: {cnt} 条")
    
    # 量比
    cur.execute("SELECT COUNT(*) FROM cn_stock_spot WHERE volume_ratio > 0")
    has_ratio = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cn_stock_spot")
    total = cur.fetchone()[0]
    print(f"cn_stock_spot 量比: {has_ratio}/{total} ({has_ratio/total*100:.1f}%)")
    
    # 行业分布
    print("\n【行业分布TOP10】")
    cur.execute("""
        SELECT industry, COUNT(*) as cnt 
        FROM stock_info 
        WHERE industry IS NOT NULL AND industry != ''
        GROUP BY industry 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}只")
    
    cur.close()
    conn.close()

def main():
    print("=" * 60)
    print("数据补充脚本 V2")
    print("=" * 60)
    
    # 1. 更新行业信息
    update_industry_info()
    
    # 2. 更新概念题材
    update_concept_info()
    
    # 3. 更新实时行情
    update_realtime_with_volume_ratio()
    
    # 4. 验证
    verify()
    
    print("\n完成!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()