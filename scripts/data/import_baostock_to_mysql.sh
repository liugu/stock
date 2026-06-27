#!/bin/bash
# 导入 Baostock 数据到 MySQL

DB_HOST="192.168.3.225"
DB_USER="root"
DB_PASSWORD="12345678"
DB_NAME="instock"
BAOSTOCK_DIR="/home/liugu/workspace/stock/data/baostock"

echo "=== 开始导入 Baostock 数据到 MySQL ==="

# 首先导入股票信息
echo "步骤 1: 导入股票基本信息..."

count=0
for csv_file in "$BAOSTOCK_DIR/"*.csv; do
    filename=$(basename "$csv_file" .csv)
    
    # 提取股票代码
    if [[ "$filename" == sh.* ]]; then
        code="${filename#sh.}"
        market="sh"
    elif [[ "$filename" == sz.* ]]; then
        code="${filename#sz.}"
        market="sz"
    else
        continue
    fi
    
    # 跳过指数和基金
    if [[ "$code" == 000* ]] || [[ "$code" == 399* ]] || [[ "$code" == 512* ]] || [[ "$code" == 159* ]]; then
        continue
    fi
    
    # 检查股票是否已存在
    stock_id=$(mysql -h$DB_HOST -u$DB_USER -p$DB_PASSWORD -D$DB_NAME -N -s -e "SELECT id FROM stock_info WHERE code='$code';" 2>/dev/null)
    
    if [ -z "$stock_id" ]; then
        # 插入股票信息
        name="股票${code}"
        mysql -h$DB_HOST -u$DB_USER -p$DB_PASSWORD -D$DB_NAME -e "
            INSERT INTO stock_info (code, name, market) VALUES ('$code', '$name', '$market');
        " 2>/dev/null
        
        if [ $? -eq 0 ]; then
            count=$((count + 1))
        fi
    fi
    
    # 每100只股票输出一次进度
    if [ $((count % 100)) -eq 0 ] && [ $count -gt 0 ]; then
        echo "已导入 $count 只股票..."
    fi
done

echo "=== 导入完成 ==="
echo "共导入 $count 只股票"
