#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隔夜财经新闻选股

功能：
1. 获取隔夜财经新闻（新浪财经、新浪科技）
2. 识别新闻中的热点板块（AI、新能源、医药、消费、金融等）
3. 从数据库筛选相关股票
4. 结合技术面（涨幅、成交量、换手率）筛选
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

# 热点板块关键词映射
SECTOR_KEYWORDS = {
    # 科技板块
    'AI算力': ['算力', 'GPU', '服务器', '数据中心', 'IDC', '智算中心', '英伟达', 'AMD'],
    'AI芯片': ['AI芯片', 'GPU芯片', 'NPU', '推理芯片', '寒武纪', '海光', '景嘉微'],
    '大模型': ['大模型', 'ChatGPT', 'GPT', 'LLM', '文心一言', '通义千问', 'Kimi', 'DeepSeek'],
    'AIGC': ['AIGC', 'AI应用', 'AI办公', 'AI教育', 'AI游戏', 'AI视频'],
    '光模块CPO': ['光模块', 'CPO', '中际旭创', '新易盛', '光通信', '400G', '800G'],
    '机器人': ['机器人', '人形机器人', '工业机器人', '特斯拉机器人', '优必选'],
    '自动驾驶': ['自动驾驶', '智能驾驶', '无人驾驶', '激光雷达', '车路协同'],
    '半导体': ['半导体', '芯片', '集成电路', '晶圆', '光刻机', '存储芯片'],
    '消费电子': ['消费电子', '手机', '苹果', '华为', '小米', 'VR', 'AR'],
    
    # 新能源板块
    '新能源汽车': ['新能源车', '电动汽车', '锂电池', '充电桩', '特斯拉', '比亚迪', '蔚来', '理想'],
    '光伏': ['光伏', '太阳能', '硅料', '逆变器', 'HJT', 'TOPCon'],
    '风电': ['风电', '风力发电', '风机', '海上风电'],
    '储能': ['储能', '电池', '钠离子电池', '固态电池', '氢能'],
    '电力': ['电力', '电网', '特高压', '虚拟电厂'],
    
    # 医药板块
    '医药生物': ['医药', '生物制药', '疫苗', '创新药', 'CRO', 'CDMO'],
    '医疗器械': ['医疗器械', '医疗设备', 'IVD', '手术机器人'],
    '中药': ['中药', '中成药', '中医药'],
    
    # 消费板块
    '白酒': ['白酒', '茅台', '五粮液', '泸州老窖', '酒类'],
    '食品饮料': ['食品', '饮料', '乳制品', '调味品', '预制菜'],
    '旅游酒店': ['旅游', '酒店', '景区', '免税', '出行'],
    '零售消费': ['零售', '电商', '消费', '百货'],
    
    # 金融板块
    '银行': ['银行', '信贷', '存款利率', '贷款利率'],
    '保险': ['保险', '寿险', '财险'],
    '证券': ['券商', '证券', '投行', '资管'],
    
    # 地产基建
    '房地产': ['房地产', '地产', '楼市', '房价', '保障房'],
    '基建': ['基建', '建筑', '工程', '水泥', '钢铁'],
    
    # 能源资源
    '煤炭': ['煤炭', '焦煤', '动力煤'],
    '石油石化': ['石油', '石化', '油气', '天然气'],
    '有色金属': ['有色金属', '铜', '铝', '锂', '稀土', '黄金'],
    
    # 制造业
    '汽车': ['汽车', '整车', '零部件', '汽车电子'],
    '机械设备': ['机械', '设备', '工程机械', '机床', '工业母机'],
    '军工': ['军工', '国防', '航空航天', '船舶'],
    
    # 其他
    '传媒': ['传媒', '影视', '游戏', '出版'],
    '教育': ['教育', '培训'],
    '环保': ['环保', '碳中和', '污水处理'],
}

# 热门股票代码（各行业龙头）
HOT_STOCKS = {
    # AI算力
    '000977': '浪潮信息', '603019': '中科曙光', '601138': '工业富联', '000063': '中兴通讯',
    # AI芯片
    '688256': '寒武纪', '688041': '海光信息', '300474': '景嘉微',
    # 光模块
    '300308': '中际旭创', '300502': '新易盛', '002281': '光迅科技', '300620': '光库科技',
    # 大模型应用
    '300033': '同花顺', '300496': '中科创达', '002230': '科大讯飞',
    '300624': '万兴科技', '300364': '中文在线',
    # 机器人
    '002747': '埃斯顿', '603283': '赛腾股份', '688169': '石头科技',
    # 半导体
    '002049': '紫光国微', '688008': '澜起科技', '603501': '韦尔股份',
    # 消费电子
    '002475': '立讯精密', '002241': '歌尔股份', '600745': '闻泰科技',
    # 新能源汽车
    '002594': '比亚迪', '300750': '宁德时代', '002460': '赣锋锂业',
    '300014': '亿纬锂能', '002074': '国轩高科', '300124': '汇川技术',
    # 光伏
    '601012': '隆基绿能', '002459': '晶澳科技', '300274': '阳光电源',
    '605117': '德业股份', '688599': '天合光能',
    # 储能
    '300014': '亿纬锂能', '002074': '国轩高科', '300769': '德方纳米',
    # 医药
    '300760': '迈瑞医疗', '300347': '泰格医药', '603259': '药明康德',
    '000661': '长春高新', '300122': '智飞生物', '002821': '凯莱英',
    # 白酒
    '600519': '贵州茅台', '000858': '五粮液', '000568': '泸州老窖',
    '002304': '洋河股份', '000596': '古井贡酒',
    # 食品饮料
    '600887': '伊利股份', '000895': '双汇发展', '603369': '今世缘',
    # 银行
    '601398': '工商银行', '601288': '农业银行', '600036': '招商银行',
    '601166': '兴业银行', '000001': '平安银行',
    # 券商
    '600030': '中信证券', '601211': '国泰君安', '600837': '海通证券',
    '601688': '华泰证券', '000166': '申万宏源',
    # 保险
    '601318': '中国平安', '601601': '中国太保', '601336': '新华保险',
    # 地产
    '000002': '万科A', '001979': '招商蛇口', '600048': '保利发展',
    # 基建
    '601668': '中国建筑', '601390': '中国中铁', '601186': '中国铁建',
    # 煤炭
    '601225': '陕西煤业', '601088': '中国神华', '000983': '山西焦煤',
    # 有色金属
    '601899': '紫金矿业', '002460': '赣锋锂业', '600547': '山东黄金',
    # 汽车
    '000625': '长安汽车', '601238': '广汽集团', '600104': '上汽集团',
    '601633': '长城汽车', '601127': '小康股份',
    # 军工
    '600893': '航发动力', '002049': '紫光国微', '600862': '中航沈飞',
    # 传媒
    '300059': '东方财富', '603444': '吉比特', '002624': '完美世界',
    # 旅游
    '601888': '中国中免', '000888': '峨眉山A', '600054': '黄山旅游',
}

# 利好关键词
POSITIVE_KEYWORDS = [
    '利好', '大涨', '暴涨', '涨停', '突破', '新高', '订单', '签约', '中标',
    '业绩大增', '扭亏', '翻倍', '扩产', '涨价', '供不应求',
    '超预期', '强劲增长', '技术突破', '领先', '首发',
]


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def fetch_news():
    """获取财经新闻"""
    print('\n[1/4] 获取隔夜财经新闻...')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': 'https://finance.sina.com.cn/'
    }
    
    all_news = []
    
    # 新浪财经
    try:
        url = 'https://feed.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=80'
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
    
    # 新浪科技
    try:
        url = 'https://feed.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=50'
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
    
    print(f'   共获取 {len(all_news)} 条新闻')
    return all_news


def analyze_news(news_list):
    """分析新闻热点板块"""
    print('\n[2/4] 分析新闻热点板块...')
    
    # 统计各板块提及次数
    sector_mentions = Counter()
    hot_stocks = set()
    
    for news in news_list:
        title = news['标题']
        
        # 检查板块关键词
        for sector, keywords in SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    sector_mentions[sector] += 1
                    break
        
        # 检查股票名称
        for code, name in HOT_STOCKS.items():
            if name in title:
                hot_stocks.add(code)
    
    # 找出热门板块
    hot_sectors = sector_mentions.most_common(8)
    
    if hot_sectors:
        print('\n   【热门板块】')
        for sector, count in hot_sectors:
            print(f'   • {sector}: {count}条新闻')
    else:
        print('   未发现明显热点板块')
    
    if hot_stocks:
        print(f'\n   【新闻提及股票】{len(hot_stocks)}只')
        for code in list(hot_stocks)[:8]:
            print(f'   • {HOT_STOCKS.get(code, code)}')
    
    return hot_sectors, hot_stocks


def get_stocks_from_db():
    """从数据库获取热门股票数据（优先cn_stock_spot，其次stock_daily）"""
    print('\n[3/4] 获取热门股票数据...')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查cn_stock_spot是否有今天数据
    cursor.execute('SELECT MAX(date) FROM cn_stock_spot')
    spot_date = cursor.fetchone()[0]
    
    # 获取股票代码列表
    codes = list(HOT_STOCKS.keys())
    code_list = "','".join(codes)
    
    # 优先使用cn_stock_spot（有PE数据）
    if spot_date:
        print(f'   cn_stock_spot 最新日期: {spot_date}')
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
            WHERE date = '{spot_date}'
        ) cs ON BINARY si.code = BINARY cs.code
        WHERE si.code IN ('{code_list}')
          AND si.code NOT LIKE '688%%'
        """
    else:
        # 使用stock_daily
        cursor.execute('SELECT MAX(date) FROM stock_daily')
        daily_date = cursor.fetchone()[0]
        print(f'   stock_daily 最新日期: {daily_date}')
        sql = f"""
        SELECT 
            si.code,
            si.name,
            sd.close as price,
            sd.change_percent as pct_change,
            sd.turnover_rate as turnover,
            sd.amount as amount,
            NULL as pe,
            NULL as market_cap
        FROM stock_info si
        INNER JOIN (
            SELECT stock_id, date, close, change_percent, turnover_rate, amount
            FROM stock_daily
            WHERE date = (SELECT MAX(date) FROM stock_daily)
        ) sd ON si.id = sd.stock_id
        WHERE si.code IN ('{code_list}')
          AND si.code NOT LIKE '688%%'
        """
    
    cursor.close()
    
    df = pd.read_sql(sql, conn)
    conn.close()
    
    df = df[df['price'].notna() & (df['price'] > 0)]
    df = df.drop_duplicates(subset=['code'], keep='first')
    
    print(f'   找到 {len(df)} 只热门股票（已过滤科创板）')
    return df


def filter_stocks(stocks_df, hot_stocks):
    """筛选符合条件的目标股票"""
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
        if -5 <= pct_change <= 7:  # 合理涨跌幅区间
            if pct_change > 0:
                score += 15
                signals.append(f'涨{pct_change:.1f}%')
            elif pct_change < 0:
                score += 5
                signals.append(f'跌{abs(pct_change):.1f}%')
        elif pct_change > 7:
            score += 5
            signals.append(f'涨幅较大{pct_change:.1f}%')
        
        # 3. 成交量筛选
        if amount > 500000000:  # 5亿以上
            score += 15
            signals.append('放量')
        elif amount > 200000000:  # 2亿以上
            score += 10
            signals.append('成交活跃')
        
        # 4. 换手率筛选
        if 2 <= turnover <= 15:
            score += 10
            signals.append(f'换手{turnover:.1f}%')
        
        # 5. 估值筛选（无PE数据时跳过）
        if pe and pe > 0:
            if pe < 50:
                score += 10
        elif pe and pe < 0:
            score -= 5
            signals.append('亏损')
        
        # 6. 市值筛选
        if market_cap > 10000000000:  # 100亿以上
            score += 5
        
        if score >= 20:
            results.append({
                '代码': code,
                '名称': name,
                '价格': round(price, 2),
                '涨跌幅': round(pct_change, 2),
                '成交额亿': round(amount / 100000000, 2),
                '换手率': round(turnover, 2),
                '市盈率': round(pe, 1) if pe and pe > 0 else ('亏损' if pe and pe < 0 else '-'),
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
    print('隔夜财经新闻选股')
    print('=' * 60)
    print(f'日期: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    
    # 1. 获取新闻
    news_list = fetch_news()
    
    # 2. 分析新闻
    hot_sectors, hot_stocks = analyze_news(news_list)
    
    # 3. 获取股票数据
    stocks_df = get_stocks_from_db()
    
    # 4. 筛选股票
    results_df = filter_stocks(stocks_df, hot_stocks)
    
    # 输出结果
    print('\n' + '=' * 60)
    print('选股结果')
    print('=' * 60)
    
    if results_df.empty:
        print('\n未找到符合条件的目标股票')
        return
    
    print(f'\n共筛选出 {len(results_df)} 只目标股票：\n')
    
    for i, row in results_df.head(20).iterrows():
        print(f'【{row["代码"]}】{row["名称"]}')
        print(f'   价格: {row["价格"]}元, 涨跌: {row["涨跌幅"]}%, 换手: {row["换手率"]}%')
        print(f'   成交额: {row["成交额亿"]}亿, PE: {row["市盈率"]}')
        print(f'   得分: {row["得分"]}分 | 信号: {row["信号"]}')
        print()
    
    # 保存结果
    output_dir = 'E:/量化研究/workspace/stock/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file = os.path.join(output_dir, f'news_selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'结果已保存: {output_file}')
    
    print('=' * 60)
    
    return results_df


if __name__ == '__main__':
    main()
