#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速更新股票历史行情 - 直接使用baostock"""
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
print("快速更新股票历史行情 - baostock直连")
print("=" * 60)

conn = pymysql.connect(**DB)
cursor = conn.cursor()

# 获取股票列表
cursor.execute('SELECT id, code, name FROM stock_info WHERE code LIKE "30%%" OR code LIKE "60%%" OR code LIKE "00%%" OR code LIKE "68%%"')
stock_map = {r[1]: (r[0], r[2]) for r in cursor.fetchall()}
total = len(stock_map)
print(f"共 {total} 只股票")

today = date.today()
end_str = today.strftime("%Y-%m-%d")
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"查询日期: {yesterday} ~ {end_str}")

lg = bs.login()
if lg.error_code != "0":
    print(f"Baostock登录失败: {lg.error_msg}")
    sys.exit(1)
print("login success!")

success = fail = skipped = 0
start_time = time.time()
batch_data = []
commit_interval = 300  # 每300条提交一次

for i, (code, (sid, name)) in enumerate(stock_map.items(), 1):
    try:
        if code.startswith(("600","601","603","605","688","689")):
            bs_code = f"sh.{code}"
        else:
            bs_code = f"sz.{code}"

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,adjustflag,turn",
            start_date=yesterday, end_date=end_str,
            frequency="d", adjustflag="2"
        )
        if rs.error_code != "0":
            fail += 1
            continue

        dl = []
        while rs.next():
            dl.append(rs.get_row_data())
        if not dl:
            skipped += 1
            continue

        df = pd.DataFrame(dl, columns=rs.fields)
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open","high","low","close","volume","amount","turn"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # 只取今天的数据
        td = df[df["date"] == pd.Timestamp(today)]
        if td.empty:
            skipped += 1
            continue

        row = td.iloc[-1]
        date_str = today.strftime("%Y-%m-%d")

        def sf(v):
            if v is None:
                return 0.0
            try:
                fv = float(v)
                return 0.0 if (np.isnan(fv) or np.isinf(fv)) else fv
            except:
                return 0.0

        # 涨跌幅
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            curr_close = float(row["close"])
            if prev_close > 0:
                change_pct = (curr_close - prev_close) / prev_close * 100
                amplitude = (float(row["high"]) - float(row["low"])) / prev_close * 100
            else:
                change_pct = 0.0
                amplitude = 0.0
        else:
            change_pct = 0.0
            amplitude = 0.0

        batch_data.append((
            sid, date_str,
            sf(row["open"]), sf(row["close"]),
            sf(row["high"]), sf(row["low"]),
            sf(row["volume"]), sf(row["amount"]),
            change_pct, amplitude, sf(row["turn"])
        ))
        success += 1

        if i % commit_interval == 0 or i == total:
            elapsed = int(time.time() - start_time)
            speed = i / elapsed if elapsed > 0 else 0
            print(f"[{i}/{total}] 成功:{success} 跳过:{skipped} 失败:{fail} 耗时:{elapsed}s ({speed:.0f}/s)")
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

# 最后提交
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

# 验证
cursor.execute("SELECT MAX(date) FROM stock_daily")
max_date = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM stock_daily WHERE date = %s", (max_date,))
cnt = cursor.fetchone()[0]
print(f"最新日期: {max_date}, 今日记录数: {cnt}")
conn.close()
