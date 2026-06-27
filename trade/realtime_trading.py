#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时行情交易系统

功能：
1. 实时行情获取（使用akshare）
2. 实时监控持仓
3. 自动止盈止损
4. 实时推送提醒

作者: Hermes
日期: 2026/5/28
"""

import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, 'E:/量化研究/workspace/stock')
from simulated_trading import SimulatedTradingAccount

class RealtimeQuote:
    """实时行情获取"""
    
    @staticmethod
    def get_realtime_quote(codes):
        """
        获取实时行情
        
        参数:
            codes: 股票代码列表
        
        返回:
            DataFrame: 实时行情数据
        """
        try:
            # 使用akshare获取实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 筛选指定股票
            df = df[df['代码'].isin(codes)]
            
            # 选择需要的列
            result = df[['代码', '名称', '最新价', '涨跌幅', '涨跌额', 
                        '成交量', '成交额', '振幅', '最高', '最低', 
                        '今开', '昨收', '换手率', '市盈率-动态', '总市值']].copy()
            
            # 重命名列
            result.columns = ['code', 'name', 'price', 'change_pct', 'change_amt',
                            'volume', 'amount', 'amplitude', 'high', 'low',
                            'open', 'pre_close', 'turnover', 'pe', 'market_cap']
            
            return result
            
        except Exception as e:
            print(f'获取实时行情失败: {e}')
            return pd.DataFrame()
    
    @staticmethod
    def get_single_quote(code):
        """获取单只股票实时行情"""
        df = RealtimeQuote.get_realtime_quote([code])
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    
    @staticmethod
    def get_stock_list_realtime():
        """获取全部A股实时行情"""
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f'获取股票列表失败: {e}')
            return pd.DataFrame()


class RealtimeTrader:
    """实时交易系统"""
    
    def __init__(self, account_name='test_account'):
        """初始化交易系统"""
        self.account = SimulatedTradingAccount(initial_capital=1000000, account_name=account_name)
        self.monitoring = False
        self.quote = RealtimeQuote()
        
        print('实时交易系统已启动')
        print(f'账户: {account_name}')
        self.account.show_account()
    
    def update_positions_price(self):
        """更新持仓价格"""
        if not self.account.positions:
            return
        
        codes = list(self.account.positions.keys())
        quotes = self.quote.get_realtime_quote(codes)
        
        if quotes.empty:
            print('无法更新持仓价格')
            return
        
        for _, row in quotes.iterrows():
            code = row['code']
            if code in self.account.positions:
                self.account.positions[code]['current_price'] = float(row['price'])
        
        # 保存账户
        self.account.save_account()
    
    def monitor_positions(self, interval=60):
        """
        实时监控持仓
        
        参数:
            interval: 刷新间隔（秒）
        """
        if not self.account.positions:
            print('当前无持仓')
            return
        
        print(f'\n开始监控持仓 (每{interval}秒刷新一次)')
        print('按 Ctrl+C 停止监控\n')
        
        self.monitoring = True
        
        try:
            while self.monitoring:
                # 清屏
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print('=' * 80)
                print(f'实时持仓监控 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                print('=' * 80)
                
                # 更新价格
                self.update_positions_price()
                
                # 显示持仓
                total_profit = 0
                total_value = 0
                
                for code, pos in self.account.positions.items():
                    current_price = pos['current_price']
                    cost_price = pos['cost_price']
                    shares = pos['shares']
                    
                    # 计算盈亏
                    profit = (current_price - cost_price) * shares
                    profit_rate = (current_price - cost_price) / cost_price * 100
                    current_value = current_price * shares
                    
                    total_profit += profit
                    total_value += current_value
                    
                    # 颜色标记
                    if profit_rate >= 0:
                        color_code = '\033[91m'  # 红色（上涨）
                    else:
                        color_code = '\033[92m'  # 绿色（下跌）
                    reset_code = '\033[0m'
                    
                    print(f'\n{pos["name"]}({code})')
                    print(f'  持仓: {shares}股')
                    print(f'  成本: {cost_price}元 → 现价: {color_code}{current_price}元{reset_code}')
                    print(f'  市值: {current_value:.2f}元')
                    print(f'  盈亏: {color_code}{profit:.2f}元 ({profit_rate:+.2f}%){reset_code}')
                
                # 显示账户总览
                print('\n' + '-' * 80)
                account_value = self.account.cash + total_value
                total_profit_rate = total_profit / (account_value - self.account.cash) * 100 if total_value > 0 else 0
                
                print(f'持仓市值: {total_value:.2f}元')
                print(f'可用现金: {self.account.cash:.2f}元')
                print(f'总资产: {account_value:.2f}元')
                print(f'持仓盈亏: {total_profit:.2f}元')
                
                # 检查止盈止损
                self.check_stop_loss_profit()
                
                print('\n下次刷新: {}秒后...'.format(interval))
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print('\n\n监控已停止')
            self.monitoring = False
    
    def check_stop_loss_profit(self, stop_loss=-3, take_profit=10):
        """
        检查止盈止损
        
        参数:
            stop_loss: 止损比例
            take_profit: 止盈比例
        """
        sell_codes = []
        
        for code, pos in self.account.positions.items():
            profit_rate = (pos['current_price'] - pos['cost_price']) / pos['cost_price'] * 100
            
            # 止损
            if profit_rate <= stop_loss:
                print(f'\n⚠️ 触发止损: {pos["name"]}({code})')
                print(f'   亏损: {profit_rate:.2f}% (止损线: {stop_loss}%)')
                sell_codes.append((code, '止损'))
            
            # 止盈
            elif profit_rate >= take_profit:
                print(f'\n✓ 触发止盈: {pos["name"]}({code})')
                print(f'   盈利: {profit_rate:.2f}% (止盈线: {take_profit}%)')
                sell_codes.append((code, '止盈'))
        
        # 执行卖出
        for code, reason in sell_codes:
            self.account.sell(code, strategy=f'{reason}策略')
    
    def scan_opportunities(self, filters=None):
        """
        扫描交易机会
        
        参数:
            filters: 筛选条件字典
        """
        if filters is None:
            filters = {
                'change_pct_min': 2,  # 最小涨幅
                'change_pct_max': 10,  # 最大涨幅
                'amount_min': 100000000,  # 最小成交额
                'turnover_min': 1,  # 最小换手率
                'turnover_max': 20,  # 最大换手率
            }
        
        print('\n扫描交易机会...')
        print('筛选条件:')
        for k, v in filters.items():
            print(f'  {k}: {v}')
        
        # 获取实时行情
        df = self.quote.get_stock_list_realtime()
        
        if df.empty:
            print('无法获取股票列表')
            return pd.DataFrame()
        
        # 筛选
        df = df[df['涨跌幅'] >= filters.get('change_pct_min', 2)]
        df = df[df['涨跌幅'] <= filters.get('change_pct_max', 10)]
        df = df[df['成交额'] >= filters.get('amount_min', 100000000)]
        df = df[df['换手率'] >= filters.get('turnover_min', 1)]
        df = df[df['换手率'] <= filters.get('turnover_max', 20)]
        
        # 排除ST
        df = df[~df['名称'].str.contains('ST|退')]
        
        # 排序
        df = df.sort_values('涨跌幅', ascending=False)
        
        print(f'\n找到 {len(df)} 只符合条件的股票')
        
        # 显示TOP20
        print('\n涨幅榜TOP20:')
        print('-' * 80)
        
        for i, row in df.head(20).iterrows():
            print(f'{row["名称"]}({row["代码"]}): {row["涨跌幅"]:+.2f}%, 换手率: {row["换手率"]:.2f}%, 成交额: {row["成交额"]/100000000:.2f}亿')
        
        return df
    
    def quick_buy(self, code, name=None, amount=100000):
        """
        快速买入
        
        参数:
            code: 股票代码
            name: 股票名称（可选）
            amount: 买入金额（默认10万）
        """
        # 获取实时行情
        quote = self.quote.get_single_quote(code)
        
        if not quote:
            print(f'无法获取股票 {code} 的行情')
            return False
        
        if not name:
            name = quote['name']
        
        price = quote['price']
        shares = int(amount / price / 100) * 100
        
        if shares < 100:
            print(f'金额不足，至少需要 {price * 100:.2f}元')
            return False
        
        print(f'\n准备买入: {name}({code})')
        print(f'  当前价格: {price}元')
        print(f'  买入数量: {shares}股')
        print(f'  预计金额: {price * shares:.2f}元')
        
        # 执行买入
        return self.account.buy(code, name, shares, '实时交易')
    
    def quick_sell(self, code, shares=None):
        """
        快速卖出
        
        参数:
            code: 股票代码
            shares: 卖出数量（None表示全部）
        """
        if code not in self.account.positions:
            print(f'未持有股票 {code}')
            return False
        
        return self.account.sell(code, shares, '实时交易')


def main():
    """主函数"""
    print('=' * 80)
    print('实时行情交易系统')
    print('=' * 80)
    
    # 创建交易系统
    trader = RealtimeTrader(account_name='test_account')
    
    while True:
        print('\n' + '=' * 80)
        print('操作菜单')
        print('=' * 80)
        print('1. 查看账户')
        print('2. 查看持仓')
        print('3. 扫描机会')
        print('4. 快速买入')
        print('5. 快速卖出')
        print('6. 实时监控')
        print('7. 更新价格')
        print('8. 查看交易记录')
        print('0. 退出')
        print()
        
        choice = input('请选择操作 (0-8): ').strip()
        
        if choice == '0':
            print('\n感谢使用，再见！')
            break
        
        elif choice == '1':
            trader.account.show_account()
        
        elif choice == '2':
            trader.update_positions_price()
            trader.account.show_positions()
        
        elif choice == '3':
            # 自定义筛选条件
            print('\n筛选条件（回车使用默认值）:')
            change_min = input('最小涨幅% (默认2): ').strip()
            change_max = input('最大涨幅% (默认10): ').strip()
            
            filters = {
                'change_pct_min': float(change_min) if change_min else 2,
                'change_pct_max': float(change_max) if change_max else 10,
                'amount_min': 100000000,
                'turnover_min': 1,
                'turnover_max': 20,
            }
            
            opportunities = trader.scan_opportunities(filters)
        
        elif choice == '4':
            code = input('请输入股票代码: ').strip()
            amount = input('买入金额 (默认100000): ').strip()
            amount = float(amount) if amount else 100000
            trader.quick_buy(code, amount=amount)
        
        elif choice == '5':
            code = input('请输入股票代码: ').strip()
            shares = input('卖出数量 (回车全部卖出): ').strip()
            shares = int(shares) if shares else None
            trader.quick_sell(code, shares)
        
        elif choice == '6':
            interval = input('刷新间隔秒数 (默认60): ').strip()
            interval = int(interval) if interval else 60
            
            stop_loss = input('止损比例% (默认-3): ').strip()
            stop_loss = float(stop_loss) if stop_loss else -3
            
            take_profit = input('止盈比例% (默认10): ').strip()
            take_profit = float(take_profit) if take_profit else 10
            
            trader.monitor_positions(interval=interval)
        
        elif choice == '7':
            trader.update_positions_price()
            print('价格已更新')
            trader.account.show_positions()
        
        elif choice == '8':
            limit = input('显示最近几条 (默认10): ').strip()
            limit = int(limit) if limit else 10
            trader.account.show_trades(limit)
        
        else:
            print('\n无效选择，请重新输入')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n程序已退出')
    except Exception as e:
        print(f'\n发生错误: {e}')
        import traceback
        traceback.print_exc()
