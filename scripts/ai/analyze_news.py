#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股票消息面分析 - 获取新闻、公告、研报等信息"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')


def get_market_id(code: str) -> int:
    """根据股票代码判断市场ID"""
    if code.startswith(('600', '601', '603', '605', '688')):
        return 1
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return 0
    return None


def get_stock_info(code: str) -> dict:
    """获取股票基本信息 - 使用新浪财经数据源"""
    market_id = get_market_id(code)
    if market_id is None:
        return {}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://vip.stock.finance.sina.com.cn/'
    }

    try:
        # 使用新浪财经API - 数据更准确
        url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

        # 分页查找股票
        for page in range(1, 60):
            params = {"page": str(page), "num": "100", "sort": "changepercent", "asc": "0", "node": "hs_a"}
            r = requests.get(url, params=params, headers=headers, timeout=30)
            data = r.json()
            if not data:
                break
            for stock in data:
                if stock.get("code") == code:
                    return {
                        '代码': stock.get('code', code),
                        '名称': stock.get('name', ''),
                        '最新价': float(stock.get('trade', 0)),
                        '涨跌幅': float(stock.get('changepercent', 0)),
                        '总市值': float(stock.get('mktcap', 0)) / 1e4,  # 万元转亿元
                        '流通市值': float(stock.get('nmc', 0)) / 1e4,  # 万元转亿元
                        '市盈率': float(stock.get('per', 0)),
                        '市净率': float(stock.get('pb', 0)),
                        '换手率': float(stock.get('turnoverratio', 0)),
                    }
    except Exception as e:
        print(f"基本信息获取失败: {e}")

    return {}


def get_stock_news(code: str, limit: int = 15) -> pd.DataFrame:
    """获取股票相关新闻 - 同花顺数据源"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://news.10jqka.com.cn/'
    }

    results = []
    try:
        # 同花顺新闻接口
        url = "https://news.10jqka.com.cn/realtimenews.html"
        params = {"page": "1", "tag": code}
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.encoding = 'utf-8'

        # 简单解析
        import re
        pattern = r'<div class="title"><a[^>]+>([^<]+)</a></div>.*?<span class="time">([^<]+)</span>'
        matches = re.findall(pattern, r.text, re.DOTALL)

        for title, time_str in matches[:limit]:
            results.append({
                '标题': title.strip(),
                '来源': '同花顺',
                '时间': time_str.strip(),
                '链接': 'https://news.10jqka.com.cn/'
            })
    except Exception as e:
        pass

    if results:
        return pd.DataFrame(results)

    # 备用：返回提示信息
    return pd.DataFrame([{
        '标题': f'请访问东方财富查看{code}相关新闻',
        '来源': '东方财富',
        '时间': datetime.now().strftime('%Y-%m-%d'),
        '链接': f'https://so.eastmoney.com/news/s?keyword={code}'
    }])


def get_stock_notice(code: str, limit: int = 10) -> pd.DataFrame:
    """获取股票公告"""
    market_id = get_market_id(code)
    if market_id is None:
        return pd.DataFrame()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://data.eastmoney.com/'
    }

    results = []
    try:
        # 东方财富公告接口 - 使用正确的参数
        url = "https://np-anotice-stock.eastmoney.com/api/content/ann"
        params = {
            "cb": "",
            "page_size": str(limit),
            "page_index": "1",
            "ann_type": "SHA,SZA",
            "client_source": "web",
            "secid": f"{market_id}.{code}",
            "f_node": "0",
            "s_node": "0"
        }
        r = requests.get(url, params=params, headers=headers, timeout=30)

        # 尝试解析JSON
        try:
            data = r.json()
            if data and 'data' in data and 'list' in data['data']:
                for item in data['data']['list']:
                    # 只保留该股票的公告
                    if code in str(item.get('secCode', '')):
                        results.append({
                            '标题': item.get('title', ''),
                            '类型': item.get('noticeType', '公告'),
                            '时间': item.get('notice_date', ''),
                            '链接': f"https://data.eastmoney.com/notices/detail/{item.get('art_code', '')}.html"
                        })
        except:
            pass
    except Exception as e:
        pass

    if results:
        return pd.DataFrame(results)

    # 备用：返回链接
    return pd.DataFrame([{
        '标题': f'查看{code}全部公告',
        '类型': '公告',
        '时间': datetime.now().strftime('%Y-%m-%d'),
        '链接': f'https://data.eastmoney.com/notices/stock/{code}.html'
    }])


def get_stock_report(code: str, limit: int = 10) -> pd.DataFrame:
    """获取股票研报"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://data.eastmoney.com/'
    }

    results = []
    try:
        # 东方财富研报接口
        url = "https://reportapi.eastmoney.com/report/list"
        params = {
            "cb": "",
            "pageNo": "1",
            "pageSize": str(limit),
            "code": code,
            "industryCode": "*",
            "qType": "0"
        }
        r = requests.get(url, params=params, headers=headers, timeout=30)

        # 尝试解析JSON
        try:
            data = r.json()
            if data and 'data' in data:
                for item in data['data']:
                    results.append({
                        '标题': item.get('title', ''),
                        '机构': item.get('orgSName', ''),
                        '研究员': item.get('researcher', ''),
                        '评级': item.get('emRatingName', ''),
                        '时间': item.get('publishDate', ''),
                        '链接': 'https://data.eastmoney.com/report/'
                    })
        except:
            pass
    except Exception as e:
        pass

    if results:
        return pd.DataFrame(results)

    # 备用：返回链接
    return pd.DataFrame([{
        '标题': f'查看{code}研报',
        '机构': '',
        '研究员': '',
        '评级': '',
        '时间': '',
        '链接': f'https://data.eastmoney.com/report/stock.jshtml?code={code}'
    }])


def get_main_business(code: str) -> pd.DataFrame:
    """获取主营业务构成"""
    market_id = get_market_id(code)
    if market_id is None:
        return pd.DataFrame()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://emweb.eastmoney.com/'
    }

    try:
        url = f"https://emweb.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={market_id}.{code}"
        r = requests.get(url, headers=headers, timeout=30)
        data = r.json()

        if data and 'fwyw' in data:
            results = []
            for item in data['fwyw'][:5]:
                results.append({
                    '业务类型': item.get('ITEM_NAME', ''),
                    '收入占比': item.get('MAIN_INCOME_RATIO', ''),
                    '毛利率': item.get('GROSS_PROFIT_RATIO', '')
                })
            return pd.DataFrame(results)
    except:
        pass

    return pd.DataFrame()


def analyze_news_sentiment(news_df: pd.DataFrame) -> dict:
    """简单新闻情绪分析"""
    if news_df.empty:
        return {'情绪': '中性', '说明': '无新闻数据'}

    # 关键词分析
    positive_words = ['利好', '上涨', '增长', '盈利', '突破', '中标', '签约', '收购', '合作', '创新高', '业绩大增', '扭亏']
    negative_words = ['利空', '下跌', '亏损', '减持', '处罚', '诉讼', '风险', '警示', '退市', '违规', '暴雷', '被查']

    positive_count = 0
    negative_count = 0

    for title in news_df['标题']:
        for word in positive_words:
            if word in str(title):
                positive_count += 1
        for word in negative_words:
            if word in str(title):
                negative_count += 1

    if positive_count > negative_count:
        return {'情绪': '偏多', '正面新闻': positive_count, '负面新闻': negative_count}
    elif negative_count > positive_count:
        return {'情绪': '偏空', '正面新闻': positive_count, '负面新闻': negative_count}
    else:
        return {'情绪': '中性', '正面新闻': positive_count, '负面新闻': negative_count}


def analyze_stock_news(code: str, name: str = None):
    """综合消息面分析"""
    print('=' * 70)
    print(f'股票消息面分析: {code}')
    print('=' * 70)

    # 0. 获取基本信息
    print('\n【基本信息】')
    info = get_stock_info(code)
    if info:
        print(f"  名称: {info.get('名称', name or '未知')}")
        print(f"  最新价: {info.get('最新价', 0):.2f}元 | 涨跌幅: {info.get('涨跌幅', 0):.2f}%")
        print(f"  总市值: {info.get('总市值', 0):.2f}亿 | 流通市值: {info.get('流通市值', 0):.2f}亿")
        print(f"  市盈率: {info.get('市盈率', 0):.2f} | 市净率: {info.get('市净率', 0):.2f}")
        print(f"  换手率: {info.get('换手率', 0):.2f}%")
    else:
        print(f"  名称: {name or '未知'}")

    # 1. 获取新闻
    print('\n【相关新闻】')
    news_df = get_stock_news(code, limit=15)
    if not news_df.empty:
        sentiment = analyze_news_sentiment(news_df)
        print(f"  新闻情绪: {sentiment['情绪']} (正面:{sentiment['正面新闻']}条, 负面:{sentiment['负面新闻']}条)")
        print()
        for i, row in news_df.head(8).iterrows():
            print(f"  [{row['时间']}] {row['标题'][:45]}...")
    else:
        print("  暂无新闻数据")

    # 2. 获取公告
    print('\n【公司公告】')
    notice_df = get_stock_notice(code, limit=10)
    if not notice_df.empty:
        for i, row in notice_df.head(8).iterrows():
            print(f"  [{row['时间']}] {row['标题'][:45]}...")
    else:
        print("  暂无公告数据")

    # 3. 获取研报
    print('\n【研究报告】')
    report_df = get_stock_report(code, limit=8)
    if not report_df.empty:
        for i, row in report_df.iterrows():
            rating = row['评级'] if row['评级'] else '未评级'
            org = row['机构'] if row['机构'] else '机构'
            print(f"  [{row['时间']}] {org} - {rating}")
            if row['标题']:
                print(f"      {row['标题'][:45]}...")
    else:
        print("  暂无研报数据")

    # 4. 主营业务
    print('\n【主营业务】')
    business_df = get_main_business(code)
    if not business_df.empty:
        for i, row in business_df.iterrows():
            print(f"  {row['业务类型']}: 占比{row['收入占比']}% | 毛利率{row['毛利率']}%")
    else:
        print("  主营业务数据请查看东方财富F10")

    # 5. 消息面综合评估
    print('\n【消息面综合评估】')
    score = 50  # 基础分
    signals = []

    # 新闻情绪评分
    if not news_df.empty:
        sentiment = analyze_news_sentiment(news_df)
        if sentiment['情绪'] == '偏多':
            score += 15
            signals.append('新闻偏正面')
        elif sentiment['情绪'] == '偏空':
            score -= 10
            signals.append('新闻偏负面')

    # 研报评分
    if not report_df.empty:
        for _, row in report_df.iterrows():
            rating = str(row['评级'])
            if '买入' in rating:
                score += 10
                signals.append('研报买入评级')
                break
            elif '增持' in rating:
                score += 5
                signals.append('研报增持评级')
                break

    # 基本面评分
    if info:
        pe = info.get('市盈率', 0)
        pb = info.get('市净率', 0)

        # 市盈率评分 (负值表示亏损，需要特殊处理)
        if pe > 0 and pe < 20:
            score += 5
            signals.append('估值偏低')
        elif pe > 0 and pe < 50:
            score += 2
        elif pe < 0:
            score -= 5
            signals.append('业绩亏损')

        # 市净率评分
        if 0 < pb < 2:
            score += 5
            signals.append('破净风险低')
        elif pb > 5:
            score -= 3

    print(f"消息面得分: {score}分")
    print(f"关键信号: {', '.join(signals) if signals else '无明确信号'}")

    if score >= 65:
        print("评级: 消息面偏多")
    elif score <= 35:
        print("评级: 消息面偏空")
    else:
        print("评级: 消息面中性")

    # 6. 参考链接
    print('\n【参考链接】')
    print(f"  东方财富F10: https://emdata.eastmoney.com/pc_hsf10/pages/index.html?code={code}")
    print(f"  同花顺F10: https://basic.10jqka.com.cn/{code}")
    print(f"  新浪财经: https://finance.sina.com.cn/realstock/company/{code}/nc.shtml")

    print('\n' + '=' * 70)
    return {
        'info': info,
        'news': news_df,
        'notice': notice_df,
        'report': report_df,
        'score': score
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else None
        analyze_stock_news(code, name)
    else:
        # 默认分析远大控股
        analyze_stock_news('000626', '远大控股')
