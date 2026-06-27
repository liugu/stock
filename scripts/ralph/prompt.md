# Ralph Agent Task

实现 A 股选股系统的功能改进，直到所有用户故事完成。

## Workflow Per Iteration

1. Read `scripts/ralph/log.md` to understand what previous iterations completed.

2. Search `docs/user-stories/` for features with `"passes": false`.

3. If no features remain with `"passes": false`:
   - Output: <promise>FINISHED</promise>

4. Pick ONE feature - the highest priority non-passing feature based on dependencies and logical order.
   Priority order: functional > integration > edge-case > ui

5. Implement the feature:
   - Read existing code in `instock/core/strategy/` for patterns
   - Create new strategy files following existing patterns
   - Update `cron/daily_task_config.json` if needed
   - Test the implementation

6. Verify the feature:
   - Run the strategy: `cd /home/liugu/workspace/stock && python cron/daily_task.py --no-update`
   - Check the output contains expected results
   - Verify no errors in execution

7. If verification fails, debug and fix. Repeat until passing.

8. Once verified:
   - Update the user story's `passes` property to `true`
   - Append to `scripts/ralph/log.md` (keep it short but helpful)

9. The iteration ends here. The next iteration will pick up the next feature.

## Project Context

- **项目**: InStock A股量化分析系统
- **语言**: Python 3.11+
- **策略目录**: `instock/core/strategy/`
- **配置文件**: `cron/daily_task_config.json`
- **主脚本**: `cron/daily_task.py`

## Key Files to Reference

- `instock/core/strategy/enter.py` - 放量上涨策略示例
- `instock/core/strategy/new_high.py` - 创新高策略示例
- `instock/core/stockfetch.py` - 股票数据获取工具
- `instock/lib/trade_time.py` - 交易时间工具

## Completion

When ALL user stories have `"passes": true`, output:

<promise>FINISHED</promise>
