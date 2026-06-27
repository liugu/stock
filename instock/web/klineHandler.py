#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import json
import requests
from abc import ABC
from tornado import gen
import instock.lib.trade_time as trd
import instock.web.base as webBase

__author__ = 'liugu'
__date__ = '2024/05/19'


class GetKlineHtmlHandler(webBase.BaseHandler, ABC):
    """K线图表页面"""
    @gen.coroutine
    def get(self):
        code = self.get_argument("code", default=None, strip=False)
        name = self.get_argument("name", default=None, strip=False)
        date = self.get_argument("date", default=None, strip=False)
        
        run_date, run_date_nph = trd.get_trade_date_last()
        date_now_str = run_date_nph.strftime("%Y-%m-%d")
        
        if not date:
            date = date_now_str
        
        self.render("kline_chart.html", code=code, name=name, date=date,
                    leftMenu=webBase.GetLeftMenu(self.request.uri))


class GetKlineDataHandler(webBase.BaseHandler, ABC):
    """获取K线数据API"""
    def get(self):
        code = self.get_argument("code", default=None, strip=False)
        
        if not code:
            self.write(json.dumps({'success': False, 'message': '股票代码不能为空'}))
            return
        
        try:
            kline_data = self.get_kline_data(code)
            
            if kline_data is None:
                self.write(json.dumps({'success': False, 'message': '获取K线数据失败'}))
                return
            
            self.write(json.dumps({
                'success': True,
                'code': code,
                'data': kline_data
            }))
        except Exception as e:
            self.write(json.dumps({
                'success': False,
                'message': str(e)
            }))

    def get_kline_data(self, code):
        """获取K线数据"""
        try:
            prefix = 'sh' if code.startswith(('600', '601', '603', '605', '688')) else 'sz'
            symbol = f'{prefix}{code}'
            
            # 获取日K线数据
            url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '100'}
            
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            
            if not data:
                return None
            
            kline_list = []
            for item in data:
                kline_list.append([
                    item['day'],
                    float(item['open']) if item['open'] else 0,
                    float(item['close']) if item['close'] else 0,
                    float(item['high']) if item['high'] else 0,
                    float(item['low']) if item['low'] else 0,
                    int(float(item['volume'])) if item['volume'] else 0
                ])
            
            return {
                'symbol': symbol,
                'name': code,
                'kline': kline_list
            }
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None
