import pymysql
from datetime import datetime, timedelta

conn = pymysql.connect(
    host='localhost',
    user='stock',
    password='12345678',
    database='instock',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 检查 stock_daily 最新日期
cursor.execute("SELECT MAX(date) as latest_date FROM stock_daily")
result = cursor.fetchone()
print(f"stock_daily 最新日期: {result[0]}")

# 检查数据条数
cursor.execute("SELECT COUNT(*) FROM stock_daily")
count = cursor.fetchone()
print(f"stock_daily 数据条数: {count[0]}")

# 检查最近几天的数据
cursor.execute("SELECT date, COUNT(*) as cnt FROM stock_daily GROUP BY date ORDER BY date DESC LIMIT 10")
print("\n最近10天的数据分布:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} 条")

# 检查 cn_stock_spot 表
cursor.execute("SHOW TABLES LIKE 'cn_stock_spot'")
if cursor.fetchone():
    cursor.execute("SELECT COUNT(*) FROM cn_stock_spot")
    spot_count = cursor.fetchone()
    print(f"\ncn_stock_spot 数据条数: {spot_count[0]}")
else:
    print("\ncn_stock_spot 表不存在")

# 判断是否需要更新
today = datetime.now().date()
yesterday = today - timedelta(days=1)
print(f"\n今天日期: {today}")
print(f"昨天日期: {yesterday}")

latest = result[0]
if latest:
    if isinstance(latest, str):
        latest = datetime.strptime(latest, '%Y-%m-%d').date()
    
    if latest < yesterday:
        print(f"\n⚠️ 数据已过时！最新数据日期 {latest}，缺少 {latest} 到 {yesterday} 的数据")
    else:
        print(f"\n✅ 数据已是最新")
else:
    print("\n❌ 无法获取数据日期")

conn.close()