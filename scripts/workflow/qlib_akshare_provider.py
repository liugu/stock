#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qlib 自定义数据提供者
使用 akshare 作为数据源，无需下载 Qlib 数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
import warnings
warnings.filterwarnings('ignore')

class AkshareQlibProvider:
    """
    自定义 Qlib 数据提供者
    使用 akshare 获取 A 股数据
    """
    
    def __init__(self):
        self._cache = {}  # 数据缓存
        self._instrument_list = None
    
    def list_instruments(self, market='all'):
        """获取股票列表"""
        if self._instrument_list is None:
            try:
                df = ak.stock_zh_a_spot_em()
                # 转换为 Qlib 格式
                instruments = []
                for _, row in df.iterrows():
                    code = row['代码']
                    # Qlib 格式: 000001.SZ, 600000.SH
                    market_suffix = '.SZ' if code.startswith(('00', '30')) else '.SH'
                    instruments.append(f"{code}{market_suffix}")
                
                self._instrument_list = instruments
            except Exception as e:
                print(f"获取股票列表失败: {e}")
                return []
        
        return self._instrument_list
    
    def get_features(self, instruments, fields, start_time, end_time):
        """
        获取股票特征数据
        
        Args:
            instruments: 股票代码列表，如 ['000001.SZ', '600000.SH']
            fields: 字段列表，如 ['$close', '$volume', '$factor']
            start_time: 开始日期
            end_time: 结束日期
        """
        results = {}
        
        for inst in instruments[:10]:  # 限制数量避免网络问题
            # 转换股票代码
            code = inst.split('.')[0]
            
            try:
                # 获取历史数据
                df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '换手率': 'turnover'
                })
                
                # 筛选日期范围
                df['date'] = pd.to_datetime(df['date'])
                df = df[(df['date'] >= start_time) & (df['date'] <= end_time)]
                
                # 构建特征
                inst_features = {}
                for field in fields:
                    field_name = field.replace('$', '')
                    if field_name in df.columns:
                        inst_features[field] = df[field_name].values
                    elif field_name == 'factor':
                        inst_features[field] = np.ones(len(df))  # 复权因子
                
                results[inst] = inst_features
                
            except Exception as e:
                print(f"获取 {inst} 数据失败: {e}")
                continue
        
        return results

# ============ Qlib 因子计算 ============

def calculate_qlib_style_factors(df):
    """
    计算 Qlib 风格因子
    参考 Alpha158/Alpha360 因子集
    """
    if df is None or len(df) < 30:
        return None
    
    df = df.copy()
    
    # ===== 价格因子 =====
    # 收益率
    df['return_0'] = df['close'] / df['close'].shift(1) - 1
    df['return_1'] = df['close'].shift(1) / df['close'].shift(2) - 1
    df['return_2'] = df['close'].shift(2) / df['close'].shift(3) - 1
    
    # 多日收益率
    for n in [5, 10, 20, 30]:
        df[f'return_{n}d'] = df['close'] / df['close'].shift(n) - 1
    
    # ===== 位置因子 =====
    # 价格相对位置
    for n in [10, 20, 30]:
        df[f'high_{n}'] = df['high'].rolling(n).max()
        df[f'low_{n}'] = df['low'].rolling(n).min()
        df[f'price_pos_{n}'] = (df['close'] - df[f'low_{n}']) / (df[f'high_{n}'] - df[f'low_{n}'] + 1e-8)
    
    # ===== 波动因子 =====
    for n in [5, 10, 20]:
        df[f'volatility_{n}'] = df['return_0'].rolling(n).std()
        df[f'range_{n}'] = (df['high'] - df['low']).rolling(n).mean() / df['close'].rolling(n).mean()
    
    # ===== 均线因子 =====
    for n in [5, 10, 20, 30, 60]:
        df[f'ma_{n}'] = df['close'].rolling(n).mean()
        df[f'ma_bias_{n}'] = df['close'] / df[f'ma_{n}'] - 1
    
    # 均线斜率
    for n in [5, 10, 20]:
        df[f'ma_slope_{n}'] = df[f'ma_{n}'] / df[f'ma_{n}'].shift(n) - 1
    
    # ===== 量能因子 =====
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(5).mean()
    
    for n in [5, 10, 20]:
        df[f'volume_ma_{n}'] = df['volume'].rolling(n).mean()
        df[f'volume_std_{n}'] = df['volume'].rolling(n).std()
    
    # ===== 动量因子 =====
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # ===== 交互因子 =====
    # 价格-成交量相关性
    for n in [10, 20]:
        df[f'price_volume_corr_{n}'] = df['close'].rolling(n).corr(df['volume'])
    
    return df

# ============ 使用示例 ============

def demo_qlib_style_selection():
    """演示使用 Qlib 风格因子选股"""
    print("=" * 60)
    print("Qlib 风格因子选股演示")
    print("=" * 60)
    
    # 创建提供者
    provider = AkshareQlibProvider()
    
    # 获取股票列表
    print("\n[1] 获取股票列表...")
    instruments = provider.list_instruments()
    print(f"股票数量: {len(instruments)}")
    
    # 获取数据
    print("\n[2] 获取股票数据...")
    features = provider.get_features(
        instruments[:5],  # 测试5只股票
        ['$close', '$volume', '$high', '$low'],
        '2024-01-01',
        '2024-12-31'
    )
    
    print(f"获取到 {len(features)} 只股票数据")
    
    # 计算因子
    print("\n[3] 计算 Qlib 风格因子...")
    for inst, data in features.items():
        if 'close' in data:
            df = pd.DataFrame({
                'close': data['$close'],
                'high': data['$high'],
                'low': data['$low'],
                'volume': data['$volume']
            })
            
            df_with_factors = calculate_qlib_style_factors(df)
            if df_with_factors is not None:
                # 显示因子数量
                new_cols = [c for c in df_with_factors.columns if c not in df.columns]
                print(f"{inst}: 计算了 {len(new_cols)} 个因子")
    
    print("\n✓ 演示完成")
    return True

# ============ 主程序 ============

def main():
    """主程序"""
    return demo_qlib_style_selection()

if __name__ == '__main__':
    main()