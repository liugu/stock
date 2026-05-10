#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股票深度分析"""

import requests
import pandas as pd
import numpy as np

def simple_ma(data, period):
    return pd.Series(data).rolling(window=period).mean().values

def analyze_stock(code, name_prefix='sz'):
    """分析指定股票"""

    print('=' * 60)
    print(f'股票深度分析: {code}')
    print('=' * 60)

    # 获取历史数据
    print(f"\n【历史数据】")
    hist_url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {'symbol': f'{name_prefix}{code}', 'scale': '240', 'ma': 'no', 'datalen': '250'}
    r = requests.get(hist_url, params=params, timeout=30)
    hist_data = r.json()

    if not hist_data or len(hist_data) == 0:
        print('无法获取历史数据，股票可能已退市或停牌')
        return

    hist_df = pd.DataFrame(hist_data)
    hist_df = hist_df.rename(columns={'day': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'})
    for col in ['open', 'close', 'high', 'low', 'volume']:
        hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')

    # 获取实时行情
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    params_rt = {'page': '1', 'num': '5000', 'sort': 'changepercent', 'asc': '0', 'node': 'hs_a'}
    try:
        r = requests.get(url, params=params_rt, timeout=30)
        data = r.json()
        df = pd.DataFrame(data)
        stock = df[df['code'] == code]

        if len(stock) > 0:
            s = stock.iloc[0]
            print(f"\n【基本信息】")
            print(f"代码: {s['code']} | 名称: {s['name']}")
            print(f"最新价: {s['trade']}元 | 涨跌幅: {s['changepercent']}%")
            print(f"今开: {s['open']} | 最高: {s['high']} | 最低: {s['low']} | 昨收: {s['settlement']}")
            print(f"成交量: {int(float(s['volume']))}手 | 成交额: {int(float(s['amount']))}元")
            print(f"总市值: {float(s['mktcap'])*10000/1e8:.2f}亿 | 流通市值: {float(s['nmc'])*10000/1e8:.2f}亿")
            print(f"市盈率: {s['per']} | 市净率: {s['pb']} | 换手率: {s['turnoverratio']}%")
    except:
        print(f"\n【基本信息】")
        print(f"代码: {code} | 名称: 远大控股")
        print(f"(实时行情暂不可用)")

    print(f"\n【历史数据】")
    hist_df = hist_df.rename(columns={'day': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'})
    for col in ['open', 'close', 'high', 'low', 'volume']:
        hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')

    print(f"数据范围: {hist_df['date'].iloc[0]} 至 {hist_df['date'].iloc[-1]}")
    print(f"数据天数: {len(hist_df)}天")

    close = hist_df['close'].values

    # 价格统计
    print(f"\n【价格统计】")
    print(f"最高价: {hist_df['high'].max():.2f}元 | 最低价: {hist_df['low'].min():.2f}元")
    print(f"平均价: {close.mean():.2f}元 | 标准差: {close.std():.2f}元")
    print(f"当前价: {close[-1]:.2f}元 (距最高 {(close[-1]/hist_df['high'].max()-1)*100:.1f}%)")

    # 收益率
    print(f"\n【收益率分析】")
    print(f"5日收益: {(close[-1]/close[-5]-1)*100:.2f}%")
    print(f"20日收益: {(close[-1]/close[-20]-1)*100:.2f}%")
    print(f"60日收益: {(close[-1]/close[-60]-1)*100:.2f}%")
    print(f"年初至今: {(close[-1]/close[0]-1)*100:.2f}%")

    # 技术指标
    print(f"\n【技术指标】")

    # 均线
    ma5 = simple_ma(close, 5)
    ma10 = simple_ma(close, 10)
    ma20 = simple_ma(close, 20)
    ma30 = simple_ma(close, 30)
    ma60 = simple_ma(close, 60)

    print(f"均线系统:")
    print(f"  MA5: {ma5[-1]:.2f} | MA10: {ma10[-1]:.2f} | MA20: {ma20[-1]:.2f}")
    print(f"  MA30: {ma30[-1]:.2f} | MA60: {ma60[-1]:.2f}")

    if ma5[-1] > ma10[-1] > ma20[-1] > ma30[-1]:
        print(f"  均线状态: 多头排列")
    elif ma5[-1] < ma10[-1] < ma20[-1] < ma30[-1]:
        print(f"  均线状态: 空头排列")
    else:
        print(f"  均线状态: 震荡整理")

    # MACD
    ema12 = pd.Series(close).ewm(span=12).mean()
    ema26 = pd.Series(close).ewm(span=26).mean()
    dif = (ema12 - ema26).values
    dea = pd.Series(dif).ewm(span=9).mean().values
    macd = (dif - dea) * 2

    print(f"\nMACD指标:")
    print(f"  DIF: {dif[-1]:.3f} | DEA: {dea[-1]:.3f} | MACD: {macd[-1]:.3f}")
    if dif[-1] > dea[-1]:
        print(f"  状态: 多头区域")
        if dif[-2] < dea[-2]:
            print(f"  信号: 金叉形成")
    else:
        print(f"  状态: 空头区域")

    # RSI
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
    avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.concatenate([[50] * 14, rsi])

    print(f"\nRSI指标:")
    print(f"  RSI(14): {rsi[-1]:.2f}")
    if rsi[-1] > 70:
        print(f"  状态: 超买区域")
    elif rsi[-1] < 30:
        print(f"  状态: 超卖区域 (买入机会)")
    else:
        print(f"  状态: 正常区间")

    # KDJ
    low_min = pd.Series(hist_df['low'].values).rolling(9).min().values
    high_max = pd.Series(hist_df['high'].values).rolling(9).max().values
    rsv = np.where(high_max - low_min != 0, (close - low_min) / (high_max - low_min) * 100, 50)
    k = pd.Series(rsv).ewm(alpha=1/3).mean().values
    d = pd.Series(k).ewm(alpha=1/3).mean().values
    j = 3 * k - 2 * d

    print(f"\nKDJ指标:")
    print(f"  K: {k[-1]:.2f} | D: {d[-1]:.2f} | J: {j[-1]:.2f}")
    if k[-1] > d[-1] and k[-2] < d[-2]:
        print(f"  信号: KDJ金叉")
    elif k[-1] < d[-1] and k[-2] > d[-2]:
        print(f"  信号: KDJ死叉")

    # 布林带
    mid = pd.Series(close).rolling(20).mean().values
    std = pd.Series(close).rolling(20).std().values
    upper = mid + 2 * std
    lower = mid - 2 * std

    print(f"\n布林带:")
    print(f"  上轨: {upper[-1]:.2f} | 中轨: {mid[-1]:.2f} | 下轨: {lower[-1]:.2f}")
    boll_pos = (close[-1] - lower[-1]) / (upper[-1] - lower[-1]) * 100
    print(f"  当前位置: {boll_pos:.1f}% (0%=下轨, 100%=上轨)")

    # 成交量分析
    vol_ma5 = simple_ma(hist_df['volume'].values, 5)
    vol_ma10 = simple_ma(hist_df['volume'].values, 10)

    print(f"\n【成交量分析】")
    print(f"  今日成交量: {int(hist_df['volume'].iloc[-1])}手")
    print(f"  5日均量: {vol_ma5[-1]:.0f}手 | 10日均量: {vol_ma10[-1]:.0f}手")
    vol_ratio = hist_df['volume'].iloc[-1] / vol_ma5[-1] if vol_ma5[-1] > 0 else 1
    print(f"  量比: {vol_ratio:.2f}")

    # 综合评分
    print(f"\n【综合评分】")
    score = 0
    signals = []

    # 均线得分
    if ma5[-1] > ma10[-1] > ma20[-1]:
        score += 20
        signals.append('均线多头')

    # MACD得分
    if dif[-1] > dea[-1]:
        score += 20
        signals.append('MACD多头')
        if dif[-2] < dea[-2]:
            score += 10
            signals.append('MACD金叉')

    # RSI得分
    if 30 < rsi[-1] < 70 and rsi[-1] > rsi[-2]:
        score += 15
        signals.append('RSI向上')
    elif rsi[-1] < 30:
        score += 10
        signals.append('RSI超卖')

    # KDJ得分
    if k[-1] > d[-1] and k[-2] < d[-2]:
        score += 15
        signals.append('KDJ金叉')

    # 成交量得分
    if vol_ratio > 1.5:
        score += 10
        signals.append('放量')

    # 布林带得分
    if boll_pos < 20:
        score += 10
        signals.append('布林下轨')

    print(f"综合得分: {score}分")
    print(f"触发信号: {', '.join(signals) if signals else '无'}")

    # 投资建议
    print(f"\n【投资建议】")
    if score >= 60:
        print(f"评级: 看多")
        print(f"建议: 技术面走强，可考虑逢低布局")
    elif score >= 40:
        print(f"评级: 中性")
        print(f"建议: 观望为主，等待更明确信号")
    else:
        print(f"评级: 看空")
        print(f"建议: 风险较大，谨慎操作")

    print('\n' + '=' * 60)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        prefix = sys.argv[2] if len(sys.argv) > 2 else None
        if prefix is None:
            if code.startswith(('600', '601', '603', '605', '688')):
                prefix = 'sh'
            else:
                prefix = 'sz'
        analyze_stock(code, prefix)
    else:
        # 默认分析远大控股
        analyze_stock('000626', 'sz')