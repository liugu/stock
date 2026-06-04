#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日任务执行脚本

功能：
1. 更新股票数据
2. 执行策略选股
3. 生成报告
4. 推送通知

作者: Hermes
日期: 2026/5/28
"""

import sys
import os
import time
import json
from datetime import datetime, date

# 添加项目路径
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}


class DailyTask:
    """每日任务管理"""
    
    def __init__(self):
        self.conn = pymysql.connect(**DB_CONFIG)
        self.today = date.today().strftime('%Y-%m-%d')
        self.results = {}
        
        print('=' * 80)
        print(f'每日任务执行 - {self.today}')
        print('=' * 80)
    
    def check_trading_day(self):
        """检查是否为交易日"""
        print('\n检查交易日...')
        
        # 简单判断：周末不交易
        weekday = date.today().weekday()
        if weekday >= 5:  # 周六、周日
            print(f'  今天是{["周一","周二","周三","周四","周五","周六","周日"][weekday]}，非交易日')
            return False
        
        print(f'  今天是{["周一","周二","周三","周四","周五","周六","周日"][weekday]}，交易日')
        return True
    
    def check_data_status(self):
        """检查数据状态"""
        print('\n数据状态检查:')
        print('-' * 60)
        
        tables = [
            'cn_stock_spot', 'cn_stock_indicator', 
            'cn_stock_klinepattern', 'strategy_enter'
        ]
        
        cursor = self.conn.cursor()
        
        for table in tables:
            try:
                # 检查表是否存在
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if cursor.fetchone():
                    cursor.execute(f"SELECT MAX(date) FROM {table}")
                    result = cursor.fetchone()
                    latest_date = result[0] if result[0] else '无数据'
                    print(f'  ✓ {table}: {latest_date}')
                else:
                    print(f'  ✗ {table}: 表不存在')
            except Exception as e:
                print(f'  ✗ {table}: {e}')
        
        cursor.close()
    
    def update_spot_data(self):
        """更新实时行情数据"""
        print('\n更新实时行情数据...')
        print('-' * 60)
        
        try:
            import akshare as ak
            
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()
            
            if df.empty:
                print('  ✗ 获取数据失败')
                return False
            
            print(f'  获取到 {len(df)} 只股票数据')
            
            # 保存到数据库
            cursor = self.conn.cursor()
            
            # 删除今天的数据
            cursor.execute("DELETE FROM cn_stock_spot WHERE date = %s", (self.today,))
            
            # 插入新数据
            insert_count = 0
            for _, row in df.iterrows():
                try:
                    sql = """
                    INSERT INTO cn_stock_spot 
                    (date, code, name, new_price, change_rate, turnoverrate, 
                     volume_ratio, deal_amount, amplitude, pe)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        self.today,
                        row['代码'],
                        row['名称'],
                        row['最新价'],
                        row['涨跌幅'],
                        row['换手率'],
                        row.get('量比', 0),
                        row['成交额'],
                        row['振幅'],
                        row['市盈率-动态']
                    ))
                    insert_count += 1
                except Exception as e:
                    pass
            
            self.conn.commit()
            cursor.close()
            
            print(f'  ✓ 更新完成，插入 {insert_count} 条数据')
            return True
            
        except Exception as e:
            print(f'  ✗ 更新失败: {e}')
            return False
    
    def run_strategy_selection(self):
        """运行策略选股"""
        print('\n运行策略选股...')
        print('-' * 60)
        
        strategies = [
            ('放量上涨', 'enter'),
            ('创新高', 'new_high'),
            ('均线多头', 'keep_increasing'),
        ]
        
        cursor = self.conn.cursor()
        results = {}
        
        for strategy_name, strategy_file in strategies:
            print(f'\n  执行策略: {strategy_name}')
            
            try:
                # 导入策略模块
                module = __import__(f'instock.core.strategy.{strategy_file}', fromlist=['check'])
                
                # 获取股票列表
                cursor.execute("""
                    SELECT code, name, new_price 
                    FROM cn_stock_spot 
                    WHERE date = %s 
                    AND change_rate > 0
                    LIMIT 100
                """, (self.today,))
                
                stocks = cursor.fetchall()
                selected = []
                
                for code, name, price in stocks:
                    try:
                        # 简化版选股逻辑
                        if strategy_file == 'enter':
                            # 放量上涨：涨幅>2%，成交额>2亿
                            cursor.execute("""
                                SELECT change_rate, deal_amount 
                                FROM cn_stock_spot 
                                WHERE code = %s AND date = %s
                            """, (code, self.today))
                            row = cursor.fetchone()
                            if row and row[0] > 2 and row[1] > 200000000:
                                selected.append((code, name, price))
                        
                        elif strategy_file == 'new_high':
                            # 创新高：涨幅>5%
                            cursor.execute("""
                                SELECT change_rate 
                                FROM cn_stock_spot 
                                WHERE code = %s AND date = %s
                            """, (code, self.today))
                            row = cursor.fetchone()
                            if row and row[0] > 5:
                                selected.append((code, name, price))
                        
                        elif strategy_file == 'keep_increasing':
                            # 均线多头：涨幅>1%
                            cursor.execute("""
                                SELECT change_rate 
                                FROM cn_stock_spot 
                                WHERE code = %s AND date = %s
                            """, (code, self.today))
                            row = cursor.fetchone()
                            if row and row[0] > 1:
                                selected.append((code, name, price))
                    
                    except:
                        pass
                
                results[strategy_name] = selected[:10]  # 只保留前10只
                print(f'    选出 {len(selected)} 只股票')
                
            except Exception as e:
                print(f'    ✗ 执行失败: {e}')
                results[strategy_name] = []
        
        cursor.close()
        self.results = results
        return results
    
    def generate_report(self):
        """生成报告"""
        print('\n' + '=' * 80)
        print('选股结果报告')
        print('=' * 80)
        
        if not self.results:
            print('\n无选股结果')
            return
        
        report_lines = []
        
        for strategy, stocks in self.results.items():
            if stocks:
                print(f'\n【{strategy}】')
                report_lines.append(f'\n【{strategy}】')
                
                for i, (code, name, price) in enumerate(stocks[:5], 1):
                    line = f'{i}. {name}({code}): {price}元'
                    print(f'  {line}')
                    report_lines.append(f'  {line}')
        
        # 保存报告
        report_file = f'E:/量化研究/workspace/stock/reports/daily_{self.today}.txt'
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f'每日选股报告 - {self.today}\n')
            f.write('=' * 80 + '\n')
            f.write('\n'.join(report_lines))
        
        print(f'\n报告已保存: {report_file}')
    
    def run_all(self):
        """执行所有任务"""
        start_time = time.time()
        
        # 1. 检查交易日
        if not self.check_trading_day():
            print('\n今天非交易日，跳过数据更新')
        else:
            # 2. 检查数据状态
            self.check_data_status()
            
            # 3. 更新数据（可选，网络可能受限）
            # self.update_spot_data()
        
        # 4. 执行策略选股
        self.run_strategy_selection()
        
        # 5. 生成报告
        self.generate_report()
        
        # 结束
        elapsed = time.time() - start_time
        print('\n' + '=' * 80)
        print(f'任务完成，耗时: {elapsed:.1f}秒')
        print('=' * 80)
        
        self.conn.close()


def main():
    """主函数"""
    task = DailyTask()
    task.run_all()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n任务已取消')
    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()
