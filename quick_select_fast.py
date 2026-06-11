#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速策略选股 - 使用并发请求"""

import requests
import pandas as pd
import numpy as np
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
warnings.filterwarnings('ignore')

def simple_ma(data, period):
    return pd.Series(data).rolling(window=period).mean().values

def get_market_id(code):
    """获取市场ID，科创板688开头返回None表示不可交易"""
    if code.startswith(('600', '601', '603', '605')):
        return 1
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return 0
    # 688科创板暂时无法买入，返回None过滤掉
    return None

def get_hist_data(code, name, row):
    """获取单只股票的历史数据并分析"""
    market_id = get_market_id(code)
    if market_id is None:
        return None
    
    prefix = 'sh' if market_id == 1 else 'sz'
    hist_url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {'symbol': f'{prefix}{code}', 'scale': '240', 'ma': 'no', 'datalen': '100'}
    
    try:
        r = requests.get(hist_url, params=params, timeout=10)
        hist_data = r.json()
        if not hist_data or len(hist_data) < 60:
            return None
        
        hist_df = pd.DataFrame(hist_data)
        for col in ['open', 'close', 'high', 'low', 'volume']:
            hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')
        
        close = hist_df['close'].values
        
        # RSI
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
        avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.concatenate([[50] * 14, rsi])
        
        # MACD
        ema12 = pd.Series(close).ewm(span=12).mean()
        ema26 = pd.Series(close).ewm(span=26).mean()
        dif = (ema12 - ema26).values
        dea = pd.Series(dif).ewm(span=9).mean().values
        
        # 均线
        ma5 = simple_ma(close, 5)
        ma10 = simple_ma(close, 10)
        ma20 = simple_ma(close, 20)
        ma30 = simple_ma(close, 30)
        
        # 评分
        score = 0
        signals = []
        
        # RSI信号
        if rsi[-2] < 30 and rsi[-1] > rsi[-2]:
            score += 35
            signals.append('RSI超卖回升')
        elif 30 < rsi[-1] < 70 and rsi[-1] > rsi[-2]:
            score += 20
            signals.append('RSI向上')
        
        # MACD信号
        if dif[-2] < dea[-2] and dif[-1] > dea[-1]:
            score += 30
            signals.append('MACD金叉')
        elif dif[-1] > 0 and dea[-1] > 0 and dif[-1] > dif[-2]:
            score += 15
            signals.append('MACD多头')
        
        # 均线信号
        if ma5[-1] > ma10[-1] > ma20[-1] > ma30[-1]:
            score += 25
            signals.append('均线多头')
        elif ma5[-2] < ma20[-2] and ma5[-1] > ma20[-1]:
            score += 20
            signals.append('均线金叉')
        
        if score >= 30:
            return {
                '代码': code,
                '名称': name,
                '最新价': row['最新价'],
                '涨跌幅': row['涨跌幅'],
                '市盈率': row['市盈率'],
                '综合得分': score,
                '信号': ', '.join(signals)
            }
    except:
        pass
    return None

print('=' * 60)
print('A股策略选股 (RSI + MACD + 均线) - 并发版')
print('=' * 60)

# 获取实时行情
print('\n[1/3] 获取实时行情...')
url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
all_data = []
for page in range(1, 50):
    params = {'page': str(page), 'num': '100', 'sort': 'changepercent', 'asc': '0', 'node': 'hs_a'}
    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        if not data:
            break
        all_data.extend(data)
        if page % 10 == 0:
            print(f'      已获取 {len(all_data)} 只...')
    except:
        break

df = pd.DataFrame(all_data)
df = df.rename(columns={'code': '代码', 'name': '名称', 'trade': '最新价', 'changepercent': '涨跌幅', 'amount': '成交额', 'mktcap': '总市值', 'per': '市盈率', 'pb': '市净率'})
for col in ['最新价', '涨跌幅', '成交额', '总市值', '市盈率', '市净率']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

print(f'      共获取 {len(df)} 只股票')

# 筛选
print('\n[2/3] 筛选候选股票...')
candidates = df[
    (df['最新价'] > 3) & (df['最新价'] < 100) &
    (df['成交额'] > 50000000) & (df['总市值'] > 200000) &
    (df['市盈率'] > 0) & (df['市盈率'] < 100)
].copy()
print(f'      筛选后剩余 {len(candidates)} 只')

# 并发获取历史数据并分析
print('\n[3/3] 分析策略信号 (并发处理)...')
results = []
total = min(len(candidates), 200)  # 限制分析数量

with ThreadPoolExecutor(max_workers=20) as executor:
    futures = []
    for _, row in candidates.head(total).iterrows():
        futures.append(executor.submit(get_hist_data, row['代码'], row['名称'], row))
    
    completed = 0
    for future in as_completed(futures):
        completed += 1
        if completed % 50 == 0:
            print(f'      进度: {completed}/{total}')
        result = future.result()
        if result:
            results.append(result)

# 输出结果
print('\n' + '=' * 60)
print('选股结果')
print('=' * 60)

if results:
    results_df = pd.DataFrame(results).sort_values('综合得分', ascending=False)
    print(f'\n共找到 {len(results_df)} 只符合条件的股票，展示前10只:\n')
    
    for i, (_, row) in enumerate(results_df.head(10).iterrows(), 1):
        print(f"【{i}】{row['代码']} {row['名称']}")
        print(f"    价格: {row['最新价']:.2f}元 | 涨跌: {row['涨跌幅']:.2f}% | PE: {row['市盈率']:.1f}")
        print(f"    得分: {row['综合得分']}分 | 信号: {row['信号']}")
        print()
    
    # 保存结果
    output_file = f"策略选股_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df.to_excel(output_file, index=False)
    print(f"结果已保存: {output_file}")
else:
    print('\n未找到符合条件的股票')

print('=' * 60)
