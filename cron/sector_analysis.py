#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
板块热度分析
获取板块涨跌幅排行，识别热门板块
"""

import json
import time
import pandas as pd
import requests

__author__ = 'liugu'
__date__ = '2026/5/11'


def get_sector_rank(indicator="今日", sector_type="行业"):
    """
    获取板块涨跌幅排行
    
    参数:
        indicator: 时间周期 {"今日", "5日", "10日"}
        sector_type: 板块类型 {"行业", "概念", "地域"}
    
    返回:
        DataFrame: 板块排行数据
    """
    sector_type_map = {"行业": "2", "概念": "3", "地域": "1"}
    indicator_map = {
        "今日": ("f3", "f12,f14,f2,f3,f62,f184"),
        "5日": ("f109", "f12,f14,f2,f109,f164"),
        "10日": ("f160", "f12,f14,f2,f160,f174"),
    }
    
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "b2884a393a59ad64002292a3e90d46a5",
        "fltt": "2",
        "invt": "2",
        "fid": indicator_map[indicator][0],
        "fs": f"m:90+t:{sector_type_map[sector_type]}",
        "fields": indicator_map[indicator][1],
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        
        if data.get("data") and data["data"].get("diff"):
            df = pd.DataFrame(data["data"]["diff"])
            df = df[~df["f2"].isin(["-"])]
            
            if indicator == "今日":
                df.columns = ["代码", "名称", "最新价", "涨跌幅", "主力净流入", "净占比"]
            elif indicator == "5日":
                df.columns = ["代码", "名称", "最新价", "5日涨跌幅", "主力净流入"]
            else:
                df.columns = ["代码", "名称", "最新价", "10日涨跌幅", "主力净流入"]
            
            # 转换数值
            for col in ["涨跌幅", "5日涨跌幅", "10日涨跌幅", "主力净流入"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            return df
    except Exception as e:
        print(f"获取板块数据失败: {e}")
    
    return pd.DataFrame()


def get_hot_sectors(top_n=5, min_amount=10000000000):
    """
    获取热门板块
    
    参数:
        top_n: 返回前N个热门板块
        min_amount: 最小成交额（默认100亿）
    
    返回:
        list: 热门板块列表
    """
    # 获取行业板块排行
    df = get_sector_rank(indicator="今日", sector_type="行业")
    
    if df.empty:
        return []
    
    # 按涨跌幅排序
    df = df.sort_values("涨跌幅", ascending=False)
    
    # 筛选热门板块
    hot_sectors = []
    for _, row in df.head(top_n).iterrows():
        sector_info = {
            "name": row["名称"],
            "code": row["代码"],
            "change": row["涨跌幅"],
            "main_inflow": row.get("主力净流入", 0),
        }
        hot_sectors.append(sector_info)
    
    return hot_sectors


def analyze_sector_heat():
    """
    分析板块热度并生成报告
    
    返回:
        str: 板块热度报告文本
    """
    report_lines = ["【板块热度分析】", ""]
    
    # 行业板块
    report_lines.append("▶ 行业板块 TOP 5")
    hot_industries = get_hot_sectors(top_n=5)
    for i, sector in enumerate(hot_industries, 1):
        inflow_str = f"主力{sector['main_inflow']/100000000:.1f}亿" if sector['main_inflow'] else ""
        report_lines.append(f"  {i}. {sector['name']} +{sector['change']:.2f}% {inflow_str}")
    
    report_lines.append("")
    
    # 概念板块
    report_lines.append("▶ 概念板块 TOP 5")
    df_concept = get_sector_rank(indicator="今日", sector_type="概念")
    if not df_concept.empty:
        df_concept = df_concept.sort_values("涨跌幅", ascending=False)
        for i, (_, row) in enumerate(df_concept.head(5).iterrows(), 1):
            report_lines.append(f"  {i}. {row['名称']} +{row['涨跌幅']:.2f}%")
    
    return "\n".join(report_lines)


if __name__ == "__main__":
    print(analyze_sector_heat())
