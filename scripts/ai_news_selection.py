#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI产业链隔夜消息选股

功能：
1. 获取AI产业链相关隔夜新闻（东方财富、新浪财经）
2. 识别新闻中的利好方向（算力、大模型、芯片、应用等）
3. 从数据库筛选AI产业链相关股票
4. 结合技术面（涨幅、成交量、均线）筛选
5. 输出符合条件的目标股票

作者: Hermes
日期: 2026/6/11
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from collections import Counter
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

# AI产业链关键词映射
AI_SECTOR_KEYWORDS = {
    'AI算力': ['算力', 'GPU', '服务器', '数据中心', 'IDC', '智算中心', '英伟达', 'AMD', '华为昇腾'],
    'AI芯片': ['AI芯片', 'GPU芯片', 'NPU', '推理芯片', '训练芯片', '算力芯片', '寒武纪', '海光', '景嘉微'],
    '大模型': ['大模型', 'ChatGPT', 'GPT', 'LLM', '语言模型', '文心一言', '通义千问', 'Kimi', 'DeepSeek'],
    'AIGC应用': ['AIGC', 'AI应用', 'AI办公', 'AI教育', 'AI医疗', 'AI游戏', 'AI视频', 'AI绘画'],
    'AI服务器': ['AI服务器', '服务器', '浪潮', '中科曙光', '工业富联', '紫光股份'],
    '光模块CPO': ['光模块', 'CPO', '中际旭创', '新易盛', '光通信', '400G', '800G'],
    'AI存储': ['AI存储', 'HBM', '存储芯片', '内存', 'DDR5', 'SSD', '闪存'],
    '机器人': ['机器人', '人形机器人', '工业机器人', '服务机器人', '特斯拉机器人', '优必选'],
    '自动驾驶': ['自动驾驶', '智能驾驶', '无人驾驶', '激光雷达', '智驾', '车路协同'],
}

# AI产业链相关股票代码（主流标的）
AI_STOCKS = {
    # 算力服务器
    '000977': '浪潮信息', '603019': '中科曙光', '601138': '工业富联', '000063': '中兴通讯',
    # AI芯片
    '688256': '寒武纪', '688041': '海光信息', '300474': '景嘉微', '300672': '国科微',
    # 光模块CPO
    '300308': '中际旭创', '300502': '新易盛', '002281': '光迅科技', '300620': '光库科技',
    # 大模型应用
    '300033': '同花顺', '300496': '中科创达', '002230': '科大讯飞', '688787': '海天瑞声',
    '300624': '万兴科技', '300364': '中文在线', '688099': '晶晨股份',
    # 数据要素
    '603138': '海量数据', '300229': '拓尔思', '300212': '易华录', '002405': '四维图新',
    # 机器人
    '002747': '埃斯顿', '603283': '赛腾股份', '688169': '石头科技', '002690': '美亚柏科',
    # 存储芯片
    '002049': '紫光国微', '688008': '澜起科技', '603501': '韦尔股份',
    # 消费电子+AI
    '002475': '立讯精密', '002241': '歌尔股份', '600745': '闻泰科技',
}

# 利好关键词
POSITIVE_KEYWORDS = [
    '利好', '大涨', '暴涨', '涨停', '突破', '新高', '订单', '签约', '中标',
    '业绩大增', '扭亏', '暴涨', '翻倍', '扩产', '涨价', '供不应求',
    '超预期', '强劲增长', '市场份额', '技术突破', '领先', '首发',
]


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def fetch_ai_news():
    """获取AI产业链相关新闻"""
    print('\n[1/4] 获取AI产业链隔夜新闻...')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': 'https://finance.sina.com.cn/'
    }
    
    all_news = []
    
    # 新浪财经财经新闻
    try:
        url = 'https://feed.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=50'
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if 'result' in data and 'data' in data['result']:
                news_list = data['result']['data']
                for item in news_list:
                    title = item.get('title', '')
                    if title:
                        all_news.append({
                            '标题': title,
                            '时间': item.get('ctime', ''),
                            '来源': '新浪财经'
                        })
                print(f'   新浪财经: {len(news_list)}条')
    except Exception as e:
        print(f'   新浪财经异常: {str(e)[:50]}')
    
    # 补充：新浪科技新闻
    try:
        url = 'https://feed.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=30'
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if 'result' in data and 'data' in data['result']:
                news_list = data['result']['data']
                for item in news_list:
                    title = item.get('title', '')
                    if title:
                        all_news.append({
                            '标题': title,
                            '时间': item.get('ctime', ''),
                            '来源': '新浪科技'
                        })
                print(f'   新浪科技: {len(news_list)}条')
    except Exception as e:
        print(f'   新浪科技异常: {str(e)[:50]}')
    
    # 过滤AI相关新闻
    ai_news = []
    for news in all_news:
        title = news['标题']
        for sector, keywords in AI_SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    ai_news.append(news)
                    break
    
    print(f'   共获取 {len(ai_news)} 条AI相关新闻（总{len(all_news)}条）')
    return ai_news if ai_news else all_news[:30]


def analyze_ai_news(news_list):
    """分析AI相关新闻，提取利好方向"""
    print('\n[2/4] 分析新闻中的AI利好方向...')
    
    # 统计各方向提及次数
    sector_mentions = Counter()
    hot_stocks = set()
    
    for news in news_list:
        title = news['标题']
        
        # 检查是否AI相关
        is_ai_related = False
        for sector, keywords in AI_SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    sector_mentions[sector] += 1
                    is_ai_related = True
                    break
        
        # 检查是否提到具体股票
        if is_ai_related:
            for code, name in AI_STOCKS.items():
                if name in title:
                    hot_stocks.add(code)
    
    # 找出热门方向
    hot_sectors = sector_mentions.most_common(5)
    
    if hot_sectors:
        print('\n   【热门AI方向】')
        for sector, count in hot_sectors:
            print(f'   • {sector}: {count}条相关新闻')
    else:
        print('   未发现明显热点方向')
    
    if hot_stocks:
        print(f'\n   【新闻提及股票】{len(hot_stocks)}只')
        for code in list(hot_stocks)[:5]:
            print(f'   • {AI_STOCKS.get(code, code)}')
    
    return hot_sectors, hot_stocks


def get_ai_stocks_from_db():
    """从数据库获取AI产业链股票数据"""
    print('\n[3/4] 获取AI产业链股票数据...')
    
    conn = get_db_connection()
    try:
        # 获取AI股票代码列表
        ai_codes = list(AI_STOCKS.keys())
        code_list = "','".join(ai_codes)
        
        # 查询实时行情（从cn_stock_spot最新数据）
        sql = f"""
        SELECT 
            si.code,
            COALESCE(cs.name, si.name) as name,
            cs.new_price as price,
            cs.change_rate as pct_change,
            cs.turnoverrate as turnover,
            cs.deal_amount as amount,
            cs.pe,
            cs.total_market_cap as market_cap
        FROM stock_info si
        LEFT JOIN (
            SELECT code, name, new_price, change_rate, turnoverrate, 
                   deal_amount, pe, total_market_cap
            FROM cn_stock_spot
            WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE si.code IN ('{code_list}')
          AND si.code NOT LIKE '688%%'
        """
        
        df = pd.read_sql(sql, conn)
        
        # 过滤有效数据并去重
        df = df[df['price'].notna() & (df['price'] > 0)]
        df = df.drop_duplicates(subset=['code'], keep='first')
        
        print(f'   找到 {len(df)} 只AI产业链股票（已过滤科创板）')
        return df
    finally:
        conn.close()


def filter_ai_stocks(stocks_df, hot_stocks):
    """筛选符合条件的AI股票"""
    print('\n[4/4] 筛选目标股票...')
    
    if stocks_df.empty:
        return pd.DataFrame()
    
    results = []
    
    for _, row in stocks_df.iterrows():
        code = row['code']
        name = row['name']
        price = float(row['price']) if row['price'] else 0
        pct_change = float(row['pct_change']) if row['pct_change'] else 0
        turnover = float(row['turnover']) if row['turnover'] else 0
        amount = float(row['amount']) if row['amount'] else 0
        pe = float(row['pe']) if row['pe'] else 0
        market_cap = float(row['market_cap']) if row['market_cap'] else 0
        
        # 计算得分
        score = 0
        signals = []
        
        # 1. 新闻热度加分
        if code in hot_stocks:
            score += 30
            signals.append('新闻热点')
        
        # 2. 涨幅筛选
        if -3 <= pct_change <= 7:  # 排除大跌和涨幅过大
            if pct_change > 0:
                score += 10
                signals.append(f'涨{pct_change:.1f}%')
        elif pct_change > 7:
            score += 5  # 涨幅过大谨慎
            signals.append(f'涨幅较大{pct_change:.1f}%')
        
        # 3. 成交量筛选
        if amount > 500000000:  # 5亿以上成交额
            score += 15
            signals.append('放量')
        elif amount > 200000000:  # 2亿以上
            score += 10
            signals.append('成交活跃')
        
        # 4. 换手率筛选
        if 3 <= turnover <= 15:  # 适度换手
            score += 10
            signals.append(f'换手{turnover:.1f}%')
        
        # 5. 估值筛选
        if 0 < pe < 50:
            score += 10
        elif pe < 0:
            score -= 5
            signals.append('亏损')
        
        # 6. 市值筛选
        if market_cap > 10000000000:  # 100亿以上
            score += 10
            signals.append('大盘股')
        
        if score >= 20:
            results.append({
                '代码': code,
                '名称': name,
                '价格': round(price, 2),
                '涨跌幅': round(pct_change, 2),
                '成交额亿': round(amount / 100000000, 2),
                '换手率': round(turnover, 2),
                '市盈率': round(pe, 1) if pe > 0 else '亏损',
                '得分': score,
                '信号': ', '.join(signals)
            })
    
    # 按得分排序
    if results:
        df = pd.DataFrame(results).sort_values('得分', ascending=False)
        return df
    
    return pd.DataFrame()


def main():
    """主函数"""
    print('=' * 60)
    print('AI产业链隔夜消息选股')
    print('=' * 60)
    print(f'日期: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    # 1. 获取新闻
    news_list = fetch_ai_news()
    
    # 2. 分析新闻
    hot_sectors, hot_stocks = analyze_ai_news(news_list)
    
    # 3. 获取AI股票数据
    stocks_df = get_ai_stocks_from_db()
    
    # 4. 筛选股票
    results_df = filter_ai_stocks(stocks_df, hot_stocks)
    
    # 输出结果
    print('\n' + '=' * 60)
    print('选股结果')
    print('=' * 60)
    
    if results_df.empty:
        print('\n未找到符合条件的AI产业链股票')
        return
    
    print(f'\n共筛选出 {len(results_df)} 只目标股票：\n')
    
    for i, row in results_df.head(15).iterrows():
        print(f'【{row["代码"]}】{row["名称"]}')
        print(f'   价格: {row["价格"]}元, 涨跌: {row["涨跌幅"]}%, 换手: {row["换手率"]}%')
        print(f'   成交额: {row["成交额亿"]}亿, PE: {row["市盈率"]}')
        print(f'   得分: {row["得分"]}分 | 信号: {row["信号"]}')
        print()
    
    # 保存结果
    output_dir = 'E:/量化研究/workspace/stock/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file = os.path.join(output_dir, f'ai_selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
    
    print('=' * 60)
    
    return results_df


if __name__ == '__main__':
    main()
