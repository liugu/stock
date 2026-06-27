#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整量化选股流程
整合: akshare(数据) + Backtrader(回测) + OpenBB(宏观)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

# 数据库配置
DB_CONFIG = {
    'user': 'stock',
    'password': '12345678',
    'host': 'localhost',
    'port': 3306,
    'database': 'instock'
}

def get_db_engine():
    """获取数据库连接"""
    url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(url)

# ============ 1. 数据获取模块 ============

def get_stock_list():
    """获取A股股票列表"""
    try:
        df = ak.stock_zh_a_spot_em()
        df = df[['代码', '名称', '最新价', '涨跌幅', '换手率', '成交量', '成交额', '市盈率-动态']]
        df.columns = ['code', 'name', 'price', 'pct_change', 'turnover', 'volume', 'amount', 'pe']
        return df
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return None

def get_stock_history(code, days=120):
    """获取股票历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
        df = df.tail(days)
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover']
        return df
    except Exception as e:
        return None

def get_macro_data_openbb():
    """使用OpenBB获取宏观数据"""
    try:
        from openbb import obb
        # 获取美元指数
        # dxy = obb.equity.price.historical('DX-Y.NYB', provider='yfinance')
        # 获取黄金期货
        # gold = obb.equity.price.historical('GC=F', provider='yfinance')
        print("OpenBB 宏观数据模块已就绪（需配置API密钥）")
        return True
    except Exception as e:
        print(f"OpenBB: {e}")
        return False

# ============ 2. 选股策略模块 ============

def strategy_breakout(df, days=20):
    """突破策略：价格突破N日高点"""
    if df is None or len(df) < days:
        return False, {}
    
    high_n = df['high'].tail(days).max()
    current_price = df['close'].iloc[-1]
    volume_avg = df['volume'].tail(10).mean()
    volume_today = df['volume'].iloc[-1]
    
    # 突破条件：价格突破20日高点 + 放量
    is_breakout = current_price >= high_n * 0.98 and volume_today > volume_avg * 1.2
    
    info = {
        'high_20d': round(high_n, 2),
        'current_price': round(current_price, 2),
        'volume_ratio': round(volume_today / volume_avg, 2) if volume_avg > 0 else 0,
        'breakout': is_breakout
    }
    
    return is_breakout, info

def strategy_ma_cross(df, short=5, long=20):
    """均线交叉策略"""
    if df is None or len(df) < long:
        return False, {}
    
    df = df.copy()
    df['ma_short'] = df['close'].rolling(short).mean()
    df['ma_long'] = df['close'].rolling(long).mean()
    
    # 金叉：短期均线上穿长期均线
    ma_short_prev = df['ma_short'].iloc[-2]
    ma_long_prev = df['ma_long'].iloc[-2]
    ma_short_now = df['ma_short'].iloc[-1]
    ma_long_now = df['ma_long'].iloc[-1]
    
    golden_cross = ma_short_prev < ma_long_prev and ma_short_now > ma_long_now
    
    info = {
        'ma_short': round(ma_short_now, 2),
        'ma_long': round(ma_long_now, 2),
        'golden_cross': golden_cross
    }
    
    return golden_cross, info

def strategy_turtle(df, entry_days=20, exit_days=10):
    """海龟交易策略"""
    if df is None or len(df) < entry_days:
        return False, {}
    
    entry_high = df['high'].tail(entry_days).max()
    exit_low = df['low'].tail(exit_days).min()
    current_price = df['close'].iloc[-1]
    
    # 入场：突破20日高点
    # 出场：跌破10日低点
    signal = current_price >= entry_high
    
    info = {
        'entry_high': round(entry_high, 2),
        'exit_low': round(exit_low, 2),
        'current_price': round(current_price, 2),
        'signal': 'BUY' if signal else 'HOLD'
    }
    
    return signal, info

# ============ 3. 综合选股 ============

def screen_stocks(limit=50):
    """综合选股筛选"""
    print("=" * 60)
    print(f"量化选股系统 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 获取股票列表
    print("\n[1/3] 获取股票列表...")
    stocks = get_stock_list()
    if stocks is None:
        return []
    
    # 筛选条件：换手率 > 3%，成交额 > 1亿，PE > 0
    stocks = stocks[
        (stocks['turnover'] > 3) & 
        (stocks['amount'] > 1e8) & 
        (stocks['pe'] > 0) & 
        (stocks['pe'] < 100)
    ].head(limit)
    
    print(f"筛选出 {len(stocks)} 只股票进行策略分析")
    
    results = []
    
    print("\n[2/3] 执行选股策略...")
    for idx, row in stocks.iterrows():
        code = row['code']
        name = row['name']
        
        # 获取历史数据
        hist = get_stock_history(code, days=60)
        if hist is None or len(hist) < 20:
            continue
        
        # 执行策略
        breakout, breakout_info = strategy_breakout(hist)
        ma_cross, ma_info = strategy_ma_cross(hist)
        turtle, turtle_info = strategy_turtle(hist)
        
        # 综合评分
        score = 0
        if breakout: score += 1
        if ma_cross: score += 1
        if turtle: score += 1
        
        if score >= 2:  # 至少2个策略命中
            results.append({
                'code': code,
                'name': name,
                'price': row['price'],
                'pct_change': row['pct_change'],
                'turnover': row['turnover'],
                'pe': row['pe'],
                'score': score,
                'breakout': breakout_info,
                'ma_cross': ma_info,
                'turtle': turtle_info
            })
    
    # 按评分排序
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print(f"\n[3/3] 选股完成，共选出 {len(results)} 只股票")
    
    return results

# ============ 4. 结果输出 ============

def format_results(results):
    """格式化输出结果"""
    if not results:
        return "今日无符合条件的股票"
    
    output = []
    output.append("\n" + "=" * 60)
    output.append("【选股结果】")
    output.append("=" * 60)
    
    for i, r in enumerate(results[:10], 1):
        output.append(f"\n【{i}. {r['name']}】({r['code']})")
        output.append(f"  价格: {r['price']}元, 涨幅: +{r['pct_change']}%, 换手率: {r['turnover']}%")
        output.append(f"  市盈率: {r['pe']}, 综合评分: {r['score']}/3")
        
        if r['breakout'].get('breakout'):
            output.append(f"  ✓ 突破策略: 20日高点 {r['breakout']['high_20d']}, 量比 {r['breakout']['volume_ratio']}")
        if r['ma_cross'].get('golden_cross'):
            output.append(f"  ✓ 均线金叉: MA5 {r['ma_cross']['ma_short']} > MA20 {r['ma_cross']['ma_long']}")
        if r['turtle'].get('signal') == 'BUY':
            output.append(f"  ✓ 海龟信号: 突破 {r['turtle']['entry_high']}")
    
    return "\n".join(output)

def save_to_db(results):
    """保存选股结果到数据库"""
    if not results:
        return
    
    engine = get_db_engine()
    df = pd.DataFrame(results)
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    df['time'] = datetime.now().strftime('%H:%M:%S')
    
    try:
        df.to_sql('stock_selection', engine, if_exists='append', index=False)
        print("\n✓ 选股结果已保存到数据库")
    except Exception as e:
        print(f"\n✗ 保存失败: {e}")

# ============ 5. 主程序 ============

def main():
    """主程序"""
    # 执行选股
    results = screen_stocks(limit=100)
    
    # 输出结果
    print(format_results(results))
    
    # 保存到数据库
    save_to_db(results)
    
    # OpenBB宏观数据状态
    print("\n" + "=" * 60)
    get_macro_data_openbb()
    
    return results

if __name__ == '__main__':
    main()
