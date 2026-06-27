#!/usr/bin/env python3
import sys
import os

cpath_current = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, cpath_current)

modules = [
    "instock.job.init_job",
    "instock.job.basic_data_daily_job",
    "instock.job.basic_data_other_daily_job",
    "instock.job.basic_data_after_close_daily_job",
    "instock.job.indicators_data_daily_job",
    "instock.job.strategy_data_daily_job",
    "instock.job.backtest_data_daily_job",
    "instock.job.klinepattern_data_daily_job",
    "instock.job.selection_data_daily_job",
    "instock.job.cpbd_data_daily_job",
]

for i, mod_name in enumerate(modules, 1):
    print(f"[{i}/{len(modules)}] 导入 {mod_name}...", end=" ")
    sys.stdout.flush()
    try:
        mod = __import__(mod_name, fromlist=['main'])
        print(f"OK - main: {hasattr(mod, 'main')}")
        sys.stdout.flush()
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        break
