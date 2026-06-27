#!/usr/bin/env python3
import sys
mods = ['pymysql', 'pandas', 'numpy', 'talib', 'tornado', 'sqlalchemy', 'requests', 'numpy', 'openpyxl']
results = []
for m in mods:
    try:
        import importlib
        mod = importlib.import_module(m)
        ver = getattr(mod, '__version__', 'unknown')
        results.append(f'{m}: OK (version {ver})')
    except ImportError:
        results.append(f'{m}: MISSING')
print('\n'.join(results))
