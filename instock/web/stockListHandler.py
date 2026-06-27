#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import json
import requests
import pandas as pd
from abc import ABC
from tornado import gen
import datetime
import instock.lib.trade_time as trd
import instock.core.singleton_stock_web_module_data as sswmd
import instock.web.base as webBase

__author__ = 'liugu'
__date__ = '2024/05/19'


class GetStockListHtmlHandler(webBase.BaseHandler, ABC):
    """获取股票列表页面"""
    @gen.coroutine
    def get(self):
        run_date, run_date_nph = trd.get_trade_date_last()
        date_now_str = run_date_nph.strftime("%Y-%m-%d")
        self.render("stock_list.html", web_module_data=sswmd.stock_web_module_data().get_data("cn_stock_spot"), date_now=date_now_str,
                    leftMenu=webBase.GetLeftMenu(self.request.uri))


class SyncRealtimeDataHandler(webBase.BaseHandler, ABC):
    """一键同步实时数据"""
    def post(self):
        self.set_header('Content-Type', 'application/json;charset=UTF-8')
        
        try:
            data = json.loads(self.request.body)
            action = data.get('action', 'sync_realtime')
            
            if action == 'sync_realtime':
                # 同步实时行情数据
                result = self.sync_realtime_data()
                self.write(json.dumps({
                    'success': True,
                    'message': f"同步完成: {result['count']} 条记录",
                    'data': result
                }))
            else:
                self.write(json.dumps({
                    'success': False,
                    'message': '未知操作'
                }))
        except Exception as e:
            self.write(json.dumps({
                'success': False,
                'message': str(e)
            }))

    def sync_realtime_data(self):
        """同步实时行情数据"""
        print("开始同步实时行情数据...")
        
        # 使用新浪API获取实时数据
        url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
        all_data = []
        
        for page in range(1, 60):
            params = {
                'page': str(page),
                'num': '100',
                'sort': 'changepercent',
                'asc': '0',
                'node': 'hs_a'
            }
            try:
                r = requests.get(url, params=params, timeout=30)
                data = r.json()
                if not data:
                    break
                all_data.extend(data)
                if page % 10 == 0:
                    print(f'已获取 {len(all_data)} 只...')
            except Exception as e:
                print(f'获取第{page}页失败: {e}')
                break
        
        if not all_data:
            return {'count': 0, 'error': '获取数据失败'}
        
        df = pd.DataFrame(all_data)
        df = df.rename(columns={
            'code': 'code', 'name': 'name', 'trade': 'new_price',
            'changepercent': 'change_rate', 'amount': 'turnover',
            'mktcap': 'total_market_cap', 'per': 'pe_ratio', 'pb': 'pb_ratio',
            'turnoverrate': 'turnover_rate', 'high': 'high_price', 'low': 'low_price',
            'openprice': 'open_price', 'low': 'low_price', 'high': 'high_price'
        })
        
        # 转换数值类型
        for col in ['new_price', 'change_rate', 'turnover', 'total_market_cap', 
                   'pe_ratio', 'pb_ratio', 'turnover_rate', 'high_price', 'low_price', 
                   'open_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        count = len(df)
        print(f"共获取 {count} 只股票数据")
        
        return {'count': count}


class GetKlineDataHandler(webBase.BaseHandler, ABC):
    """获取K线数据"""
    def get(self):
        code = self.get_argument("code", default=None, strip=False)
        date = self.get_argument("date", default=None, strip=False)
        
        if not code:
            self.write(json.dumps({'success': False, 'message': '股票代码不能为空'}))
            return
        
        try:
            # 获取历史K线数据
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
            # 使用新浪API获取历史K线数据
            prefix = 'sh' if code.startswith(('600', '601', '603', '605', '688')) else 'sz'
            symbol = f'{prefix}{code}'
            
            url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
            params = {'symbol': symbol, 'scale': '240', 'ma': 'no', 'datalen': '100'}
            
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            
            if not data:
                return None
            
            # 转换为K线图需要的格式 [时间, 开盘, 收盘, 最高, 最低, 成交量]
            kline_list = []
            for item in data:
                kline_list.append([
                    item['day'],
                    float(item['open']),
                    float(item['close']),
                    float(item['high']),
                    float(item['low']),
                    int(item['volume'])
                ])
            
            return {
                'symbol': symbol,
                'name': code,
                'kline': kline_list
            }
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None
