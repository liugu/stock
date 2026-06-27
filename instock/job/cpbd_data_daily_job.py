#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import logging
import os.path
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
import pandas as pd
from sqlalchemy import VARCHAR

import instock.lib.run_template as runt
import instock.core.tablestructure as tbs
import instock.lib.database as mdb
import instock.core.stockfetch as stf
from instock.core.stockfetch import is_a_stock

__author__ = 'myh '
__date__ = '2023/3/10 '

_COLLATE = "utf8mb4_general_ci"


def _drop_old_table_if_exists():
    """删除旧表让 insert_db_from_df 按新类型自动重建"""
    table_name = tbs.CN_STOCK_CPBD['name']
    if mdb.checkTableIsExist(table_name):
        logging.info(f"cpbd_data_daily_job: 删除旧表 {table_name} 以重建正确类型")
        with mdb.get_connection() as conn:
            with conn.cursor() as db:
                db.execute(f'DROP TABLE IF EXISTS `{table_name}`')


def get_all_a_stock_codes():
    """从股票数据表获取所有A股代码列表"""
    try:
        table_name = tbs.TABLE_CN_STOCK_SPOT['name']
        if not mdb.checkTableIsExist(table_name):
            logging.info(f"cpbd_data_daily_job: 表 {table_name} 不存在，无法获取股票列表")
            return []
        sql = f"SELECT DISTINCT `code` FROM `{table_name}` WHERE `date` = (SELECT MAX(`date`) FROM `{table_name}`)"
        result = mdb.executeSqlFetch(sql)
        if result:
            return [row[0] for row in result]
    except Exception as e:
        logging.error(f"cpbd_data_daily_job.get_all_a_stock_codes处理异常：{e}")
    return []


def save_cpbd_data(date, before=True):
    """抓取并存储操盘必读数据（含股东人数）"""
    if before:
        return

    try:
        table_name = tbs.CN_STOCK_CPBD['name']

        # 首次运行：删除旧表（字段类型可能不正确），让 insert_db_from_df 按新类型重建
        _drop_old_table_if_exists()

        # 获取A股股票列表
        stock_codes = get_all_a_stock_codes()
        if not stock_codes:
            logging.info(f"cpbd_data_daily_job: 未获取到A股股票列表")
            return

        # 过滤ST和退市股票
        try:
            spot_table = tbs.TABLE_CN_STOCK_SPOT['name']
            if mdb.checkTableIsExist(spot_table):
                max_date_sql = f"SELECT `code`, `name` FROM `{spot_table}` WHERE `date` = (SELECT MAX(`date`) FROM `{spot_table}`)"
                spot_data = mdb.executeSqlFetch(max_date_sql)
                if spot_data:
                    code_name_map = {row[0]: row[1] for row in spot_data}
                    stock_codes = [
                        code for code in stock_codes
                        if is_a_stock(code)
                        and code_name_map.get(code, '')
                        and not code_name_map[code].startswith(('*ST', 'ST', '退', '退市'))
                    ]
        except Exception as e:
            logging.error(f"cpbd_data_daily_job: 过滤ST股票处理异常：{e}")
            stock_codes = [c for c in stock_codes if is_a_stock(c)]

        logging.info(f"cpbd_data_daily_job: 开始抓取 {len(stock_codes)} 只股票的操盘必读数据")

        # 批量抓取
        data = stf.fetch_stock_cpbd_all(stock_codes)

        if data is None or len(data.index) == 0:
            logging.info("cpbd_data_daily_job: 未获取到操盘必读数据")
            return

        # 清理日期时间字段中的时间部分
        for col in ['END_DATE', 'LHBD_DATE', 'DZJY_DATE', 'RZRQ_DATE']:
            if col in data.columns:
                data[col] = pd.to_datetime(data[col], errors='coerce').dt.date

        # 插入数据（首次按新类型建表，后续只更新）
        if mdb.checkTableIsExist(table_name):
            # 删除老数据（按股票更新）
            del_codes = list(data['SECURITY_CODE'].unique())
            for code in del_codes:
                del_sql = f"DELETE FROM `{table_name}` WHERE `SECURITY_CODE` = '{code}'"
                mdb.executeSql(del_sql)

        # 列类型映射
        cols_type = tbs.get_field_types(tbs.CN_STOCK_CPBD['columns'])
        cols_type['BOARD_NAME'] = VARCHAR(255, _COLLATE)

        # 插入数据
        mdb.insert_db_from_df(data, table_name, cols_type, False, "`SECURITY_CODE`")

        logging.info(f"cpbd_data_daily_job: 成功存储 {len(data)} 只股票的操盘必读数据")

    except Exception as e:
        logging.error(f"cpbd_data_daily_job.save_cpbd_data处理异常：{e}")


def main():
    runt.run_with_args(save_cpbd_data)


# main函数入口
if __name__ == '__main__':
    main()
