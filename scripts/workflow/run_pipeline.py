#!/usr/bin/env python3
"""
完整流程执行脚本:
1. 检查数据库连接
2. 运行数据更新
3. 运行策略选股
4. 检查结果
"""
import sys
import os
import datetime

# Add path
sys.path.insert(0, os.path.dirname(__file__))

def check_db():
    """检查数据库连接"""
    import pymysql
    try:
        conn = pymysql.connect(
            host='localhost',
            user='stock',
            password='12345678',
            database='instock',
            port=3306
        )
        cur = conn.cursor()
        cur.execute('SHOW TABLES')
        tables = cur.fetchall()
        print(f"数据库连接成功，共 {len(tables)} 张表")
        
        # 查看策略选股表
        cur.execute("""SELECT table_name FROM information_schema.tables 
                       WHERE table_schema='instock' AND table_name LIKE '%strategy%'""")
        strategy_tables = [t[0] for t in cur.fetchall()]
        print(f"\n策略表 ({len(strategy_tables)} 张):")
        
        for st in strategy_tables:
            try:
                cur.execute(f'SELECT MAX(date), COUNT(*) FROM `{st}`')
                row = cur.fetchone()
                latest = row[0]
                cnt = row[1]
                print(f"  {st}: 最新日期={latest}, 记录数={cnt}")
            except Exception as e:
                print(f"  {st}: 错误 - {e}")
        
        # 查看基础数据表最新日期
        print(f"\n基础数据表:")
        for tbl in ['basic_data', 'indicators_data', 'klinepattern_data']:
            try:
                cur.execute(f'SELECT MAX(date), COUNT(*) FROM `{tbl}`')
                row = cur.fetchone()
                print(f"  {tbl}: 最新日期={row[0]}, 记录数={row[1]}")
            except Exception as e:
                print(f"  {tbl}: 错误 - {e}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False

def main():
    print("=" * 60)
    print(f"数据更新 + 策略选股 流程执行")
    print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Check DB
    print("\n[步骤 1/4] 检查数据库连接...")
    if not check_db():
        print("数据库连接失败，请先确认 MySQL 服务运行中")
        sys.exit(1)
    print("数据库连接正常")
    
    # Step 2: Run data update
    print("\n[步骤 2/4] 运行数据更新...")
    import subprocess
    result = subprocess.run(
        [sys.executable, 'instock/job/execute_daily_job.py'],
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
        timeout=600
    )
    if result.returncode == 0:
        print("数据更新完成")
        # 显示最后几行日志
        lines = result.stdout.strip().split('\n')
        for line in lines[-5:]:
            print(f"  {line}")
    else:
        print(f"数据更新失败 (exit code: {result.returncode})")
        print(result.stderr[-500:] if result.stderr else "无错误信息")
    
    # Step 3: Run strategy selection
    print("\n[步骤 3/4] 运行策略选股...")
    result = subprocess.run(
        [sys.executable, 'instock/job/strategy_data_daily_job.py'],
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
        timeout=600
    )
    if result.returncode == 0:
        print("策略选股完成")
        lines = result.stdout.strip().split('\n')
        for line in lines[-5:]:
            print(f"  {line}")
    else:
        print(f"策略选股失败 (exit code: {result.returncode})")
        print(result.stderr[-500:] if result.stderr else "无错误信息")
    
    # Step 4: Check results
    print("\n[步骤 4/4] 检查选股结果...")
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
        cur.execute("""SELECT table_name FROM information_schema.tables 
                       WHERE table_schema='instock' AND table_name LIKE '%strategy%'""")
        strategy_tables = [t[0] for t in cur.fetchall()]
        
        print("\n策略选股结果汇总:")
        total_stocks = 0
        for st in strategy_tables:
            try:
                cur.execute(f'SELECT MAX(date), COUNT(*) FROM `{st}`')
                row = cur.fetchone()
                latest = row[0]
                cnt = row[1]
                total_stocks += cnt
                print(f"  {st}: 最新日期={latest}, 选中股票={cnt}")
            except Exception as e:
                print(f"  {st}: 错误 - {e}")
        
        print(f"\n策略选股表总记录数: {total_stocks}")
        
        # 显示最近的选股结果
        if strategy_tables:
            latest_table = strategy_tables[-1]
            print(f"\n最近表 '{latest_table}' 的部分结果:")
            cur.execute(f'SELECT * FROM `{latest_table}` ORDER BY date DESC LIMIT 5')
            rows = cur.fetchall()
            cur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name="{latest_table}" ORDER BY ordinal_position')
            cols = [c[0] for c in cur.fetchall()]
            print(f"  列: {', '.join(cols[:10])}...")
            for row in rows:
                print(f"  {row[0]} {row[1]} 价格={row[2]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"检查结果失败: {e}")
    
    print("\n" + "=" * 60)
    print("流程执行完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
