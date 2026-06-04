#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from instock.core.singleton_trade_date import stock_trade_date

__author__ = 'myh '
__date__ = '2023/4/10 '


def is_trade_date(date=None):
    trade_date = stock_trade_date().get_data()
    if trade_date is None:
        return False
    if date in trade_date:
        return True
    else:
        return False


def is_holiday(date=None):
    """
    判断是否为节假日（非交易日）
    
    参数:
        date: 日期对象或日期字符串
    
    返回:
        bool: True表示节假日，False表示交易日
    """
    if date is None:
        date = datetime.datetime.now().date()
    
    # 转换字符串为日期对象
    if isinstance(date, str):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            try:
                date = datetime.datetime.strptime(date, '%Y%m%d').date()
            except ValueError:
                return True
    
    return not is_trade_date(date)


def get_holiday_name(date=None):
    """
    获取节假日名称（常见节假日）
    
    参数:
        date: 日期对象
    
    返回:
        str: 节假日名称，如果不是节假日返回空字符串
    """
    if date is None:
        date = datetime.datetime.now().date()
    
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    
    # 如果是交易日，返回空
    if is_trade_date(date):
        return ""
    
    # 周末
    if date.weekday() in [5, 6]:
        return "周末"
    
    # 常见节假日判断（简化版）
    month = date.month
    day = date.day
    
    if month == 1 and day == 1:
        return "元旦"
    elif month == 5 and day in range(1, 6):
        return "劳动节"
    elif month == 10 and day in range(1, 8):
        return "国庆节"
    elif month == 2 and day in range(1, 15):
        return "春节"
    elif month == 4 and day in range(4, 7):
        return "清明节"
    elif month == 6 and day in range(10, 15):
        return "端午节"
    elif month == 9 and day in range(20, 30):
        return "中秋节"
    
    return "休市日"


def should_run_task(date=None):
    """
    判断是否应该执行任务
    
    参数:
        date: 日期对象
    
    返回:
        tuple: (是否执行, 原因)
    """
    if date is None:
        date = datetime.datetime.now().date()
    
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    
    if is_trade_date(date):
        return True, "交易日"
    
    holiday_name = get_holiday_name(date)
    return False, f"非交易日({holiday_name})"


def get_previous_trade_date(date):
    trade_date = stock_trade_date().get_data()
    if trade_date is None:
        return date
    tmp_date = date
    while True:
        tmp_date += datetime.timedelta(days=-1)
        if tmp_date in trade_date:
            break
    return tmp_date


def get_next_trade_date(date):
    trade_date = stock_trade_date().get_data()
    if trade_date is None:
        return date
    tmp_date = date
    while True:
        tmp_date += datetime.timedelta(days=1)
        if tmp_date in trade_date:
            break
    return tmp_date


OPEN_TIME = (
    (datetime.time(9, 15, 0), datetime.time(11, 30, 0)),
    (datetime.time(13, 0, 0), datetime.time(15, 0, 0)),
)


def is_tradetime(now_time):
    now = now_time.time()
    for begin, end in OPEN_TIME:
        if begin <= now < end:
            return True
    else:
        return False


PAUSE_TIME = (
    (datetime.time(11, 30, 0), datetime.time(12, 59, 30)),
)


def is_pause(now_time):
    now = now_time.time()
    for b, e in PAUSE_TIME:
        if b <= now < e:
            return True


CONTINUE_TIME = (
    (datetime.time(12, 59, 30), datetime.time(13, 0, 0)),
)


def is_continue(now_time):
    now = now_time.time()
    for b, e in CONTINUE_TIME:
        if b <= now < e:
            return True
    return False


CLOSE_TIME = (
    datetime.time(15, 0, 0),
)


def is_closing(now_time, start=datetime.time(14, 54, 30)):
    now = now_time.time()
    for close in CLOSE_TIME:
        if start <= now < close:
            return True
    return False


def is_close(now_time):
    now = now_time.time()
    for close in CLOSE_TIME:
        if now >= close:
            return True
    return False


def is_open(now_time):
    now = now_time.time()
    if now >= datetime.time(9, 30, 0):
        return True
    return False


def get_trade_hist_interval(date):
    tmp_year, tmp_month, tmp_day = date.split("-")
    date_end = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day))
    date_start = (date_end + datetime.timedelta(days=-(365 * 3))).strftime("%Y%m%d")

    now_time = datetime.datetime.now()
    now_date = now_time.date()
    is_trade_date_open_close_between = False
    if date_end.date() == now_date:
        if is_trade_date(now_date):
            if is_open(now_time) and not is_close(now_time):
                is_trade_date_open_close_between = True

    return date_start, not is_trade_date_open_close_between


def get_trade_date_last():
    now_time = datetime.datetime.now()
    run_date = now_time.date()
    run_date_nph = run_date
    if is_trade_date(run_date):
        if not is_close(now_time):
            run_date = get_previous_trade_date(run_date)
            if not is_open(now_time):
                run_date_nph = run_date
    else:
        run_date = get_previous_trade_date(run_date)
        run_date_nph = run_date
    return run_date, run_date_nph


def get_quarterly_report_date():
    now_time = datetime.datetime.now()
    year = now_time.year
    month = now_time.month
    if 1 <= month <= 3:
        month_day = '1231'
    elif 4 <= month <= 6:
        month_day = '0331'
    elif 7 <= month <= 9:
        month_day = '0630'
    else:
        month_day = '0930'
    return f"{year}{month_day}"


def get_bonus_report_date():
    now_time = datetime.datetime.now()
    year = now_time.year
    month = now_time.month
    if 2 <= month <= 6:
        year -= 1
        month_day = '1231'
    elif 8 <= month <= 12:
        month_day = '0630'
    elif month == 7:
        if now_time.day > 25:
            month_day = '0630'
        else:
            year -= 1
            month_day = '1231'
    else:
        year -= 1
        if now_time.day > 25:
            month_day = '1231'
        else:
            month_day = '0630'
    return f"{year}{month_day}"
