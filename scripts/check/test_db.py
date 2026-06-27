import pymysql
try:
    conn = pymysql.connect(
        host='localhost',
        user='stock',
        password='12345678',
        database='instock',
        port=3306
    )
    print("DB CONNECTED")
    cur = conn.cursor()
    cur.execute('SHOW TABLES')
    tables = cur.fetchall()
    print(f"Tables: {len(tables)}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"DB ERROR: {e}")
