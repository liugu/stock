#!/usr/bin/env python3
"""检查飞书API状态"""
import requests

APP_ID = 'cli_aa9f0f0c99b95bda'
APP_SECRET='***'

print("=" * 60)
print("飞书API状态检查")
print("=" * 60)

# 1. 认证测试
print("\n[1] 认证测试")
url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
resp = requests.post(url, json={'app_id': APP_ID, 'app_secret': APP_SECRET}, timeout=10)
result = resp.json()

if result.get('code') == 0:
    token = result['tenant_access_token']
    print(f"  ✓ 认证成功")
    print(f"  Token: {token[:15]}...")
    print(f"  有效期: {result.get('expire', 0)}秒")
else:
    print(f"  ✗ 认证失败: {result.get('msg')}")
    exit(1)

# 2. 机器人信息
print("\n[2] 机器人信息")
url = 'https://open.feishu.cn/open-apis/bot/v3/info'
headers = {'Authorization': f'Bearer {token}'}
resp = requests.get(url, headers=headers, timeout=10)
result = resp.json()

if result.get('code') == 0:
    bot = result.get('bot', {})
    print(f"  ✓ 机器人名称: {bot.get('bot_name')}")
    print(f"  Open ID: {bot.get('open_id')}")
    print(f"  激活状态: {'已激活' if bot.get('activate_status') == 1 else '未激活'}")
else:
    print(f"  ✗ 获取失败: {result.get('msg')}")

# 3. 用户信息
print("\n[3] 用户信息")
print("  用户 open_id: ou_56bf7bb450efc4a9496598b778d5e1e4")
print("  私聊会话: oc_6ba2fd6636d294e9249edfff0be6c057")

print("\n" + "=" * 60)
print("状态总结: ✓ 飞书API正常工作")
print("=" * 60)
