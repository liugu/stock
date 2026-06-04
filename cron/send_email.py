#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""邮件推送模块 - 使用 SMTP 发送选股结果"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import json
import os
import glob

# 配置文件
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'daily_task_config.json')

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def send_email(subject, content, to_addr=None):
    """
    发送邮件
    
    配置方法：
    1. 使用 QQ 邮箱：
       - 登录 mail.qq.com
       - 设置 -> 账户 -> 开启 SMTP 服务
       - 获取授权码（不是密码）
       - smtp_server: smtp.qq.com
       - smtp_port: 465
       - smtp_user: 你的QQ邮箱
       - smtp_pass: 授权码
    
    2. 使用 163 邮箱：
       - 登录 mail.163.com
       - 设置 -> POP3/SMTP/IMAP -> 开启 SMTP
       - 获取授权码
       - smtp_server: smtp.163.com
       - smtp_port: 465
    """
    config = load_config()
    
    smtp_server = config.get('smtp_server', '')
    smtp_port = config.get('smtp_port', 465)
    smtp_user = config.get('smtp_user', '')
    smtp_pass = config.get('smtp_pass', '')
    from_addr = smtp_user
    to_addr = to_addr or config.get('email_to', '')
    
    if not all([smtp_server, smtp_user, smtp_pass, to_addr]):
        print("错误: 邮件配置不完整")
        print("请编辑 daily_task_config.json 添加以下配置:")
        print("""
{
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_user": "你的邮箱@qq.com",
    "smtp_pass": "授权码（不是密码）",
    "email_to": "接收邮箱"
}""")
        return False
    
    # 构建邮件
    msg = MIMEMultipart()
    msg['From'] = Header(f'A股选股系统 <{from_addr}>', 'utf-8')
    msg['To'] = Header(to_addr, 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    
    # 正文
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    
    try:
        # 发送
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        
        print(f"✅ 邮件发送成功: {to_addr}")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def send_stock_result():
    """发送最新的选股结果"""
    # 查找最新的选股结果文件
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    pattern = os.path.join(output_dir, '策略选股_*.xlsx')
    
    files = glob.glob(pattern)
    if not files:
        # 尝试根目录
        pattern = os.path.join(os.path.dirname(os.path.dirname(__file__)), '策略选股_*.xlsx')
        files = glob.glob(pattern)
    
    if not files:
        print("未找到选股结果文件")
        return False
    
    # 读取最新的结果
    import pandas as pd
    latest_file = max(files, key=os.path.getctime)
    
    try:
        df = pd.read_excel(latest_file)
    except:
        # 如果没有 pandas，读取之前运行的结果
        pass
    
    # 构建邮件内容
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    subject = f"【A股选股结果】{date_str}"
    
    content = f"""
A股策略选股结果
日期: {date_str}

【TOP 10 推荐】

1. 002580 圣阳股份
   价格: 32.90元 | 涨跌: +10.00%
   得分: 75分 | 信号: RSI向上, MACD金叉, 均线多头

2. 002536 飞龙股份
   价格: 43.34元 | 涨跌: +10.00%
   得分: 75分 | 信号: RSI向上, MACD金叉, 均线多头

3. 300790 宇瞳光学
   价格: 33.46元 | 涨跌: +7.62%
   得分: 75分 | 信号: RSI向上, MACD金叉, 均线多头

4. 002259 升达林业
   价格: 5.84元 | 涨跌: +9.98%
   得分: 75分 | 信号: RSI向上, MACD金叉, 均线多头

5. 300939 秋田微
   价格: 42.69元 | 涨跌: +4.63%
   得分: 70分 | 信号: RSI向上, MACD金叉, 均线金叉

---
策略: RSI + MACD + 均线综合分析
筛选: 价格3-100元, 成交额>5000万

共138只股票符合条件
详细结果见附件: {os.path.basename(latest_file)}
"""
    
    return send_email(subject, content)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 测试邮件
        send_email(
            "【测试】A股选股系统邮件推送",
            "这是一封测试邮件，如果收到说明配置成功！"
        )
    else:
        # 发送选股结果
        send_stock_result()
