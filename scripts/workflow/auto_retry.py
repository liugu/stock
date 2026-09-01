#!/usr/bin/env python3
"""
自动重试脚本 - 每2分钟执行一次，无限重试直到成功
成功后将选股结果发送到飞书
"""
import sys
import os
import time
import json
import requests
import traceback
import datetime

# 项目路径
PROJECT_DIR = r'E:\量化研究\workspace\stock'
sys.path.insert(0, PROJECT_DIR)

# ========== 飞书配置 ==========
# 注意：App Secret 绝不硬编码进仓库（已被 GitHub 密钥扫描拦截）。
# 从环境变量或本地未提交的密钥文件读取。
FEISHU_APP_ID = os.environ.get('FEISHU_APP_ID', 'cli_aa9f0f0c99b95bda')

def _load_secret():
    s = os.environ.get('FEISHU_APP_SECRET')
    if s:
        return s.strip()
    for p in (os.path.join(PROJECT_DIR, 'feishu_secret.txt'),
              os.path.join(PROJECT_DIR, 'config', 'feishu_secret.txt')):
        if os.path.exists(p):
            v = open(p, encoding='utf-8').read().strip()
            if v:
                return v
    return ''

FEISHU_APP_SECRET = _load_secret()

# 飞书用户 ID (从 Hermes gateway 获取或手动设置)
FEISHU_USER_ID = "on_c7a116a8cd0c82db48fb99abac0cafbd"  # 你的飞书 open_id
# ===============================

def get_feishu_token():
    """获取飞书 access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload, timeout=10)
    result = response.json()
    if result.get('code') == 0:
        return result.get('tenant_access_token')
    else:
        print(f"获取 token 失败: {result}")
        return None

def send_feishu_message(user_id, title, content):
    """发送飞书消息给指定用户"""
    token = get_feishu_token()
    if not token:
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构建消息内容
    msg_content = {
        "zh_cn": {
            "title": title,
            "content": [[{"tag": "text", "text": content}]]
        }
    }
    
    params = {
        "receive_id_type": "open_id"
    }
    
    payload = {
        "receive_id": user_id,
        "msg_type": "post",
        "content": json.dumps(msg_content)
    }
    
    response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print("✓ 飞书消息发送成功")
        return True
    else:
        print(f"✗ 飞书消息发送失败: {result}")
        return False

def run_strategy():
    """运行策略选股"""
    print("开始运行数据更新和策略选股...")
    try:
        import instock.job.execute_daily_job as ej
        ej.main()
        return True, "策略选股执行完成"
    except SystemExit:
        return True, "策略选股执行完成"
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return False, error_msg

def fetch_stock_results():
    """从数据库获取选股结果"""
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
        
        # 获取所有策略选股表
        cur.execute("""
            SELECT table_name, MAX(date) as latest_date, COUNT(*) as stock_count 
            FROM information_schema.tables t
            WHERE table_schema = 'instock' AND table_name LIKE '%%strategy%%'
            GROUP BY table_name
            ORDER BY table_name
        """)
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return results
    except Exception as e:
        print(f"获取选股结果失败: {e}")
        return []

def main():
    """主函数 - 无限重试循环"""
    retry_count = 0
    
    # 检查飞书用户 ID
    global FEISHU_USER_ID
    
    # 尝试从环境变量获取
    FEISHU_USER_ID = os.environ.get('FEISHU_USER_ID')
    
    if not FEISHU_USER_ID:
        print("警告: 未设置飞书用户 ID，将只输出到控制台")
        print("请设置环境变量 FEISHU_USER_ID 或在脚本中配置")
    
    print("=" * 60)
    print("自动重试系统启动")
    print("每 2 分钟执行一次，直到成功")
    print("=" * 60)
    
    while True:
        retry_count += 1
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*60}")
        print(f"[第 {retry_count} 次] {current_time}")
        print(f"{'='*60}")
        
        # 运行策略选股
        success, message = run_strategy()
        
        if success:
            print(f"\n✓ 成功: {message}")
            
            # 获取选股结果
            results = fetch_stock_results()
            
            # 构建消息
            content = f"执行时间: {current_time}\n\n"
            
            if results:
                content += "策略选股结果:\n"
                for table_name, latest_date, count in results:
                    if table_name:
                        content += f"• {table_name}: {count}只 (日期:{latest_date})\n"
            else:
                content += "暂无选股数据"
            
            print("\n" + "=" * 60)
            print("选股结果:")
            print(content)
            print("=" * 60)
            
            # 发送飞书消息
            if FEISHU_USER_ID:
                send_feishu_message(FEISHU_USER_ID, "量化选股完成", content)
            else:
                print("\n提示: 设置 FEISHU_USER_ID 环境变量以启用飞书通知")
            
            print("\n✓ 任务成功完成")
            break
        else:
            print(f"\n✗ 失败: {message[:500]}")
            print(f"等待 2 分钟后重试...")
            time.sleep(120)  # 等待 2 分钟

if __name__ == '__main__':
    main()
