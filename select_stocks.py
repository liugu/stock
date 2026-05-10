#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合选股脚本 - 基于多策略筛选未来趋势上涨的股票
不依赖数据库，直接从东方财富网获取实时数据
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

# 尝试导入talib，如果没有则使用简化版本
try:
    import talib as tl
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("警告: TA-Lib未安装，将使用简化版技术指标计算")


def simple_ma(data, period):
    """简单移动平均线"""
    return pd.Series(data).rolling(window=period).mean().values


def stock_zh_a_spot_em() -> pd.DataFrame:
    """获取A股实时行情数据 - 分页获取全部数据"""
    all_data = []
    url = "http://82.push2.eastmoney.com/api/qt/clist/get"

    # 分页获取，每次5000条
    for page in range(1, 20):  # 最多获取20页，约10万条
        params = {
            "pn": str(page), "pz": "5000", "po": "1", "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2", "invt": "2", "fid": "f3",
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f14,f15,f16,f17,f18,f20,f21,f22,f23,f24,f25,f26,f37,f38,f39,f40,f41,f45,f46,f48,f49,f57,f61,f100,f112,f113,f114,f115,f221",
            "_": "1623833739532",
        }
        try:
            r = requests.get(url, params=params, timeout=30)
            data_json = r.json()
            if not data_json["data"]["diff"]:
                break
            all_data.extend(data_json["data"]["diff"])
            print(f"      已获取 {len(all_data)} 只股票...")
        except Exception as e:
            print(f"      第{page}页获取失败: {e}")
            break

    if not all_data:
        return pd.DataFrame()

    temp_df = pd.DataFrame(all_data)
    temp_df.columns = [
        "最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "换手率",
        "市盈率动", "量比", "5分钟涨跌", "代码", "名称", "最高", "最低",
        "今开", "昨收", "总市值", "流通市值", "涨速", "市净率", "60日涨跌幅",
        "年初至今涨跌幅", "上市时间", "加权净资产收益率", "总股本", "已流通股份",
        "营业收入", "营业收入同比增长", "归属净利润", "归属净利润同比增长",
        "每股未分配利润", "毛利率", "资产负债率", "每股公积金", "所处行业",
        "每股收益", "每股净资产", "市盈率静", "市盈率TTM", "报告期"
    ]

    temp_df = temp_df[[
        "代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交量", "成交额",
        "振幅", "换手率", "量比", "今开", "最高", "最低", "昨收", "涨速",
        "5分钟涨跌", "60日涨跌幅", "年初至今涨跌幅", "市盈率动", "市盈率TTM",
        "市盈率静", "市净率", "每股收益", "每股净资产", "总市值", "流通市值",
        "所处行业", "上市时间"
    ]]

    for col in ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "量比",
                "换手率", "最高", "最低", "今开", "昨收", "涨速", "5分钟涨跌",
                "60日涨跌幅", "年初至今涨跌幅", "市盈率动", "市盈率TTM", "市盈率静",
                "市净率", "每股收益", "每股净资产", "总市值", "流通市值"]:
        temp_df[col] = pd.to_numeric(temp_df[col], errors="coerce")

    return temp_df


@lru_cache()
def code_id_map_em() -> dict:
    """获取股票和市场代码映射"""
    url = "http://80.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "50000", "po": "1", "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f3",
        "fs": "m:1 t:2,m:1 t:23", "fields": "f12",
        "_": "1623833739532",
    }
    r = requests.get(url, params=params, timeout=30)
    data_json = r.json()
    if not data_json["data"]["diff"]:
        return dict()
    temp_df = pd.DataFrame(data_json["data"]["diff"])
    temp_df["market_id"] = 1
    temp_df.columns = ["sh_code", "sh_id"]
    code_id_dict = dict(zip(temp_df["sh_code"], temp_df["sh_id"]))

    params["fs"] = "m:0 t:6,m:0 t:80"
    r = requests.get(url, params=params, timeout=30)
    data_json = r.json()
    if data_json["data"]["diff"]:
        temp_df_sz = pd.DataFrame(data_json["data"]["diff"])
        temp_df_sz["sz_id"] = 0
        code_id_dict.update(dict(zip(temp_df_sz["f12"], temp_df_sz["sz_id"])))

    params["fs"] = "m:0 t:81 s:2048"
    r = requests.get(url, params=params, timeout=30)
    data_json = r.json()
    if data_json["data"]["diff"]:
        temp_df_sz = pd.DataFrame(data_json["data"]["diff"])
        temp_df_sz["bj_id"] = 0
        code_id_dict.update(dict(zip(temp_df_sz["f12"], temp_df_sz["bj_id"])))

    return code_id_dict


def stock_zh_a_hist(symbol: str, start_date: str = "20240101",
                    end_date: str = "20500101", adjust: str = "qfq") -> pd.DataFrame:
    """获取股票历史数据"""
    code_id_dict = code_id_map_em()
    if symbol not in code_id_dict:
        return pd.DataFrame()

    adjust_dict = {"qfq": "1", "hfq": "2", "": "0"}
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101", "fqt": adjust_dict.get(adjust, "1"),
        "secid": f"{code_id_dict[symbol]}.{symbol}",
        "beg": start_date, "end": end_date,
        "_": "1623766962675",
    }
    r = requests.get(url, params=params, timeout=30)
    data_json = r.json()
    if not (data_json["data"] and data_json["data"]["klines"]):
        return pd.DataFrame()

    temp_df = pd.DataFrame([item.split(",") for item in data_json["data"]["klines"]])
    temp_df.columns = ["date", "open", "close", "high", "low", "volume",
                       "amount", "amplitude", "p_change", "change", "turnover"]

    for col in ["open", "close", "high", "low", "volume", "amount",
                "amplitude", "p_change", "change", "turnover"]:
        temp_df[col] = pd.to_numeric(temp_df[col], errors="coerce")

    return temp_df


def is_valid_stock(code, name):
    """过滤有效A股股票"""
    # 排除ST股票
    if 'ST' in name or 'st' in name:
        return False
    # 排除退市股票
    if '退' in name:
        return False
    # 只保留A股代码
    if not (code.startswith(('600', '601', '603', '605', '000', '001', '002', '003', '300', '301'))):
        return False
    return True


def calc_ma(close_data, period):
    """计算移动平均线"""
    if HAS_TALIB:
        return tl.MA(close_data, timeperiod=period)
    else:
        return simple_ma(close_data, period)


def strategy_volume_breakthrough(hist_data, threshold=60):
    """放量上涨策略"""
    if len(hist_data) < threshold:
        return False, 0

    data = hist_data.tail(threshold + 1)
    if len(data) < threshold + 1:
        return False, 0

    last = data.iloc[-1]
    # 当日上涨大于2%且收阳
    if last['p_change'] < 2 or last['close'] < last['open']:
        return False, 0

    # 成交额不低于2亿
    if last['amount'] < 200000000:
        return False, 0

    # 计算量比
    vol_ma5 = calc_ma(data['volume'].values, 5)
    vol_ma5 = np.nan_to_num(vol_ma5, nan=0.0)
    if vol_ma5[-1] == 0:
        return False, 0

    vol_ratio = last['volume'] / vol_ma5[-1]
    if vol_ratio >= 2:
        return True, vol_ratio

    return False, 0


def strategy_turtle_trade(hist_data, threshold=60):
    """海龟交易法则 - 突破60日新高"""
    if len(hist_data) < threshold:
        return False, 0

    data = hist_data.tail(threshold)
    last_close = data.iloc[-1]['close']
    max_close = data['close'].max()

    if last_close >= max_close:
        return True, (last_close / max_close - 1) * 100

    return False, 0


def strategy_ma_bullish(hist_data, threshold=30):
    """均线多头排列"""
    if len(hist_data) < threshold + 30:
        return False, 0

    close_data = hist_data['close'].values

    ma5 = calc_ma(close_data, 5)
    ma10 = calc_ma(close_data, 10)
    ma20 = calc_ma(close_data, 20)
    ma30 = calc_ma(close_data, 30)

    if any(np.isnan([ma5[-1], ma10[-1], ma20[-1], ma30[-1]])):
        return False, 0

    # 均线多头排列: MA5 > MA10 > MA20 > MA30
    if ma5[-1] > ma10[-1] > ma20[-1] > ma30[-1]:
        # 30日均线向上
        if ma30[-1] > ma30[-5]:
            return True, (ma5[-1] / ma30[-1] - 1) * 100

    return False, 0


def strategy_breakthrough_platform(hist_data, threshold=60):
    """平台突破策略"""
    if len(hist_data) < threshold + 10:
        return False, 0

    close_data = hist_data['close'].values
    ma60 = calc_ma(close_data, 60)
    ma60 = np.nan_to_num(ma60, nan=0.0)

    data = hist_data.tail(threshold).copy()
    data['ma60'] = ma60[-threshold:]

    # 寻找突破日
    for i in range(len(data) - 1):
        row = data.iloc[i]
        if row['open'] < row['ma60'] <= row['close']:
            # 突破后确认
            after = data.iloc[i+1:]
            if len(after) >= 5:
                # 突破后维持在均线上方
                if (after['close'] > after['ma60']).all():
                    return True, (data.iloc[-1]['close'] / row['close'] - 1) * 100

    return False, 0


def strategy_low_atr(hist_data, threshold=20):
    """低波动率成长 - 近期波动率较低且上涨"""
    if len(hist_data) < threshold:
        return False, 0

    data = hist_data.tail(threshold)

    # 计算波动率
    returns = data['p_change'].values
    volatility = np.std(returns)

    # 波动率低于3%且上涨
    if volatility < 3:
        total_return = (data.iloc[-1]['close'] / data.iloc[0]['close'] - 1) * 100
        if total_return > 5:
            return True, total_return

    return False, 0


def strategy_rsi_oversold(hist_data, threshold=30):
    """RSI超卖反弹"""
    if len(hist_data) < threshold:
        return False, 0

    close_data = hist_data['close'].values

    if HAS_TALIB:
        rsi = tl.RSI(close_data, timeperiod=14)
    else:
        # 简化RSI计算
        deltas = np.diff(close_data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
        avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.concatenate([[50], rsi])

    rsi = np.nan_to_num(rsi, nan=50)

    # RSI从超卖区域回升
    if len(rsi) >= 5:
        if rsi[-5] < 30 and rsi[-1] > rsi[-5] and rsi[-1] < 70:
            return True, rsi[-1] - rsi[-5]

    return False, 0


def strategy_macd_golden(hist_data):
    """MACD金叉"""
    if len(hist_data) < 35:
        return False, 0

    close_data = hist_data['close'].values

    if HAS_TALIB:
        macd, signal, hist = tl.MACD(close_data, fastperiod=12, slowperiod=26, signalperiod=9)
    else:
        # 简化MACD计算
        ema12 = pd.Series(close_data).ewm(span=12).mean()
        ema26 = pd.Series(close_data).ewm(span=26).mean()
        macd = (ema12 - ema26).values
        signal = pd.Series(macd).ewm(span=9).mean().values
        hist = macd - signal

    macd = np.nan_to_num(macd, nan=0)
    signal = np.nan_to_num(signal, nan=0)

    # MACD金叉: DIF上穿DEA
    if len(macd) >= 2:
        if macd[-2] < signal[-2] and macd[-1] > signal[-1]:
            return True, (macd[-1] - signal[-1]) * 100

    return False, 0


def comprehensive_score(stock_info, hist_data):
    """综合评分"""
    score = 0
    signals = []

    # 策略权重
    strategies = [
        (strategy_volume_breakthrough, 25, "放量上涨"),
        (strategy_turtle_trade, 20, "突破新高"),
        (strategy_ma_bullish, 20, "均线多头"),
        (strategy_breakthrough_platform, 15, "平台突破"),
        (strategy_low_atr, 10, "低波动成长"),
        (strategy_rsi_oversold, 5, "RSI超卖反弹"),
        (strategy_macd_golden, 5, "MACD金叉"),
    ]

    for strategy_func, weight, name in strategies:
        try:
            result, value = strategy_func(hist_data)
            if result:
                score += weight
                signals.append(f"{name}({value:.1f})")
        except Exception as e:
            pass

    # 基本面加分
    try:
        # 市盈率合理
        pe = stock_info.get('市盈率TTM', 0)
        if 0 < pe < 30:
            score += 5
        elif 30 <= pe < 50:
            score += 2

        # 市净率合理
        pb = stock_info.get('市净率', 0)
        if 0 < pb < 3:
            score += 3

        # 60日涨幅适中
        change_60 = stock_info.get('60日涨跌幅', 0)
        if 0 < change_60 < 30:
            score += 3
        elif -10 < change_60 <= 0:
            score += 5  # 近期回调但基本面好的股票
    except:
        pass

    return score, signals


def main():
    print("=" * 60)
    print("A股综合选股系统 - 多策略筛选")
    print("=" * 60)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 获取实时行情数据
    print("[1/4] 正在获取A股实时行情数据...")
    try:
        spot_df = stock_zh_a_spot_em()
        print(f"      获取到 {len(spot_df)} 只股票数据")
    except Exception as e:
        print(f"      错误: {e}")
        return

    # 过滤有效股票
    spot_df = spot_df[spot_df.apply(lambda x: is_valid_stock(x['代码'], x['名称']), axis=1)]
    print(f"      过滤后剩余 {len(spot_df)} 只A股")

    # 2. 筛选候选股票
    print("\n[2/4] 正在筛选候选股票...")

    # 基本筛选条件
    candidates = spot_df[
        (spot_df['最新价'] > 3) &  # 价格大于3元
        (spot_df['最新价'] < 100) &  # 价格小于100元
        (spot_df['成交额'] > 100000000) &  # 成交额大于1亿
        (spot_df['总市值'] > 5000000000) &  # 总市值大于50亿
        (spot_df['总市值'] < 500000000000) &  # 总市值小于5000亿
        (spot_df['市盈率TTM'] > 0) &  # 盈利
        (spot_df['市盈率TTM'] < 100)  # 市盈率小于100
    ].copy()

    print(f"      基本筛选后剩余 {len(candidates)} 只股票")

    # 3. 获取历史数据并评分
    print("\n[3/4] 正在分析历史数据并评分...")
    results = []

    # 计算起始日期（获取最近120个交易日数据）
    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

    for idx, (_, row) in enumerate(candidates.iterrows()):
        code = row['代码']
        name = row['名称']

        if idx % 50 == 0:
            print(f"      进度: {idx}/{len(candidates)}")

        try:
            hist_data = stock_zh_a_hist(code, start_date=start_date)
            if len(hist_data) < 60:
                continue

            score, signals = comprehensive_score(row, hist_data)

            if score >= 30:  # 最低30分入选
                results.append({
                    '代码': code,
                    '名称': name,
                    '最新价': row['最新价'],
                    '涨跌幅': row['涨跌幅'],
                    '60日涨跌幅': row['60日涨跌幅'],
                    '成交额(亿)': row['成交额'] / 100000000,
                    '市盈率TTM': row['市盈率TTM'],
                    '市净率': row['市净率'],
                    '总市值(亿)': row['总市值'] / 100000000,
                    '所处行业': row['所处行业'],
                    '综合得分': score,
                    '信号': ', '.join(signals)
                })
        except Exception as e:
            continue

    # 4. 输出结果
    print("\n[4/4] 选股结果")
    print("=" * 60)

    if not results:
        print("未找到符合条件的股票")
        return

    # 按得分排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('综合得分', ascending=False)

    # 输出前10只股票
    top10 = results_df.head(10)

    print(f"\n精选推荐股票 (共{len(results_df)}只符合条件，展示前10只):\n")

    for i, (_, row) in enumerate(top10.iterrows(), 1):
        print(f"【{i}】{row['代码']} {row['名称']}")
        print(f"    最新价: {row['最新价']:.2f}元  今日涨跌: {row['涨跌幅']:.2f}%")
        print(f"    60日涨跌: {row['60日涨跌幅']:.2f}%  成交额: {row['成交额(亿)']:.2f}亿")
        print(f"    市盈率: {row['市盈率TTM']:.2f}  市净率: {row['市净率']:.2f}  总市值: {row['总市值(亿)']:.2f}亿")
        print(f"    行业: {row['所处行业']}")
        print(f"    综合得分: {row['综合得分']}分")
        print(f"    触发信号: {row['信号']}")
        print()

    # 保存结果
    output_file = f"选股结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df.to_excel(output_file, index=False)
    print(f"完整结果已保存至: {output_file}")

    print("\n" + "=" * 60)
    print("选股策略说明:")
    print("  - 放量上涨: 当日上涨>2%，成交量/5日均量>=2")
    print("  - 突破新高: 收盘价创60日新高")
    print("  - 均线多头: MA5>MA10>MA20>MA30且向上发散")
    print("  - 平台突破: 突破60日均线后确认站稳")
    print("  - 低波动成长: 波动率低且稳步上涨")
    print("  - RSI超卖反弹: RSI从超卖区回升")
    print("  - MACD金叉: DIF上穿DEA")
    print("=" * 60)


if __name__ == '__main__':
    main()
