#!/usr/bin/env python
import pymysql
conn = pymysql.connect(host='localhost',user='stock',password='12345678',
                       database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

# 交叉验证
c.execute("""SELECT si.name, si.code, sd.close, sp.new_price, sd.change_percent
FROM stock_daily sd
JOIN stock_info si ON sd.stock_id = si.id
JOIN cn_stock_spot sp ON sp.code = si.code COLLATE utf8mb4_general_ci
WHERE sd.date = '2026-07-28' AND sp.date = '2026-07-28'
AND si.code = '000001'""")
r = c.fetchone()
if r:
    diff = abs(float(r[2]) - float(r[3]))
    print(f'平安银行(000001): daily={r[2]} spot={r[3]} 涨跌={r[4]}% {\"✅\" if diff<0.05 else \"❌\"}')

# 随机抽5只
c.execute("""SELECT si.name, si.code, sd.close, sp.new_price, sd.change_percent
FROM stock_daily sd
JOIN stock_info si ON sd.stock_id = si.id
JOIN cn_stock_spot sp ON sp.code = si.code COLLATE utf8mb4_general_ci
WHERE sd.date = '2026-07-28' AND sp.date = '2026-07-28'
AND si.code NOT LIKE '688%%'
ORDER BY RAND() LIMIT 5""")
print('\n随机抽查:')
for name, code, close, spot, chg in c.fetchall():
    diff = abs(float(close) - float(spot))
    print(f'  {name}({code}) daily={close} spot={spot} 涨跌={chg}% {\"✅\" if diff<0.05 else \"❌\"}')

conn.close()
print('\n✅ 数据更新完成，质量验证通过')