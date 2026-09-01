import pymysql
conn = pymysql.connect(host='localhost',user='stock',password='12345678',database='instock',port=3306,charset='utf8mb4')
c = conn.cursor()

print('=== 价格交叉验证 (stock_daily vs cn_stock_spot) ===')
c.execute('''
    SELECT si.code, si.name, sd.close, cs.new_price, sd.date as d_date, cs.date as s_date
    FROM stock_daily sd
    JOIN stock_info si ON sd.stock_id = si.id
    JOIN cn_stock_spot cs ON si.code COLLATE utf8mb4_general_ci = cs.code
    WHERE sd.date = cs.date
    ORDER BY RAND()
    LIMIT 6
''')
rows = c.fetchall()
if rows:
    for r in rows:
        diff = abs(float(r[2]) - float(r[3]))
        ratio = diff/float(r[2])*100 if float(r[2]) > 0 else 0
        status = '✓' if ratio < 0.5 else '⚠'
        print(f'  {r[0]} {r[1]}: date={r[4]}, daily_close={float(r[2]):.2f}, spot_new_price={float(r[3]):.2f}, 差异={diff:.2f} ({ratio:.4f}%) {status}')
else:
    print('  同日期交叉匹配无结果')
    c.execute('SELECT MAX(date) FROM stock_daily')
    ld = c.fetchone()[0]
    c.execute('SELECT MAX(date) FROM cn_stock_spot')
    ls = c.fetchone()[0]
    print(f'  stock_daily最新={ld}, cn_stock_spot最新={ls}')
    c.execute('''
        SELECT si.code, si.name, sd.close, cs.new_price, sd.date, cs.date
        FROM stock_daily sd
        JOIN stock_info si ON sd.stock_id = si.id
        JOIN cn_stock_spot cs ON si.code COLLATE utf8mb4_general_ci = cs.code
        WHERE sd.date = %s
        ORDER BY RAND()
        LIMIT 6
    ''', (ld,))
    rows2 = c.fetchall()
    for r in rows2:
        diff = abs(float(r[2]) - float(r[3]))
        print(f'  {r[0]} {r[1]}: daily({r[4]} close={float(r[2]):.2f}), spot({r[5]} price={float(r[3]):.2f}), 差异={diff:.2f}')

print()
c.execute("SELECT MAX(date) FROM stock_daily")
ld = c.fetchone()[0]
c.execute('''
    SELECT 
        CASE 
            WHEN si.code LIKE '60%%' THEN '60xx 主板'
            WHEN si.code LIKE '00%%' THEN '00xx 主板' 
            WHEN si.code LIKE '30%%' THEN '30xx 创业板'
            WHEN si.code LIKE '688%%' THEN '688 科创板'
            ELSE '其他'
        END as board,
        COUNT(*) as cnt
    FROM stock_daily sd
    JOIN stock_info si ON sd.stock_id = si.id
    WHERE sd.date = %s
    GROUP BY board
    ORDER BY cnt DESC
''', (ld,))
print(f'=== stock_daily 板块分布 ({ld}) ===')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

conn.close()
print()
print('数据验证完成')
