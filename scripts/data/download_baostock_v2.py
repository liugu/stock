import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

def download_stock_data():
    """下载所有A股历史数据到本地"""
    
    # 登录
    lg = bs.login()
    print(f"登录状态: {lg.error_code} - {lg.error_msg}")
    
    # 获取所有A股
    rs = bs.query_all_stock(day='2026-05-21')
    stock_list = []
    while (rs.error_code == '0') & rs.next():
        stock_list.append(rs.get_row_data())
    
    print(f"共找到 {len(stock_list)} 只股票")
    
    # 创建数据目录
    data_dir = '/home/liugu/workspace/stock/data/baostock'
    os.makedirs(data_dir, exist_ok=True)
    
    # 已下载的文件列表
    downloaded_files = set(os.listdir(data_dir))
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, stock in enumerate(stock_list):
        code = stock[0]
        name = stock[2]
        
        # 跳过指数和基金
        if code.startswith('sh.000') or code.startswith('sz.000'):
            continue
        if code.startswith('sh.399') or code.startswith('sz.399'):
            continue
        if code.startswith('sh.512') or code.startswith('sz.159'):
            continue
        
        filename = f"{code}.csv"
        
        # 跳过已存在的文件
        if filename in downloaded_files:
            skip_count += 1
            if skip_count % 100 == 0:
                print(f"跳过已存在: {skip_count}")
            continue
        
        try:
            # 获取历史数据（最近1年）
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                code,
                'date,code,open,high,low,close,volume,amount,pctChg',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='3'
            )
            
            if rs.error_code != '0':
                fail_count += 1
                print(f"{code} - {name}: 获取失败 - {rs.error_msg}")
                continue
            
            df_list = []
            while (rs.error_code == '0') & rs.next():
                df_list.append(rs.get_row_data())
            
            if df_list:
                df = pd.DataFrame(df_list, columns=rs.fields)
                df['date'] = pd.to_datetime(df['date'])
                df['code'] = code
                filepath = os.path.join(data_dir, filename)
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                success_count += 1
                
                # 每下载100只打印一次进度
                if success_count % 100 == 0:
                    print(f"已下载: {success_count} 只股票...")
                
                # 每下载200只休眠一下，避免被封
                if success_count % 200 == 0:
                    print("休眠5秒...")
                    import time
                    time.sleep(5)
        
        except Exception as e:
            fail_count += 1
            error_msg = str(e)
            print(f"{code} - {name}: 下载异常 - {error_msg}")
            
            # 检测大模型错误 - 间隔2分钟重试
            if "Xunfei claude request failed" in error_msg or "NotEnoughCvError" in error_msg:
                print("检测到大模型错误，等待120秒后继续...")
                import time
                time.sleep(120)
            else:
                # 其他错误等待60秒
                print("等待60秒后继续...")
                import time
                time.sleep(60)
    
    bs.logout()
    
    print(f"\n下载完成！")
    print(f"成功: {success_count} 只")
    print(f"失败: {fail_count} 只")
    print(f"跳过: {skip_count} 只")
    print(f"数据目录: {data_dir}")

if __name__ == '__main__':
    # 确保使用虚拟环境
    if 'VIRTUAL_ENV' not in os.environ:
        print("请在虚拟环境中运行此脚本")
        sys.exit(1)
    
    download_stock_data()
