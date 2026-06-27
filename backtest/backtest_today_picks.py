#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
选股回测验证脚本
对选出的股票进行历史回测，验证策略有效性
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 今日推荐前三名
SELECTED_STOCKS = [
    {'code': '600969', 'name': '郴电国际'},
    {'code': '601069', 'name': '西部黄金'},
    {'code': '600255', 'name': '鑫科材料'},
]


def get_market_id(code: str) -> int:
    """根据股票代码判断市场ID"""
    if code.startswith(('600', '601', '603', '605', '688')):
        return 1
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return 0
    else:
        return 0


def stock_zh_a_hist(symbol: str, start_date: str = "20230101",
                    end_date: str = "20500101", adjust: str = "qfq") -> pd.DataFrame:
    """获取股票历史数据（前复权）"""
    market_id = get_market_id(symbol)
    
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101",
        "fqt": "1",
        "secid": f"{market_id}.{symbol}",
        "beg": start_date, "end": end_date,
        "_": "1623766962675",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        data_json = r.json()
        if not (data_json.get("data") and data_json["data"].get("klines")):
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


def calculate_max_drawdown(prices):
    """计算最大回撤"""
    peak = prices[0]
    max_dd = 0
    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


def backtest_stock(hist_data, stock_name):
    """对单只股票进行回测"""
    if len(hist_data) < 60:
        return None
    
    close = hist_data['close'].values
    results = {'name': stock_name}
    
    # 1. 不同持有期收益率
    for days in [5, 10, 20, 60]:
        if len(hist_data) >= days:
            buy_price = close[-days]
            sell_price = close[-1]
            ret = (sell_price - buy_price) / buy_price * 100
            results[f'{days}日收益'] = round(ret, 2)
    
    # 2. 均线策略回测 (MA5上穿MA20)
    ma5 = simple_ma(close, 5)
    ma20 = simple_ma(close, 20)
    
    ma_signals = []
    for i in range(20, len(close) - 1):
        if ma5[i-1] < ma20[i-1] and ma5[i] > ma20[i]:
            ma_signals.append(i)
    
    if ma_signals:
        buy_idx = ma_signals[-1]
        buy_price = close[buy_idx]
        sell_price = close[-1]
        hold_days = len(close) - buy_idx - 1
        ret = (sell_price - buy_price) / buy_price * 100
        results['MA交叉收益'] = round(ret, 2)
        results['MA持有天数'] = hold_days
    
    # 3. 突破策略 (突破20日高点)
    high = hist_data['high'].values
    breakout_signals = []
    for i in range(20, len(close) - 1):
        period_high = max(high[i-20:i])
        if close[i] > period_high:
            breakout_signals.append(i)
    
    if breakout_signals:
        buy_idx = breakout_signals[-1]
        buy_price = close[buy_idx]
        sell_price = close[-1]
        hold_days = len(close) - buy_idx - 1
        ret = (sell_price - buy_price) / buy_price * 100
        results['突破收益'] = round(ret, 2)
        results['突破持有天数'] = hold_days
    
    # 4. MACD金叉策略
    ema12 = pd.Series(close).ewm(span=12).mean()
    ema26 = pd.Series(close).ewm(span=26).mean()
    dif = (ema12 - ema26).values
    dea = pd.Series(dif).ewm(span=9).mean().values
    
    macd_signals = []
    for i in range(26, len(close) - 1):
        if dif[i-1] < dea[i-1] and dif[i] > dea[i]:
            macd_signals.append(i)
    
    if macd_signals:
        buy_idx = macd_signals[-1]
        buy_price = close[buy_idx]
        sell_price = close[-1]
        hold_days = len(close) - buy_idx - 1
        ret = (sell_price - buy_price) / buy_price * 100
        results['MACD收益'] = round(ret, 2)
        results['MACD持有天数'] = hold_days
    
    # 5. 风险指标
    results['最大回撤'] = calculate_max_drawdown(close)
    
    # 6. 近期表现
    results['近5日涨幅'] = round((close[-1] - close[-6]) / close[-6] * 100, 2) if len(close) >= 6 else None
    results['近10日涨幅'] = round((close[-1] - close[-11]) / close[-11] * 100, 2) if len(close) >= 11 else None
    results['近20日涨幅'] = round((close[-1] - close[-21]) / close[-21] * 100, 2) if len(close) >= 21 else None
    
    # 7. 当前技术状态
    results['当前价'] = round(close[-1], 2)
    results['MA5'] = round(ma5[-1], 2)
    results['MA10'] = round(simple_ma(close, 10)[-1], 2)
    results['MA20'] = round(ma20[-1], 2)
    results['MA60'] = round(simple_ma(close, 60)[-1], 2) if len(close) >= 60 else None
    
    # 8. 均线多头判断
    if ma5[-1] > ma20[-1]:
        results['均线状态'] = '多头排列'
    else:
        results['均线状态'] = '空头排列'
    
    return results


def main():
    print("=" * 80)
    print("📊 选股回测验证报告")
    print("=" * 80)
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"回测股票: {[s['name'] for s in SELECTED_STOCKS]}")
    print("=" * 80)
    
    all_results = []
    
    for stock in SELECTED_STOCKS:
        print(f"\n正在分析 {stock['name']}({stock['code']})...")
        
        # 获取历史数据
        hist_data = stock_zh_a_hist(stock['code'])
        
        if hist_data.empty:
            print(f"  无法获取 {stock['name']} 的历史数据")
            continue
        
        print(f"  获取到 {len(hist_data)} 条历史数据")
        
        # 回测
        results = backtest_stock(hist_data, stock['name'])
        if results:
            results['code'] = stock['code']
            all_results.append(results)
    
    # 输出结果
    print("\n" + "=" * 80)
    print("📈 回测结果汇总")
    print("=" * 80)
    
    for r in all_results:
        print(f"\n【{r['name']}({r['code']})】")
        print("-" * 60)
        print(f"  当前价格: {r.get('当前价', 'N/A')} 元")
        print(f"  均线状态: {r.get('均线状态', 'N/A')}")
        print(f"  MA5: {r.get('MA5', 'N/A')} | MA20: {r.get('MA20', 'N/A')}")
        print(f"\n  持有期收益率:")
        print(f"    5日: {r.get('5日收益', 'N/A')}%")
        print(f"    10日: {r.get('10日收益', 'N/A')}%")
        print(f"    20日: {r.get('20日收益', 'N/A')}%")
        print(f"    60日: {r.get('60日收益', 'N/A')}%")
        print(f"\n  策略回测:")
        print(f"    MA交叉: {r.get('MA交叉收益', 'N/A')}% (持有{r.get('MA持有天数', 'N/A')}天)")
        print(f"    突破策略: {r.get('突破收益', 'N/A')}% (持有{r.get('突破持有天数', 'N/A')}天)")
        print(f"    MACD策略: {r.get('MACD收益', 'N/A')}% (持有{r.get('MACD持有天数', 'N/A')}天)")
        print(f"\n  风险指标:")
        print(f"    最大回撤: {r.get('最大回撤', 'N/A')}%")
    
    # 综合评价
    print("\n" + "=" * 80)
    print("🎯 综合评价与建议")
    print("=" * 80)
    
    # 按各指标排序
    print("\n1. 短期表现(5日)排名:")
    sorted_5d = sorted(all_results, key=lambda x: x.get('5日收益', -999), reverse=True)
    for i, r in enumerate(sorted_5d, 1):
        print(f"   {i}. {r['name']}: {r.get('5日收益', 'N/A')}%")
    
    print("\n2. 中期表现(20日)排名:")
    sorted_20d = sorted(all_results, key=lambda x: x.get('20日收益', -999), reverse=True)
    for i, r in enumerate(sorted_20d, 1):
        print(f"   {i}. {r['name']}: {r.get('20日收益', 'N/A')}%")
    
    print("\n3. 风险控制(最大回撤)排名:")
    sorted_dd = sorted(all_results, key=lambda x: x.get('最大回撤', 999))
    for i, r in enumerate(sorted_dd, 1):
        print(f"   {i}. {r['name']}: {r.get('最大回撤', 'N/A')}%")
    
    print("\n" + "=" * 80)
    print("✅ 结论:")
    print("=" * 80)
    
    # 综合评分
    for r in all_results:
        score = 0
        # 收益加分
        if r.get('5日收益', 0) > 0: score += 10
        if r.get('10日收益', 0) > 0: score += 10
        if r.get('20日收益', 0) > 0: score += 15
        # 风险扣分
        if r.get('最大回撤', 0) > 20: score -= 10
        # 均线状态加分
        if r.get('均线状态') == '多头排列': score += 10
        r['综合得分'] = score
    
    sorted_final = sorted(all_results, key=lambda x: x.get('综合得分', 0), reverse=True)
    
    print("\n综合推荐排序:")
    for i, r in enumerate(sorted_final, 1):
        print(f"  {i}. {r['name']}: 得分 {r.get('综合得分', 0)}")
        print(f"     理由: 20日收益{r.get('20日收益', 'N/A')}%, 最大回撤{r.get('最大回撤', 'N/A')}%, {r.get('均线状态', 'N/A')}")


if __name__ == '__main__':
    main()
