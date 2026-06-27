#!/bin/bash
# 运行选股任务 - 清除代理环境变量

# 清除所有代理环境变量
unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY
unset all_proxy
unset ALL_PROXY

# 设置PYTHONPATH
export PYTHONPATH=/home/liugu/workspace/stock

# 切换到项目目录
cd /home/liugu/workspace/stock

# 运行选股任务
python3 "$@"
