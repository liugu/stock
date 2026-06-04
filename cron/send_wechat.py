#!/usr/bin/env python3
# -*- coding: utf-8 -*-"""发送选股结果到微信"""

import requests
import sys

# 企业微信机器人 webhook URL
# 请替换为你的实际 webhook URL
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=716e4d3e-8a8b-43a3-b67d-5d5f3e7c5a9b"

def send_message(content):
    """发送文本消息到企业微信"""
    data = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    try:
        r = requests.post(WEBHOOK_URL, json=data, timeout=30)
        result = r.json()
        if result.get('errcode') == 0:
            print("发送成功!")
            return True
        else:
            print(f"发送失败: {result}")
            return False
    except Exception as e:
        print(f"发送异常: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
    else:
        message = "【数据同步监督】自动检查完成 - 无异常"
    
    send_message(message)
