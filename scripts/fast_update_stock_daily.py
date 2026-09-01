#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速更新股票历史行情 - 仅更新今日数据"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np
from datetime import date, timedelta
import baostock as bs

DB = {'host': 'localhost', 'user': 'stock', 'password': '12345678',
      'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'}

print("=" * 60)
print("快速更新股票历史行情 - 仅今日数据")
print("=" * 60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%%" OR code LIKE "60%%" OR code LIKE "00%%" OR code LIKE "68%%"')
stock_map = {r[1]: (r[0], r[2]) for r in cursor.fetchall()}
print(f"共 {len(stock_map)} 只股票")

today = date.today()
end_date = today.strftime("%Y%m%d")
yesterday = (today - timedelta(days=1)).strftime("%Y%m%d")
print(f"更新日期范围: {yesterday} - {end_date}")

lg = bs.login()
if lg.error_code != "0":
    print(f"baostock登录失败: {lg.error_msg}")
    sys.exit(1)
print("login success!")

success = fail = skipped = 0
start_time = time.time()
batch_data = []

for i, (code, (sid, name)) in enumerate(stock_map.items(), 1):
    try:
        if code.startswith(("600","601","603","605","688","689")):
            bs_code = f"sh.{code}"
        else:
            bs_code = f"sz.{code}"
        rs = bs.query_history_k_data_plus(
            bs_code, "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pbMRQ,peTTM",
            start_date=yesterday, end_date=end_date, frequency="d", adjustflag="2")
        if rs.error_code != "0":
            fail += 1
            if i <= 3 or i % 500 == 0:
                print(f"[{i}/{len(stock_map)}] {code} 查询失败: {rs.error_msg}")
            continue
        dl = []
        while (rs.error_code == "0") & rs.next():
            dl.append(rs.get_row_data())
        if not dl:
            skipped += 1
            continue
        df = pd.DataFrame(dl, columns=rs.fields)
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open","high","low","close","volume","amount","turn"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        td = df[df["date"] == pd.Timestamp(today)]
        if td.empty:
            skipped += 1
            continue
        row = td.iloc[-1]
        date_str = today.strftime("%Y-%m-%d")
        def sf(v):
            if v is None: return 0.0
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return 0.0
            return float(v)
        if len(df) >= 2:
            pc = float(df.iloc[-2]["close"])
            cc = float(row["close"])
            cp = ((cc - pc) / pc * 100) if pc > 0 else 0.0
            amp = ((float(row["high"]) - float(row["low"])) / pc * 100) if pc > 0 else 0.0
        else:
            cp = amp = 0.0
        batch_data.append((sid, date_str, sf(row["open"]), sf(row["close"]),
                          sf(row["high"]), sf(row["low"]), sf(row["volume"]),
                          sf(row["amount"]), cp, amp, sf(row["turn"])))
        success += 1
        if i % 200 == 0:
            elapsed = int(time.time() - start_time)
            print(f"进度: {i}/{len(stock_map)} 成功:{success} 失败:{fail} 跳过:{skipped} 耗时:{elapsed}s")
            if batch_data:
                sql = """INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),low=VALUES(low),
                volume=VALUES(volume),amount=VALUES(amount),change_percent=VALUES(change_percent),
                amplitude=VALUES(amplitude),turnover_rate=VALUES(turnover_rate)"""
                cursor.executemany(sql, batch_data)
                conn.commit()
                batch_data = []
    except Exception as e:
        fail += 1
        if i <= 3:
            print(f"[{i}] {code} 异常: {e}")

if batch_data:
    sql = """INSERT INTO stock_daily (stock_id,date,open,close,high,low,volume,amount,change_percent,amplitude,turnover_rate)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE open=VALUES(open),close=VALUES(close),high=VALUES(high),low=VALUES(low),
    volume=VALUES(volume),amount=VALUES(amount),change_percent=VALUES(change_percent),
    amplitude=VALUES(amplitude),turnover_rate=VALUES(turnover_rate)"""
    cursor.executemany(sql, batch_data)
    conn.commit()

bs.logout()
elapsed = int(time.time() - start_time)
print(f"\n完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}, 耗时 {elapsed}s")
cursor.execute("SELECT MAX(date) FROM stock_daily")
print(f"最新日期: {cursor.fetchone()[0]}")
cursor.close()
conn.close()
