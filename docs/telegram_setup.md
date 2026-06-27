# Telegram Bot 推送搭建指南

## 步骤1: 创建 Telegram Bot

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置机器人名称（如：`StockAlertBot`）
4. 设置用户名（如：`stock_alert_xxx_bot`，必须以 `bot` 结尾）
5. 获得 **Bot Token**（格式：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

## 步骤2: 获取你的 Chat ID

方法一：给机器人发消息后访问
```
https://api.telegram.org/bot<你的TOKEN>/getUpdates
```

方法二：使用 @userinfobot
1. 搜索 `@userinfobot`
2. 发送任意消息
3. 它会返回你的 Chat ID

## 步骤3: 测试发送

```bash
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=测试消息"
```

## 步骤4: 配置到选股系统

编辑 ~/workspace/stock/cron/daily_task_config.json:
```json
{
    "telegram_token": "你的BOT_TOKEN",
    "telegram_chat_id": "你的CHAT_ID",
    "push_method": "telegram"
}
```

## 完整推送脚本

见：send_telegram.py
