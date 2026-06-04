#!/bin/bash
# 每日选股启动脚本 - 清除代理，使用国内API
# 用法: bash cron/run_daily.sh

# 清除所有代理设置
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY

# 进入项目目录
cd /home/liugu/workspace/stock

# 激活虚拟环境
source .venv/bin/activate

# 1. 先同步数据
echo "=== 步骤1: 同步数据 ==="
python cron/sync_data.py

# 2. 再运行选股
echo ""
echo "=== 步骤2: 策略选股 ==="
python cron/optimized_daily.py

# 退出
echo ""
echo "=== 完成 ==="