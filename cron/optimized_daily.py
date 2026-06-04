#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版每日选股 - 使用腾讯API，无代理，控制频次
"""
import requests
import pandas as pd
import numpy as np
import warnings
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import sys

warnings.filterwarnings('ignore')

# 禁用代理
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('all_proxy', None)
os.environ.pop('ALL_PROXY', None)

# Server酱配置
SENDKEY = 'SCT347969TWcw4Zztqp8nMDiwYE4ik2EOW'

# 请求配置
REQUEST_DELAY = (0.3, 0.8)  # 请求间隔范围(秒)
MAX_WORKERS = 10  # 并发数，降低避免被封
TIMEOUT = 15


def get_market_prefix(code):
    """获取市场前缀"""
    if code.startswith(('600', '601', '603', '605', '688', '689')):
        return 'sh'
    return 'sz'


def fetch_realtime_quotes():
    """获取所有A股实时行情 - 使用腾讯API"""
    print('[1/3] 获取实时行情...')
    
    # 腾讯股票列表API - 一次性获取所有A股
    all_stocks = []
    
    # 沪市A股代码范围
    sh_codes = [
        'sh600000', 'sh600001', 'sh600002', 'sh600003', 'sh600004', 'sh600005',
        'sh600006', 'sh600007', 'sh600008', 'sh600009', 'sh600010', 'sh600011',
    ]
    
    # 使用新浪分页接口获取完整列表（腾讯需要知道具体代码）
    url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    
    session = requests.Session()
    session.trust_env = False  # 禁用代理
    
    all_data = []
    for page in range(1, 60):  # 约5000只股票
        try:
            params = {
                'page': str(page),
                'num': '100',
                'sort': 'changepercent',
                'asc': '0',
                'node': 'hs_a'
            }
            r = session.get(url, params=params, timeout=TIMEOUT)
            data = r.json()
            if not data:
                break
            all_data.extend(data)
            if page % 10 == 0:
                print(f'      已获取 {len(all_data)} 只...')
            time.sleep(random.uniform(*REQUEST_DELAY))
        except Exception as e:
            print(f'      获取第{page}页失败: {e}')
            break
    
    if not all_data:
        print('      获取数据失败')
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    df = df.rename(columns={
        'code': '代码', 'name': '名称', 'trade': '最新价',
        'changepercent': '涨跌幅', 'amount': '成交额',
        'mktcap': '总市值', 'per': '市盈率', 'pb': '市净率',
        'turnoverratio': '换手率'
    })
    
    for col in ['最新价', '涨跌幅', '成交额', '总市值', '市盈率', '市净率', '换手率']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f'      共获取 {len(df)} 只股票')
    return df


def fetch_hist_data_tencent(code, name, row):
    """获取历史数据并分析 - 使用腾讯API"""
    prefix = get_market_prefix(code)
    symbol = f'{prefix}{code}'
    
    # 腾讯历史K线API
    url = 'https://web.sqt.gtimg.cn/q=' + symbol
    
    session = requests.Session()
    session.trust_env = False
    
    try:
        # 添加随机延迟
        time.sleep(random.uniform(*REQUEST_DELAY))
        
        r = session.get(url, timeout=TIMEOUT)
        text = r.text
        
        if not text or 'v_' not in text:
            return None
        
        # 解析腾讯数据格式
        # v_sz000001="51~平安银行~000001~10.86~..."
        import re
        match = re.search(r'v_\w+="([^"]+)"', text)
        if not match:
            return None
        
        parts = match.group(1).split('~')
        if len(parts) < 45:
            return None
        
        # 腾讯数据字段索引
        # 3=最新价, 4=昨收, 5=今开, 6=成交量, 7=成交额, 30=市盈率, 31=最高, 32=最低, 33=换手率
        
        try:
            price = float(parts[3])
            prev_close = float(parts[4])
            high = float(parts[31])
            low = float(parts[32])
            volume = float(parts[6])
            amount = float(parts[7])
            # PE在parts[30]，但格式可能异常，从row获取
            pe = float(row.get('市盈率', 0)) if row.get('市盈率') else 0
            turnover = float(parts[33]) if len(parts) > 33 and parts[33] else 0
        except (ValueError, IndexError):
            return None
        
        # 获取历史数据用于技术分析 - 使用新浪接口
        hist_url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '60'}
        
        time.sleep(random.uniform(*REQUEST_DELAY))
        r2 = session.get(hist_url, params=params, timeout=TIMEOUT)
        hist_data = r2.json()
        
        if not hist_data or len(hist_data) < 30:
            return None
        
        hist_df = pd.DataFrame(hist_data)
        for col in ['open', 'close', 'high', 'low', 'volume']:
            hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')
        
        close = hist_df['close'].values
        
        # 计算技术指标
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
        ma5 = pd.Series(close).rolling(5).mean().values
        ma10 = pd.Series(close).rolling(10).mean().values
        ma20 = pd.Series(close).rolling(20).mean().values
        ma30 = pd.Series(close).rolling(30).mean().values
        
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
        if not np.isnan(ma5[-1]) and not np.isnan(ma30[-1]):
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
                '最新价': price,
                '涨跌幅': row.get('涨跌幅', 0),
                '市盈率': pe,
                '综合得分': score,
                '信号': ', '.join(signals)
            }
    except Exception as e:
        pass
    
    return None


def run_selection():
    """运行选股"""
    print('=' * 60)
    print(f'A股策略选股 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    
    # 获取实时行情
    df = fetch_realtime_quotes()
    if df.empty:
        return []
    
    # 筛选
    print('\n[2/3] 筛选候选股票...')
    candidates = df[
        (df['最新价'] > 3) & (df['最新价'] < 100) &
        (df['成交额'] > 50000000) & (df['总市值'] > 200000) &
        (df['市盈率'] > 0) & (df['市盈率'] < 100)
    ].copy()
    print(f'      筛选后剩余 {len(candidates)} 只')
    
    # 并发分析
    print('\n[3/3] 分析策略信号 (并发处理)...')
    results = []
    total = min(len(candidates), 300)  # 限制分析数量
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for _, row in candidates.head(total).iterrows():
            futures.append(executor.submit(fetch_hist_data_tencent, row['代码'], row['名称'], row))
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                print(f'      进度: {completed}/{total}')
            result = future.result()
            if result:
                results.append(result)
    
    return results


def send_to_wechat(results, date_str):
    """发送到微信"""
    if not results:
        print('没有结果需要推送')
        return False
    
    df = pd.DataFrame(results).sort_values('综合得分', ascending=False)
    
    title = f'📊 A股策略选股 ({date_str})'
    content = f"""
共筛选出 {len(df)} 只股票

🏆 **Top 10:**

|| 排名 | 代码 | 名称 | 价格 | 涨跌 | 得分 | 信号 ||
||------|------|------|------|------|------|------||
"""
    
    for i, row in df.head(10).iterrows():
        content += f"| {i+1} | {row['代码']} | {row['名称']} | {row['最新价']:.2f} | {row['涨跌幅']:.2f}% | {row['综合得分']} | {row['信号']} |\n"
    
    # Server酱推送
    url = f'https://sctapi.ftqq.com/{SENDKEY}.send'
    data = {'title': title, 'desp': content}
    
    session = requests.Session()
    session.trust_env = False
    
    try:
        r = session.post(url, data=data, timeout=10)
        result = r.json()
        if result.get('code') == 0:
            print('✅ 推送成功')
            return True
        else:
            print(f'❌ 推送失败: {result}')
            return False
    except Exception as e:
        print(f'❌ 推送失败: {e}')
        return False


def main():
    """主函数"""
    # 运行选股
    results = run_selection()
    
    # 输出结果
    print('\n' + '=' * 60)
    print('选股结果')
    print('=' * 60)
    
    if results:
        df = pd.DataFrame(results).sort_values('综合得分', ascending=False)
        print(f'\n共找到 {len(df)} 只符合条件的股票，展示前10只:\n')
        
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            print(f"【{i}】{row['代码']} {row['名称']}")
            print(f"    价格: {row['最新价']:.2f}元 | 涨跌: {row['涨跌幅']:.2f}% | PE: {row['市盈率']:.1f}")
            print(f"    得分: {row['综合得分']}分 | 信号: {row['信号']}")
            print()
        
        # 保存结果
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"策略选股_{date_str}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"✅ 结果已保存: {output_file}")
        
        # 推送到微信
        date_str_short = datetime.now().strftime('%m/%d')
        send_to_wechat(results, date_str_short)
    else:
        print('\n未找到符合条件的股票')
    
    print('=' * 60)


if __name__ == '__main__':
    main()
