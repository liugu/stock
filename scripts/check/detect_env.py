#!/usr/bin/env python3
import sys
import os
results = []

# Python version
results.append(f"Python: {sys.version}")
results.append(f"Prefix: {sys.prefix}")
results.append(f"Executable: {sys.executable}")
results.append("")
results.append("=== Package Check ===")

mods = ['pymysql', 'pandas', 'numpy', 'talib', 'tornado', 'sqlalchemy', 'requests', 'openpyxl']
for m in mods:
    try:
        mod = __import__(m)
        ver = getattr(mod, '__version__', 'unknown')
        results.append(f'{m}: OK (version {ver})')
    except ImportError as e:
        results.append(f'{m}: MISSING ({e})')

results.append("")
results.append("=== Database Config Check ===")
try:
    # Read the database config
    db_path = os.path.join(os.path.dirname(__file__), 'instock', 'lib', 'database.py')
    with open(db_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'db_user' in line or 'db_password' in line or 'db_database' in line or 'db_host' in line:
                if not line.strip().startswith('#'):
                    results.append(line.strip())
except Exception as e:
    results.append(f"DB config error: {e}")

results.append("")
results.append("=== Requirements Check ===")
try:
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            results.append(f"requirements.txt has {len(lines)} packages")
    else:
        results.append("requirements.txt not found")
except Exception as e:
    results.append(f"requirements.txt error: {e}")

results.append("")
results.append("=== Tables Check ===")
try:
    import pymysql
    conn = pymysql.connect(
        host='localhost',
        user='stock',
        password='12345678',
        database='instock',
        port=3306
    )
    cur = conn.cursor()
    cur.execute('SHOW TABLES')
    tables = cur.fetchall()
    results.append(f"Database 'instock' has {len(tables)} tables")
    
    # Check strategy tables for latest dates
    cur.execute("""SELECT table_name FROM information_schema.tables 
                   WHERE table_schema='instock' AND table_name LIKE '%strategy%'""")
    strategy_tables = [t[0] for t in cur.fetchall()]
    results.append(f"Strategy tables: {len(strategy_tables)}")
    for st in strategy_tables[:5]:
        try:
            cur.execute(f'SELECT MAX(date) as latest_date, COUNT(*) as cnt FROM `{st}`')
            row = cur.fetchone()
            results.append(f"  {st}: latest={row[0]}, count={row[1]}")
        except Exception as e:
            results.append(f"  {st}: error - {e}")
    
    cur.close()
    conn.close()
except Exception as e:
    results.append(f"Database connection error: {e}")

with open('check_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print("Done. Results written to check_results.txt")
