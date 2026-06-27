
import baostock as bs
import pandas as pd
import os
from datetime import datetime, timedelta

# 登录
lg = bs.login()
print(f"登录状态: {lg.error_code} - {lg.error_msg}")

# 获取所有A股股票代码
print("正在获取所有A股股票代码...")
rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
stock_list = []
while (rs.error_code == '0') & rs.next():
    stock_list.append(rs.get_row_data())

print(f"共获取到 {len(stock_list)} 只股票")

# 设置时间范围（近2年）
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")

print(f"时间范围: {start_date} 到 {end_date}")

# 创建数据文件
output_file = "/home/liugu/workspace/stock/data/all_stocks_kline_2years.csv"
print(f"数据将保存到: {output_file}")

# 获取每只股票的数据
all_data = []
count = 0
error_count = 0

for stock in stock_list[:100]:  # 先测试前100只
    code = stock[1]  # 股票代码
    name = stock[2]  # 股票名称
    
    try:
        # 查询历史K线数据
        rs = bs.query_history_k_data_plus(
            code,
            "date,code,open,high,low,close,preclose,volume,amount,pctChg,change,pchQ,turn,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2"  # 2:后复权
        )
        
        # 读取数据
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['date'] = pd.to_datetime(df['date'])
            df['code'] = code
            df['name'] = name
            all_data.append(df)
            count += 1
            print(f"[{count}] {name}({code}): 获取到 {len(df)} 条数据")
        else:
            print(f"[{count}] {name}({code}): 无数据")
            
    except Exception as e:
        error_count += 1
        print(f"[{count}] {name}({code}): 错误 - {e}")

# 合并所有数据
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    final_df = final_df.sort_values(['date', 'code'])
    
    # 保存到CSV
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n完成! 共处理 {count} 只股票，获取 {len(final_df)} 条K线数据")
    print(f"数据已保存到: {output_file}")
else:
    print("未获取到任何数据")

# 登出
bs.logout()
