#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速更新股票历史行情 - TickFlow 免费版批量并发
"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import pandas as pd
import numpy as np
from datetime import date

DB = {
    'host': 'localhost', 'user': 'stock', 'password': '12345678',
    'database': 'instock', 'port': 3306, 'charset': 'utf8mb4'
}

def safe_float(val):
    try:
        if val is None or (isinstance(val, float) and (pd.isna(val) or np.isinf(val))):
            return 0.0
        return float(val)
    except:
        return 0.0

def convert_code_to_symbol(code):
    if code.startswith('6'):
        return f'{code}.SH'
    elif code.startswith(('0', '3')):
        return f'{code}.SZ'
    elif code.startswith(('8', '4')):
        return f'{code}.BJ'
    return None

def main():
    from tickflow import TickFlow
    tf = TickFlow.free()

    print('=' * 60)
    print('快速更新股票行情 (TickFlow 免费版批量并发)')
    print('=' * 60)

    conn = pymysql.connect(**DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, code, name FROM stock_info 
        WHERE code LIKE '60%' OR code LIKE '00%' OR code LIKE '30%' OR code LIKE '68%'
        ORDER BY code
    """)
    all_stocks = cursor.fetchall()
    print(f'股票总数: {len(all_stocks)}')

    target_date = date.today().strftime('%Y-%m-%d')
    print(f'目标日期: {target_date}')

    cursor.execute('SELECT stock_id FROM stock_daily WHERE date = %s', (target_date,))
    existing = {r[0] for r in cursor.fetchall()}
    print(f'今日已有: {len(existing)} 条')

    to_update = [(sid, code, name) for sid, code, name in all_stocks if sid not in existing]
    print(f'需要更新: {len(to_update)} 只')

    if not to_update:
        print('数据已完整，无需更新')
        cursor.close()
        conn.close()
        return

    symbols_map = {}
    for sid, code, name in to_update:
        sym = convert_code_to_symbol(code)
        if sym:
            symbols_map[sym] = (sid, code, name)

    symbols = list(symbols_map.keys())
    print(f'转换后 {len(symbols)} 个 symbol')

    start_time = time.time()

    print('正在通过 TickFlow 批量获取数据...')
    result_dfs = tf.klines.batch(
        symbols, period='1d', count=5,
        as_dataframe=True, show_progress=True,
        max_workers=10, batch_size=100
    )
    fetch_time = time.time()
    print(f'数据获取完成, 耗时 {fetch_time - start_time:.1f}s')

    insert_sql = """INSERT INTO stock_daily (stock_id, date, open, close, high, low, volume, amount, change_percent, amplitude, turnover_rate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
        volume=VALUES(volume), amount=VALUES(amount), change_percent=VALUES(change_percent),
        amplitude=VALUES(amplitude), turnover_rate=VALUES(turnover_rate)"""

    success = 0
    fail = 0
    batch_data = []

    for sym, df in result_dfs.items():
        if df is None or df.empty:
            fail += 1
            continue

        info = symbols_map.get(sym)
        if not info:
            fail += 1
            continue
        stock_id, code, name = info

        try:
            row = df.iloc[-1]
            trade_date = str(row['trade_date'])[:10]

            if trade_date != target_date:
                fail += 1
                continue

            close = safe_float(row['close'])
            # 获取前收盘价用于计算涨跌幅
            if len(df) > 1:
                prev_close = safe_float(df.iloc[-2]['close'])
            else:
                prev_close = close
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0

            high = safe_float(row['high'])
            low = safe_float(row['low'])
            amplitude = ((high - low) / prev_close * 100) if prev_close > 0 else 0

            # TickFlow volume 以万手为单位，转换为股
            volume = safe_float(row.get('volume', 0)) * 10000 * 100  # 万手 -> 股
            amount = safe_float(row.get('amount', 0))

            batch_data.append((
                stock_id, trade_date,
                safe_float(row['open']), close, high, low,
                volume, amount,
                change_pct, amplitude, 0.0
            ))
            success += 1
        except Exception as e:
            fail += 1

    if batch_data:
        print(f'写入数据库 ({len(batch_data)} 条)...')
        cursor.executemany(insert_sql, batch_data)
        conn.commit()

    elapsed = time.time() - start_time
    print()
    print('=' * 60)
    print(f'完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed:.1f}s')

    cursor.execute('SELECT COUNT(*) FROM stock_daily WHERE date = %s', (target_date,))
    final_count = cursor.fetchone()[0]
    print(f'今日数据: {final_count} 条')

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
