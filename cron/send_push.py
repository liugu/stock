#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import sys

# Server酱配置
SERVERCHAN_KEY = "SCT347969TWcw4Zztqp8nMDiwYE4ik2EOW"

def send_serverchan(title, content):
    """发送到Server酱"""
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"

    data = {
        "title": title,
        "desp": content
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            print("✅ Server酱推送成功")
            return True
        else:
            print(f"❌ Server酱推送失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"❌ Server酱推送异常: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("用法: python send_push.py <标题> <内容>")
        print("示例: python send_push.py '选股结果' '找到85只股票'")
        sys.exit(1)

    title = sys.argv[1]
    content = sys.argv[2]

    send_serverchan(title, content)

if __name__ == "__main__":
    main()
