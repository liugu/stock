#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/05/31
Desc: 增强版数据适配器 - 集成多数据源自动切换
数据源优先级: Baostock -> efinance -> AkShare -> 新浪
"""

import logging
from typing import Optional
import pandas as pd
import datetime

logger = logging.getLogger(__name__)

# ==================== 数据源可用性检查 ====================

_BAOSTOCK_AVAILABLE = None
_EFINANCE_AVAILABLE = None
_AKSHARE_AVAILABLE = None

def is_baostock_available() -> bool:
    """检查 Baostock 是否可用"""
    global _BAOSTOCK_AVAILABLE
    if _BAOSTOCK_AVAILABLE is None:
        try:
            import baostock
            _BAOSTOCK_AVAILABLE = True
            logger.info("[Baostock] 数据源可用")
        except ImportError:
            _BAOSTOCK_AVAILABLE = False
            logger.warning("[Baostock] 未安装，请运行: pip install baostock")
    return _BAOSTOCK_AVAILABLE

def is_efinance_available() -> bool:
    """检查 efinance 是否可用"""
    global _EFINANCE_AVAILABLE
    if _EFINANCE_AVAILABLE is None:
        try:
            import efinance
            _EFINANCE_AVAILABLE = True
            logger.info("[efinance] 数据源可用")
        except ImportError:
            _EFINANCE_AVAILABLE = False
            logger.warning("[efinance] 未安装，请运行: pip install efinance")
    return _EFINANCE_AVAILABLE

def is_akshare_available() -> bool:
    """检查 AkShare 是否可用"""
    global _AKSHARE_AVAILABLE
    if _AKSHARE_AVAILABLE is None:
        try:
            import akshare
            _AKSHARE_AVAILABLE = True
            logger.info("[AkShare] 数据源可用")
        except ImportError:
            _AKSHARE_AVAILABLE = False
            logger.warning("[AkShare] 未安装，请运行: pip install akshare")
    return _AKSHARE_AVAILABLE


# ==================== Baostock 数据源 (最稳定) ====================

_baostock_logged_in = False

def baostock_login():
    """登录 Baostock"""
    global _baostock_logged_in
    if not _baostock_logged_in:
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                _baostock_logged_in = True
                logger.info("[Baostock] 登录成功")
                return True
            else:
                logger.error(f"[Baostock] 登录失败: {lg.error_msg}")
                return False
        except Exception as e:
            logger.error(f"[Baostock] 登录异常: {e}")
            return False
    return True

def baostock_logout():
    """登出 Baostock"""
    global _baostock_logged_in
    if _baostock_logged_in:
        try:
            import baostock as bs
            bs.logout()
            _baostock_logged_in = False
        except:
            pass

def stock_zh_a_hist_baostock(symbol: str, start_date: str = "2020-01-01", 
                              end_date: str = "2050-01-01", 
                              adjust: str = "2") -> pd.DataFrame:
    """
    使用 Baostock 获取个股历史数据
    :param symbol: 股票代码 (6位数字)
    :param start_date: 开始日期 YYYY-MM-DD 或 YYYYMMDD
    :param end_date: 结束日期 YYYY-MM-DD 或 YYYYMMDD
    :param adjust: 1-后复权, 2-前复权, 3-不复权
    """
    if not is_baostock_available():
        return pd.DataFrame()
    
    import baostock as bs
    
    try:
        # 登录
        if not baostock_login():
            return pd.DataFrame()
        
        # 转换日期格式 (支持 YYYYMMDD 和 YYYY-MM-DD)
        if len(start_date) == 8:
            start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        if len(end_date) == 8:
            end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        
        # 转换股票代码格式 (000001 -> sz.000001 或 sh.600000)
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            bs_code = f'sh.{symbol}'
        else:
            bs_code = f'sz.{symbol}'
        
        # 查询数据
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pbMRQ,peTTM",
            start_date=start_date, 
            end_date=end_date,
            frequency="d", 
            adjustflag=adjust
        )
        
        if rs.error_code != '0':
            logger.warning(f"[Baostock] 查询失败: {rs.error_msg}")
            return pd.DataFrame()
        
        # 整理数据
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 转换数据类型
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 重命名列
        df = df.rename(columns={
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量',
            'amount': '成交额',
            'turn': '换手率'
        })
        
        # 计算涨跌幅
        df['涨跌幅'] = df['收盘'].pct_change() * 100
        df['涨跌额'] = df['收盘'].diff()
        df['振幅'] = ((df['最高'] - df['最低']) / df['收盘'].shift(1)) * 100
        
        df = df[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', 
                 '振幅', '涨跌幅', '涨跌额', '换手率']]
        
        logger.info(f"[Baostock] 获取 {symbol} 历史数据成功, {len(df)} 条")
        return df
        
    except Exception as e:
        logger.warning(f"[Baostock] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_baostock() -> pd.DataFrame:
    """使用 Baostock 获取 A 股实时行情 (当日快照)"""
    if not is_baostock_available():
        return pd.DataFrame()
    
    import baostock as bs
    
    try:
        if not baostock_login():
            return pd.DataFrame()
        
        # 获取当日日期
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 获取所有股票列表
        rs = bs.query_stock_basic()
        
        stock_list = []
        while (rs.error_code == '0') & rs.next():
            row = rs.get_row_data()
            # 只取A股
            if row[2] in ['1', '2', '3', '4']:  # 沪深A股
                stock_list.append(row)
        
        logger.info(f"[Baostock] 获取到 {len(stock_list)} 只股票")
        
        # 批量获取行情 (每100只一批)
        all_data = []
        for i in range(0, len(stock_list), 100):
            batch = stock_list[i:i+100]
            codes = [s[0] for s in batch]
            
            # 获取当日快照
            rs2 = bs.get_realtime_quotes(codes)
            while (rs2.error_code == '0') & rs2.next():
                all_data.append(rs2.get_row_data())
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        logger.info(f"[Baostock] 获取实时行情成功, {len(df)} 条")
        return df
        
    except Exception as e:
        logger.warning(f"[Baostock] 获取实时行情失败: {e}")
        return pd.DataFrame()


# ==================== efinance 数据源 (东方财富官方) ====================

def stock_zh_a_hist_efinance(symbol: str, period: str = "daily",
                              start_date: str = "20200101",
                              end_date: str = "20500101") -> pd.DataFrame:
    """
    使用 efinance 获取个股历史数据
    :param symbol: 股票代码
    :param period: daily/weekly/monthly
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    """
    if not is_efinance_available():
        return pd.DataFrame()
    
    import efinance as ef
    
    try:
        # efinance 使用 YYYYMMDD 格式
        df = ef.stock.get_quote_history(
            symbol,
            beg=start_date,
            end=end_date,
            klt=101 if period == 'daily' else 102,  # 101=日K, 102=周K
            fqt=1  # 1=前复权
        )
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            '日期': '日期',
            '开盘': '开盘',
            '收盘': '收盘',
            '最高': '最高',
            '最低': '最低',
            '成交量': '成交量',
            '成交额': '成交额',
            '振幅': '振幅',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '换手率': '换手率'
        })
        
        df['日期'] = pd.to_datetime(df['日期'])
        
        logger.info(f"[efinance] 获取 {symbol} 历史数据成功, {len(df)} 条")
        return df[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', 
                   '振幅', '涨跌幅', '涨跌额', '换手率']]
        
    except Exception as e:
        logger.warning(f"[efinance] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_efinance() -> pd.DataFrame:
    """使用 efinance 获取 A 股实时行情"""
    if not is_efinance_available():
        return pd.DataFrame()
    
    import efinance as ef
    
    try:
        df = ef.stock.get_realtime_quotes()
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        logger.info(f"[efinance] 获取实时行情成功, {len(df)} 只股票")
        return df
        
    except Exception as e:
        logger.warning(f"[efinance] 获取实时行情失败: {e}")
        return pd.DataFrame()


# ==================== AkShare 数据源 ====================

def stock_zh_a_hist_akshare(symbol: str, period: str = "daily",
                            start_date: str = "20200101",
                            end_date: str = "20500101",
                            adjust: str = "qfq") -> pd.DataFrame:
    """使用 AkShare 获取个股历史数据"""
    if not is_akshare_available():
        return pd.DataFrame()
    
    import akshare as ak
    
    try:
        start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_fmt,
            end_date=end_fmt,
            adjust=adjust
        )
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.rename(columns={
            '日期': '日期',
            '开盘': '开盘',
            '收盘': '收盘',
            '最高': '最高',
            '最低': '最低',
            '成交量': '成交量',
            '成交额': '成交额',
            '振幅': '振幅',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '换手率': '换手率'
        })
        
        df['日期'] = pd.to_datetime(df['日期'])
        
        logger.info(f"[AkShare] 获取 {symbol} 历史数据成功, {len(df)} 条")
        return df[['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', 
                   '振幅', '涨跌幅', '涨跌额', '换手率']]
        
    except Exception as e:
        logger.warning(f"[AkShare] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_akshare() -> pd.DataFrame:
    """使用 AkShare 获取 A 股实时行情"""
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


# ==================== 统一接口 (自动切换数据源) ====================

def get_stock_hist(symbol: str, start_date: str = "20200101", 
                   end_date: str = "20500101", adjust: str = "qfq") -> pd.DataFrame:
    """
    获取个股历史数据 - 自动切换数据源
    优先级: Baostock -> efinance -> AkShare
    
    :param symbol: 股票代码 (6位数字)
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    :param adjust: qfq-前复权, hfq-后复权, none-不复权
    """
    # 转换复权参数
    adjust_map = {'qfq': '2', 'hfq': '1', 'none': '3'}
    bs_adjust = adjust_map.get(adjust, '2')
    
    # 1. 尝试 Baostock (最稳定)
    if is_baostock_available():
        df = stock_zh_a_hist_baostock(symbol, start_date, end_date, bs_adjust)
        if not df.empty:
            return df
    
    # 2. 尝试 efinance
    if is_efinance_available():
        df = stock_zh_a_hist_efinance(symbol, 'daily', start_date, end_date)
        if not df.empty:
            return df
    
    # 3. 尝试 AkShare
    if is_akshare_available():
        df = stock_zh_a_hist_akshare(symbol, 'daily', start_date, end_date, adjust)
        if not df.empty:
            return df
    
    logger.error(f"[数据适配器] 所有数据源均失败: {symbol}")
    return pd.DataFrame()


def get_stock_spot() -> pd.DataFrame:
    """
    获取 A 股实时行情 - 自动切换数据源
    优先级: efinance -> AkShare -> Baostock
    """
    # 1. 尝试 efinance (实时性最好)
    if is_efinance_available():
        df = stock_zh_a_spot_efinance()
        if not df.empty:
            return df
    
    # 2. 尝试 AkShare
    if is_akshare_available():
        df = stock_zh_a_spot_akshare()
        if not df.empty:
            return df
    
    # 3. 尝试 Baostock
    if is_baostock_available():
        df = stock_zh_a_spot_baostock()
        if not df.empty:
            return df
    
    logger.error("[数据适配器] 所有实时行情数据源均失败")
    return pd.DataFrame()


def get_available_sources() -> dict:
    """获取可用的数据源列表"""
    return {
        'baostock': is_baostock_available(),
        'efinance': is_efinance_available(),
        'akshare': is_akshare_available()
    }


# ==================== 测试 ====================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("数据源可用性检查")
    print("=" * 60)
    sources = get_available_sources()
    for name, available in sources.items():
        status = "✓ 可用" if available else "✗ 不可用"
        print(f"  {name}: {status}")
    
    print()
    print("=" * 60)
    print("测试获取历史数据 (000001)")
    print("=" * 60)
    df = get_stock_hist('000001', start_date='20260501')
    if not df.empty:
        print(f"成功获取 {len(df)} 条数据")
        print(df.tail())
    else:
        print("获取失败")
    
    print()
    print("=" * 60)
    print("测试获取实时行情")
    print("=" * 60)
    df = get_stock_spot()
    if not df.empty:
        print(f"成功获取 {len(df)} 只股票")
    else:
        print("获取失败")
    
    # 登出 Baostock
    baostock_logout()
