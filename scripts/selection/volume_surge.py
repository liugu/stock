#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""成交量连续上涨选股 — 连续3日放量+价格配合"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pymysql
import numpy as np
import pandas as pd
from datetime import date, timedelta

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
TODAY = date.today()
LOOKBACK = 60  # 取60天数据

def main():
    conn = pymysql.connect(**DB)
    
    # 1. 获取所有非科创板股票ID
    sql = """SELECT i.id, i.code, i.name FROM stock_info i 
             WHERE (i.code LIKE '60%' OR i.code LIKE '00%' OR i.code LIKE '30%')
             AND i.code NOT LIKE '688%' ORDER BY i.code"""
    stocks = pd.read_sql(sql, conn)
    
    # 2. 获取日期范围
    end_date = TODAY
    start_date = end_date - timedelta(days=LOOKBACK+10)
    
    # 3. 批量获取日K数据
    placeholders = ','.join(['%s'] * len(stocks))
    sql_daily = f"""SELECT sd.stock_id, sd.date, sd.close, sd.volume, sd.change_percent, sd.turnover_rate
                    FROM stock_daily sd
                    WHERE sd.stock_id IN ({placeholders})
                    AND sd.date >= %s AND sd.date <= %s
                    ORDER BY sd.stock_id, sd.date"""
    params = list(stocks['id'].values) + [start_date, end_date]
    daily = pd.read_sql(sql_daily, conn, params=params)
    
    # 4. 获取实时行情
    codes = stocks['code'].tolist()
    placeholders2 = ','.join(['%s'] * len(codes))
    sql_spot = f"""SELECT cs.code, cs.new_price, cs.change_rate, cs.turnoverrate, 
                   cs.total_market_cap, cs.industry
                   FROM cn_stock_spot cs
                   WHERE cs.code IN ({placeholders2})
                   AND cs.date = (SELECT MAX(date) FROM cn_stock_spot)"""
    spot = pd.read_sql(sql_spot, conn, params=codes)
    
    conn.close()
    
    # 5. 逐只分析
    results = []
    for _, stock in stocks.iterrows():
        sid = stock['id']
        df = daily[daily['stock_id'] == sid].copy()
        if len(df) < 10:
            continue
        
        df = df.sort_values('date')
        closes = df['close'].values
        volumes = df['volume'].values
        chgs = df['change_percent'].values
        
        last_vols = volumes[-5:]  # 最近5天成交量
        last_chgs = chgs[-5:]     # 最近5天涨跌幅
        last_closes = closes[-5:]
        
        # 判断成交量是否连续上涨（至少3天连续放大）
        vol_up_days = 0
        max_vol_up = 0
        for i in range(len(last_vols)-1, 0, -1):
            if last_vols[i] > last_vols[i-1] * 1.05:  # 比前一日增长5%+
                vol_up_days += 1
                if vol_up_days > max_vol_up:
                    max_vol_up = vol_up_days
            else:
                break
        
        # 连续放量天数
        consecutive_up = max_vol_up
        
        # 成交量与60日均量比
        avg_vol_60 = np.mean(volumes[-min(60, len(volumes)):])
        latest_vol = volumes[-1]
        vol_ratio = latest_vol / avg_vol_60 if avg_vol_60 > 0 else 1
        
        # 最近3天平均量比
        avg_vol_3 = np.mean(volumes[-3:]) if len(volumes) >= 3 else latest_vol
        vol_ratio_3 = avg_vol_3 / avg_vol_60 if avg_vol_60 > 0 else 1
        
        # 价格配合检查
        price_up_days = sum(1 for c in last_chgs if c > 0)
        price_dn_days = sum(1 for c in last_chgs if c < 0)
        last_chg = last_chgs[-1]
        
        # 均线
        if len(closes) >= 5:
            ma5 = np.mean(closes[-5:])
        else:
            ma5 = closes[-1]
        if len(closes) >= 10:
            ma10 = np.mean(closes[-10:])
        else:
            ma10 = ma5
        if len(closes) >= 20:
            ma20 = np.mean(closes[-20:])
        else:
            ma20 = ma10
        
        bullish = ma5 > ma10 > ma20
        above_ma5 = closes[-1] > ma5
        
        # 评分
        score = 0
        
        # 成交量连续上涨得分 (0-40)
        if consecutive_up >= 4:
            score += 40
        elif consecutive_up >= 3:
            score += 30
        elif consecutive_up >= 2:
            score += 20
        elif vol_ratio_3 > 1.5:
            score += 15  # 虽然没有严格连续放大，但三日均量显著放大
        
        # 量比得分 (0-20)
        if vol_ratio > 2.0:
            score += 20
        elif vol_ratio > 1.5:
            score += 15
        elif vol_ratio > 1.2:
            score += 10
        
        # 价格配合得分 (0-20)
        if price_up_days >= 3 and last_chg > 0:
            score += 20
        elif price_up_days >= 2 and last_chg > 0:
            score += 15
        elif last_chg > 0:
            score += 8
        elif price_dn_days >= 3 and consecutive_up >= 3:
            score -= 10  # 连续放量下跌（出货信号）
        
        # 技术形态得分 (0-20)
        if bullish:
            score += 12
        if above_ma5:
            score += 8
        
        # 最低要求：至少连续2日放量或量比>1.5
        if consecutive_up < 2 and vol_ratio_3 < 1.5:
            continue
        
        # 涨幅领先的额外加分
        hot_score = 0
        if last_chg > 5:
            hot_score = min(15, int(last_chg * 1.5))
        
        total = min(score + hot_score, 100)
        
        # 获取实时行情
        sp = spot[spot['code'] == stock['code']]
        if sp.empty:
            continue
        r = sp.iloc[0]
        
        results.append({
            'name': stock['name'],
            'code': stock['code'],
            'price': r['new_price'],
            'chg': r['change_rate'] or 0,
            'turnover': r['turnoverrate'] or 0,
            'cap': r['total_market_cap'] or 0,
            'industry': r['industry'] or '',
            'vol_up_days': consecutive_up,
            'vol_ratio': round(vol_ratio, 2),
            'vol_ratio_3': round(vol_ratio_3, 2),
            'price_up_days': price_up_days,
            'bullish': bullish,
            'total': total,
            'score': score,
        })
    
    # 排序输出
    results.sort(key=lambda x: (-x['total'], -x['vol_up_days']))
    
    print('=' * 65)
    print('  成交量连续上涨选股  %s' % TODAY)
    print('=' * 65)
    
    strong = [r for r in results if r['total'] >= 65]
    watch = [r for r in results if 50 <= r['total'] < 65]
    
    print('\n🏆 强势放量股 (评分>=65) — %d只' % len(strong))
    print('=' * 65)
    for r in strong[:20]:
        vtag = '连升%d日' % r['vol_up_days'] if r['vol_up_days'] >= 2 else '量比%.2f' % r['vol_ratio_3']
        chg_sym = '+' if r['chg'] > 0 else ''
        print('  %s(%s) %.2f %s%.2f%%' % (r['name'], r['code'], r['price'], chg_sym, r['chg']))
        print('    放量:%s | 量比%.2f | 涨多跌少:%d/%d | 多头:%s | 评分%d' % 
              (vtag, r['vol_ratio'], r['price_up_days'], 5-r['price_up_days'], 'Y' if r['bullish'] else 'N', r['total']))
        print()
    
    print('\n📋 关注池 (评分50-64) — %d只' % len(watch))
    print('=' * 65)
    for r in watch[:10]:
        print('  %s(%s) %.2f %+.2f%% | 放量%d日 | 量比%.2f | 评分%d' % 
              (r['name'], r['code'], r['price'], r['chg'], r['vol_up_days'], r['vol_ratio'], r['total']))
    
    # 保存
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'volume_surge_%s.csv' % TODAY.strftime('%Y%m%d'))
    cols = ['name','code','price','chg','turnover','industry','vol_up_days','vol_ratio','vol_ratio_3','price_up_days','bullish','total','score']
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(','.join(cols) + '\n')
        for r in results:
            f.write(','.join(str(r[c]) for c in cols) + '\n')
    print('\n结果已保存: %s' % out_file)


if __name__ == '__main__':
    main()