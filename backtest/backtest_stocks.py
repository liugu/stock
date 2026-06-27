#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测分析脚本 - 验证选股策略的历史表现
对选出的股票进行多策略回测，计算收益率
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

# 昨天选出的10支股票
SELECTED_STOCKS = [
    {'code': '601882', 'name': '海天精工'},
    {'code': '002317', 'name': '众生药业'},
    {'code': '002081', 'name': '金螳螂'},
    {'code': '600736', 'name': '苏州高新'},
    {'code': '002757', 'name': '南兴股份'},
    {'code': '601199', 'name': '江南水务'},
    {'code': '300184', 'name': '力源信息'},
    {'code': '300398', 'name': '飞凯材料'},
    {'code': '603285', 'name': '键邦股份'},
    {'code': '000060', 'name': '中金岭南'},
]


def get_market_id(code: str) -> int:
    """根据股票代码判断市场ID"""
    # 沪市: 600/601/603/605/688开头
    if code.startswith(('600', '601', '603', '605', '688')):
        return 1
    # 深市: 000/001/002/003/300/301开头
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return 0
    # 北交所: 8开头
    elif code.startswith('8'):
        return 0
    else:
        return None


def stock_zh_a_hist(symbol: str, start_date: str = "20230101",
                    end_date: str = "20500101", adjust: str = "qfq") -> pd.DataFrame:
    """获取股票历史数据"""
    market_id = get_market_id(symbol)
    if market_id is None:
        print(f"  警告: 无法识别股票代码 {symbol} 的市场")
        return pd.DataFrame()

    adjust_dict = {"qfq": "1", "hfq": "2", "": "0"}
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101", "fqt": adjust_dict.get(adjust, "1"),
        "secid": f"{market_id}.{symbol}",
        "beg": start_date, "end": end_date,
        "_": "1623766962675",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        data_json = r.json()
        if not (data_json.get("data") and data_json["data"].get("klines")):
            print(f"  警告: {symbol} 无历史数据返回")
            return pd.DataFrame()

        temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
        temp_df.columns = ["date", "open", "close", "high", "low", "volume",
                           "amount", "amplitude", "p_change", "change", "turnover"]

        for col in ["open", "close", "high", "low", "volume", "amount",
                    "amplitude", "p_change", "change", "turnover"]:
            temp_df[col] = pd.to_numeric(temp_df[col], errors="coerce")

        return temp_df
    except Exception as e:
        print(f"  错误: {symbol} 数据获取失败 - {e}")
        return pd.DataFrame()


def simple_ma(data, period):
    """简单移动平均线"""
    return pd.Series(data).rolling(window=period).mean().values


# ============== 策略回测函数 ==============

def backtest_buy_hold(hist_data, hold_days_list=[5, 10, 20, 60]):
    """买入持有策略回测"""
    results = {}
    for days in hold_days_list:
        if len(hist_data) >= days:
            buy_price = hist_data.iloc[-days]['close']
            sell_price = hist_data.iloc[-1]['close']
            ret = (sell_price - buy_price) / buy_price * 100
            results[f'{days}日收益'] = round(ret, 2)
        else:
            results[f'{days}日收益'] = None
    return results


def backtest_ma_cross(hist_data, fast=5, slow=20):
    """均线交叉策略回测"""
    if len(hist_data) < slow + 30:
        return {'均线交叉': None}

    close = hist_data['close'].values
    ma_fast = simple_ma(close, fast)
    ma_slow = simple_ma(close, slow)

    # 找最近的金叉买入点
    signals = []
    for i in range(slow, len(close) - 1):
        if ma_fast[i-1] < ma_slow[i-1] and ma_fast[i] > ma_slow[i]:
            signals.append(i)

    if not signals:
        return {'均线交叉': None}

    # 最近一次金叉买入
    buy_idx = signals[-1]
    buy_price = close[buy_idx]
    sell_price = close[-1]
    hold_days = len(close) - buy_idx - 1
    ret = (sell_price - buy_price) / buy_price * 100

    return {
        '均线交叉': round(ret, 2),
        '持有天数': hold_days
    }


def backtest_breakout(hist_data, period=20):
    """突破策略回测 - 突破N日高点买入"""
    if len(hist_data) < period + 30:
        return {'突破策略': None}

    close = hist_data['close'].values
    high = hist_data['high'].values

    # 找突破点
    signals = []
    for i in range(period, len(close) - 1):
        period_high = max(high[i-period:i])
        if close[i] > period_high:
            signals.append(i)

    if not signals:
        return {'突破策略': None}

    # 最近一次突破买入
    buy_idx = signals[-1]
    buy_price = close[buy_idx]
    sell_price = close[-1]
    hold_days = len(close) - buy_idx - 1
    ret = (sell_price - buy_price) / buy_price * 100

    return {
        '突破策略': round(ret, 2),
        '持有天数': hold_days
    }


def backtest_rsi(hist_data, oversold=30, overbought=70):
    """RSI策略回测"""
    if len(hist_data) < 30:
        return {'RSI策略': None}

    close = hist_data['close'].values

    # 简化RSI计算
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
    avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.concatenate([[50] * 14, rsi])

    # 找RSI超卖后回升的买入点
    signals = []
    for i in range(15, len(rsi) - 1):
        if rsi[i-1] < oversold and rsi[i] > rsi[i-1]:
            signals.append(i)

    if not signals:
        return {'RSI策略': None}

    buy_idx = signals[-1]
    buy_price = close[buy_idx]
    sell_price = close[-1]
    hold_days = len(close) - buy_idx - 1
    ret = (sell_price - buy_price) / buy_price * 100

    return {
        'RSI策略': round(ret, 2),
        '持有天数': hold_days
    }


def backtest_macd(hist_data):
    """MACD金叉策略回测"""
    if len(hist_data) < 35:
        return {'MACD策略': None}

    close = hist_data['close'].values

    # 简化MACD计算
    ema12 = pd.Series(close).ewm(span=12).mean()
    ema26 = pd.Series(close).ewm(span=26).mean()
    dif = (ema12 - ema26).values
    dea = pd.Series(dif).ewm(span=9).mean().values

    # 找金叉点
    signals = []
    for i in range(26, len(close) - 1):
        if dif[i-1] < dea[i-1] and dif[i] > dea[i]:
            signals.append(i)

    if not signals:
        return {'MACD策略': None}

    buy_idx = signals[-1]
    buy_price = close[buy_idx]
    sell_price = close[-1]
    hold_days = len(close) - buy_idx - 1
    ret = (sell_price - buy_price) / buy_price * 100

    return {
        'MACD策略': round(ret, 2),
        '持有天数': hold_days
    }


def backtest_turtle(hist_data, entry_period=20, exit_period=10):
    """海龟交易策略回测"""
    if len(hist_data) < entry_period + 30:
        return {'海龟策略': None}

    close = hist_data['close'].values
    high = hist_data['high'].values
    low = hist_data['low'].values

    # 找突破买入点
    signals = []
    for i in range(entry_period, len(close) - 1):
        entry_high = max(high[i-entry_period:i])
        if close[i] > entry_high:
            signals.append(i)

    if not signals:
        return {'海龟策略': None}

    buy_idx = signals[-1]
    buy_price = close[buy_idx]
    sell_price = close[-1]
    hold_days = len(close) - buy_idx - 1
    ret = (sell_price - buy_price) / buy_price * 100

    return {
        '海龟策略': round(ret, 2),
        '持有天数': hold_days
    }


def calculate_max_drawdown(hist_data):
    """计算最大回撤"""
    close = hist_data['close'].values
    peak = close[0]
    max_dd = 0

    for price in close:
        if price > peak:
            peak = price
        dd = (peak - price) / peak
        if dd > max_dd:
            max_dd = dd

    return round(max_dd * 100, 2)


def calculate_sharpe(hist_data, risk_free_rate=0.03):
    """计算夏普比率（年化）"""
    returns = hist_data['p_change'].values
    if len(returns) < 30:
        return None

    mean_return = np.mean(returns) * 252  # 年化
    std_return = np.std(returns) * np.sqrt(252)  # 年化

    if std_return == 0:
        return None

    sharpe = (mean_return - risk_free_rate) / std_return
    return round(sharpe, 2)


def calculate_win_rate(hist_data):
    """计算胜率"""
    p_changes = hist_data['p_change'].values
    up_days = np.sum(p_changes > 0)
    total_days = len(p_changes)

    if total_days == 0:
        return None

    return round(up_days / total_days * 100, 2)


def run_backtest():
    """运行回测"""
    print("=" * 70)
    print("A股选股策略回测分析")
    print("=" * 70)
    print(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"回测股票: {len(SELECTED_STOCKS)}只")
    print()

    # 获取2年历史数据，确保有足够数据
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y%m%d")

    all_results = []

    for stock in SELECTED_STOCKS:
        code = stock['code']
        name = stock['name']

        print(f"正在回测: {code} {name}...")

        try:
            hist_data = stock_zh_a_hist(code, start_date=start_date)
            if len(hist_data) < 60:
                print(f"  数据不足，跳过")
                continue

            # 计算各项指标
            result = {
                '代码': code,
                '名称': name,
                '最新价': hist_data.iloc[-1]['close'],
                '数据天数': len(hist_data),
            }

            # 买入持有策略
            hold_results = backtest_buy_hold(hist_data)
            result.update(hold_results)

            # 均线交叉策略
            ma_results = backtest_ma_cross(hist_data)
            result['均线交叉收益%'] = ma_results.get('均线交叉')

            # 突破策略
            breakout_results = backtest_breakout(hist_data)
            result['突破策略收益%'] = breakout_results.get('突破策略')

            # RSI策略
            rsi_results = backtest_rsi(hist_data)
            result['RSI策略收益%'] = rsi_results.get('RSI策略')

            # MACD策略
            macd_results = backtest_macd(hist_data)
            result['MACD策略收益%'] = macd_results.get('MACD策略')

            # 海龟策略
            turtle_results = backtest_turtle(hist_data)
            result['海龟策略收益%'] = turtle_results.get('海龟策略')

            # 风险指标
            result['最大回撤%'] = calculate_max_drawdown(hist_data)
            result['夏普比率'] = calculate_sharpe(hist_data)
            result['胜率%'] = calculate_win_rate(hist_data)

            # 年化收益
            first_close = hist_data.iloc[0]['close']
            last_close = hist_data.iloc[-1]['close']
            days = len(hist_data)
            annual_return = (last_close / first_close) ** (252 / days) - 1
            result['年化收益%'] = round(annual_return * 100, 2)

            all_results.append(result)
            print(f"  完成")

        except Exception as e:
            print(f"  错误: {e}")
            continue

    # 输出结果
    print("\n" + "=" * 70)
    print("回测结果汇总")
    print("=" * 70)

    if not all_results:
        print("无回测结果")
        return

    results_df = pd.DataFrame(all_results)

    # 输出详细结果
    print("\n【各股票策略收益对比】\n")

    # 策略收益列
    strategy_cols = ['5日收益', '10日收益', '20日收益', '60日收益',
                     '均线交叉收益%', '突破策略收益%', 'RSI策略收益%',
                     'MACD策略收益%', '海龟策略收益%']

    for _, row in results_df.iterrows():
        print(f"\n{row['代码']} {row['名称']}")
        print(f"  最新价: {row['最新价']:.2f}元 | 年化收益: {row['年化收益%']}%")
        print(f"  最大回撤: {row['最大回撤%']}% | 夏普比率: {row['夏普比率']} | 胜率: {row['胜率%']}%")
        print("  策略收益:")

        for col in strategy_cols:
            if col in row and pd.notna(row[col]):
                val = row[col]
                color = "✓" if val > 0 else "✗"
                print(f"    {col}: {val}% {color}")

    # 汇总统计
    print("\n" + "=" * 70)
    print("【策略平均收益统计】\n")

    for col in strategy_cols:
        if col in results_df.columns:
            avg = results_df[col].mean()
            positive_rate = (results_df[col] > 0).sum() / results_df[col].notna().sum() * 100
            print(f"  {col}: 平均 {avg:.2f}%, 正收益比例 {positive_rate:.1f}%")

    # 风险指标汇总
    print("\n【风险指标汇总】\n")
    print(f"  平均最大回撤: {results_df['最大回撤%'].mean():.2f}%")
    print(f"  平均夏普比率: {results_df['夏普比率'].mean():.2f}")
    print(f"  平均胜率: {results_df['胜率%'].mean():.2f}%")
    print(f"  平均年化收益: {results_df['年化收益%'].mean():.2f}%")

    # 保存结果
    output_file = f"回测结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df.to_excel(output_file, index=False)
    print(f"\n详细结果已保存至: {output_file}")

    print("\n" + "=" * 70)
    print("回测结论:")
    print("  - 买入持有策略适合中长期投资")
    print("  - 均线交叉策略适合趋势行情")
    print("  - 突破策略适合震荡上行市场")
    print("  - RSI/MACD策略适合短线操作")
    print("  - 海龟策略适合趋势跟踪")
    print("=" * 70)

    return results_df


if __name__ == '__main__':
    run_backtest()
