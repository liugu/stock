#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI产业链早报 - 数据采集脚本
通过curl/requests获取财经资讯，替代web_search
"""
import sys, os, json, subprocess, re, time
sys.path.insert(0, 'E:/量化研究/workspace/stock')
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

# 用curl获取东方财富AI板块热门新闻
def fetch_eastmoney_news(keyword='AI', limit=10):
    """获取东方财富行情中心的AI相关新闻"""
    try:
        # 东方财富新闻API
        url = f'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f12,f14&secids=1.688981,1.688041,1.002230,1.688111,1.603019,1.000977,1.688802,1.603893,1.002415,1.002371'
        result = subprocess.run(['curl', '-s', '--connect-timeout', '10', url], capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        
        stocks = []
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                stocks.append({
                    'code': str(item.get('f12','')),
                    'name': item.get('f14',''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'turnover': item.get('f4', 0),
                })
        return stocks
    except Exception as e:
        return [{'error': str(e)}]

def fetch_industry_news():
    """用curl获取新浪财经/东财快讯"""
    news = []
    sources = [
        ('东方财富', 'https://finance.eastmoney.com/a/czqyw.html'),
        ('新浪财经', 'https://finance.sina.com.cn/stock/usstock/sector_AI.shtml'),
    ]
    
    for name, url in sources:
        try:
            result = subprocess.run(['curl', '-s', '--connect-timeout', '10', 
                '-H', 'User-Agent: Mozilla/5.0', url], capture_output=True, text=True, timeout=15)
            if result.stdout:
                # 提取标题
                titles = re.findall(r'<a[^>]*title="([^"]*AI[^"]*)"', result.stdout, re.I)
                titles += re.findall(r'<a[^>]*>([^<]*AI[^<]*人工智能[^<]*)</a>', result.stdout, re.I)
                if titles:
                    news.append(f'[{name}] ' + ' | '.join(titles[:5]))
        except:
            pass
    return news

# 获取重点AI产业链股票行情
def get_ai_stocks():
    """获取AI重点股实时行情（从本地数据库）"""
    import pymysql
    DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
    
    targets = [
        ('中芯国际', '688981'), ('海光信息', '688041'), ('科大讯飞', '002230'),
        ('金山办公', '688111'), ('中科曙光', '603019'), ('浪潮信息', '000977'),
        ('沐曦集成', '688802'), ('瑞芯微', '603893'), ('海康威视', '002415'),
        ('北方华创', '002371'), ('中际旭创', '300308'), ('韦尔股份', '603501'),
        ('澜起科技', '688008'), ('寒武纪', '688256'), ('紫光股份', '000938'),
        ('中科创达', '300496'), ('拓尔思', '300229'), ('神州数码', '000034'),
        ('长电科技', '600584'), ('通富微电', '002156'),
    ]
    
    try:
        conn = pymysql.connect(**DB)
        cur = conn.cursor()
        results = []
        for name, code in targets:
            cur.execute('''SELECT sp.new_price, sp.change_rate, sp.turnoverrate, sp.pe, sp.total_market_cap
                FROM cn_stock_spot sp WHERE sp.code = %s ORDER BY sp.date DESC LIMIT 1''', (code,))
            r = cur.fetchone()
            if r:
                chg = r[1] or 0
                results.append(f'{name}({code}) {r[0]:.2f} {"🔴" if chg>9 else ("🟢" if chg>2 else ("⚪" if chg>-2 else "🔴"))} {chg:+.2f}% PE{r[3]:.0f}')
            else:
                results.append(f'{name}({code}) 无数据')
        cur.close()
        conn.close()
        return results
    except Exception as e:
        return [f'数据库读取失败: {e}']

if __name__ == '__main__':
    import datetime
    today = datetime.date.today().strftime('%Y-%m-%d')
    weekday = ['周一','周二','周三','周四','周五','周六','周日'][datetime.date.today().weekday()]
    
    print(f'AI产业链早报 - {today} {weekday}')
    print(f'{"="*60}')
    
    # AI热点板块行情
    print('\n【AI产业链重点股行情】')
    stocks = get_ai_stocks()
    for s in stocks:
        print(f'  {s}')
    
    # 涨幅榜
    print('\n【AI板块今日亮点】')
    high_chg = [s for s in stocks if '🔴' in s or ('🟢' in s and '+' in s)]
    if high_chg:
        for s in high_chg[:5]:
            print(f'  {s}')
    else:
        print(f'  无明显大涨个股')
    
    # 热门资讯
    print('\n【AI产业热点资讯】')
    news = fetch_industry_news()
    if news:
        for n in news:
            print(f'  {n}')
    else:
        print(f'  今日暂无抓取到AI相关头条')
    
    # 板块热度总结
    print(f'\n{"="*60}')
    print(f'数据来源: 东方财富行情 + 本地数据库')
    print(f'提示: 以上为机器采集数据，仅供参考，不构成投资建议')