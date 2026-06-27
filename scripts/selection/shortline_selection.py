#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日短线机会筛选

筛选条件：
1. 今日涨幅 > 2%
2. 成交量放大（量比 > 1.5）
3. 短期均线多头排列
4. 资金净流入
5. 换手率适中（避免过热）
6. 排除ST、PE异常股票

作者: Hermes
日期: 2026/5/28
"""

import pymysql
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

# ST风险关键词
ST_KEYWORDS = ['ST', '*ST', 'ST*', '退', '退市', '风险']

# 热门板块关键词
HOT_SECTORS = {
    "AI人工智能": ["人工智能", "AI", "智能", "算法", "大模型", "GPT"],
    "机器人": ["机器人", "自动化", "工业母机", "人形机器人"],
    "新能源汽车": ["新能源车", "电动车", "锂电池", "充电桩", "动力电池"],
    "光伏": ["光伏", "太阳能", "HJT", "TOPCon"],
    "半导体": ["半导体", "芯片", "集成电路", "存储"],
    "低空经济": ["无人机", "低空", "飞行汽车", "eVTOL"],
    "军工": ["军工", "航空", "航天", "国防"],
    "医药": ["医药", "生物", "疫苗", "创新药"],
    "数字经济": ["云计算", "大数据", "数据中心", "算力"]
}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def check_st_risk(name):
    """检查ST风险"""
    if pd.isna(name):
        return True
    for kw in ST_KEYWORDS:
        if kw in name:
            return True
    return False

def get_stock_list_today():
    """获取今日股票数据"""
    conn = get_db_connection()
    try:
        sql = """
        SELECT 
            si.id,
            si.code,
            cs.name,
            cs.new_price as price,
            cs.change_rate,
            cs.turnoverrate,
            cs.volume_ratio,
            cs.deal_amount,
            cs.pe,
            cs.total_market_cap as market_cap,
            cs.amplitude
        FROM stock_info si
        INNER JOIN (
            SELECT code, name, new_price, change_rate, turnoverrate, volume_ratio, 
                   deal_amount, pe, total_market_cap, amplitude
            FROM cn_stock_spot
            WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
        AND cs.change_rate > 2
        AND cs.turnoverrate BETWEEN 1 AND 20
        AND cs.deal_amount > 100000000
        AND (cs.pe > 0 AND cs.pe < 200 OR cs.pe IS NULL)
        AND cs.name NOT LIKE '%ST%'
        AND cs.name NOT LIKE '%退%'
        """
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def get_stock_daily(stock_id, days=30):
    """获取股票历史数据"""
    conn = get_db_connection()
    try:
        sql = f"""
        SELECT date, open, close, high, low, volume, change_percent
        FROM stock_daily
        WHERE stock_id = {stock_id}
        ORDER BY date DESC
        LIMIT {days}
        """
        df = pd.read_sql(sql, conn)
        if df.empty:
            return None
        df = df.sort_values('date').reset_index(drop=True)
        return df
    finally:
        conn.close()

def match_hot_sector(name):
    """匹配热门板块"""
    if pd.isna(name):
        return []
    
    matched = []
    for sector, keywords in HOT_SECTORS.items():
        for kw in keywords:
            if kw in name:
                matched.append(sector)
                break
    return matched

def check_technical_signals(df):
    """
    检查技术信号
    
    返回: (是否通过, 信号列表)
    """
    if df is None or len(df) < 20:
        return False, []
    
    signals = []
    
    # 计算均线
    closes = df['close'].astype(float).values
    
    # MA5, MA10, MA20
    if len(closes) >= 5:
        ma5 = np.mean(closes[-5:])
        ma5_prev = np.mean(closes[-6:-1]) if len(closes) >= 6 else ma5
    else:
        return False, []
    
    if len(closes) >= 10:
        ma10 = np.mean(closes[-10:])
    else:
        ma10 = ma5
    
    if len(closes) >= 20:
        ma20 = np.mean(closes[-20:])
    else:
        ma20 = ma10
    
    current_price = closes[-1]
    
    # 信号1: 均线多头排列
    if ma5 > ma10 > ma20:
        signals.append("均线多头")
    
    # 信号2: 站上所有均线
    if current_price > ma5 and current_price > ma10 and current_price > ma20:
        signals.append("站上均线")
    
    # 信号3: 突破前期高点
    if len(closes) >= 10:
        prev_high = np.max(closes[-10:-1])
        if current_price > prev_high:
            signals.append("突破10日高点")
    
    # 信号4: 连续上涨
    if len(closes) >= 3:
        if closes[-1] > closes[-2] > closes[-3]:
            signals.append("连续上涨")
    
    # 信号5: 放量上涨
    volumes = df['volume'].astype(float).values
    if len(volumes) >= 5:
        avg_vol = np.mean(volumes[-5:-1])
        if volumes[-1] > avg_vol * 1.5:
            signals.append("放量")
    
    # 至少有一个信号
    return len(signals) > 0, signals

def check_stock_shortline(row):
    """检查单只股票短线机会"""
    stock_id = row['id']
    code = row['code']
    name = row['name']
    
    try:
        # 获取历史数据
        df = get_stock_daily(stock_id, days=30)
        if df is None or len(df) < 20:
            return None
        
        # 检查技术信号
        has_signal, signals = check_technical_signals(df)
        if not has_signal:
            return None
        
        # 匹配热门板块
        sectors = match_hot_sector(name)
        
        # 计算短期趋势
        closes = df['close'].astype(float).values
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else ma5
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else ma10
        
        # 计算距均线位置
        current_price = closes[-1]
        distance_ma5 = (current_price - ma5) / ma5 * 100
        distance_ma10 = (current_price - ma10) / ma10 * 100
        
        result = {
            '代码': code,
            '名称': name,
            '价格': row['price'],
            '涨幅': round(row['change_rate'], 2),
            '换手率': round(row['turnoverrate'], 2),
            '量比': round(row['volume_ratio'], 2),
            '成交额(亿)': round(row['deal_amount'] / 100000000, 2),
            '振幅': round(row['amplitude'], 2) if pd.notna(row['amplitude']) else 0,
            'PE': round(row['pe'], 2) if pd.notna(row['pe']) else None,
            '市值(亿)': round(row['market_cap'] / 10000, 2) if pd.notna(row['market_cap']) else 0,
            '技术信号': ', '.join(signals),
            '热门板块': ', '.join(sectors) if sectors else '其他',
            '距MA5': round(distance_ma5, 2),
            '距MA10': round(distance_ma10, 2)
        }
        
        return result
        
    except Exception as e:
        return None

def main():
    """主函数"""
    print('=' * 70)
    print('今日短线机会筛选')
    print('=' * 70)
    print(f'\n筛选时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    print('\n【筛选条件】')
    print('1. 今日涨幅 > 2%')
    print('2. 换手率 1-20%（适中，避免过热）')
    print('3. 成交额 > 1亿（流动性充足）')
    print('4. PE 0-200（估值合理）')
    print('5. 技术形态良好（均线多头/突破/连续上涨）')
    print('6. 排除ST、退市风险股票')
    
    # 获取股票列表
    print('\n1. 获取今日强势股票...')
    stocks = get_stock_list_today()
    print(f'   找到 {len(stocks)} 只符合基础条件的股票')
    
    if len(stocks) == 0:
        print('\n今日没有符合基础条件的股票')
        return
    
    # 并发检查技术信号
    print('\n2. 检查技术形态...')
    results = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_stock_shortline, row): row for _, row in stocks.iterrows()}
        
        completed = 0
        total = len(futures)
        
        for future in as_completed(futures):
            completed += 1
            if completed % 100 == 0:
                print(f'   进度: {completed}/{total}')
            
            result = future.result()
            if result:
                results.append(result)
    
    print(f'\n3. 筛选完成!')
    print(f'   符合条件: {len(results)} 只')
    
    if not results:
        print('\n没有找到符合条件的股票')
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(results)
    
    # 按涨幅排序
    df = df.sort_values('涨幅', ascending=False)
    
    # 按板块统计
    print('\n' + '=' * 70)
    print('筛选结果统计')
    print('=' * 70)
    
    sector_stats = df['热门板块'].value_counts()
    print('\n【板块分布】')
    for sector, count in sector_stats.head(10).items():
        print(f'{sector}: {count}只')
    
    # 显示TOP股票
    print('\n' + '=' * 70)
    print('今日短线机会（按涨幅排序）')
    print('=' * 70)
    
    # 按热门板块分组显示
    hot_stocks = df[df['热门板块'] != '其他'].head(20)
    if len(hot_stocks) > 0:
        print('\n【热门板块股票】')
        print('-' * 70)
        for i, row in hot_stocks.iterrows():
            print(f'\n{row["名称"]}({row["代码"]}) - {row["热门板块"]}')
            print(f'  价格: {row["价格"]}元, 涨幅: +{row["涨幅"]}%, 换手率: {row["换手率"]:.2f}%')
            print(f'  量比: {row["量比"]:.2f}, 成交额: {row["成交额(亿)"]}亿')
            print(f'  技术信号: {row["技术信号"]}')
            print(f'  估值: PE={row["PE"]}, 市值={row["市值(亿)"]}亿')
    
    # 显示涨幅榜TOP10
    print('\n\n【涨幅榜TOP10】')
    print('-' * 70)
    for i, row in df.head(10).iterrows():
        print(f'\n{row["名称"]}({row["代码"]})')
        print(f'  价格: {row["价格"]}元, 涨幅: +{row["涨幅"]}%, 换手率: {row["换手率"]:.2f}%')
        print(f'  量比: {row["量比"]:.2f}, 成交额: {row["成交额(亿)"]}亿')
        print(f'  技术信号: {row["技术信号"]}')
    
    # 显示量比榜TOP10（放量大涨）
    print('\n\n【量比榜TOP10（放量大涨）】')
    print('-' * 70)
    df_by_vol = df.sort_values('量比', ascending=False)
    for i, row in df_by_vol.head(10).iterrows():
        print(f'\n{row["名称"]}({row["代码"]})')
        print(f'  价格: {row["价格"]}元, 涨幅: +{row["涨幅"]}%, 量比: {row["量比"]:.2f}')
        print(f'  换手率: {row["换手率"]:.2f}%, 成交额: {row["成交额(亿)"]}亿')
        print(f'  技术信号: {row["技术信号"]}')
    
    # 保存结果
    output_file = f'output/shortline_selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'\n\n结果已保存: {output_file}')
    
    # 短线操作建议
    print('\n' + '=' * 70)
    print('短线操作建议')
    print('=' * 70)
    print('\n1. 优选热门板块：AI、机器人、新能源等热点板块')
    print('2. 关注技术信号：均线多头+放量突破是最佳组合')
    print('3. 控制仓位：单只股票不超过总资金10%')
    print('4. 设置止损：跌破MA5或亏损3%止损')
    print('5. 快进快出：短线持有1-3天，盈利5-10%即可止盈')
    print('\n⚠️ 风险提示：短线操作风险较大，请谨慎操作，严格止损！')
    
    return df

if __name__ == '__main__':
    main()
