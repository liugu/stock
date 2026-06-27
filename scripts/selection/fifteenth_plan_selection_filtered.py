#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十五五规划相关板块低位潜力股票筛选 - 增强版
添加财务健康度过滤：排除ST风险、净利润亏损

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

# 十五五规划重点板块关键词映射
FIFTEENTH_PLAN_SECTORS = {
    "新质生产力-AI": ["人工智能", "AI", "智能", "算法", "芯片", "算力", "数据", "软件", "信息"],
    "新质生产力-机器人": ["机器人", "自动化", "工业母机", "数控", "伺服", "精密"],
    "新能源-光伏": ["光伏", "太阳能", "硅料", "多晶", "单晶", "电池片", "组件"],
    "新能源-风电": ["风电", "风力", "叶片", "塔筒", "风能"],
    "新能源-储能": ["储能", "电池", "锂电", "钠电", "氢能", "充电"],
    "新能源-汽车": ["新能源车", "电动车", "汽车电子", "动力电池", "电机"],
    "数字经济": ["云计算", "大数据", "物联网", "5G", "通信", "数据中心", "IDC"],
    "高端制造-半导体": ["半导体", "芯片", "集成电路", "晶圆", "封测", "光刻"],
    "高端制造-军工": ["军工", "航空", "航天", "国防", "兵器", "雷达"],
    "生物医药": ["医药", "生物", "疫苗", "创新药", "CRO", "CDMO", "医疗器械"],
    "新材料": ["新材料", "稀土", "磁性材料", "碳纤维", "复合材料", "特种材料"],
    "低空经济": ["无人机", "低空", "飞行器", "eVTOL"],
    "商业航天": ["卫星", "火箭", "航天", "空间"]
}

# ST风险关键词
ST_KEYWORDS = ['ST', '*ST', 'ST*', '退', '退市', '风险']

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def get_stock_list():
    """获取股票列表，包含财务数据"""
    conn = get_db_connection()
    try:
        sql = """
        SELECT DISTINCT 
            si.id, 
            si.code, 
            COALESCE(cs.name, si.name) as name,
            cs.new_price as price,
            cs.change_rate as change_pct,
            cs.turnoverrate as turnover,
            cs.pe as pe_ratio,
            cs.pbnewmrq as pb_ratio,
            cs.roe_weight as roe,
            cs.total_market_cap as market_cap,
            cs.industry
        FROM stock_info si
        INNER JOIN stock_daily sd ON si.id = sd.stock_id
        INNER JOIN (
            SELECT code, name, new_price, change_rate, turnoverrate, pe, pbnewmrq, roe_weight, total_market_cap, industry
            FROM cn_stock_spot
            WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE sd.date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
        AND si.code REGEXP '^(600|601|603|605|000|001|002|003|300|301)'
        """
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def match_sector(name):
    """匹配股票所属板块"""
    if pd.isna(name):
        return []
    
    matched = []
    for sector, keywords in FIFTEENTH_PLAN_SECTORS.items():
        for kw in keywords:
            if kw in name:
                matched.append(sector)
                break
    return matched

def check_st_risk(name):
    """检查ST风险"""
    if pd.isna(name):
        return True  # 无名称的股票跳过
    
    # 检查是否包含ST关键词
    for kw in ST_KEYWORDS:
        if kw in name:
            return True
    
    return False

def check_financial_health(row):
    """
    检查财务健康度
    
    过滤条件:
    1. 排除ST股票（名称检查）
    2. PE必须为正且合理（PE > 0 且 PE < 200）
    3. 市值必须大于10亿（排除小盘股风险）
    """
    # 检查ST风险
    name = row['name']
    if check_st_risk(name):
        return False, "ST风险"
    
    # 检查PE（市盈率）
    pe = row['pe_ratio']
    if pd.notna(pe):
        if pe <= 0 or pe > 200:  # PE负值或超高PE（可能亏损或估值过高）
            return False, "PE异常"
    
    # 检查市值（避免小盘股风险）
    market_cap = row['market_cap']
    if pd.notna(market_cap) and market_cap < 100000:  # 市值小于10亿（单位：万元）
        return False, "市值过小"
    
    return True, "财务健康"

def get_stock_daily(stock_id, days=250):
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

def check_low_position(df, lookback=250, max_price_ratio=1.5, percentile=30):
    """
    检查股价是否在低位
    
    参数:
        max_price_ratio: 当前价/期间最低价 <= 1.5 (距低点不超过50%)
        percentile: 价格分位数 <= 30% (处于历史低位区域)
    """
    if df is None or len(df) < 60:
        return False, {}
    
    actual_lookback = min(lookback, len(df))
    recent = df.tail(actual_lookback)
    
    current_close = float(recent.iloc[-1]['close'])
    period_low = float(recent['low'].min())
    period_high = float(recent['high'].max())
    
    # 计算价格比率
    price_ratio = current_close / period_low if period_low > 0 else 999
    
    # 计算价格分位数
    closes = recent['close'].astype(float).values
    price_pct = (np.sum(closes <= current_close) / len(closes)) * 100
    
    # 判断低位
    is_low = price_ratio <= max_price_ratio and price_pct <= percentile
    
    details = {
        'current_price': round(current_close, 2),
        'period_low': round(period_low, 2),
        'period_high': round(period_high, 2),
        'price_ratio': round(price_ratio, 2),
        'price_percentile': round(price_pct, 1),
        'distance_from_low': round((current_close - period_low) / period_low * 100, 2),
        'distance_from_high': round((period_high - current_close) / period_high * 100, 2)
    }
    
    return is_low, details

def check_stock(row):
    """检查单只股票"""
    stock_id = row['id']
    code = row['code']
    name = row['name']
    
    try:
        # 1. 匹配板块
        sectors = match_sector(name)
        if not sectors:
            return None
        
        # 2. 检查财务健康度
        is_healthy, reason = check_financial_health(row)
        if not is_healthy:
            return None
        
        # 3. 获取历史数据
        df = get_stock_daily(stock_id, days=250)
        if df is None or len(df) < 60:
            return None
        
        # 4. 检查低位
        is_low, low_details = check_low_position(df)
        if not is_low:
            return None
        
        # 5. 获取最新数据
        last_row = df.iloc[-1]
        latest_price = float(last_row['close'])
        change_pct = float(last_row['change_percent']) if last_row['change_percent'] is not None else 0
        
        # 6. 计算成交量比
        recent_vol = df.tail(5)['volume'].mean()
        hist_vol = df.head(60)['volume'].mean()
        vol_ratio = round(recent_vol / hist_vol, 2) if hist_vol > 0 else 0
        
        # 7. 获取财务数据
        pe = row['pe_ratio'] if pd.notna(row['pe_ratio']) else None
        pb = row['pb_ratio'] if pd.notna(row['pb_ratio']) else None
        roe = row['roe'] if pd.notna(row['roe']) else None
        market_cap = row['market_cap'] if pd.notna(row['market_cap']) else 0
        
        result = {
            '代码': code,
            '名称': name,
            '板块': ', '.join(sectors),
            '最新价': latest_price,
            '涨跌幅': round(change_pct, 2),
            '换手率': row['turnover'] if pd.notna(row['turnover']) else 0,
            '量比': vol_ratio,
            'PE': round(pe, 2) if pe and pe > 0 else None,
            'PB': round(pb, 2) if pb and pb > 0 else None,
            'ROE': round(roe, 2) if roe and roe > 0 else None,
            '市值(亿)': round(market_cap / 100000000, 2) if market_cap > 0 else 0,
            **low_details
        }
        
        return result
        
    except Exception as e:
        return None

def main():
    """主函数"""
    print('=' * 70)
    print('十五五规划相关板块低位潜力股票筛选 - 增强版')
    print('=' * 70)
    
    # 显示筛选条件
    print('\n【筛选条件】')
    print('1. 十五五规划重点板块：AI、机器人、新能源、数字经济、生物医药等')
    print('2. 价格低位：价格分位数 ≤ 30%，距年内低点 ≤ 50%')
    print('3. 财务健康：')
    print('   - 排除ST、*ST、退市风险股票')
    print('   - PE为正且合理（0 < PE < 200）')
    print('   - 市值 ≥ 10亿（排除小盘股风险）')
    
    # 显示重点板块
    print('\n【十五五规划重点发展方向】')
    for i, sector in enumerate(FIFTEENTH_PLAN_SECTORS.keys(), 1):
        print(f'{i}. {sector}')
    
    # 获取股票列表
    print('\n1. 获取股票列表（含财务数据）...')
    stocks = get_stock_list()
    print(f'   共 {len(stocks)} 只股票')
    
    # 统计财务过滤
    print('\n2. 预筛选财务健康度...')
    
    # 统计ST股票
    st_count = 0
    pe_abnormal_count = 0
    small_cap_count = 0
    
    for _, row in stocks.iterrows():
        if check_st_risk(row['name']):
            st_count += 1
        elif pd.notna(row['pe_ratio']) and (row['pe_ratio'] <= 0 or row['pe_ratio'] > 200):
            pe_abnormal_count += 1
        elif pd.notna(row['market_cap']) and row['market_cap'] < 1000000000:
            small_cap_count += 1
    
    print(f'   ST风险股票: {st_count} 只 (已排除)')
    print(f'   PE异常(≤0或>200): {pe_abnormal_count} 只 (已排除)')
    print(f'   市值过小(<10亿): {small_cap_count} 只 (已排除)')
    
    # 并发检查
    print('\n3. 筛选十五五规划相关板块低位股票...')
    results = []
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(check_stock, row): row for _, row in stocks.iterrows()}
        
        completed = 0
        total = len(futures)
        
        for future in as_completed(futures):
            completed += 1
            if completed % 500 == 0:
                print(f'   进度: {completed}/{total}')
            
            result = future.result()
            if result:
                results.append(result)
    
    print(f'\n4. 筛选完成!')
    print(f'   符合条件: {len(results)} 只')
    
    if not results:
        print('\n没有找到符合条件的股票')
        return
    
    # 转换为DataFrame并去重
    df = pd.DataFrame(results)
    df_unique = df.drop_duplicates(subset=['代码'], keep='first')
    df_unique = df_unique.sort_values(['板块', 'distance_from_low'])
    
    # 按板块统计
    print('\n' + '=' * 70)
    print('筛选结果统计')
    print('=' * 70)
    
    sector_stats = df_unique['板块'].value_counts()
    print('\n【板块分布】')
    for sector, count in sector_stats.items():
        print(f'{sector}: {count}只')
    
    # 打印结果
    print('\n' + '=' * 70)
    print('各板块重点推荐股票')
    print('=' * 70)
    
    # 按板块分组显示TOP股票
    for sector in FIFTEENTH_PLAN_SECTORS.keys():
        sector_df = df_unique[df_unique['板块'].str.contains(sector)]
        if len(sector_df) > 0:
            print(f'\n【{sector}】({len(sector_df)}只)')
            print('-' * 70)
            for i, row in sector_df.head(5).iterrows():
                print(f'• {row["名称"]}({row["代码"]})')
                print(f'  价格: {row["最新价"]}元, 涨幅: +{row["涨跌幅"]}%, 换手率: {row["换手率"]:.2f}%')
                print(f'  估值: PE={row["PE"]}, PB={row["PB"]}, ROE={row["ROE"]}%')
                print(f'  市值: {row["市值(亿)"]}亿')
                print(f'  距低点: {row["distance_from_low"]}%, 距高点: {row["distance_from_high"]}%')
                print(f'  价格分位: {row["price_percentile"]}%')
    
    # 保存结果
    output_file = f'output/fifteenth_plan_selection_filtered_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df_unique.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'\n\n结果已保存: {output_file}')
    
    # 按价格分位数排序，显示最安全的股票
    print('\n' + '=' * 70)
    print('价格分位极低股票（分位<5%，最安全）')
    print('=' * 70)
    
    very_low_df = df_unique[df_unique['price_percentile'] < 5].sort_values('price_percentile')
    for i, row in very_low_df.head(10).iterrows():
        print(f'{row["名称"]}({row["代码"]}) - {row["板块"]}')
        print(f'  价格: {row["最新价"]}元, 价格分位: {row["price_percentile"]}%')
        print(f'  估值: PE={row["PE"]}, PB={row["PB"]}, ROE={row["ROE"]}%')
    
    return df_unique

if __name__ == '__main__':
    main()