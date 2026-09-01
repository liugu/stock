#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""十五五规划×热点选股 — 细分方向龙头榜"""
import sys, os, re
os.chdir(r'E:\量化研究\workspace\stock')
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

import pymysql, numpy as np
from datetime import date
from urllib.request import urlopen, Request

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

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
DIR_ORDER = ['半导体','人工智能','算力','创新药','风电光伏','新型储能','氢能','核电','特高压电网','新能源汽车','电池回收']
HOT_KEYWORDS = ['碳达峰','碳中和','新能源','光伏','风电','储能','氢能','半导体','芯片','人工智能','AI','算力','大模型','新能源汽车','锂电池','创新药']

# 抓新闻
headlines=[]
for url in ['https://www.gov.cn/','https://www.xinhuanet.com/','https://finance.eastmoney.com/']:
    try:
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urlopen(req,timeout=8) as r:
            html=r.read().decode('utf-8',errors='ignore')
        for m in re.findall(r'(?:title|alt)=\x22([^\x22]{10,100})\x22',html):
            m=m.strip()
            if m and len(m)>8 and not any(x in m for x in ['首页','无障碍','登录','关于']):
                if m not in headlines: headlines.append(m)
    except: pass
text=' '.join(headlines)
hot=set()
for kw in HOT_KEYWORDS:
    if kw in text:
        for d in POLICY_MAP: hot.add(d)

conn=pymysql.connect(**DB)
c=conn.cursor()

sid_map={}
for d,v in POLICY_MAP.items():
    for n,code in v['stocks'].items():
        c.execute('SELECT id FROM stock_info WHERE code=%s',(code,))
        r=c.fetchone()
        if r: sid_map[code]=r[0]

prices={}
all_codes=list(set(vv for v in POLICY_MAP.values() for vv in v['stocks'].values()))
for code in all_codes:
    c.execute('SELECT new_price,change_rate,turnoverrate FROM cn_stock_spot WHERE code=%s ORDER BY date DESC LIMIT 1',(code,))
    r=c.fetchone()
    if r: prices[code]={'p':r[0],'chg':r[1],'to':r[2]}

def tech_score(cursor,sid):
    cursor.execute('SELECT close FROM stock_daily WHERE stock_id=%s ORDER BY date DESC LIMIT 15',(sid,))
    rows=[r[0] for r in cursor.fetchall()]
    if len(rows)<5: return 10
    closes=list(reversed(rows))
    s=10
    ma5=np.mean(closes[-5:]); ma10=np.mean(closes[-10:]) if len(closes)>=10 else ma5
    if ma5>ma10: s+=10
    ret=(closes[-1]-closes[-5])/closes[-5]*100
    if ret>3: s+=5
    elif ret>0: s+=2
    if closes[-1]>ma5: s+=3
    return min(s,30)

all_results=[]
for direction,v in POLICY_MAP.items():
    for name,code in v['stocks'].items():
        pi=prices.get(code)
        if not pi: continue
        ps=40 if direction in hot else 30
        ts=tech_score(c,sid_map.get(code,0)) if sid_map.get(code) else 10
        chg=pi['chg'] or 0
        ms=0
        if chg>5: ms=25+(min(chg,10)-5)*2
        elif chg>3: ms=20+(chg-3)*5
        elif chg>1: ms=10+chg*5
        else: ms=max(0,10+chg)
        to=pi['to'] or 0
        if to>5: ms+=3
        elif to>2: ms+=1
        ms=min(ms,30)
        total=min(ps+ts+ms,100)
        all_results.append({'name':name,'code':code,'price':pi['p'],'chg':chg,'to':to,'total':total,'dir':direction})

c.close()
conn.close()

# 打印
today=date.today()
print('='*70)
print(' %s' % today)
print('='*70)

for direction in DIR_ORDER:
    v=POLICY_MAP[direction]
    grp=[r for r in all_results if r['dir']==direction]
    if not grp: continue
    best=max(grp,key=lambda x:x['total'])
    hot_leader=max(grp,key=lambda x:abs(x['chg']))

    print()
    print('【%s】(共%d只)' % (direction,len(v['stocks'])))
    print('  ★ 龙头(最高分): %s(%s) %.2f %+.2f%% 评分%d' % (best['name'],best['code'],best['price'],best['chg'],best['total']))
    if hot_leader != best:
        print('  ★ 人气王(涨幅领先): %s(%s) %.2f %+.2f%%' % (hot_leader['name'],hot_leader['code'],hot_leader['price'],hot_leader['chg']))
    # 全列表
    for r in sorted(grp,key=lambda x:-x['total']):
        if r is best:
            sym='🐲 '
        elif r is hot_leader:
            sym='🔥 '
        else:
            sym='   '
        print('  %s%s(%s) %.2f %+.2f%% 换手%.1f%% 评分%d' % (sym,r['name'],r['code'],r['price'],r['chg'],r['to'],r['total']))