#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/05/22
Desc: Baostock 数据适配器 - 在其他数据源失败时自动切换到 Baostock
"""
import logging
from typing import Optional
import pandas as pd
import os
import glob

logger = logging.getLogger(__name__)

# Baostock 数据目录
_BAOSTOCK_DATA_DIR = '/home/liugu/workspace/stock/data/baostock'

def is_baostock_available() -> bool:
    """检查 Baostock 本地数据是否可用"""
    return os.path.isdir(_BAOSTOCK_DATA_DIR)

def _load_local_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """
    从本地 Baostock CSV 文件加载数据
    :param symbol: 股票代码 (如 '600000')
    :return: DataFrame 或 None
    """
    try:
        # 转换股票代码格式
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            prefix = 'sh'
        elif symbol.startswith(('000', '001', '002', '300')):
            prefix = 'sz'
        else:
            return None
        
        code = f"{prefix}.{symbol}"
        filepath = os.path.join(_BAOSTOCK_DATA_DIR, f"{code}.csv")
        
        if not os.path.exists(filepath):
            return None
        
        # 读取 CSV
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        
        if df.empty:
            return None
        
        # 重命名列以匹配现有格式
        df = df.rename(columns={
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量',
            'amount': '成交额',
            'pctChg': '涨跌幅'
        })
        
        # 转换日期格式
        df['日期'] = pd.to_datetime(df['日期'])
        
        # 转换数值列
        numeric_cols = ['开盘', '收盘', '最高', '最低', '成交量', '成交额', '涨跌幅']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算缺失的列
        df['涨跌额'] = df['收盘'].diff()
        df['振幅'] = ((df['最高'] - df['最低']) / df['收盘'].shift(1)) * 100
        df['换手率'] = 0  # Baostock 不提供换手率
        
        # 确保列顺序一致
        required_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', 
                        '振幅', '涨跌幅', '涨跌额', '换手率']
        df = df[[col for col in required_cols if col in df.columns]]
        
        df.index = df['日期']
        df.reset_index(drop=True, inplace=True)
        
        return df
    
    except Exception as e:
        logger.warning(f"[Baostock] 加载本地数据失败 {symbol}: {e}")
        return None


def stock_zh_a_hist_baostock(symbol: str, period: str = "daily", 
                             start_date: str = "19700101", 
                             end_date: str = "20500101",
                             adjust: str = "") -> pd.DataFrame:
    """
    使用 Baostock 本地数据获取个股历史数据
    :param symbol: 股票代码
    :param period: daily/weekly/monthly (暂不支持)
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    :param adjust: qfq/hfq/"" (暂不支持)
    """
    if not is_baostock_available():
        return pd.DataFrame()
    
    try:
        df = _load_local_stock_data(symbol)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 日期过滤
        if start_date != "19700101":
            start_dt = pd.to_datetime(start_date)
            df = df[df['日期'] >= start_dt]
        
        if end_date != "20500101":
            end_dt = pd.to_datetime(end_date)
            df = df[df['日期'] <= end_dt]
        
        if df.empty:
            return pd.DataFrame()
        
        logger.info(f"[Baostock] 获取 {symbol} 历史数据成功, {len(df)} 条")
        return df
    
    except Exception as e:
        logger.warning(f"[Baostock] 获取 {symbol} 历史数据失败: {e}")
        return pd.DataFrame()


def stock_zh_a_spot_baostock() -> pd.DataFrame:
    """
    使用 Baostock 获取 A 股实时行情 (从最新数据推断)
    """
    if not is_baostock_available():
        return pd.DataFrame()
    
    try:
        # 获取所有最新数据文件
        csv_files = glob.glob(os.path.join(_BAOSTOCK_DATA_DIR, "*.csv"))
        
        if not csv_files:
            return pd.DataFrame()
        
        all_data = []
        
        for filepath in csv_files[:500]:  # 限制读取前500个文件
            try:
                df = pd.read_csv(filepath, encoding='utf-8-sig', nrows=1)
                
                if df.empty:
                    continue
                
                # 解析股票代码
                filename = os.path.basename(filepath).replace('.csv', '')
                code = filename.split('.')[1] if '.' in filename else filename
                
                # 确定市场
                if filename.startswith('sh.'):
                    market = 'sh'
                elif filename.startswith('sz.'):
                    market = 'sz'
                else:
                    continue
                
                # 构建行情数据
                row = {
                    '代码': code,
                    '名称': filename,  # Baostock CSV 不包含名称
                    '最新价': df['close'].values[0] if 'close' in df.columns else None,
                    '涨跌幅': df['pctChg'].values[0] if 'pctChg' in df.columns else None,
                    '成交量': df['volume'].values[0] if 'volume' in df.columns else None,
                    '成交额': df['amount'].values[0] if 'amount' in df.columns else None,
                }
                
                all_data.append(row)
                
            except Exception as e:
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.DataFrame(all_data)
        
        # 转换数值列
        for col in ['最新价', '涨跌幅', '成交量', '成交额']:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce')
        
        logger.info(f"[Baostock] 获取实时行情成功, {len(result)} 只股票")
        return result
    
    except Exception as e:
        logger.warning(f"[Baostock] 获取实时行情失败: {e}")
        return pd.DataFrame()


# ============ 带自动切换的包装函数 ============

def get_stock_hist_baostock(symbol: str, period: str = "daily", 
                           start_date: str = "19700101", 
                           end_date: str = "20500101",
                           adjust: str = "qfq") -> pd.DataFrame:
    """
    获取个股历史数据 - Baostock 数据源
    作为最后的数据源 fallback
    """
    logger.info(f"[Baostock] 尝试获取 {symbol} 历史数据")
    return stock_zh_a_hist_baostock(symbol, period, start_date, end_date, adjust)


def get_stock_spot_baostock() -> pd.DataFrame:
    """
    获取 A 股实时行情 - Baostock 数据源
    作为最后的数据源 fallback
    """
    logger.info("[Baostock] 尝试获取实时行情")
    return stock_zh_a_spot_baostock()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== 测试 Baostock 适配器 ===")
    
    # 测试历史数据
    df = get_stock_hist_baostock("600000", start_date="20260101", end_date="20260522")
    print(f"历史数据: {len(df)} 条")
    if not df.empty:
        print(df.tail(3))
    
    # 测试实时行情
    df = get_stock_spot_baostock()
    print(f"\n实时行情: {len(df)} 只")
    if not df.empty:
        print(df.head(3))
