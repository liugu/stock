#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建缺失的数据库表
"""

import pymysql

# 数据库配置
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'instockdb',
    'charset': 'utf8mb4'
}

# 表结构定义
table_definitions = {
    'cn_stock_attention': """
    CREATE TABLE `cn_stock_attention` (
      `datetime` DATETIME NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      PRIMARY KEY (`datetime`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_fund_flow_concept': """
    CREATE TABLE `cn_stock_fund_flow_concept` (
      `date` DATE NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `change_rate` FLOAT,
      `fund_amount` BIGINT,
      `fund_rate` FLOAT,
      `fund_amount_super` BIGINT,
      `fund_rate_super` FLOAT,
      `fund_amount_large` BIGINT,
      `fund_rate_large` FLOAT,
      PRIMARY KEY (`date`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_indicators': """
    CREATE TABLE `cn_stock_indicators` (
      `date` DATE NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `macd` FLOAT,
      `kdj_k` FLOAT,
      `kdj_d` FLOAT,
      `kdj_j` FLOAT,
      `boll_upper` FLOAT,
      `boll_middle` FLOAT,
      `boll_lower` FLOAT,
      `rsi_6` FLOAT,
      `rsi_12` FLOAT,
      `rsi_24` FLOAT,
      PRIMARY KEY (`date`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_indicators_buy': """
    CREATE TABLE `cn_stock_indicators_buy` (
      `date` DATE NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `macd_buy` TINYINT,
      `kdj_buy` TINYINT,
      `boll_buy` TINYINT,
      `rsi_buy` TINYINT,
      PRIMARY KEY (`date`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_indicators_sell': """
    CREATE TABLE `cn_stock_indicators_sell` (
      `date` DATE NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `macd_sell` TINYINT,
      `kdj_sell` TINYINT,
      `boll_sell` TINYINT,
      `rsi_sell` TINYINT,
      PRIMARY KEY (`date`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_fund_flow_industry': """
    CREATE TABLE `cn_stock_fund_flow_industry` (
      `date` DATE NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `change_rate` FLOAT,
      `fund_amount` BIGINT,
      `fund_rate` FLOAT,
      `fund_amount_super` BIGINT,
      `fund_rate_super` FLOAT,
      `fund_amount_large` BIGINT,
      `fund_rate_large` FLOAT,
      PRIMARY KEY (`date`, `name`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'cn_stock_spot_buy': """
    CREATE TABLE `cn_stock_spot_buy` (
      `date` DATE NOT NULL,
      `code` VARCHAR(6) NOT NULL,
      `name` VARCHAR(20) NOT NULL,
      `new_price` FLOAT,
      `change_rate` FLOAT,
      `volume` BIGINT,
      `deal_amount` BIGINT,
      `pe` FLOAT,
      `pb` FLOAT,
      `roe` FLOAT,
      `debt_ratio` FLOAT,
      PRIMARY KEY (`date`, `code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
}

def create_tables():
    """创建缺失的表"""

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    missing_tables = []

    for table_name, create_sql in table_definitions.items():
        try:
            # 检查表是否存在
            cursor.execute(f"DESCRIBE {table_name}")
            result = cursor.fetchone()
            if result:
                print(f"✓ {table_name} - 已存在")
            else:
                print(f"✗ {table_name} - 缺失，正在创建...")
                cursor.execute(create_sql)
                conn.commit()
                print(f"  ✓ 创建成功")
        except Exception as e:
            print(f"  ✗ 创建失败: {e}")

    cursor.close()
    conn.close()

    print("\n表创建完成")

if __name__ == '__main__':
    create_tables()
