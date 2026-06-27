#!/usr/bin/env python3
"""
逐步执行数据更新流程（串行 + 异常捕获）
"""
import sys
import os
import traceback
import time

cpath_current = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, cpath_current)

steps = [
    ("初始化数据库", "instock.job.init_job"),
    ("股票基础数据", "instock.job.basic_data_daily_job"),
    ("综合选股数据", "instock.job.selection_data_daily_job"),
    ("股票其它基础数据", "instock.job.basic_data_other_daily_job"),
    ("技术指标数据", "instock.job.indicators_data_daily_job"),
    ("K线形态数据", "instock.job.klinepattern_data_daily_job"),
    ("策略选股数据", "instock.job.strategy_data_daily_job"),
    ("回测数据", "instock.job.backtest_data_daily_job"),
    ("操盘必读", "instock.job.cpbd_data_daily_job"),
    ("闭盘数据", "instock.job.basic_data_after_close_daily_job"),
]

total_start = time.time()
step_num = 0

for name, module_name in steps:
    step_num += 1
    print(f"\n{'='*60}")
    print(f"[{step_num}/{len(steps)}] 开始: {name}")
    print(f"{'='*60}")
    sys.stdout.flush()
    try:
        t0 = time.time()
        mod = __import__(module_name, fromlist=['main'])
        if not hasattr(mod, 'main'):
            print(f"  ✗ 没有 main 函数")
            sys.stdout.flush()
            continue
        mod.main()
        elapsed = time.time() - t0
        print(f"  ✓ 完成 ({elapsed:.1f}秒)")
        sys.stdout.flush()
    except SystemExit:
        elapsed = time.time() - t0
        print(f"  ✓ 正常退出 ({elapsed:.1f}秒)")
        sys.stdout.flush()
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ✗ 异常 ({elapsed:.1f}秒): {e}")
        traceback.print_exc()
        sys.stdout.flush()
        break
    except BaseException as e:
        elapsed = time.time() - t0
        print(f"  ✗ 严重错误 ({elapsed:.1f}秒): {e}")
        import sys as _sys
        _sys.exit(1)

total_elapsed = time.time() - total_start
print(f"\n{'='*60}")
print(f"完成: {step_num} 个步骤, 总耗时: {total_elapsed:.1f}秒")
print(f"{'='*60}")
sys.stdout.flush()
