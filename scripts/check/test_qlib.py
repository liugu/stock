#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qlib 功能测试脚本
在 Qlib 安装完成后运行
"""

import sys
import os

def test_qlib_import():
    """测试 Qlib 导入"""
    try:
        import qlib
        print(f"✓ Qlib 版本: {qlib.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Qlib 未安装: {e}")
        return False

def test_qlib_init():
    """测试 Qlib 初始化"""
    try:
        import qlib
        from qlib.config import REG_CN
        
        # 尝试初始化（需要下载数据）
        print("\n正在初始化 Qlib...")
        print("注意: 首次运行需要下载约 1GB 数据")
        
        # 检查数据是否存在
        data_path = os.path.expanduser("~/.qlib/qlib_data/cn_data")
        if os.path.exists(data_path):
            print(f"✓ 数据目录存在: {data_path}")
            qlib.init(provider_uri=data_path, region=REG_CN)
            print("✓ Qlib 初始化成功")
            return True
        else:
            print(f"✗ 数据目录不存在: {data_path}")
            print("请运行以下命令下载数据:")
            print("  python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn")
            return False
            
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return False

def test_qlib_data():
    """测试 Qlib 数据获取"""
    try:
        from qlib.data import D
        
        print("\n测试数据获取...")
        
        # 获取股票列表
        instruments = D.instruments(market='all')
        print(f"✓ 股票数量: {len(instruments)}")
        
        # 获取单只股票数据
        df = D.features(['000001.SZ'], ['$close', '$volume', '$factor'], 
                       start_time='2024-01-01', end_time='2024-12-31')
        print(f"✓ 数据形状: {df.shape}")
        print(df.head())
        
        return True
    except Exception as e:
        print(f"✗ 数据获取失败: {e}")
        return False

def test_alpha360():
    """测试 Alpha360 因子集"""
    try:
        from qlib.contrib.data.handler import Alpha360
        
        print("\n测试 Alpha360 因子...")
        
        # 创建数据集
        dataset = Alpha360(
            instruments=['000001.SZ', '000002.SZ'],
            start_time='2024-01-01',
            end_time='2024-12-31'
        )
        
        # 获取因子数据
        factor_data = dataset.fetch()
        print(f"✓ 因子数量: {factor_data.shape[1]}")
        print(f"✓ 数据形状: {factor_data.shape}")
        
        return True
    except Exception as e:
        print(f"✗ Alpha360 测试失败: {e}")
        return False

def main():
    """主测试流程"""
    print("=" * 60)
    print("Qlib 功能测试")
    print("=" * 60)
    
    # 1. 测试导入
    print("\n[1/4] 测试导入...")
    if not test_qlib_import():
        return False
    
    # 2. 测试初始化
    print("\n[2/4] 测试初始化...")
    if not test_qlib_init():
        return False
    
    # 3. 测试数据获取
    print("\n[3/4] 测试数据获取...")
    if not test_qlib_data():
        return False
    
    # 4. 测试因子
    print("\n[4/4] 测试 Alpha360...")
    if not test_alpha360():
        return False
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！Qlib 已就绪")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    main()
