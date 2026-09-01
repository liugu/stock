#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 Playwright 打开雪球，通过 JS 直接调用 API 发帖"""
import os, sys, glob, json, time
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
report_dir = 'E:/量化研究/workspace/stock/output/review'
report_file = f'{report_dir}/review_{today}.txt'

if not os.path.exists(report_file):
    files = sorted(glob.glob(f'{report_dir}/review_*.txt'), reverse=True)
    if not files:
        print('❌ 无复盘报告')
        sys.exit(1)
    report_file = files[0]

with open(report_file, 'r', encoding='utf-8') as f:
    content = f.read()

print(f'📄 报告: {len(content)} 字')

chromium_path = os.path.expanduser(
    '~/AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe'
)
user_data_dir = os.path.expanduser('~/AppData/Local/Google/Chrome/User Data')

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path=chromium_path,
        headless=True,
        args=['--no-sandbox'],
    )
    page = browser.new_page()

    print('🌐 打开雪球...')
    page.goto('https://xueqiu.com/', wait_until='domcontentloaded', timeout=30000)
    time.sleep(3)
    print(f'  标题: {page.title()}')

    # 通过 JS 直接从页面发 API 请求
    print('📤 通过 JS 发帖...')
    result = page.evaluate('''(text) => {
        return fetch('/statuses/update.json', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'status=' + encodeURIComponent(text)
        }).then(r => r.text());
    }''', content)

    print(f'  结果: {result[:300]}')

    if '"id"' in result or '"status"' in result:
        print('✅ 发帖成功！')
        try:
            resp = json.loads(result)
            pid = resp.get('id', '?')
            uid = resp.get('user_id', '?')
            print(f'  链接: https://xueqiu.com/{uid}/{pid}')
        except:
            pass
    else:
        print('❌ 发帖失败')

    page.screenshot(path='output/xq_result.png')
    browser.close()
    print('✅ 完成')