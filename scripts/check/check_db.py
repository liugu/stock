import pymysql
conn = pymysql.connect(host='localhost', user='stock', password='12345678', database='instock', port=3306)
cur = conn.cursor()
cur.execute('SHOW TABLES')
tables = cur.fetchall()
print(f'Tables: {len(tables)}')
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t[0]}')
        count = cur.fetchone()[0]
        if count > 0:
            print(f'{t[0]}: {count} rows')
    except:
        pass
cur.close()
conn.close()