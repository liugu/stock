#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
消息面分析模块
功能：
1. 收集财经新闻（东方财富、同花顺、新浪）
2. 分析利好板块
3. 生成每日报告并推送

使用方法：
    python news_analysis.py                    # 分析今日新闻
    python news_analysis.py --push             # 分析并推送微信
    python news_analysis.py --date 2024-01-15  # 指定日期
"""

import argparse
import datetime
import json
import logging
import os
import re
import sys
import time
from collections import Counter, defaultdict

import pandas as pd
import requests

# 配置
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'daily_task_config.json')

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    filename=os.path.join(LOG_DIR, 'news_analysis.log'),
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== 板块关键词映射 ====================
SECTOR_KEYWORDS = {
    # 科技板块
    '人工智能': ['AI', '人工智能', 'ChatGPT', '大模型', 'AIGC', '机器学习', '深度学习', '算力', 'GPU'],
    '芯片半导体': ['芯片', '半导体', '集成电路', '晶圆', '光刻机', '存储芯片', 'GPU', 'CPU'],
    '消费电子': ['手机', '苹果', '华为', '小米', '消费电子', '智能穿戴', 'VR', 'AR'],
    '通信5G': ['5G', '通信', '基站', '光纤', '物联网', '卫星通信', '6G'],
    '计算机': ['软件', '云计算', '大数据', '网络安全', '信创', '操作系统', '数据库'],
    
    # 新能源板块
    '新能源汽车': ['新能源车', '电动汽车', '锂电池', '充电桩', '特斯拉', '比亚迪', '蔚来', '理想'],
    '光伏': ['光伏', '太阳能', '硅料', '逆变器', '组件', 'HJT', 'TOPCon'],
    '风电': ['风电', '风力发电', '风机', '叶片', '海上风电'],
    '储能': ['储能', '电池', '钠离子电池', '固态电池', '氢能'],
    
    # 医药板块
    '医药生物': ['医药', '生物制药', '疫苗', '创新药', '仿制药', 'CRO', 'CDMO'],
    '医疗器械': ['医疗器械', '医疗设备', 'IVD', '影像设备', '手术机器人'],
    '中药': ['中药', '中成药', '中医药', '配方颗粒'],
    
    # 消费板块
    '白酒': ['白酒', '茅台', '五粮液', '泸州老窖', '酒类'],
    '食品饮料': ['食品', '饮料', '乳制品', '调味品', '预制菜'],
    '旅游酒店': ['旅游', '酒店', '景区', '免税', '出行'],
    '零售消费': ['零售', '电商', '消费', '百货', '超市'],
    
    # 金融板块
    '银行': ['银行', '信贷', '存款利率', '贷款利率'],
    '保险': ['保险', '寿险', '财险', '健康险'],
    '证券': ['券商', '证券', '投行', '资管'],
    
    # 地产基建
    '房地产': ['房地产', '地产', '楼市', '房价', '保障房', '城中村'],
    '基建': ['基建', '建筑', '工程', '水泥', '钢铁'],
    
    # 能源资源
    '煤炭': ['煤炭', '焦煤', '动力煤', '煤化工'],
    '石油石化': ['石油', '石化', '油气', '炼化', '天然气'],
    '有色金属': ['有色金属', '铜', '铝', '锂', '稀土', '黄金'],
    
    # 制造业
    '汽车': ['汽车', '整车', '零部件', '汽车电子', '智能驾驶'],
    '机械设备': ['机械', '设备', '工程机械', '机床', '工业机器人'],
    '军工': ['军工', '国防', '航空航天', '船舶'],
    
    # 其他
    '传媒': ['传媒', '影视', '游戏', '出版', '广告'],
    '教育': ['教育', '培训', '在线教育'],
    '环保': ['环保', '污水处理', '固废', '碳中和'],
}

# 利好关键词
POSITIVE_KEYWORDS = [
    '利好', '上涨', '增长', '盈利', '突破', '中标', '签约', '收购',
    '合作', '创新高', '业绩大增', '扭亏', '订单', '扩产', '涨价',
    '政策支持', '补贴', '减税', '降准', '降息', '获批', '上市'
]

# 利空关键词
NEGATIVE_KEYWORDS = [
    '利空', '下跌', '亏损', '减持', '处罚', '诉讼', '风险', '警示',
    '退市', '违规', '暴雷', '被查', '调查', '停产', '裁员', '破产',
    '违约', '债务', '质押', '冻结', '下滑', '下降'
]


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_eastmoney_news(limit=50):
    """获取东方财富财经新闻"""
    url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.eastmoney.com/'
    }
    
    news_list = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.encoding = 'utf-8'
        data = r.json()
        
        if data and 'batch' in data:
            for item in data['batch'][:limit]:
                news_list.append({
                    'title': item.get('title', ''),
                    'time': item.get('showtime', ''),
                    'source': '东方财富',
                    'url': item.get('url', '')
                })
    except Exception as e:
        logger.error(f"获取东方财富新闻失败: {e}")
    
    return news_list


def get_sina_finance_news(limit=50):
    """获取新浪财经新闻"""
    url = "https://feed.mix.sina.com.cn/api/roll/get"
    params = {
        'pageid': '153',
        'lid': '2516',
        'k': '',
        'num': str(limit),
        'page': '1',
        'r': str(time.time())
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn/'
    }
    
    news_list = []
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        data = r.json()
        
        if data and 'result' in data and 'data' in data['result']:
            for item in data['result']['data'][:limit]:
                news_list.append({
                    'title': item.get('title', ''),
                    'time': item.get('ctime', ''),
                    'source': '新浪财经',
                    'url': item.get('url', '')
                })
    except Exception as e:
        logger.error(f"获取新浪财经新闻失败: {e}")
    
    return news_list


def get_10jqka_news(limit=50):
    """获取同花顺财经新闻"""
    url = "https://news.10jqka.com.cn/realtimenews.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://news.10jqka.com.cn/'
    }
    
    news_list = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.encoding = 'utf-8'
        
        # 简单解析
        pattern = r'<div class="title"><a[^>]+>([^<]+)</a></div>.*?<span class="time">([^<]+)</span>'
        matches = re.findall(pattern, r.text, re.DOTALL)
        
        for title, time_str in matches[:limit]:
            news_list.append({
                'title': title.strip(),
                'time': time_str.strip(),
                'source': '同花顺',
                'url': 'https://news.10jqka.com.cn/'
            })
    except Exception as e:
        logger.error(f"获取同花顺新闻失败: {e}")
    
    return news_list


def identify_sectors(title):
    """识别新闻涉及的板块"""
    sectors = []
    title_lower = title.lower()
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                sectors.append(sector)
                break
    
    return sectors


def analyze_sentiment(title):
    """分析新闻情绪"""
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)
    
    if positive_count > negative_count:
        return '利好'
    elif negative_count > positive_count:
        return '利空'
    else:
        return '中性'


def analyze_news_data(news_list):
    """分析新闻数据"""
    sector_stats = Counter()
    sector_sentiment = defaultdict(lambda: {'利好': 0, '利空': 0, '中性': 0})
    sector_news = defaultdict(list)
    
    for news in news_list:
        title = news['title']
        sectors = identify_sectors(title)
        sentiment = analyze_sentiment(title)
        
        for sector in sectors:
            sector_stats[sector] += 1
            sector_sentiment[sector][sentiment] += 1
            if len(sector_news[sector]) < 5:  # 每个板块保留5条新闻
                sector_news[sector].append({
                    'title': title,
                    'sentiment': sentiment,
                    'source': news['source']
                })
    
    return sector_stats, sector_sentiment, sector_news


def generate_report(sector_stats, sector_sentiment, sector_news, date_str):
    """生成分析报告"""
    report = []
    report.append("=" * 60)
    report.append(f"【每日消息面分析报告】 {date_str}")
    report.append("=" * 60)
    
    # 热门板块排行
    report.append("\n【热门板块排行 TOP 10】")
    report.append("-" * 60)
    
    top_sectors = sector_stats.most_common(10)
    for i, (sector, count) in enumerate(top_sectors, 1):
        sentiment_info = sector_sentiment[sector]
        positive = sentiment_info['利好']
        negative = sentiment_info['利空']
        neutral = sentiment_info['中性']
        
        # 计算情绪得分
        score = positive * 2 - negative
        if score > 0:
            trend = "📈 利好"
        elif score < 0:
            trend = "📉 利空"
        else:
            trend = "➡️ 中性"
        
        report.append(f"{i}. {sector}: {count}条新闻 | {trend} (利{positive}/利{negative}/中{neutral})")
    
    # 利好板块推荐
    report.append("\n【利好板块推荐】")
    report.append("-" * 60)
    
    bullish_sectors = []
    for sector, count in sector_stats.items():
        sentiment_info = sector_sentiment[sector]
        positive = sentiment_info['利好']
        negative = sentiment_info['利空']
        
        # 利好条件：利好新闻数量 > 利空新闻数量，且利好新闻 >= 2条
        if positive > negative and positive >= 2:
            score = positive * 2 - negative
            bullish_sectors.append((sector, count, positive, negative, score))
    
    # 按得分排序
    bullish_sectors.sort(key=lambda x: x[4], reverse=True)
    
    if bullish_sectors:
        for i, (sector, count, positive, negative, score) in enumerate(bullish_sectors[:5], 1):
            report.append(f"{i}. {sector} (利好{positive}条，利空{negative}条)")
            # 显示相关新闻
            if sector in sector_news:
                for news in sector_news[sector][:3]:
                    if news['sentiment'] == '利好':
                        report.append(f"   • {news['title'][:50]}...")
    else:
        report.append("暂无明显利好板块")
    
    # 利空板块警示
    report.append("\n【利空板块警示】")
    report.append("-" * 60)
    
    bearish_sectors = []
    for sector, count in sector_stats.items():
        sentiment_info = sector_sentiment[sector]
        positive = sentiment_info['利好']
        negative = sentiment_info['利空']
        
        # 利空条件：利空新闻数量 > 利好新闻数量，且利空新闻 >= 2条
        if negative > positive and negative >= 2:
            score = negative * 2 - positive
            bearish_sectors.append((sector, count, positive, negative, score))
    
    bearish_sectors.sort(key=lambda x: x[4], reverse=True)
    
    if bearish_sectors:
        for i, (sector, count, positive, negative, score) in enumerate(bearish_sectors[:5], 1):
            report.append(f"{i}. {sector} (利空{negative}条，利好{positive}条)")
    else:
        report.append("暂无明显利空板块")
    
    # 重点新闻摘要
    report.append("\n【重点新闻摘要】")
    report.append("-" * 60)
    
    # 收集所有利好新闻
    important_news = []
    for sector, news_list in sector_news.items():
        for news in news_list:
            if news['sentiment'] == '利好':
                important_news.append((sector, news))
    
    if important_news:
        for sector, news in important_news[:10]:
            report.append(f"[{sector}] {news['title'][:50]}...")
    else:
        report.append("暂无重点利好新闻")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)


def send_wechat_message(report, config):
    """发送微信消息"""
    webhook = config.get('wechat_webhook', '')
    if not webhook or 'YOUR_WEBHOOK_KEY' in webhook:
        logger.warning("未配置企业微信webhook，跳过推送")
        return False
    
    # 构建消息
    data = {
        "msgtype": "text",
        "text": {
            "content": report
        }
    }
    
    try:
        r = requests.post(webhook, json=data, timeout=30)
        result = r.json()
        if result.get('errcode') == 0:
            logger.info("微信推送成功")
            return True
        else:
            logger.error(f"微信推送失败: {result}")
            return False
    except Exception as e:
        logger.error(f"微信推送异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='消息面分析')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--push', action='store_true', help='推送到微信')
    parser.add_argument('--limit', type=int, default=100, help='新闻数量限制')
    args = parser.parse_args()
    
    date_str = args.date if args.date else datetime.datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"开始分析 {date_str} 的消息面")
    
    # 1. 收集新闻
    logger.info("正在收集新闻...")
    all_news = []
    
    # 东方财富
    news = get_eastmoney_news(args.limit)
    all_news.extend(news)
    logger.info(f"东方财富: {len(news)} 条")
    
    # 新浪财经
    news = get_sina_finance_news(args.limit)
    all_news.extend(news)
    logger.info(f"新浪财经: {len(news)} 条")
    
    # 同花顺
    news = get_10jqka_news(args.limit)
    all_news.extend(news)
    logger.info(f"同花顺: {len(news)} 条")
    
    logger.info(f"共收集 {len(all_news)} 条新闻")
    
    if not all_news:
        logger.error("未收集到任何新闻")
        return
    
    # 2. 分析新闻
    logger.info("正在分析新闻...")
    sector_stats, sector_sentiment, sector_news = analyze_news_data(all_news)
    
    # 3. 生成报告
    logger.info("正在生成报告...")
    report = generate_report(sector_stats, sector_sentiment, sector_news, date_str)
    
    # 打印报告
    print(report)
    
    # 4. 推送微信
    if args.push:
        config = load_config()
        send_wechat_message(report, config)
    
    # 5. 保存报告
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    report_file = os.path.join(output_dir, f'news_analysis_{date_str}.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存到: {report_file}")


if __name__ == '__main__':
    main()
