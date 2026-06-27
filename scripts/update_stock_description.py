#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票简介信息
使用 akshare 获取公司概况
"""

import sys
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import time
import akshare as ak

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

def update_stock_description():
    """更新股票简介"""
    print('=' * 60)
    print('更新股票简介信息')
    print('=' * 60)
    
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 获取所有A股代码
    cursor.execute('''
        SELECT code, name FROM stock_info 
        WHERE code LIKE "60%" OR code LIKE "00%" OR code LIKE "30%"
        ORDER BY code
    ''')
    stocks = cursor.fetchall()
    print(f'共 {len(stocks)} 只股票')
    
    success = 0
    fail = 0
    start_time = time.time()
    
    for i, (code, name) in enumerate(stocks, 1):
        try:
            # 获取公司概况
            df = ak.stock_profile_cninfo(symbol=code)
            
            if df is not None and not df.empty:
                # 提取信息
                row = df.iloc[0]
                description = row.get('机构简介', '')
                main_business = row.get('主营业务', '')
                business_scope = row.get('经营范围', '')
                industry = row.get('所属行业', '')
                website = row.get('官方网站', '')
                
                # 组合简介
                full_desc = f"主营业务: {main_business}\n\n经营范围: {business_scope}\n\n简介: {description}"
                
                # 更新数据库
                sql = '''
                UPDATE stock_info SET 
                    description = %s,
                    industry = IFNULL(NULLIF(%s, ''), industry)
                WHERE code = %s
                '''
                cursor.execute(sql, (full_desc[:5000], industry, code))
                conn.commit()
                success += 1
                
                # 打印包含ABF等关键词的股票
                if any(kw in full_desc.upper() for kw in ['ABF', '封装基板', '载板', 'PCB']):
                    print(f'\n✓ {code} {name}: 包含相关关键词')
                    print(f'  主营: {main_business[:100]}...')
            else:
                fail += 1
                
        except Exception as e:
            fail += 1
        
        # 控制频率，避免被封
        time.sleep(0.5)
        
        if i % 100 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{len(stocks)} 成功:{success} 失败:{fail} 耗时:{elapsed:.0f}s')
    
    cursor.close()
    conn.close()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 成功 {success}, 失败 {fail}')
    print(f'耗时: {elapsed:.1}s')

if __name__ == '__main__':
    update_stock_description()
