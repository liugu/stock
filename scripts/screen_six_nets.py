#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""筛选六张网核心标的技术面数据"""
import pymysql
from datetime import date, timedelta
from collections import defaultdict

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

stocks = {
    '水网': {
        '水利建设': ['钱江水利', '安徽建工', '粤水电', '中国电建'],
        '管材': ['青龙管业', '伟星新材', '新兴铸管', '韩建河山'],
        '水务': ['重庆水务', '洪城环境', '首创环保'],
    },
    '新型电网': {
        '电力运营': ['立新能源', '湖南发展', '华银电力', '乐山电力', '桂冠电力'],
        '电网设备': ['国电南瑞', '特变电工', '许继电气', '平高电气'],
        '新能源装备': ['阳光电源', '中国能建', '东方电气'],
    },
    '算力网': {
        'AI服务器': ['浪潮信息', '中科曙光', '寒武纪', '海光信息'],
        '光模块': ['中际旭创', '新易盛', '天孚通信', '光迅科技'],
        '数据中心': ['光环新网', '奥飞数据', '宝信软件', '润泽科技'],
    },
    '通信网': {
        '主设备': ['中兴通讯', '烽火通信'],
        '光通信': ['亨通光电', '长飞光纤', '中天科技'],
        '卫星互联': ['中国卫星', '上海瀚讯', '铖昌科技'],
    },
    '物流网': {
        '快递物流': ['顺丰控股', '中储股份', '圆通速递'],
        '智慧交通': ['隧道股份', '深高速', '宁沪高速'],
        '低空经济': ['中航科工', '纵横股份', '莱斯信息'],
    },
    '生态环保': {
        '市政管网': ['数字政通', '纳川股份', '国统股份'],
        '环境治理': ['碧水源', '高能环境', '伟明环保'],
        '固废处理': ['瀚蓝环境', '旺能环境', '绿色动力'],
    }
}

all_names = []
for cat in stocks.values():
    for sub in cat.values():
        all_names.extend(sub)

conn = pymysql.connect(**DB)
c = conn.cursor()

# 获取code和name映射
ph0 = ','.join(['%s'] * len(all_names))
sql0 = "SELECT code, name FROM stock_info WHERE name IN (" + ph0 + ")"
c.execute(sql0, all_names)
name_to_code = {name: code for code, name in c.fetchall()}

# 取最新spot数据
c.execute("SELECT MAX(date) FROM cn_stock_spot")
latest_spot_date = c.fetchone()[0]

codes = list(name_to_code.values())
ph1 = ','.join(['%s'] * len(codes))
sql1 = ("SELECT sp.code, si.name, sp.new_price, sp.change_rate, sp.turnoverrate "
        "FROM cn_stock_spot sp "
        "JOIN stock_info si ON sp.code = si.code COLLATE utf8mb4_general_ci "
        "WHERE sp.date = %s AND sp.code IN (" + ph1 + ")")
c.execute(sql1, (latest_spot_date, *codes))
spot_data = {r[1]: r for r in c.fetchall()}

# 最新stock_daily日期
c.execute("SELECT MAX(date) FROM stock_daily")
latest_daily = c.fetchone()[0]

# 获取近期每日收盘价
ph2 = ','.join(['%s'] * len(all_names))
sql2 = ("SELECT si.name, sd.close, sd.change_percent, sd.date "
        "FROM stock_daily sd "
        "JOIN stock_info si ON sd.stock_id = si.id "
        "WHERE si.name IN (" + ph2 + ") "
        "AND sd.date >= %s "
        "ORDER BY si.name, sd.date")
thirty_ago = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
c.execute(sql2, (*all_names, thirty_ago))

price_history = defaultdict(list)
for name, close, chg, d in c.fetchall():
    price_history[name].append((str(d), float(close), float(chg) if chg else 0))

conn.close()

print(f"数据日期: spot={latest_spot_date}, daily={latest_daily}")
print()

for net_name, categories in stocks.items():
    print(f"\n【{net_name}】")
    for sub_name, names in categories.items():
        hits = []
        for name in names:
            if name not in spot_data:
                continue
            row = spot_data[name]
            code = row[0]
            price = float(row[2])
            chg = float(row[3]) if row[3] else 0
            turn = float(row[4]) if row[4] else 0
            
            if code.startswith('688'):
                continue
            
            hist = price_history.get(name, [])
            closes = [h[1] for h in hist[-10:]]
            if len(closes) >= 5:
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes) / len(closes)
                close_now = closes[-1]
                if ma5 > ma10 and close_now >= ma5 * 0.97:
                    trend = "\u2191"
                elif abs(ma5/ma10 - 1) < 0.03:
                    trend = "\u2192"
                else:
                    trend = "\u2193"
            else:
                trend = "?"
            
            score = 0
            if chg > 0: score += 1
            if 0.3 < turn < 15: score += 1
            if trend == "\u2191": score += 2
            if chg < 5: score += 1
            
            hits.append((score, name, code, price, chg, turn, trend))
        
        if hits:
            hits.sort(reverse=True)
            print(f"\n  {sub_name}:")
            for score, name, code, price, chg, turn, trend in hits[:5]:
                print(f"    {name}({code}) {price:.2f}元 {chg:+.2f}% 换手{turn:.1f}% {trend}")