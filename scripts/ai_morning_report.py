#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI产业链早报 - 直接从stock_daily读取数据"""
import sys, pymysql
sys.path.insert(0, 'E:/量化研究/workspace/stock')
from datetime import date

today = date.today()
weekday = ['周一','周二','周三','周四','周五','周六','周日'][today.weekday()]
print(f'AI产业链早报 - {today} {weekday}')
print('='*60)

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}
conn = pymysql.connect(**DB)
cur = conn.cursor()

# 最新交易日
cur.execute('SELECT DISTINCT date FROM stock_daily ORDER BY date DESC LIMIT 1')
latest = str(cur.fetchone()[0])
print(f'最新交易日: {latest}')

# 板块统计
cur.execute("""SELECT COUNT(*), ROUND(AVG(sd.change_percent),2),
    SUM(CASE WHEN sd.change_percent > 2 THEN 1 ELSE 0 END),
    SUM(CASE WHEN sd.change_percent < -2 THEN 1 ELSE 0 END)
    FROM stock_daily sd JOIN stock_info si ON sd.stock_id=si.id
    WHERE sd.date=%s AND (si.name LIKE '%%AI%%' OR si.name LIKE '%%智能%%' OR si.name LIKE '%%芯片%%'
    OR si.name LIKE '%%算力%%' OR si.name LIKE '%%机器人%%' OR si.name LIKE '%%半导体%%')""", (latest,))
r = cur.fetchone()
if r and r[0] > 0:
    print(f'板块概况: AI/智能/芯片共{r[0]}只, 均涨幅{r[1]:+.2f}%, 大涨{r[2]}只, 大跌{r[3]}只')

# 重点股行情
targets = [
    ('中芯国际','688981'),('海光信息','688041'),('科大讯飞','002230'),
    ('金山办公','688111'),('中科曙光','603019'),('浪潮信息','000977'),
    ('沐曦集成','688802'),('瑞芯微','603893'),('海康威视','002415'),
    ('北方华创','002371'),('中际旭创','300308'),('韦尔股份','603501'),
    ('澜起科技','688008'),('紫光股份','000938'),('中科创达','300496'),
    ('拓尔思','300229'),('神州数码','000034'),('长电科技','600584'),
    ('通富微电','002156'),
]
print('\n【AI产业链重点股行情】')
for name, code in targets:
    cur.execute("SELECT sd.close, sd.change_percent, sd.turnover_rate FROM stock_daily sd JOIN stock_info si ON sd.stock_id=si.id WHERE si.code=%s AND sd.date=%s", (code, latest))
    r = cur.fetchone()
    if r:
        chg = r[1] or 0
        icon = '🔴' if chg >= 9.5 else ('🟢' if chg >= 2 else ('⚪' if chg > -2 else '🔴'))
        print(f'  {name}({code}) {r[0]:>8.2f} {icon}{chg:>+6.2f}% 换手{r[2]:>5.2f}%')
    else:
        print(f'  {name}({code}) 暂无{latest}数据')

# WAIC 2026
waics = [('瑞芯微','603893'),('沐曦集成','688802'),('金山办公','688111'),
         ('中科创达','300496'),('广和通','300638'),('中科曙光','603019'),
         ('浪潮信息','000977'),('海康威视','002415'),('神州数码','000034')]
print('\n【WAIC 2026 参展A股关注】')
for name, code in waics:
    cur.execute("SELECT sd.close, sd.change_percent FROM stock_daily sd JOIN stock_info si ON sd.stock_id=si.id WHERE si.code=%s AND sd.date=%s", (code, latest))
    r = cur.fetchone()
    if r:
        print(f'  {name}({code}) {r[0]:.2f} {r[1]:+.2f}%')

cur.close(); conn.close()
print(f'\n{"="*60}')
print('数据来源: stock_daily（本地数据库instock）')
print('提示: 仅供参考，不构成投资建议')