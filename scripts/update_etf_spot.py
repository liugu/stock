#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""更新ETF实时行情 (cn_etf_spot表)
数据源: 东方财富 push2delay (延迟行情，封版稳定)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import pymysql
import requests
from datetime import datetime
import time

BASE = 'https://push2delay.eastmoney.com/api/qt/clist/get'
FS = 'b:MK0021'  # 场内全部ETF(沪+深)
FIELDS = 'f2,f3,f4,f5,f6,f8,f12,f14,f15,f16,f17,f18,f20,f21'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0',
    'Referer': 'https://quote.eastmoney.com/',
}

def fetch_all():
    """分页抓取全部ETF行情（delay每页最多100条）"""
    all_data = []
    pn = 1
    pz = 100
    while True:
        params = {
            'pn': pn, 'pz': pz, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2,
            'fid': 'f6', 'fs': FS, 'fields': FIELDS
        }
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
            d = r.json().get('data')
            if not d or not d.get('diff'):
                break
            diff = d['diff']
            all_data.extend(diff)
            total = d.get('total', 0)
            pn += 1
            if len(all_data) >= total:
                break
            time.sleep(0.2)
        except Exception as e:
            print(f'  第{pn}页失败: {e}')
            break
    return all_data

def main():
    print('=' * 60)
    print(f'更新ETF实时行情 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)

    data = fetch_all()
    print(f'获取ETF: {len(data)} 只')

    if not data:
        print('❌ 获取失败')
        return

    today = datetime.now().strftime('%Y-%m-%d')
    conn = pymysql.connect(host='localhost', user='stock', password='12345678',
                           database='instock', port=3306, charset='utf8mb4')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM cn_etf_spot WHERE date=%s', (today,))
    print(f'删除今日旧数据: {cursor.rowcount} 条')

    insert_sql = """
        INSERT INTO cn_etf_spot (date, code, name, new_price, change_rate, ups_downs,
            volume, deal_amount, open_price, high_price, low_price, pre_close_price,
            turnoverrate, total_market_cap, free_cap)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    success = 0
    fail = 0
    for d in data:
        try:
            code = d.get('f12')
            name = d.get('f14')
            if not code or not name:
                fail += 1
                continue
            values = (
                today, code, name,
                d.get('f2'), d.get('f3'), d.get('f4'),
                int(d.get('f5') or 0), int(d.get('f6') or 0), d.get('f17'),
                d.get('f15'), d.get('f16'), d.get('f18'),
                d.get('f8'), int(d.get('f20') or 0), int(d.get('f21') or 0)
            )
            cursor.execute(insert_sql, values)
            success += 1
        except Exception as e:
            fail += 1
            if fail <= 3:
                print(f'  插入失败: {e}')

    conn.commit()
    cursor.execute('SELECT MAX(date), COUNT(*) FROM cn_etf_spot WHERE date=%s', (today,))
    max_date, cnt = cursor.fetchone()
    cursor.close()
    conn.close()

    print(f'✓ 完成: 成功{success}, 失败{fail}')
    print(f'✓ 今日日期: {max_date}, 记录数: {cnt}')
    print('=' * 60)

if __name__ == '__main__':
    main()