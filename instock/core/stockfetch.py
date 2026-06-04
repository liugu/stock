#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os.path
import datetime
import numpy as np
import pandas as pd
import talib as tl
import instock.core.tablestructure as tbs
import instock.lib.trade_time as trd
import instock.core.crawling.trade_date_hist as tdh
import instock.core.crawling.fund_etf_em as fee
import instock.core.crawling.stock_selection as sst
import instock.core.crawling.stock_lhb_em as sle
import instock.core.crawling.stock_lhb_sina as sls
import instock.core.crawling.stock_dzjy_em as sde
import instock.core.crawling.stock_hist_em as she
import instock.core.crawling.stock_fund_em as sff
import instock.core.crawling.stock_fhps_em as sfe
import instock.core.crawling.stock_cpbd as scp

__author__ = 'myh '
__date__ = '2023/3/10 '

# 设置基础目录，每次加载使用。
cpath_current = os.path.dirname(os.path.dirname(__file__))
stock_hist_cache_path = os.path.join(cpath_current, 'cache', 'hist')
if not os.path.exists(stock_hist_cache_path):
    os.makedirs(stock_hist_cache_path)  # 创建多个文件夹结构。


# 600 601 603 605开头的股票是上证A股
# 600开头的股票是上证A股，属于大盘股，其中6006开头的股票是最早上市的股票，
# 6016开头的股票为大盘蓝筹股；900开头的股票是上证B股；
# 688开头的是上证科创板股票；
# 000开头的股票是深证A股，001、002开头的股票也都属于深证A股，
# 其中002开头的股票是深证A股中小企业股票；
# 200开头的股票是深证B股；
# 300、301开头的股票是创业板股票；400开头的股票是三板市场股票。
# 430、83、87开头的股票是北证A股
def is_a_stock(code):
    # 上证A股  # 深证A股
    return code.startswith(('600', '601', '603', '605', '000', '001', '002', '003', '300', '301'))


# 过滤掉 st 股票。
def is_not_st(name):
    return not name.startswith(('*ST', 'ST'))


# 过滤退市风险股票（名称包含退市、退等字样）
def is_not_delisted(name):
    """过滤退市风险股票"""
    delisted_keywords = ['退', '退市', 'PT']
    return not any(kw in name for kw in delisted_keywords)


# 综合风控过滤
def filter_risk_stocks(data, name_col='name'):
    """
    过滤风险股票（ST、退市风险等）
    
    参数:
        data: DataFrame，包含股票名称列
        name_col: 股票名称列名
    
    返回:
        DataFrame: 过滤后的数据
        dict: 过滤统计信息
    """
    if data is None or len(data) == 0:
        return data, {}
    
    original_count = len(data)
    
    # 过滤ST股票
    st_mask = data[name_col].apply(lambda x: 'ST' in str(x).upper())
    st_count = st_mask.sum()
    
    # 过滤退市风险股票
    delisted_mask = data[name_col].apply(lambda x: any(kw in str(x) for kw in ['退', '退市', 'PT']))
    delisted_count = delisted_mask.sum()
    
    # 应用过滤
    risk_mask = ~(st_mask | delisted_mask)
    filtered_data = data[risk_mask]
    
    stats = {
        'original_count': original_count,
        'filtered_count': len(filtered_data),
        'st_count': st_count,
        'delisted_count': delisted_count,
        'total_removed': st_count + delisted_count
    }
    
    return filtered_data, stats


# 过滤价格，如果没有基本上是退市了。
def is_open(price):
    return not np.isnan(price)


def is_open_with_line(price):
    return price != '-'


# 读取股票交易日历数据
def fetch_stocks_trade_date():
    try:
        data = tdh.tool_trade_date_hist_sina()
        if data is None or len(data.index) == 0:
            return None
        data_date = set(data['trade_date'].values.tolist())
        return data_date
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_trade_date处理异常：{e}")
    return None


# 读取当天股票数据
def fetch_etfs(date):
    try:
        data = fee.fund_etf_spot_em()
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_ETF_SPOT['columns'])
        data = data.loc[data['new_price'].apply(is_open)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etfs处理异常：{e}")
    return None


# 读取当天股票数据
def fetch_stocks(date):
    try:
        # 使用data_adapter获取数据 (支持自动切换数据源)
        from instock.core.crawling.data_adapter import get_stock_spot
        data = get_stock_spot()
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        
        # 创建符合表结构的DataFrame (41列)
        result = pd.DataFrame()
        result['date'] = data['date']
        result['code'] = data['代码']
        result['name'] = data['名称']
        result['new_price'] = data['最新价']
        result['change_rate'] = data['涨跌幅']
        result['ups_downs'] = data['涨跌额']
        result['volume'] = data['成交量']
        result['deal_amount'] = data['成交额']
        # 振幅和量比：东方财富有，新浪没有
        result['amplitude'] = data.get('振幅', 0) if '振幅' in data.columns else 0
        result['volume_ratio'] = data.get('量比', 0) if '量比' in data.columns else 0
        result['turnoverrate'] = data['换手率']
        result['open_price'] = data['今开']
        result['high_price'] = data['最高']
        result['low_price'] = data['最低']
        result['pre_close_price'] = data['昨收']
        result['speed_increase'] = 0
        result['speed_increase_5'] = 0
        result['speed_increase_60'] = 0
        result['speed_increase_all'] = 0
        
        # 市盈率字段处理 - 东方财富有完整数据，新浪只有动态PE
        result['dtsyl'] = data.get('市盈率动', 0) if '市盈率动' in data.columns else 0
        result['pe9'] = data.get('市盈率TTM', 0) if '市盈率TTM' in data.columns else 0
        result['pe'] = data.get('市盈率静', data.get('市盈率动', 0)) if '市盈率静' in data.columns else data.get('市盈率动', 0)
        result['pbnewmrq'] = data.get('市净率', 0) if '市净率' in data.columns else 0
        
        # 基本面数据 - 东方财富有完整数据
        result['basic_eps'] = data.get('每股收益', 0) if '每股收益' in data.columns else 0
        result['bvps'] = data.get('每股净资产', 0) if '每股净资产' in data.columns else 0
        result['per_capital_reserve'] = data.get('每股公积金', 0) if '每股公积金' in data.columns else 0
        result['per_unassign_profit'] = data.get('每股未分配利润', 0) if '每股未分配利润' in data.columns else 0
        result['roe_weight'] = data.get('加权净资产收益率', 0) if '加权净资产收益率' in data.columns else 0
        result['sale_gpr'] = data.get('毛利率', 0) if '毛利率' in data.columns else 0
        result['debt_asset_ratio'] = data.get('资产负债率', 0) if '资产负债率' in data.columns else 0
        result['total_operate_income'] = data.get('营业收入', 0) if '营业收入' in data.columns else 0
        result['toi_yoy_ratio'] = data.get('营业收入同比增长', 0) if '营业收入同比增长' in data.columns else 0
        result['parent_netprofit'] = data.get('归属净利润', 0) if '归属净利润' in data.columns else 0
        result['netprofit_yoy_ratio'] = data.get('归属净利润同比增长', 0) if '归属净利润同比增长' in data.columns else 0
        result['report_date'] = None
        result['total_shares'] = data.get('总股本', 0) if '总股本' in data.columns else 0
        result['free_shares'] = data.get('已流通股份', 0) if '已流通股份' in data.columns else 0
        result['total_market_cap'] = data['总市值']
        result['free_cap'] = data['流通市值']
        result['industry'] = data.get('所处行业', '') if '所处行业' in data.columns else ''
        result['listing_date'] = None
        
        result.columns = list(tbs.TABLE_CN_STOCK_SPOT['columns'])
        result = result.loc[result['code'].apply(is_a_stock)].loc[result['new_price'].apply(is_open)]
        return result
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks处理异常：{e}")
    return None


def fetch_stock_selection():
    try:
        data = sst.stock_selection()
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(tbs.TABLE_CN_STOCK_SELECTION['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_selection处理异常：{e}")
    return None


# 读取股票资金流向
def fetch_stocks_fund_flow(index):
    try:
        cn_flow = tbs.CN_STOCK_FUND_FLOW[index]
        data = sff.stock_individual_fund_flow_rank(indicator=cn_flow['cn'])
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(cn_flow['columns'])
        data = data.loc[data['code'].apply(is_a_stock)].loc[data['new_price'].apply(is_open_with_line)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_fund_flow处理异常：{e}")
    return None


# 读取板块资金流向
def fetch_stocks_sector_fund_flow(index_sector, index_indicator):
    try:
        cn_flow = tbs.CN_STOCK_SECTOR_FUND_FLOW[1][index_indicator]
        data = sff.stock_sector_fund_flow_rank(indicator=cn_flow['cn'], sector_type=tbs.CN_STOCK_SECTOR_FUND_FLOW[0][index_sector])
        if data is None or len(data.index) == 0:
            return None
        data.columns = list(cn_flow['columns'])
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_sector_fund_flow处理异常：{e}")
    return None


# 读取股票分红配送
def fetch_stocks_bonus(date):
    try:
        data = sfe.stock_fhps_em(date=trd.get_bonus_report_date())
        if data is None or len(data.index) == 0:
            return None
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_BONUS['columns'])
        data = data.loc[data['code'].apply(is_a_stock)]
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stocks_bonus处理异常：{e}")
    return None


# 股票近三月上龙虎榜且必须有2次以上机构参与的
def fetch_stock_top_entity_data(date):
    run_date = date + datetime.timedelta(days=-90)
    start_date = run_date.strftime("%Y%m%d")
    end_date = date.strftime("%Y%m%d")
    code_name = '代码'
    entity_amount_name = '买方机构数'
    try:
        data = sle.stock_lhb_jgmmtj_em(start_date, end_date)
        if data is None or len(data.index) == 0:
            return None

        # 机构买入次数大于1计算方法，首先：每次要有买方机构数(>0),然后：这段时间买方机构数求和大于1
        mask = (data[entity_amount_name] > 0)  # 首先：每次要有买方机构数(>0)
        data = data.loc[mask]

        if len(data.index) == 0:
            return None

        grouped = data.groupby(by=data[code_name])
        data_series = grouped[entity_amount_name].sum()
        data_code = set(data_series[data_series > 1].index.values)  # 然后：这段时间买方机构数求和大于1

        if not data_code:
            return None

        return data_code
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_entity_data处理异常：{e}")
    return None


# 描述: 获取新浪财经-龙虎榜-个股上榜统计
def fetch_stock_top_data(date):
    try:
        data = sls.stock_lhb_ggtj_sina()
        if data is None or len(data.index) == 0:
            return None
        _columns = list(tbs.TABLE_CN_STOCK_TOP['columns'])
        _columns.pop(0)
        data.columns = _columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop_duplicates('code', keep='last', inplace=True)
        if date is None:
            data.insert(0, 'date', datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, 'date', date.strftime("%Y-%m-%d"))
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_top_data处理异常：{e}")
    return None


# 描述: 获取东方财富网-数据中心-大宗交易-每日统计
def fetch_stock_blocktrade_data(date):
    date_str = date.strftime("%Y%m%d")
    try:
        data = sde.stock_dzjy_mrtj(start_date=date_str, end_date=date_str)
        if data is None or len(data.index) == 0:
            return None

        columns = list(tbs.TABLE_CN_STOCK_BLOCKTRADE['columns'])
        columns.insert(0, 'index')
        data.columns = columns
        data = data.loc[data['code'].apply(is_a_stock)]
        data.drop('index', axis=1, inplace=True)
        return data
    except TypeError:
        logging.error("处理异常：目前还没有大宗交易数据，请17:00点后再获取！")
        return None
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_blocktrade_data处理异常：{e}")
    return None


# 读取股票历史数据
def fetch_etf_hist(data_base, date_start=None, date_end=None, adjust='qfq'):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
    try:
        if date_end is not None:
            data = fee.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, end_date=date_end,
                                        adjust=adjust)
        else:
            data = fee.fund_etf_hist_em(symbol=code, period="daily", start_date=date_start, adjust=adjust)

        if data is None or len(data.index) == 0:
            return None
        
        # 创建副本避免只读错误
        data = data.copy()
        
        # 转换列名格式
        data = data.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'p_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })
        data = data.sort_index()  # 将数据按照日期排序下。
        if data is not None:
            # 使用assign避免SettingWithCopyWarning
            p_change = tl.ROC(data['close'].values, 1)
            p_change[np.isnan(p_change)] = 0.0
            data = data.assign(p_change=p_change)
            data['volume'] = data['volume'].values.astype('float64') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_etf_hist处理异常：{e}")
    return None


# 读取股票历史数据
def fetch_stock_hist(data_base, date_start=None, is_cache=True):
    date = data_base[0]
    code = data_base[1]

    if date_start is None:
        date_start, is_cache = trd.get_trade_hist_interval(date)  # 提高运行效率，只运行一次
        # date_end = date_end.strftime("%Y%m%d")
    try:
        data = stock_hist_cache(code, date_start, None, is_cache, 'qfq')
        if data is not None:
            # 创建副本避免只读错误
            data = data.copy()
            # 使用assign避免SettingWithCopyWarning
            p_change = tl.ROC(data['close'].values, 1)
            p_change[np.isnan(p_change)] = 0.0
            data = data.assign(p_change=p_change)
            data['volume'] = data['volume'].values.astype('float64') * 100  # 成交量单位从手变成股。
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_hist处理异常：{e}")
    return None


# 增加读取股票缓存方法。加快处理速度。多线程解决效率
def stock_hist_cache(code, date_start, date_end=None, is_cache=True, adjust=''):
    cache_dir = os.path.join(stock_hist_cache_path, date_start[0:6], date_start)
    # 如果没有文件夹创建一个。月文件夹和日文件夹。方便删除。
    try:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    except Exception:
        pass
    cache_file = os.path.join(cache_dir, "%s%s.gzip.pickle" % (code, adjust))
    # 如果缓存存在就直接返回缓存数据。压缩方式。
    try:
        if os.path.isfile(cache_file):
            data = pd.read_pickle(cache_file, compression="gzip")
            return data.copy()  # 返回副本避免只读错误
        else:
            # 使用data_adapter获取数据 (支持自动切换数据源)
            from instock.core.crawling.data_adapter import get_stock_hist
            
            # 格式转换: date_start是YYYYMMDD格式
            stock = get_stock_hist(symbol=code, start_date=date_start, adjust=adjust, skip_em=True)

            if stock is None or len(stock.index) == 0:
                return None
            
            # 创建副本避免只读错误
            stock = stock.copy()
            
            # 转换列名格式
            stock = stock.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'p_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            # 不需要重新赋值列名，rename已经完成
            stock = stock.sort_index()  # 将数据按照日期排序下。
            try:
                if is_cache:
                    stock.to_pickle(cache_file, compression="gzip")
            except Exception:
                pass
            # time.sleep(1)
            return stock
    except Exception as e:
        logging.error(f"stockfetch.stock_hist_cache处理异常：{code}代码{e}")
    return None


# 读取股票操盘必读数据（包含股东人数）
def fetch_stock_cpbd_all(stock_codes):
    """
    批量抓取操盘必读数据（含股东人数）
    :param stock_codes: 股票代码列表
    :return: 合并后的DataFrame
    """
    try:
        data = scp.stock_cpbd_all_em(stock_codes)
        if data is None or len(data.index) == 0:
            return None
        return data
    except Exception as e:
        logging.error(f"stockfetch.fetch_stock_cpbd_all处理异常：{e}")
    return None
