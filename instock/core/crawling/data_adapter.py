#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/05/11
Desc: AkShare 数据适配器 - 在东方财富接口失败时自动切换到 AkShare
"""
import logging
from typing import Optional
import pandas as pd
import requests
from instock.core.crawling.rate_limiter import limiter

logger = logging.getLogger(__name__)

# AkShare 是否可用
_AKSHARE_AVAILABLE = None

def is_akshare_available() -> bool:
    """检查 AkShare 是否可用"""
    global _AKSHARE_AVAILABLE
    if _AKSHARE_AVAILABLE is None:
        try:
            import akshare
            _AKSHARE_AVAILABLE = True
        except ImportError:
            _AKSHARE_AVAILABLE = False
    return _AKSHARE_AVAILABLE


def stock_zh_a_hist_akshare(symbol: str, period: str = "daily", 
                            start_date: str = "19700101", 
                            end_date: str = "20500101",
                            adjust: str = "") -> pd.DataFrame:
    """
    使用 AkShare 获取个股历史数据
    :param symbol: 股票代码
    :param period: daily/weekly/monthly
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    :param adjust: qfq/hfq/""
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        # AkShare 使用 YYYY-MM-DD 格式
        start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        
        df = ak.stock_zh_a_hist(
            symbol=symbol, 
            period=period, 
            start_date=start_fmt,
            end_date=end_fmt,
            adjust=adjust if adjust else ""
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 统一列名格式 (AkShare 已是中文列名)
        # 日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        result = df[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']].copy()
        result.index = pd.to_datetime(result['日期'])
        result.reset_index(drop=True, inplace=True)
        
        logger.info(f"[AkShare] 获取 {symbol} 历史数据成功, {len(result)} 条")
        return result
        
    except Exception as e:
        logger.warning(f"[AkShare] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_hist_sina(symbol: str, datalen: int = 100) -> pd.DataFrame:
    """
    使用新浪接口获取个股历史数据 (备用)
    :param symbol: 股票代码
    :param datalen: 数据条数
    """
    import requests
    try:
        # 判断市场
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            prefix = 'sh'
        else:
            prefix = 'sz'
        
        url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {'symbol': f'{prefix}{symbol}', 'scale': '240', 'ma': 'no', 'datalen': str(datalen)}
        
        r = limiter.get(url, params=params, timeout=30)
        data = r.json()
        
        if not data or len(data) < 30:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df = df.rename(columns={'day': '日期', 'open': '开盘', 'close': '收盘', 
                                  'high': '最高', 'low': '最低', 'volume': '成交量'})
        
        for col in ['开盘', '收盘', '最高', '最低', '成交量']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['成交额'] = df['收盘'] * df['成交量']
        df['涨跌幅'] = df['收盘'].pct_change() * 100
        df['涨跌额'] = df['收盘'].diff()
        df['振幅'] = ((df['最高'] - df['最低']) / df['收盘'].shift(1)) * 100
        df['换手率'] = 0  # 新浪不提供换手率
        
        df.index = pd.to_datetime(df['日期'])
        df.reset_index(drop=True, inplace=True)
        
        logger.info(f"[新浪] 获取 {symbol} 历史数据成功, {len(df)} 条")
        return df[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']]
        
    except Exception as e:
        logger.warning(f"[新浪] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_akshare() -> pd.DataFrame:
    """
    使用 AkShare 获取 A 股实时行情
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_zh_a_spot_em()
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取实时行情成功, {len(df)} 只股票")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取实时行情失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_sina_full() -> pd.DataFrame:
    """
    使用新浪接口获取 A 股实时行情 (完整版，分页获取)
    """
    try:
        all_data = []
        
        # 获取沪市A股
        for page in range(1, 20):  # 沪市约1800只，每页100条
            try:
                url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
                params = {
                    'page': page,
                    'num': 100,
                    'sort': 'symbol',
                    'asc': 1,
                    'node': 'sh_a',
                    '_s_r_a': 'page'
                }
                headers = {'Referer': 'http://vip.stock.finance.sina.com.cn/'}
                
                r = limiter.get(url, params=params, headers=headers, timeout=10)
                data = r.json()
                
                if not data or len(data) == 0:
                    break
                all_data.extend(data)
                if len(data) < 100:  # 最后一页
                    break
            except Exception as e:
                logger.warning(f"[新浪] 获取沪市第{page}页失败: {e}")
                break
        
        # 获取深市A股
        for page in range(1, 30):  # 深市约2700只
            try:
                url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
                params = {
                    'page': page,
                    'num': 100,
                    'sort': 'symbol',
                    'asc': 1,
                    'node': 'sz_a',
                    '_s_r_a': 'page'
                }
                headers = {'Referer': 'http://vip.stock.finance.sina.com.cn/'}
                
                r = limiter.get(url, params=params, headers=headers, timeout=10)
                data = r.json()
                
                if not data or len(data) == 0:
                    break
                all_data.extend(data)
                if len(data) < 100:
                    break
            except Exception as e:
                logger.warning(f"[新浪] 获取深市第{page}页失败: {e}")
                break
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        # 重命名列
        df = df.rename(columns={
            'code': '代码',
            'name': '名称',
            'trade': '最新价',
            'pricechange': '涨跌额',
            'changepercent': '涨跌幅',
            'buy': '买一',
            'sell': '卖一',
            'settlement': '昨收',
            'open': '今开',
            'high': '最高',
            'low': '最低',
            'volume': '成交量',
            'amount': '成交额',
            'per': '市盈率动',
            'pb': '市净率',
            'mktcap': '总市值',
            'nmc': '流通市值',
            'turnoverratio': '换手率'
        })
        
        # 转换数值
        for col in ['最新价', '涨跌额', '涨跌幅', '昨收', '今开', '最高', '最低', '成交量', '成交额', '市盈率动', '市净率', '总市值', '流通市值', '换手率']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info(f"[新浪] 获取实时行情成功, {len(df)} 只股票")
        return df[['代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '今开', '最高', '最低', '昨收', '市盈率动', '市净率', '总市值', '流通市值', '换手率']]
        
    except Exception as e:
        logger.warning(f"[新浪] 获取实时行情失败: {e}")
        return pd.DataFrame()


def stock_lhb_detail_akshare(start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 AkShare 获取龙虎榜数据
    :param start_date: YYYYMMDD
    :param end_date: YYYYMMDD
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取龙虎榜数据成功, {len(df)} 条")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取龙虎榜数据失败: {e}")
        return pd.DataFrame()


def stock_individual_fund_flow_akshare(stock: str, market: str = "sh") -> pd.DataFrame:
    """
    使用 AkShare 获取个股资金流向
    :param stock: 股票代码
    :param market: sh/sz
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_individual_fund_flow(stock=stock, market=market)
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取 {stock} 资金流向成功, {len(df)} 条")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取 {stock} 资金流向失败: {e}")
        return pd.DataFrame()


def stock_zt_pool_akshare(date: str) -> pd.DataFrame:
    """
    使用 AkShare 获取涨停板数据
    :param date: YYYYMMDD
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em(date=date)
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取涨停板数据成功, {len(df)} 只")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取涨停板数据失败: {e}")
        return pd.DataFrame()


def stock_hsgt_fund_flow_summary_akshare() -> pd.DataFrame:
    """
    使用 AkShare 获取北向资金汇总
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取北向资金汇总成功, {len(df)} 条")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取北向资金汇总失败: {e}")
        return pd.DataFrame()


def stock_hsgt_hold_stock_akshare(market: str = "北向") -> pd.DataFrame:
    """
    使用 AkShare 获取北向持股数据
    :param market: 北向/南向
    """
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    try:
        df = ak.stock_hsgt_hold_stock_em(market=market)
        if df.empty:
            return pd.DataFrame()
        logger.info(f"[AkShare] 获取北向持股数据成功, {len(df)} 条")
        return df
    except Exception as e:
        logger.warning(f"[AkShare] 获取北向持股数据失败: {e}")
        return pd.DataFrame()


# ============ 带自动切换的包装函数 ============

def get_stock_hist(symbol: str, period: str = "daily", 
                   start_date: str = "19700101", 
                   end_date: str = "20500101",
                   adjust: str = "qfq",
                   skip_em: bool = False) -> pd.DataFrame:
    """
    获取个股历史数据 - 自动切换数据源
    优先级: 新浪 -> 东方财富 -> AkShare -> Baostock(本地)
    
    :param skip_em: 是否跳过东方财富接口 (网络问题时设为True)
    """
    # 优先使用新浪接口 (更稳定)
    df = stock_zh_a_hist_sina(symbol, datalen=100)
    if not df.empty:
        return df
    
    if not skip_em:
        # 尝试东方财富接口
        from instock.core.crawling.stock_hist_em import stock_zh_a_hist as em_hist
        try:
            df = em_hist(symbol=symbol, period=period, 
                         start_date=start_date, end_date=end_date, adjust=adjust)
            if not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[东方财富] 获取 {symbol} 历史数据失败: {e}")
    
    # 切换到 AkShare
    logger.info(f"[切换] 使用 AkShare 获取 {symbol} 历史数据")
    df = stock_zh_a_hist_akshare(symbol, period, start_date, end_date, adjust)
    if not df.empty:
        return df
    
    # 最后尝试 Baostock 本地数据
    logger.info(f"[切换] 使用 Baostock 获取 {symbol} 历史数据")
    from instock.core.crawling.data_adapter_baostock import get_stock_hist_baostock
    df = get_stock_hist_baostock(symbol, period, start_date, end_date, adjust)
    if not df.empty:
        return df
    
    return pd.DataFrame()


def get_stock_spot() -> pd.DataFrame:
    """
    获取 A 股实时行情 - 自动切换数据源
    优先级: 新浪 -> 东方财富 -> AkShare -> Baostock(本地)
    """
    # 优先使用新浪接口 (更稳定)
    df = stock_zh_a_spot_sina_full()
    if not df.empty:
        return df
    
    # 切换到东方财富
    from instock.core.crawling.stock_hist_em import stock_zh_a_spot_em as em_spot
    try:
        df = em_spot()
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"[东方财富] 获取实时行情失败: {e}")
    
    logger.info("[切换] 使用 AkShare 获取实时行情")
    df = stock_zh_a_spot_akshare()
    if not df.empty:
        return df
    
    # 最后尝试 Baostock 本地数据
    logger.info("[切换] 使用 Baostock 获取实时行情")
    from instock.core.crawling.data_adapter_baostock import get_stock_spot_baostock
    return get_stock_spot_baostock()


def get_lhb_detail(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取龙虎榜数据 - 自动切换数据源
    """
    from instock.core.crawling.stock_lhb_em import stock_lhb_detail_em as em_lhb
    
    try:
        df = em_lhb(start_date=start_date, end_date=end_date)
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"[东方财富] 获取龙虎榜数据失败: {e}")
    
    logger.info("[切换] 使用 AkShare 获取龙虎榜数据")
    return stock_lhb_detail_akshare(start_date, end_date)


def get_zt_pool(date: str) -> pd.DataFrame:
    """
    获取涨停板数据 - 自动切换数据源
    """
    from instock.core.crawling.stock_hist_em import stock_zt_pool_em as em_zt
    
    try:
        df = em_zt(date=date)
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"[东方财富] 获取涨停板数据失败: {e}")
    
    logger.info("[切换] 使用 AkShare 获取涨停板数据")
    return stock_zt_pool_akshare(date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== 测试 AkShare 适配器 ===")
    
    # 测试历史数据
    df = get_stock_hist("000001", start_date="20260101", end_date="20260511")
    print(f"历史数据: {len(df)} 条")
    if not df.empty:
        print(df.tail(3))
    
    # 测试涨停板
    df = get_zt_pool("20260511")
    print(f"\n涨停板: {len(df)} 只")
    if not df.empty:
        print(df.head(3))
