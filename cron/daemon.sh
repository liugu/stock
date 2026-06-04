#!/bin/bash
# A股选股系统 - 后台守护进程
# 每30分钟检查一次，有新数据就运行选股

SCRIPT_DIR="/home/liugu/workspace/stock"
LOG_FILE="$SCRIPT_DIR/log/daemon.log"

while true; do
    HOUR=$(date +%H)
    MINUTE=$(date +%M)
    DAY=$(date +%u)  # 1-7, 1是周一
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') 守护进程检查中..." >> $LOG_FILE
    
    # 交易日 15:00-16:00 运行选股
    if [ $DAY -le 5 ] && [ $HOUR -eq 15 ]; then
        if [ $MINUTE -ge 30 ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') 开始运行选股任务" >> $LOG_FILE
            cd $SCRIPT_DIR && python3 quick_select.py >> $LOG_FILE 2>&1
            
            # 发送邮件推送
            cd $SCRIPT_DIR && python3 cron/send_email.py >> $LOG_FILE 2>&1
        fi
    fi
    
    # 交易日 18:00 运行消息面分析
    if [ $DAY -le 5 ] && [ $HOUR -eq 18 ] && [ $MINUTE -lt 30 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') 开始运行消息面分析" >> $LOG_FILE
        cd $SCRIPT_DIR && python3 cron/news_analysis.py --push >> $LOG_FILE 2>&1
    fi
    
    # 每30分钟检查一次
    sleep 1800
done
