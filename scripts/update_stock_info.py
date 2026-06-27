#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新股票基本信息
使用 baostock 作为数据源
"""

import sys
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import time
from datetime import datetime

# 数据库配置
DB = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

import baostock as bs

def update_stock_info():
    """更新股票基本信息"""
    print('=' * 60)
    print('更新股票基本信息')
    print('=' * 60)
    
    # 登录 baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f'Baostock 登录失败: {lg.error_msg}')
        return
    print('Baostock 登录成功')
    
    # 获取所有证券信息
    print('获取所有证券信息...')
    rs = bs.query_stock_basic()
    if rs.error_code != '0':
        print(f'获取失败: {rs.error_msg}')
        return
    
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    
    print(f'获取到 {len(data_list)} 条记录')
    
    # 字段: code, code_name, ipoDate, outDate, type, status
    # type: 1=沪深A股, 2=深证A股, 3=创业板, 4=科创板
    
    # 连接数据库
    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    
    # 统计
    total = len(data_list)
    updated = 0
    inserted = 0
    skipped = 0
    start_time = time.time()
    
    for i, item in enumerate(data_list, 1):
        try:
            code_full = item[0]  # sh.600000 或 sz.000001
            name = item[1]       # 名称
            list_date = item[2]  # 上市日期
            out_date = item[3]   # 退市日期
            type_code = item[4]  # 类型
            status = item[5]     # 状态
            
            # 只处理A股 (类型 1-4)
            if type_code not in ['1', '2', '3', '4']:
                skipped += 1
                continue
            
            # 转换代码格式 (sh.600000 -> 600000)
            code = code_full.replace('sh.', '').replace('sz.', '')
            
            # 判断市场
            if code_full.startswith('sh.'):
                market = 'sh'
            else:
                market = 'sz'
            
            # 只处理6位数字代码
            if not (code.isdigit() and len(code) == 6):
                skipped += 1
                continue
            
            # 转换日期格式
            if list_date:
                try:
                    list_date_fmt = datetime.strptime(list_date, '%Y-%m-%d').date()
                except:
                    list_date_fmt = None
            else:
                list_date_fmt = None
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM stock_info WHERE code = %s', (code,))
            result = cursor.fetchone()
            
            if result:
                # 更新
                sql = '''
                UPDATE stock_info SET 
                    name = %s,
                    market = %s,
                    list_date = %s
                WHERE code = %s
                '''
                cursor.execute(sql, (name, market, list_date_fmt, code))
                conn.commit()
                updated += 1
            else:
                # 插入
                sql = '''
                INSERT INTO stock_info (code, name, market, list_date)
                VALUES (%s, %s, %s, %s)
                '''
                cursor.execute(sql, (code, name, market, list_date_fmt))
                conn.commit()
                inserted += 1
            
        except Exception as e:
            skipped += 1
        
        if i % 500 == 0:
            elapsed = time.time() - start_time
            print(f'进度: {i}/{total} 更新:{updated} 新增:{inserted} 跳过:{skipped} 耗时:{elapsed:.0}s')
    
    # 获取行业分类
    print('\n获取行业分类信息...')
    rs2 = bs.query_stock_industry()
    if rs2.error_code == '0':
        industry_list = []
        while (rs2.error_code == '0') & rs2.next():
            industry_list.append(rs2.get_row_data())
        
        print(f'获取到 {len(industry_list)} 条行业记录')
        
        # 字段: updateDate, code, code_name, industry, industryClassification
        industry_updated = 0
        for item in industry_list:
            try:
                code = item[1].replace('sh.', '').replace('sz.', '')
                industry = item[3]  # 行业
                
                if code.isdigit() and len(code) == 6 and industry:
                    cursor.execute('UPDATE stock_info SET industry = %s WHERE code = %s', (industry, code))
                    conn.commit()
                    industry_updated += 1
            except:
                pass
        
        print(f'更新行业信息: {industry_updated} 条')
    
    cursor.close()
    conn.close()
    bs.logout()
    
    elapsed = time.time() - start_time
    print()
    print(f'✓ 完成: 更新 {updated}, 新增 {inserted}, 跳过 {skipped}')
    print(f'耗时: {elapsed:.1}s')

if __name__ == '__main__':
    update_stock_info()
