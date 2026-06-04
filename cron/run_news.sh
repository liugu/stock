#!/bin/bash
# 消息面分析启动脚本 - 清除代理
# 用法: bash cron/run_news.sh

# 清除所有代理设置
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY

# 进入项目目录
cd /home/liugu/workspace/stock

# 激活虚拟环境
source .venv/bin/activate

# 运行消息面分析脚本
python cron/news_analysis.py --push

echo "消息面分析完成"