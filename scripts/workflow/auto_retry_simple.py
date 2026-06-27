#!/usr/bin/env python3
"""
自动重试脚本 - 每2分钟执行一次，无限重试直到成功
成功后输出选股结果（飞书通知待修复）
"""
import sys
import os
import time
import traceback
import datetime

# 项目路径
PROJECT_DIR = r'E:\量化研究\workspace\stock'
sys.path.insert(0, PROJECT_DIR)

print("=" * 60)
print("自动重试系统启动")
print("每 2 分钟执行一次，直到成功")
print("=" * 60)

def run_strategy():
    """运行策略选股"""
    print("开始运行数据更新和策略选股...")
    try:
        import instock.job.execute_daily_job as ej
        ej.main()
        return True, "策略选股执行完成"
    except SystemExit:
        return True, "策略选股执行完成"
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return False, error_msg

def fetch_stock_results():
    """从数据库获取选股结果"""
    try:
        import pymysql
        conn = pymysql.connect(
            host='localhost',
            user='stock',
            password='12345678',
            database='instock',
            port=3306
        )
        cur = conn.cursor()
        
        # 获取所有策略选股表
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'instock' AND table_name LIKE '%strategy%'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        results = []
        
        for (table_name,) in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                cur.execute(f"SELECT MAX(date) FROM {table_name}")
                max_date = cur.fetchone()[0]
                results.append((table_name, max_date, count))
            except:
                pass
        
        cur.close()
        conn.close()
        
        return results
    except Exception as e:
        print(f"获取选股结果失败: {e}")
        return []

def main():
    """主函数 - 无限重试循环"""
    retry_count = 0
    
    while True:
        retry_count += 1
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*60}")
        print(f"[第 {retry_count} 次] {current_time}")
        print(f"{'='*60}")
        
        # 运行策略选股
        success, message = run_strategy()
        
        if success:
            print(f"\n✓ 成功: {message}")
            
            # 获取选股结果
            results = fetch_stock_results()
            
            # 输出结果
            print("\n" + "=" * 60)
            print("选股结果:")
            print("=" * 60)
            
            if results:
                for table_name, latest_date, count in results:
                    print(f"• {table_name}: {count}只 (日期:{latest_date})")
            else:
                print("暂无选股数据")
            
            print("\n✓ 任务成功完成")
            break
        else:
            print(f"\n✗ 失败: {message[:200]}")
            print(f"等待 2 分钟后重试...")
            time.sleep(120)

if __name__ == '__main__':
    main()