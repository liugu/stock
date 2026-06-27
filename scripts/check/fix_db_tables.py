#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库表问题
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instock.core import tablestructure
from instock.lib import database

def create_missing_tables():
    """创建缺失的表"""

    # 获取所有表定义
    tables = []
    for key in dir(tablestructure):
        if key.startswith('TABLE_'):
            table = getattr(tablestructure, key)
            if isinstance(table, dict) and 'name' in table:
                tables.append(table)

    print(f"找到 {len(tables)} 个表定义")

    # 数据库连接
    db = database.engine().connect()

    missing_tables = []

    for table_def in tables:
        table_name = table_def['name']

        # 检查表是否存在
        try:
            db.execute(f"DESCRIBE {table_name}")
            print(f"✓ {table_name} - 已存在")
        except Exception as e:
            print(f"✗ {table_name} - 缺失，需要创建")
            missing_tables.append(table_def)

    db.close()

    print(f"\n共发现 {len(missing_tables)} 个缺失的表")

    return missing_tables

if __name__ == '__main__':
    missing = create_missing_tables()

    if missing:
        print("\n需要创建以下表:")
        for table in missing:
            print(f"  - {table['name']} ({table['cn']})")
    else:
        print("\n所有表都已存在，无需创建")
