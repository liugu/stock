#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据补充脚本 - 补充缺失的公司简介、概念题材、行业信息等

作者: Hermes
日期: 2026/5/29
"""

import sys
import os
import time
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime

# 项目路径
PROJECT_DIR = r'E:\量化研究\workspace\stock'
sys.path.insert(0, PROJECT_DIR)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def create_missing_tables():
    """创建缺失的表"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n【创建缺失表】")
    print("-" * 60)
    
    # 1. 公司简介表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_company (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) NOT NULL,
            name VARCHAR(50),
            industry VARCHAR(50),
            sector VARCHAR(50),
            area VARCHAR(50),
            list_date DATE,
            description TEXT,
            main_business TEXT,
            website VARCHAR(100),
            employees INT,
            chairman VARCHAR(50),
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_code (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✓ stock_company 表创建成功")
    
    # 2. 概念题材表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_concept (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) NOT NULL,
            name VARCHAR(50),
            concept VARCHAR(100),
            concept_name VARCHAR(100),
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_concept (concept)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✓ stock_concept 表创建成功")
    
    # 3. 给stock_info添加缺失字段
    try:
        cur.execute("ALTER TABLE stock_info ADD COLUMN list_date DATE")
        print("✓ stock_info 添加 list_date 字段")
    except:
        print("○ list_date 字段已存在")
    
    try:
        cur.execute("ALTER TABLE stock_info ADD COLUMN description TEXT")
        print("✓ stock_info 添加 description 字段")
    except:
        print("○ description 字段已存在")
    
    conn.commit()
    cur.close()
    conn.close()

def fetch_company_info_akshare():
    """使用akshare获取公司基本信息"""
    print("\n【获取公司基本信息】")
    print("-" * 60)
    
    try:
        import akshare as ak
        
        # 获取A股列表（包含行业信息）
        print("获取A股列表...")
        df_stock_list = ak.stock_info_a_code_name()
        
        # 获取行业分类
        print("获取行业分类...")
        try:
            df_industry = ak.stock_board_industry_name_em()
            print(f"  获取到 {len(df_industry)} 个行业板块")
        except Exception as e:
            print(f"  行业板块获取失败: {e}")
            df_industry = pd.DataFrame()
        
        # 获取概念板块
        print("获取概念板块...")
        try:
            df_concept = ak.stock_board_concept_name_em()
            print(f"  获取到 {len(df_concept)} 个概念板块")
        except Exception as e:
            print(f"  概念板块获取失败: {e}")
            df_concept = pd.DataFrame()
        
        return df_stock_list, df_industry, df_concept
        
    except Exception as e:
        print(f"✗ akshare获取失败: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def fetch_stock_individual_info(code):
    """获取单只股票详细信息"""
    try:
        import akshare as ak
        
        # 获取个股信息
        df = ak.stock_individual_info_em(symbol=code)
        
        info = {}
        if not df.empty:
            for _, row in df.iterrows():
                info[row['item']] = row['value']
        
        return info
        
    except Exception as e:
        return {}

def fetch_concept_stocks(concept_name):
    """获取概念板块成分股"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_cons_em(symbol=concept_name)
        return df
    except:
        return pd.DataFrame()

def fetch_industry_stocks(industry_name):
    """获取行业板块成分股"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_cons_em(symbol=industry_name)
        return df
    except:
        return pd.DataFrame()

def update_stock_info_industry():
    """更新stock_info的行业信息"""
    print("\n【更新行业信息】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        import akshare as ak
        
        # 获取所有行业
        df_industries = ak.stock_board_industry_name_em()
        
        updated = 0
        for _, row in df_industries.iterrows():
            industry_name = row['板块名称']
            
            # 获取行业成分股
            try:
                df_stocks = ak.stock_board_industry_cons_em(symbol=industry_name)
                
                for _, stock in df_stocks.iterrows():
                    code = stock['代码']
                    name = stock['名称']
                    
                    # 更新stock_info
                    cur.execute("""
                        UPDATE stock_info SET industry = %s WHERE code = %s
                    """, (industry_name, code))
                    
                    if cur.rowcount > 0:
                        updated += 1
                        
            except:
                pass
            
            if updated % 100 == 0:
                print(f"  已更新 {updated} 条...")
        
        conn.commit()
        print(f"✓ 行业信息更新完成，共 {updated} 条")
        
    except Exception as e:
        print(f"✗ 行业更新失败: {e}")
    
    cur.close()
    conn.close()

def populate_stock_company():
    """填充公司简介表"""
    print("\n【填充公司简介表】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 获取所有股票代码
    cur.execute("SELECT code FROM stock_info WHERE code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'")
    codes = [row[0] for row in cur.fetchall()]
    
    print(f"共 {len(codes)} 只股票需要补充")
    
    try:
        import akshare as ak
        
        success = 0
        failed = 0
        
        for i, code in enumerate(codes):
            try:
                # 获取个股信息
                info = {}
                try:
                    df = ak.stock_individual_info_em(symbol=code)
                    if not df.empty:
                        for _, row in df.iterrows():
                            info[row['item']] = row['value']
                except:
                    pass
                
                # 插入或更新
                cur.execute("""
                    INSERT INTO stock_company (code, name, industry, list_date, description)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    name = VALUES(name),
                    industry = VALUES(industry),
                    list_date = VALUES(list_date),
                    description = VALUES(description)
                """, (
                    code,
                    info.get('股票简称', ''),
                    info.get('行业', ''),
                    info.get('上市时间', None),
                    info.get('公司简介', '')
                ))
                
                success += 1
                
                if success % 50 == 0:
                    print(f"  进度: {success}/{len(codes)}")
                    conn.commit()
                    
            except Exception as e:
                failed += 1
        
        conn.commit()
        print(f"✓ 公司简介填充完成: 成功 {success}, 失败 {failed}")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def populate_stock_concept():
    """填充概念题材表"""
    print("\n【填充概念题材表】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        import akshare as ak
        
        # 获取所有概念板块
        df_concepts = ak.stock_board_concept_name_em()
        print(f"共 {len(df_concepts)} 个概念板块")
        
        total = 0
        
        for _, row in df_concepts.iterrows():
            concept_name = row['板块名称']
            concept_code = row.get('板块代码', concept_name)
            
            try:
                # 获取概念成分股
                df_stocks = ak.stock_board_concept_cons_em(symbol=concept_name)
                
                for _, stock in df_stocks.iterrows():
                    code = stock['代码']
                    name = stock['名称']
                    
                    cur.execute("""
                        INSERT INTO stock_concept (code, name, concept, concept_name)
                        VALUES (%s, %s, %s, %s)
                    """, (code, name, concept_code, concept_name))
                    
                    total += 1
                
                if total % 500 == 0:
                    print(f"  进度: 已插入 {total} 条")
                    conn.commit()
                    
            except:
                pass
        
        conn.commit()
        print(f"✓ 概念题材填充完成: 共 {total} 条")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def update_volume_ratio():
    """更新量比数据"""
    print("\n【更新量比数据】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        import akshare as ak
        
        # 获取实时行情
        df = ak.stock_zh_a_spot_em()
        
        if df.empty:
            print("✗ 获取实时行情失败")
            return
        
        latest_date = datetime.now().strftime('%Y-%m-%d')
        
        # 删除当日旧数据
        cur.execute("DELETE FROM cn_stock_spot WHERE date = %s", (latest_date,))
        
        # 插入新数据（包含量比）
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
        print(f"✓ 实时行情更新完成: {insert_count} 条")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def supplement_stock_daily():
    """补充历史日线数据"""
    print("\n【补充历史日线数据】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 找出缺失日线数据的股票
    cur.execute("""
        SELECT si.id, si.code, si.name 
        FROM stock_info si
        WHERE NOT EXISTS (
            SELECT 1 FROM stock_daily sd WHERE sd.stock_id = si.id
        )
        AND si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
    """)
    
    missing_stocks = cur.fetchall()
    
    if not missing_stocks:
        print("✓ 所有股票都有日线数据")
        cur.close()
        conn.close()
        return
    
    print(f"缺失日线数据的股票: {len(missing_stocks)} 只")
    
    try:
        import akshare as ak
        
        success = 0
        failed = 0
        
        for stock_id, code, name in missing_stocks:
            try:
                # 获取历史数据
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
                
                if df.empty:
                    failed += 1
                    continue
                
                # 插入数据
                for _, row in df.iterrows():
                    try:
                        cur.execute("""
                            INSERT INTO stock_daily 
                            (stock_id, date, open, close, high, low, volume, amount, change_percent)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            stock_id,
                            row['日期'],
                            row['开盘'],
                            row['收盘'],
                            row['最高'],
                            row['最低'],
                            row['成交量'],
                            row['成交额'],
                            row.get('涨跌幅', 0)
                        ))
                    except:
                        pass
                
                success += 1
                print(f"  ✓ {name}({code}): {len(df)}条")
                
                if success % 10 == 0:
                    conn.commit()
                    
            except Exception as e:
                failed += 1
                print(f"  ✗ {name}({code}): {e}")
        
        conn.commit()
        print(f"✓ 日线补充完成: 成功 {success}, 失败 {failed}")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    cur.close()
    conn.close()

def verify_data():
    """验证数据完整性"""
    print("\n【数据完整性验证】")
    print("-" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 检查各表数据量
    tables = ['stock_company', 'stock_concept', 'stock_info', 'stock_daily', 'cn_stock_spot']
    
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count} 条")
        except:
            print(f"  {table}: 表不存在")
    
    # 检查stock_info行业字段
    cur.execute("SELECT COUNT(*) FROM stock_info WHERE industry IS NOT NULL AND industry != ''")
    has_industry = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stock_info")
    total = cur.fetchone()[0]
    print(f"\n  stock_info行业填充率: {has_industry}/{total} ({has_industry/total*100:.1f}%)")
    
    # 检查量比
    cur.execute("SELECT COUNT(*) FROM cn_stock_spot WHERE volume_ratio > 0")
    has_ratio = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cn_stock_spot")
    total_spot = cur.fetchone()[0]
    print(f"  cn_stock_spot量比填充率: {has_ratio}/{total_spot} ({has_ratio/total_spot*100:.1f}%)")
    
    cur.close()
    conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("数据补充脚本")
    print("=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 创建缺失表
    create_missing_tables()
    
    # 2. 更新行业信息
    update_stock_info_industry()
    
    # 3. 填充公司简介表
    populate_stock_company()
    
    # 4. 填充概念题材表
    populate_stock_concept()
    
    # 5. 更新量比数据
    update_volume_ratio()
    
    # 6. 补充日线数据
    supplement_stock_daily()
    
    # 7. 验证
    verify_data()
    
    print("\n" + "=" * 60)
    print("数据补充完成!")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()