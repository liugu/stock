#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ETF网格交易回测 - 用腾讯行情历史K线
网格策略：历史价格穿越网格价位时的套利轮数统计
"""
import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')

GTIMG = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120.0'}

# 候选ETF: (名称, 腾讯代码, secid市场)
CANDIDATES = [
    ('有色金属ETF南方 512400', 'sh512400'),
    ('通信ETF国泰 515880', 'sh515880'),
    ('芯片ETF华夏 159995', 'sz159995'),
    ('科创50ETF华夏 588000', 'sh588000'),
]

def fetch_kline(tencent_code, days=180):
    """从腾讯抓历史日K线 [date, open, close, high, low, vol]"""
    params = {'param': f'{tencent_code},day,,,{days},qfq'}
    r = requests.get(GTIMG, params=params, headers=HEADERS, timeout=20)
    data = r.json().get('data', {})
    sec = data.get(tencent_code, {})
    klines = sec.get('qfqday') or sec.get('day') or []
    rows = []
    for k in klines:
        rows.append({'date': k[0], 'open': float(k[1]), 'close': float(k[2]),
                     'high': float(k[3]), 'low': float(k[4]), 'vol': float(k[5])})
    return rows

def grid_backtest(rows, lower, upper, n_grid):
    """网格回测：统计价格穿越网格时的套利轮数
    lower~upper区间均分n_grid格，价格下穿买入/上穿卖出，完成一买一卖=1轮套利
    返回: 完成轮数、收盘持有格数
    """
    step = (upper - lower) / n_grid
    levels = [lower + step * i for i in range(1, n_grid)]
    n_buy = 0
    rounds = 0
    prev = None
    for r in rows:
        p = r['close']
        if prev is not None:
            lo, hi = min(prev, p), max(prev, p)
            for lv in levels:
                if lo <= lv <= hi:
                    if p < prev:  # 下穿 -> 买入
                        n_buy += 1
                    else:  # 上穿 -> 卖出
                        if n_buy > 0:
                            n_buy -= 1
                            rounds += 1
        prev = p
    return rounds, n_buy

def main():
    print('=' * 62)
    print('ETF网格回测 (腾讯历史K线)')
    print('=' * 62)
    for name, code in CANDIDATES:
        rows = fetch_kline(code)
        if not rows:
            print(f'\n{name}: 抓取失败')
            continue
        closes = [r['close'] for r in rows]
        cur = closes[-1]
        lo30, hi30 = min(closes[-30:]), max(closes[-30:])
        loA, hiA = min(closes), max(closes)
        span = hiA - loA
        print(f'\n=== {name} ===')
        print(f'  现价:{cur:.3f}  30日[{lo30:.3f}~{hi30:.3f}]  全部[{loA:.3f}~{hiA:.3f}]  历史跨度{span:.3f}')
        print(f'  数据{len(rows)}根日K, 最近:{rows[-1]["date"]}')
        print('  网格区间(±%):      8格轮数  |  10格轮数')
        for w in [0.10, 0.15, 0.20, 0.30]:
            lower = cur * (1 - w)
            upper = cur * (1 + w)
            r8, h8 = grid_backtest(rows, lower, upper, 8)
            r10, h10 = grid_backtest(rows, lower, upper, 10)
            # 用历史实际波动区间做参照
            print(f'  ±{int(w*100):>2}% [$ {lower:.3f}~{upper:.3f}]:  {r8:>4}轮(剩{h8}格) | {r10:>4}轮(剩{h10}格)')
        time.sleep(0.4)
    print('\n' + '=' * 62)

if __name__ == '__main__':
    main()