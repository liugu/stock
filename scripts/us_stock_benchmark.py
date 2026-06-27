# -*- coding: utf-8 -*-
"""
美股同行业龙头对标选股
将A股股票与美股同行业龙头进行对比分析
"""
import os
import sys
import time
from datetime import datetime
import pymysql
import pandas as pd

# 强制UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 美股行业龙头映射
US_LEADERS = {
    '计算机、通信和其他电子设备制造业': {'symbol': 'AAPL', 'name': '苹果', 'sector': '科技'},
    'C39计算机、通信和其他电子设备制造业': {'symbol': 'AAPL', 'name': '苹果', 'sector': '科技'},
    '半导体': {'symbol': 'NVDA', 'name': '英伟达', 'sector': '半导体'},
    '软件和信息技术服务业': {'symbol': 'MSFT', 'name': '微软', 'sector': '软件'},
    'I65软件和信息技术服务业': {'symbol': 'MSFT', 'name': '微软', 'sector': '软件'},
    '汽车制造业': {'symbol': 'TSLA', 'name': '特斯拉', 'sector': '新能源汽车'},
    '医药制造业': {'symbol': 'JNJ', 'name': '强生', 'sector': '医药'},
    '食品饮料': {'symbol': 'KO', 'name': '可口可乐', 'sector': '消费'},
    '农副食品加工业': {'symbol': 'GIS', 'name': '通用磨坊', 'sector': '食品'},
    '金融': {'symbol': 'JPM', 'name': '摩根大通', 'sector': '金融'},
    '电气机械和器材制造业': {'symbol': 'GE', 'name': '通用电气', 'sector': '电力设备'},
    'C38电气机械和器材制造业': {'symbol': 'GE', 'name': '通用电气', 'sector': '电力设备'},
    '有色金属冶炼和压延加工业': {'symbol': 'AA', 'name': '美国铝业', 'sector': '有色金属'},
    '化学原料和化学制品制造业': {'symbol': 'DOW', 'name': '陶氏化学', 'sector': '化工'},
    '航空运输业': {'symbol': 'BA', 'name': '波音', 'sector': '航空'},
}

# 行业关键词映射
KEYWORD_MAP = {
    '计算机、通信和其他电子设备制造业': ['计算机', '电子', '通信', 'C39'],
    'C39计算机、通信和其他电子设备制造业': ['计算机', '电子', 'C39'],
    '半导体': ['半导体'],
    '软件和信息技术服务业': ['软件', '信息技术', 'I65'],
    'I65软件和信息技术服务业': ['软件', 'I65'],
    '汽车制造业': ['汽车'],
    '医药制造业': ['医药'],
    '食品饮料': ['饮料', '食品'],
    '农副食品加工业': ['食品', '农副'],
    '金融': ['金融'],
    '电气机械和器材制造业': ['电气', '机械', 'C38'],
    'C38电气机械和器材制造业': ['电气', 'C38'],
    '有色金属冶炼和压延加工业': ['有色', '金属'],
    '化学原料和化学制品制造业': ['化学'],
    '航空运输业': ['航空'],
}


def get_us_stock_batch(symbols):
    """批量获取美股数据（新浪接口）"""
    results = {}
    try:
        import requests
        symbols_str = ','.join([f"gb_{s.lower()}" for s in symbols])
        url = f"https://hq.sinajs.cn/list={symbols_str}"
        headers = {'Referer': 'https://finance.sina.com.cn'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        for line in resp.text.strip().split('\n'):
            if 'FAILED' in line or '=' not in line:
                continue
            try:
                var_part, data_part = line.split('="')
                symbol = var_part.split('_')[-1].upper()
                data = data_part.replace('";', '').split(',')
                if len(data) >= 4:
                    results[symbol] = {
                        'name': data[0],
                        'price': float(data[1]) if data[1] else 0,
                        'change': float(data[2]) if data[2] else 0,
                    }
            except:
                continue
    except Exception as e:
        print(f"获取美股数据失败: {e}")
    
    return results


def get_a_stocks(industry):
    """获取A股行业股票（从stock_daily最新数据）"""
    conn = pymysql.connect(user='stock', password='12345678', database='instock')
    cursor = conn.cursor()
    
    keywords = KEYWORD_MAP.get(industry, [industry.replace('、', '').replace('制造业', '')[:4]])
    conditions = ' OR '.join([f"si.industry LIKE '%{kw}%'" for kw in keywords])
    
    cursor.execute(f"""
        SELECT si.code, si.name, si.industry, sd.close, sd.change_percent
        FROM stock_daily sd
        JOIN stock_info si ON sd.stock_id = si.id
        WHERE sd.date = (SELECT MAX(date) FROM stock_daily)
        AND ({conditions})
        AND si.code NOT LIKE '688%%'
        AND sd.close IS NOT NULL AND sd.close > 0
        ORDER BY sd.amount DESC
        LIMIT 15
    """)
    
    df = pd.DataFrame(cursor.fetchall(), columns=['code', 'name', 'industry', 'price', 'change'])
    conn.close()
    return df


def run_benchmark(industries=None):
    """运行对标分析"""
    print(f"\n{'='*60}")
    print(f"美股同行业龙头对标分析")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 去重：只保留每个sector的第一个行业
    seen_sectors = set()
    target = {}
    for k, v in US_LEADERS.items():
        if v['sector'] not in seen_sectors:
            if not industries or k in industries or v['sector'] in industries:
                target[k] = v
                seen_sectors.add(v['sector'])
    
    # 获取美股数据
    us_symbols = list(set([v['symbol'] for v in target.values()]))
    print(f"获取美股数据: {', '.join(us_symbols)}")
    us_data = get_us_stock_batch(us_symbols)
    print(f"成功获取 {len(us_data)} 只\n")
    
    results = []
    
    for cn_industry, us_info in target.items():
        symbol = us_info['symbol']
        sector = us_info['sector']
        
        print(f"\n【{sector}】{cn_industry}")
        print(f"  对标美股: {us_info['name']}({symbol})")
        
        # 获取A股
        a_df = get_a_stocks(cn_industry)
        if a_df.empty:
            print(f"  未找到A股对应行业股票")
            continue
        
        print(f"  A股股票数: {len(a_df)}")
        
        # 美股数据
        us = us_data.get(symbol)
        if us:
            pct = (us['change'] / us['price'] * 100) if us['price'] > 0 else 0
            print(f"  美股价格: ${us['price']:.2f} ({pct:+.2f}%)")
        
        # A股活跃股票
        print(f"\n  A股活跃股票:")
        for _, row in a_df.head(8).iterrows():
            chg = row['change'] if row['change'] else 0
            print(f"    {row['name']}({row['code']}): {row['price']:.2f}元, {chg:+.2f}%")
        
        results.append({
            'sector': sector,
            'us_info': us_info,
            'us_data': us,
            'cn_industry': cn_industry,
            'a_stocks': a_df.head(8),
        })
        
        time.sleep(0.3)
    
    return results


def format_report(results):
    """格式化报告"""
    if not results:
        return "未找到对标数据"
    
    lines = []
    lines.append("【美股同行业龙头对标】")
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    for r in results:
        us = r['us_data']
        info = r['us_info']
        
        lines.append(f"\n━━ {r['sector']} ━━")
        lines.append(f"美股: {info['name']}({info['symbol']})")
        if us:
            pct = (us['change'] / us['price'] * 100) if us['price'] > 0 else 0
            lines.append(f"  ${us['price']:.2f} ({pct:+.2f}%)")
        
        lines.append(f"A股: {r['cn_industry']}")
        for _, s in r['a_stocks'].head(6).iterrows():
            chg = s['change'] if s['change'] else 0
            lines.append(f"  {s['name']}({s['code']}): {s['price']:.2f}元 {chg:+.2f}%")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='美股同行业龙头对标')
    parser.add_argument('-i', '--industry', help='指定行业')
    args = parser.parse_args()
    
    industries = [args.industry] if args.industry else None
    results = run_benchmark(industries)
    print("\n" + format_report(results))
