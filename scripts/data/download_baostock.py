import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import os

lg = bs.login()
print(f"登录状态: {lg.error_code} - {lg.error_msg}")

rs = bs.query_all_stock(day='2026-05-21')
stock_list = []
while (rs.error_code == '0') & rs.next():
    stock_list.append(rs.get_row_data())

print(f"共找到 {len(stock_list)} 只股票")

data_dir = '/home/liugu/workspace/stock/data/baostock'
os.makedirs(data_dir, exist_ok=True)

success_count = 0
fail_count = 0

for i, stock in enumerate(stock_list):
    code = stock[0]
    name = stock[2]
    
    if code.startswith('sh.000') or code.startswith('sz.000'):
        continue
    if code.startswith('sh.399') or code.startswith('sz.399'):
        continue
    if code.startswith('sh.512') or code.startswith('sz.159'):
        continue
    
    try:
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
            continue
        
        df_list = []
        while (rs.error_code == '0') & rs.next():
            df_list.append(rs.get_row_data())
        
        if df_list:
            df = pd.DataFrame(df_list, columns=rs.fields)
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = code
            filename = f"{code}.csv"
            filepath = os.path.join(data_dir, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            success_count += 1
            if success_count % 100 == 0:
                print(f"已下载 {success_count} 只股票...")
    
    except Exception as e:
        fail_count += 1

bs.logout()
print(f"下载完成！成功: {success_count}, 失败: {fail_count}")
