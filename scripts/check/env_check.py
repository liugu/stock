import sys
import os

out = []
out.append(f"Python: {sys.version}")
out.append(f"Path: {sys.executable}")
out.append(f"CWD: {os.getcwd()}")

mods = ['pymysql', 'pandas', 'numpy', 'talib', 'tornado', 'sqlalchemy']
for m in mods:
    try:
        import importlib
        mod = importlib.import_module(m)
        ver = getattr(mod, '__version__', 'N/A')
        out.append(f"  {m}: OK ({ver})")
    except ImportError:
        out.append(f"  {m}: MISSING")

out.append("---")
out.append("Checking database config...")

db_conf_path = os.path.join(os.path.dirname(__file__), 'instock', 'lib', 'database.py')
with open(db_conf_path, 'r', encoding='utf-8') as f:
    for line in f:
        stripped = line.strip()
        if 'db_host' in stripped or 'db_user' in stripped or 'db_password' in stripped or 'db_database' in stripped:
            if not stripped.startswith('#'):
                out.append(f"  {stripped}")

with open(os.path.join(os.path.dirname(__file__), 'output.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
    
print("Written to output.txt")
