#!/usr/bin/env python3
"""
测试脚本 - 测试数据库连接和飞书通知
"""
import sys
import os
import json
import requests

# ========== 飞书配置 ==========
FEISHU_APP_ID = 'cli_aa9f0f0c99b95bda'
FEISHU_APP_SECRET='nvzP9L...gwEd'
FEISHU_USER_ID = "on_c7a116a8cd0c82db48fb99abac0cafbd"
# ===============================

print("开始测试...")

# 测试数据库连接
print("\n1. 测试数据库连接...")
try:
    import pymysql
    conn = pymysql.connect(
        host='localhost',
        user='stock',
        password='12345678',
        database='instock',
        port=3306
    )
    cur = conn.cursor()
    cur.execute('SHOW TABLES')
    tables = cur.fetchall()
    print(f"   ✓ 数据库连接成功，共 {len(tables)} 张表")
    cur.close()
    conn.close()
except Exception as e:
    print(f"   ✗ 数据库连接失败: {e}")

# 测试飞书通知
print("\n2. 测试飞书通知...")
try:
    # 获取 token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        token = result.get('tenant_access_token')
        print(f"   ✓ 获取 token 成功")
        
        # 发送消息
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        msg_content = {
            "zh_cn": {
                "title": "Hermes 测试消息",
                "content": [[{"tag": "text", "text": "测试成功！飞书通知功能正常。"}]]
            }
        }
        
        params = {"receive_id_type": "open_id"}
        payload = {
            "receive_id": FEISHU_USER_ID,
            "msg_type": "post",
            "content": json.dumps(msg_content)
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            print("   ✓ 飞书消息发送成功！")
        else:
            print(f"   ✗ 飞书消息发送失败: {result}")
    else:
        print(f"   ✗ 获取 token 失败: {result}")
        
except Exception as e:
    print(f"   ✗ 飞书通知测试失败: {e}")

print("\n测试完成！")
