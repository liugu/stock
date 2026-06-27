import subprocess
import os

db_host = "192.168.3.225"
db_user = "stock"
db_password = "12345678"
db_name = "instock"
baostock_dir = "/home/liugu/workspace/stock/data/baostock"

print("=== 开始批量导入历史行情数据 ===")

csv_files = [f for f in os.listdir(baostock_dir) if f.endswith('.csv')]
print(f"找到 {len(csv_files)} 个 CSV 文件")

stock_ids = {}
total_lines = 0
inserted = 0

for i, csv_file in enumerate(csv_files):
    filename = csv_file.replace('.csv', '')
    
    if filename.startswith('sh.'):
        code = filename[3:]
        market = 'sh'
    elif filename.startswith('sz.'):
        code = filename[3:]
        market = 'sz'
    else:
        continue
    
    if code.startswith(('000', '399', '512', '159')):
        continue
    
    if code not in stock_ids:
        check_cmd = ['mysql', '-h', db_host, '-u', db_user, '-p' + db_password, db_name, '-N', '-s', '-e', f"SELECT id FROM stock_info WHERE code='{code}';"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        stock_id = result.stdout.strip()
        
        if not stock_id:
            insert_cmd = ['mysql', '-h', db_host, '-u', db_user, '-p' + db_password, db_name, '-e', f"INSERT INTO stock_info (code, name, market) VALUES ('{code}', '股票{code}', '{market}');"]
            subprocess.run(insert_cmd, capture_output=True, text=True)
            
            check_cmd = ['mysql', '-h', db_host, '-u', db_user, '-p' + db_password, db_name, '-N', '-s', '-e', f"SELECT id FROM stock_info WHERE code='{code}';"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            stock_id = result.stdout.strip()
        
        stock_ids[code] = stock_id
    
    try:
        with open(os.path.join(baostock_dir, csv_file), 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.strip().split(',')
            if len(parts) < 9:
                continue
            
            try:
                date = parts[0]
                open_price = parts[2]
                close_price = parts[5]
                high_price = parts[3]
                low_price = parts[4]
                volume = int(parts[6])
                amount = parts[7]
                pct_chg = parts[8]
                
                sql = f"INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent) VALUES ({stock_ids[code]}, '{date}', {open_price}, {close_price}, {high_price}, {low_price}, {volume}, {amount}, {pct_chg});"
                
                insert_cmd = ['mysql', '-h', db_host, '-u', db_user, '-p' + db_password, db_name, '-e', sql]
                result = subprocess.run(insert_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    inserted += 1
                total_lines += 1
                
            except Exception as e:
                continue
        
    except Exception as e:
        continue
    
    if (i + 1) % 100 == 0:
        print(f"处理进度: {i + 1}/{len(csv_files)}, 已导入 {inserted} 条记录")

print(f"=== 导入完成 ===")
print(f"总记录数: {total_lines}, 成功导入: {inserted}")
