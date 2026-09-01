#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
十五五规划 + 热点新闻选股
政策研究 + 权威媒体热点 → 龙头股 + 潜力股
"""
import sys, os, re
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql
import numpy as np
from datetime import date, timedelta
from urllib.request import urlopen, Request

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

# ========== 十五五规划方向·概念股 ==========
POLICY_MAP = {
    '风电光伏': {'stocks':{'明阳智能':'601615','金风科技':'002202','运达股份':'300772','天顺风能':'002531','大金重工':'002487','海力风电':'301155','隆基绿能':'601012','通威股份':'600438','阳光电源':'300274','晶澳科技':'002459','天合光能':'688599','福莱特':'601865'}},
    '新型储能': {'stocks':{'宁德时代':'300750','亿纬锂能':'300014','国轩高科':'002074','派能科技':'688063','鹏辉能源':'300438','德业股份':'605117'}},
    '氢能':      {'stocks':{'美锦能源':'000723','京城股份':'600860','厚普股份':'300471','雄韬股份':'002733','亿华通':'688339'}},
    '核电':      {'stocks':{'中国广核':'003816','中国核电':'601985','沃尔核材':'002130'}},
    '特高压电网':{'stocks':{'特变电工':'600089','国电南瑞':'600406','许继电气':'000400','平高电气':'600312','中国西电':'601179'}},
    '新能源汽车':{'stocks':{'比亚迪':'002594','赛力斯':'601127','长安汽车':'000625','宇通客车':'600066'}},
    '半导体':    {'stocks':{'中芯国际':'688981','华大九天':'301269','北方华创':'002371','中微公司':'688012','豪威集团':'603501','紫光国微':'002049','兆易创新':'603986','长电科技':'600584'}},
    '人工智能':  {'stocks':{'科大讯飞':'002230','中科创达':'300496','海康威视':'002415','寒武纪':'688256','拓尔思':'300229'}},
    '算力':      {'stocks':{'中科曙光':'603019','浪潮信息':'000977','紫光股份':'000938','中兴通讯':'000063','润泽科技':'300442'}},
    '创新药':    {'stocks':{'恒瑞医药':'600276','药明康德':'603259','百济神州':'688235','凯莱英':'002821','泰格医药':'300347'}},
    '电池回收':  {'stocks':{'格林美':'002340','华友钴业':'600516','天奇股份':'002009'}},
}

HOT_KEYWORDS = ['碳达峰','碳中和','新能源','光伏','风电','储能','氢能','半导体','芯片','人工智能','AI','算力','大模型','新能源汽车','锂电池','固态电池','特高压','智能电网','虚拟电厂','创新药','生物医药','CXO','低空经济','商业航天','机器人','数据要素','数字经济','信创']

def fetch_news():
    headlines = []
    for url in ['https://www.gov.cn/','https://www.xinhuanet.com/','https://finance.eastmoney.com/']:
        try:
            req = Request(url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urlopen(req, timeout=8) as r:
                html = r.read().decode('utf-8',errors='ignore')
            for pat in [r'(?:title|alt)=\x22([^\x22]{10,100})\x22', r'<a[^>]*>([^<]{10,80})</a>']:
                for m in re.findall(pat, html):
                    m=m.strip()
                    if m and len(m)>8 and not any(x in m for x in ['首页','无障碍','登录','邮箱','关于','网站声明']):
                        if m not in headlines: headlines.append(m)
        except: pass
    return headlines[:30]

def check_news(headlines):
    text = ' '.join(headlines)
    hot = set()
    for kw in HOT_KEYWORDS:
        if kw in text:
            for d in POLICY_MAP:
                if any(k in d for k in [kw]) or any(k[:2] in d for k in [kw]):
                    hot.add(d)
    return hot

def analyze_stock(cursor, sid, code):
    """获取完整技术分析数据"""
    result = {'sid': sid}
    # 日K数据
    cursor.execute('SELECT close,high,low,volume FROM stock_daily WHERE stock_id=%s ORDER BY date DESC LIMIT 60', (sid,))
    rows = list(reversed([(r[0],r[1],r[2],r[3]) for r in cursor.fetchall()]))
    if len(rows) < 5:
        result['valid'] = False
        return result
    result['valid'] = True
    closes = [r[0] for r in rows]
    highs = [r[1] for r in rows]
    lows = [r[2] for r in rows]
    vols = [r[3] for r in rows]
    n = len(closes)
    last = closes[-1]

    # 均线
    ma5 = np.mean(closes[-5:])
    ma10 = np.mean(closes[-10:]) if n>=10 else ma5
    ma20 = np.mean(closes[-20:]) if n>=20 else ma10
    ma60 = np.mean(closes[-60:]) if n>=60 else ma20
    result['ma5'], result['ma10'], result['ma20'], result['ma60'] = ma5, ma10, ma20, ma60
    result['price_to_ma20'] = (last - ma20) / ma20 * 100 if ma20 else 0

    # 趋势
    result['bullish'] = ma5 > ma10 > ma20  # 多头排列
    result['near_ma20'] = abs(result['price_to_ma20']) < 5  # 在MA20附近(支撑)

    # 近5日涨幅
    ret5 = (last - closes[-5]) / closes[-5] * 100 if n>=5 else 0
    result['ret5'] = ret5
    result['quiet'] = -3 < ret5 < 1  # 近期横盘/微调

    # RSI
    if n >= 14:
        gains = []; losses = []
        for i in range(n-14, n):
            if i == n-14: continue
            ch = closes[i] - closes[i-1]
            gains.append(max(0,ch))
            losses.append(max(0,-ch))
        avg_g = np.mean(gains) if gains else 0
        avg_l = np.mean(losses) if losses else 1
        rsi = 100 - 100/(1+avg_g/avg_l) if avg_l>0 else 100
        result['rsi'] = rsi
        result['oversold'] = 30 <= rsi <= 45  # 偏弱但未超卖，有反弹空间
    else:
        result['rsi'] = 50
        result['oversold'] = False

    # 成交量
    if n >= 20:
        avg_vol = np.mean(vols[-21:-1])
        last_vol = vols[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        result['vol_ratio'] = vol_ratio
        result['quiet_vol'] = vol_ratio < 1.3  # 无明显放量（蓄力中）
    else:
        result['vol_ratio'] = 1
        result['quiet_vol'] = True

    # 20日涨幅
    result['ret20'] = (last - closes[-20]) / closes[-20] * 100 if n>=20 else ret5

    return result

def main():
    today = date.today()
    print('='*70)
    print(f'  十五五规划 + 热点新闻选股  {today}')
    print('='*70)

    conn = pymysql.connect(**DB)
    cursor = conn.cursor()

    # 获取新闻
    headlines = fetch_news()
    hot_dirs = check_news(headlines)

    print(f'\n📰 新闻来源: gov.cn + xinhuanet + eastmoney ({len(headlines)}条)')
    for hl in headlines[:8]:
        print(f'  • {hl}')
    if hot_dirs:
        print(f'\n🔥 政策热点方向: {", ".join(sorted(hot_dirs))}')

    # 获取映射
    sid_map = {}
    for d, v in POLICY_MAP.items():
        for n, code in v['stocks'].items():
            cursor.execute('SELECT id FROM stock_info WHERE code=%s', (code,))
            r = cursor.fetchone()
            if r: sid_map[code] = r[0]

    # 获取行情 + 分析
    results = []
    for direction, v in POLICY_MAP.items():
        for name, code in v['stocks'].items():
            cursor.execute('SELECT new_price,change_rate,turnoverrate,total_market_cap FROM cn_stock_spot WHERE code=%s ORDER BY date DESC LIMIT 1', (code,))
            pi = cursor.fetchone()
            if not pi: continue
            price, chg, to, cap = pi
            chg = chg or 0; to = to or 0

            sid = sid_map.get(code, 0)
            ta = analyze_stock(cursor, sid, code) if sid else {}
            if not ta.get('valid', True): continue

            # === 政策分 (0-40) ===
            ps = 40 if direction in hot_dirs else 30

            # ========== 龙头分 ==========
            # 技术动能 0-30
            ts_leader = 10  # base
            if ta.get('bullish'): ts_leader += 10
            if chg > 0: ts_leader += 5
            if ta.get('ret5', 0) > 3: ts_leader += 5
            ts_leader = min(ts_leader, 30)

            # 市场热度 0-30
            ms_leader = 0
            if chg > 5: ms_leader = 25 + (min(chg,10)-5)*2
            elif chg > 3: ms_leader = 20 + (chg-3)*5
            elif chg > 1: ms_leader = 10 + chg*5
            else: ms_leader = max(0, 10 + chg)
            if to > 5: ms_leader += 3
            elif to > 2: ms_leader += 1
            ms_leader = min(ms_leader, 30)

            leader_total = min(ps + ts_leader + ms_leader, 100)

            # ========== 潜力分 ==========
            # 技术位置 0-30 (低吸信号)
            ts_potential = 10  # base
            if ta.get('near_ma20'): ts_potential += 8   # 回踩MA20支撑
            if ta.get('oversold'): ts_potential += 7     # RSI合理偏低
            if ta.get('quiet'): ts_potential += 5        # 近期横盘未动
            if ta.get('quiet_vol'): ts_potential += 3    # 缩量/正常量
            if ta.get('bullish') and ta.get('near_ma20'): ts_potential += 5  # 多头+回踩=最佳买点
            ts_potential = min(ts_potential, 30)

            # 安全边际 0-30 (不追高)
            ms_potential = 15  # base
            if -3 <= chg <= 1: ms_potential += 5   # 今天没大涨，可低吸
            elif chg > 3: ms_potential -= 10       # 已经涨了，不追
            if to < 5: ms_potential += 5            # 换手不过热
            if cap and cap > 2e9: ms_potential += 3 # 市值>20亿(避免仙股)
            cap = cap or 0
            ms_potential = max(0, min(ms_potential, 30))

            potential_total = min(ps + ts_potential + ms_potential, 100)

            results.append({
                'name': name, 'code': code, 'dir': direction,
                'price': price, 'chg': chg, 'to': to, 'cap': cap,
                'leader': leader_total, 'potential': potential_total,
                'ps': ps, 'ts_l': ts_leader, 'ms_l': ms_leader,
                'ts_p': ts_potential, 'ms_p': ms_potential,
                'bullish': ta.get('bullish', False),
                'near_ma20': ta.get('near_ma20', False),
                'oversold': ta.get('oversold', False),
                'quiet': ta.get('quiet', False),
                'ret5': ta.get('ret5', 0),
                'rsi': round(ta.get('rsi', 0), 1),
            })

    cursor.close(); conn.close()

    # ========== 输出 ==========
    # 龙头榜：按龙头分排序
    leaders = sorted(results, key=lambda x: -x['leader'])
    # 潜力榜：按潜力分排序 + 过滤已涨幅过大的
    potentials = sorted([r for r in results if r['chg'] < 4], key=lambda x: -x['potential'])

    print(f'\n{"="*70}')
    print(f'🏆 龙头股 (今日强势+政策共振)')
    print(f'{"="*70}')
    for r in leaders[:15]:
        sym = '🐲 ' if r['bullish'] else '   '
        print(f'  {sym}{r["name"]}({r["code"]}) {r["price"]} {r["chg"]:+.2f}% | 龙{r["leader"]}分 | {r["dir"]}')

    print(f'\n{"="*70}')
    print(f'💎 潜力股 (政策对+还没涨+位置好)')
    print(f'{"="*70}')
    printed = set()
    for r in potentials[:15]:
        if r['code'] in printed: continue
        printed.add(r['code'])
        tags = []
        if r['near_ma20']: tags.append('MA20支撑')
        if r['oversold']: tags.append('RSI偏低')
        if r['quiet']: tags.append('横盘中')
        if r['bullish']: tags.append('多头排列')
        sig = ','.join(tags) if tags else '观察'
        print(f'  💎 {r["name"]}({r["code"]}) {r["price"]} {r["chg"]:+.2f}% | 潜{r["potential"]}分 | {r["dir"]}')
        print(f'    信号: {sig} | RSI{r["rsi"]} | 近5日{r["ret5"]:+.1f}%')

    print(f'\n{"="*70}')
    print(f'📊 各方向龙头+潜力')
    print(f'{"="*70}')
    for direction in ['半导体','人工智能','算力','创新药','风电光伏','新型储能','氢能','核电','特高压电网','新能源汽车','电池回收']:
        grp = [r for r in results if r['dir']==direction]
        if not grp: continue
        best_l = max(grp, key=lambda x: x['leader'])
        best_p = max([r for r in grp if r['chg']<4], key=lambda x: x['potential'], default=None)
        print(f'  {direction}:')
        print(f'    龙头 {best_l["name"]}({best_l["code"]}) {best_l["chg"]:+.2f}% 龙{best_l["leader"]}分')
        if best_p and best_p['code'] != best_l['code']:
            print(f'    潜力 {best_p["name"]}({best_p["code"]}) {best_p["chg"]:+.2f}% 潜{best_p["potential"]}分')

    # 保存
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(out_dir, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    out_file = os.path.join(out_dir, f'policy_news_selection_{ts}.csv')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('名称,代码,十五五方向,价格,涨跌幅%,换手%,龙头分,潜力分,多头,MA20支撑,RSI偏低,横盘,近5日%,RSI\n')
        for r in sorted(results, key=lambda x: -x['leader']):
            f.write(f'{r["name"]},{r["code"]},{r["dir"]},{r["price"]},{r["chg"]:.2f},{r["to"]},{r["leader"]},{r["potential"]},{r["bullish"]},{r["near_ma20"]},{r["oversold"]},{r["quiet"]},{r["ret5"]:.1f},{r["rsi"]}\n')
    print(f'\n结果已保存: {out_file}')

if __name__ == '__main__':
    main()