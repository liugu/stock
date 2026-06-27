#!/usr/bin/env python3
import sys
import traceback
try:
    import instock.job.execute_daily_job as jd
    print("Import OK")
except Exception as e:
    print(f"Import error: {e}")
    traceback.print_exc()
