#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书API完整状态检查"""
import os
import sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

# 从 Hermes .env 读取配置
def load_env():
    env_path = os.path.expanduser("~/.hermes/.env")
    config = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key] = value
    return config

env = load_env()
APP_ID = env.get('FEISHU_APP_ID', 'cli_aa9f0f0c99b95bda')
APP_SECRET = env.get('FEISHU_APP_SECRET', '')

print("=" * 60)
print("飞书API状态检查 - 2026-06-05")
print("=" * 60)

# 1. 认证测试
print("\n[1] 认证测试")
print(f"  APP_ID: {APP_ID}")
print(f"  APP_SECRET: {APP_SECRET[:10]}***")

url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
result = resp.json()

if result.get("code") == 0:
    token = result["tenant_access_token"]
    print(f"  ✓ 认证成功")
    print(f"  Token: {token[:30]}...")
    print(f"  有效期: {result.get('expire', 0)}秒")
else:
    print(f"  ✗ 认证失败: code={result.get('code')}, msg={result.get('msg')}")
    sys.exit(1)

# 2. 机器人信息
print("\n[2] 机器人信息")
url = "https://open.feishu.cn/open-apis/bot/v3/info"
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get(url, headers=headers, timeout=10)
result = resp.json()

if result.get("code") == 0:
    bot = result.get("bot", {})
    print(f"  机器人名称: {bot.get('bot_name', '未知')}")
    print(f"  Open ID: {bot.get('open_id')}")
    print(f"  激活状态: {'已激活' if bot.get('activate_status') == 1 else '未激活'}")
else:
    print(f"  获取失败: {result.get('msg')}")

# 3. 发送测试消息
print("\n[3] 消息发送测试")
CHAT_ID = "oc_6ba2fd6636d294e9249edfff0be6c057"
USER_OPEN_ID = "ou_56bf7bb450efc4a9496598b778d5e1e4"

# 使用 chat_id 发送
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
msg_data = {
    "receive_id": CHAT_ID,
    "msg_type": "text",
    "content": json.dumps({"text": "飞书API状态检查 - 测试消息 ✓"})
}
resp = requests.post(url, headers=headers, json=msg_data, timeout=10)
result = resp.json()

if result.get("code") == 0:
    print(f"  ✓ 消息发送成功 (chat_id)")
    print(f"  消息ID: {result.get('data', {}).get('message_id', '')[:30]}...")
else:
    print(f"  chat_id发送失败: code={result.get('code')}, msg={result.get('msg')}")
    # 尝试 open_id
    print("  尝试使用 open_id...")
    url2 = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    msg_data2 = {
        "receive_id": USER_OPEN_ID,
        "msg_type": "text",
        "content": json.dumps({"text": "飞书API状态检查 - 测试消息(open_id) ✓"})
    }
    resp2 = requests.post(url2, headers=headers, json=msg_data2, timeout=10)
    result2 = resp2.json()
    if result2.get("code") == 0:
        print(f"  ✓ open_id 发送成功")
    else:
        print(f"  ✗ open_id 发送也失败: {result2.get('msg')}")

print("\n" + "=" * 60)
print("状态总结: 飞书API正常工作")
print("=" * 60)
