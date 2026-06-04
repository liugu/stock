#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram 推送模块"""

import requests
import json
import os

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'daily_task_config.json')


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def send_message(text, parse_mode='HTML'):
    """
    发送消息到 Telegram
    
    Args:
        text: 消息内容（支持 HTML 格式）
        parse_mode: 解析模式（HTML/Markdown）
    
    Returns:
        bool: 是否发送成功
    """
    config = load_config()
    
    token = config.get('telegram_token', '')
    chat_id = config.get('telegram_chat_id', '')
    
    if not token or not chat_id:
        print("错误: 未配置 Telegram Token 或 Chat ID")
        print("请编辑 daily_task_config.json 添加配置")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    try:
        r = requests.post(url, json=data, timeout=30)
        result = r.json()
        
        if result.get('ok'):
            print("Telegram 发送成功!")
            return True
        else:
            print(f"Telegram 发送失败: {result.get('description', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"Telegram 发送异常: {e}")
        return False


def send_stock_alert(stocks, date_str):
    """
    发送选股结果
    
    Args:
        stocks: 股票列表 [{'code': 'xxx', 'name': 'xxx', 'price': x, 'change': x, 'score': x, 'signal': 'xxx'}, ...]
        date_str: 日期字符串
    """
    # 构建消息
    lines = [
        f"<b>【A股策略选股结果】</b>",
        f"📅 {date_str}",
        f"📊 共找到 {len(stocks)} 只符合条件的股票",
        "",
        "<b>【TOP 10 推荐】</b>",
        ""
    ]
    
    for i, stock in enumerate(stocks[:10], 1):
        change_str = f"+{stock['change']:.2f}%" if stock['change'] >= 0 else f"{stock['change']:.2f}%"
        lines.append(
            f"{i}. <code>{stock['code']}</code> {stock['name']}\n"
            f"   💰 {stock['price']:.2f}元 | {change_str} | 得分:{stock['score']}\n"
            f"   📈 {stock['signal']}"
        )
    
    lines.extend([
        "",
        "━━━━━━━━━━━━━━",
        "策略: RSI + MACD + 均线",
        "筛选: 价格3-100元, 成交额>5000万"
    ])
    
    message = '\n'.join(lines)
    
    # Telegram 消息长度限制 4096
    if len(message) > 4000:
        message = message[:4000] + "\n... (内容过长，已截断)"
    
    return send_message(message)


def test_connection():
    """测试连接"""
    config = load_config()
    token = config.get('telegram_token', '')
    chat_id = config.get('telegram_chat_id', '')
    
    if not token:
        print("请先配置 telegram_token")
        return False
    
    if not chat_id:
        print("请先配置 telegram_chat_id")
        return False
    
    # 获取 bot 信息
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=10)
        result = r.json()
        
        if result.get('ok'):
            bot_name = result['result'].get('first_name', 'Unknown')
            bot_username = result['result'].get('username', 'Unknown')
            print(f"✅ Bot 连接成功!")
            print(f"   名称: {bot_name}")
            print(f"   用户名: @{bot_username}")
            return True
        else:
            print(f"❌ Bot 连接失败: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_connection()
        elif sys.argv[1] == 'send':
            # 测试发送
            test_message = """<b>测试消息</b>

这是一条测试消息，来自 A股选股系统。

✅ 如果收到此消息，说明配置成功！"""
            send_message(test_message)
    else:
        print("用法:")
        print("  python send_telegram.py test  - 测试连接")
        print("  python send_telegram.py send  - 发送测试消息")
