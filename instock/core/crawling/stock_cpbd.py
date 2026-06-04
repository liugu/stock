# -*- coding:utf-8 -*-
# !/usr/bin/env python

import logging
import concurrent.futures
import time

import pandas as pd
import requests
from instock.core.crawling.rate_limiter import limiter

__author__ = 'myh '
__date__ = '2023/5/7 '



def stock_cpbd_em(code: str = "688041") -> pd.DataFrame:
    """
    东方财富网-个股-操盘必读
    https://emweb.securities.eastmoney.com/PC_HSF10/OperationsRequired/Index?type=web&code=SH688041#
    :param code: 股票代码（6位数字，不带市场前缀）
    :type code: str
    :return: 操盘必读数据（合并了主要指标、板块、股东分析、龙虎榜、大宗交易、融资融券）
    :rtype: pandas.DataFrame
    """
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/OperationsRequired/PageAjax"
    if code.startswith("6"):
        symbol = f"SH{code}"
    else:
        symbol = f"SZ{code}"
    params = {"code": symbol}

    r = limiter.get(url, params=params)
    data_json = r.json()
    zxzb = data_json.get("zxzb", [])
    if len(zxzb) < 1:
        return None

    data_dict = zxzb[0].copy()
    zxzbOther = data_json.get("zxzbOther", [])
    if len(zxzbOther) > 0:
        data_dict.update(zxzbOther[0])

    # 所属板块
    _ssbks = data_json.get("ssbk", [])
    ssbk = None
    for s in _ssbks:
        _v = s.get("BOARD_NAME")
        if _v is not None:
            ssbk = f"{ssbk}、{_v}" if ssbk else f"{_v}"
    data_dict["BOARD_NAME"] = ssbk

    # 股东分析（包含股东人数等关键数据）
    gdrs = data_json.get("gdrs", [])
    if len(gdrs) > 0:
        data_dict.update(gdrs[0])

    # 龙虎榜单
    lhbd = data_json.get("lhbd", [])
    if len(lhbd) > 0:
        lhbd = lhbd[0]
        lhbd["LHBD_DATE"] = lhbd.pop("TRADE_DATE", lhbd.pop("LHBD_DATE", None))
        data_dict.update(lhbd)

    # 大宗交易
    dzjy = data_json.get("dzjy", [])
    if len(dzjy) > 0:
        dzjy = dzjy[0]
        dzjy["DZJY_DATE"] = dzjy.pop("TRADE_DATE", dzjy.pop("DZJY_DATE", None))
        data_dict.update(dzjy)

    # 融资融券
    rzrq = data_json.get("rzrq", [])
    if len(rzrq) > 0:
        rzrq = rzrq[0]
        rzrq["RZRQ_DATE"] = rzrq.pop("TRADE_DATE", rzrq.pop("RZRQ_DATE", None))
        data_dict.update(rzrq)

    # 将结果转为DataFrame（单行）
    result = pd.DataFrame([data_dict])

    # 确保SECURITY_CODE字段存在
    result["SECURITY_CODE"] = code
    if "SECURITY_NAME_ABBR" not in result.columns:
        result["SECURITY_NAME_ABBR"] = ""

    return result


def stock_cpbd_all_em(stock_list: list) -> pd.DataFrame:
    """
    批量抓取多只股票的操盘必读数据（使用线程池并发）
    :param stock_list: 股票代码列表
    :type stock_list: list
    :return: 合并后的操盘必读DataFrame
    :rtype: pandas.DataFrame
    """
    results = {}
    errors = []
    total = len(stock_list)
    success = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(stock_cpbd_em, code): code for code in stock_list}
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                data = future.result()
                if data is not None and len(data) > 0:
                    results[code] = data
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append((code, str(e)))

    if not results:
        return None

    # 打印进度
    if errors:
        logging.info(f"stock_cpbd_all_em: 完成 {success}/{total} (失败 {failed})")
    else:
        logging.info(f"stock_cpbd_all_em: 完成 {success}/{total} 只股票")

    df_list = list(results.values())
    return pd.concat(df_list, ignore_index=True)


if __name__ == "__main__":
    stock_cpbd_em_df = stock_cpbd_em(code="688041")
    print(stock_cpbd_em_df)
