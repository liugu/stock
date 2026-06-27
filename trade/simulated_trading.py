#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟交易系统

功能：
1. 模拟账户管理（资金、持仓）
2. 策略买入卖出
3. 持仓管理
4. 盈亏计算
5. 交易记录

作者: Hermes
日期: 2026/5/28
"""

import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import warnings
warnings.filterwarnings('ignore')

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

class SimulatedTradingAccount:
    """模拟交易账户"""
    
    def __init__(self, initial_capital=1000000, account_name='default'):
        """
        初始化模拟账户
        
        参数:
            initial_capital: 初始资金（默认100万）
            account_name: 账户名称
        """
        self.account_name = account_name
        self.initial_capital = initial_capital
        self.cash = initial_capital  # 可用现金
        self.positions = {}  # 持仓 {code: {shares, cost_price, current_price}}
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日资产价值
        
        # 创建数据目录
        self.data_dir = 'output/trading_accounts'
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载已有账户
        self.load_account()
    
    def load_account(self):
        """加载账户数据"""
        account_file = f'{self.data_dir}/{self.account_name}.json'
        if os.path.exists(account_file):
            with open(account_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.initial_capital = data.get('initial_capital', self.initial_capital)
                self.cash = data.get('cash', self.cash)
                self.positions = data.get('positions', {})
                self.trades = data.get('trades', [])
                self.daily_values = data.get('daily_values', [])
            print(f'加载账户: {self.account_name}')
            print(f'初始资金: {self.initial_capital:.2f}元, 可用现金: {self.cash:.2f}元')
            print(f'持仓数量: {len(self.positions)}只')
        else:
            print(f'创建新账户: {self.account_name}')
            print(f'初始资金: {self.initial_capital:.2f}元')
    
    def save_account(self):
        """保存账户数据"""
        account_file = f'{self.data_dir}/{self.account_name}.json'
        data = {
            'account_name': self.account_name,
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades[-100:],  # 只保存最近100条交易
            'daily_values': self.daily_values[-30:]  # 只保存最近30天
        }
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_current_price(self, code):
        """获取股票当前价格"""
        conn = pymysql.connect(**DB_CONFIG)
        try:
            sql = f"""
            SELECT new_price FROM cn_stock_spot 
            WHERE code = '{code}' 
            AND date = (SELECT MAX(date) FROM cn_stock_spot)
            """
            df = pd.read_sql(sql, conn)
            if not df.empty:
                return float(df.iloc[0]['new_price'])
            return None
        finally:
            conn.close()
    
    def buy(self, code, name, shares, strategy='手动买入'):
        """
        买入股票
        
        参数:
            code: 股票代码
            name: 股票名称
            shares: 买入股数（必须是100的整数倍）
            strategy: 买入策略
        """
        # 确保股数是100的整数倍
        shares = int(shares / 100) * 100
        if shares <= 0:
            print(f'买入失败: 股数必须大于0且为100的整数倍')
            return False
        
        # 获取当前价格
        price = self.get_current_price(code)
        if price is None:
            print(f'买入失败: 无法获取股票价格')
            return False
        
        # 计算所需资金
        amount = price * shares
        commission = max(amount * 0.0003, 5)  # 佣金，最低5元
        transfer_fee = amount * 0.00002  # 过户费
        total_cost = amount + commission + transfer_fee
        
        # 检查资金是否足够
        if total_cost > self.cash:
            print(f'买入失败: 资金不足 (需要{total_cost:.2f}元, 可用{self.cash:.2f}元)')
            return False
        
        # 执行买入
        self.cash -= total_cost
        
        # 更新持仓
        if code in self.positions:
            # 加仓
            old_shares = self.positions[code]['shares']
            old_cost = self.positions[code]['cost_price']
            new_shares = old_shares + shares
            new_cost = (old_shares * old_cost + shares * price) / new_shares
            self.positions[code] = {
                'name': name,
                'shares': new_shares,
                'cost_price': round(new_cost, 2),
                'current_price': price,
                'buy_time': self.positions[code].get('buy_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
        else:
            # 新建仓位
            self.positions[code] = {
                'name': name,
                'shares': shares,
                'cost_price': round(price, 2),
                'current_price': price,
                'buy_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 记录交易
        trade = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': '买入',
            'code': code,
            'name': name,
            'price': price,
            'shares': shares,
            'amount': round(amount, 2),
            'commission': round(commission + transfer_fee, 2),
            'total_cost': round(total_cost, 2),
            'strategy': strategy
        }
        self.trades.append(trade)
        
        # 保存账户
        self.save_account()
        
        print(f'✓ 买入成功: {name}({code})')
        print(f'  价格: {price}元, 数量: {shares}股')
        print(f'  成交额: {amount:.2f}元, 手续费: {commission + transfer_fee:.2f}元')
        print(f'  总成本: {total_cost:.2f}元')
        print(f'  剩余现金: {self.cash:.2f}元')
        
        return True
    
    def sell(self, code, shares=None, strategy='手动卖出'):
        """
        卖出股票
        
        参数:
            code: 股票代码
            shares: 卖出股数（None表示全部卖出）
            strategy: 卖出策略
        """
        # 检查是否持有该股票
        if code not in self.positions:
            print(f'卖出失败: 未持有该股票')
            return False
        
        # 获取当前价格
        price = self.get_current_price(code)
        if price is None:
            print(f'卖出失败: 无法获取股票价格')
            return False
        
        # 确定卖出数量
        position = self.positions[code]
        if shares is None:
            shares = position['shares']  # 全部卖出
        else:
            shares = min(int(shares / 100) * 100, position['shares'])
        
        if shares <= 0:
            print(f'卖出失败: 股数必须大于0')
            return False
        
        # 计算收入
        amount = price * shares
        commission = max(amount * 0.0003, 5)
        transfer_fee = amount * 0.00002
        stamp_duty = amount * 0.001  # 印花税（卖出）
        total_income = amount - commission - transfer_fee - stamp_duty
        
        # 计算盈亏
        cost = position['cost_price'] * shares
        profit = amount - cost - commission - transfer_fee - stamp_duty
        profit_rate = profit / cost * 100
        
        # 执行卖出
        self.cash += total_income
        
        # 更新持仓
        if shares == position['shares']:
            # 全部卖出
            del self.positions[code]
        else:
            # 部分卖出
            self.positions[code]['shares'] -= shares
            self.positions[code]['current_price'] = price
        
        # 记录交易
        trade = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': '卖出',
            'code': code,
            'name': position['name'],
            'price': price,
            'shares': shares,
            'amount': round(amount, 2),
            'commission': round(commission + transfer_fee + stamp_duty, 2),
            'total_income': round(total_income, 2),
            'profit': round(profit, 2),
            'profit_rate': round(profit_rate, 2),
            'strategy': strategy
        }
        self.trades.append(trade)
        
        # 保存账户
        self.save_account()
        
        print(f'✓ 卖出成功: {position["name"]}({code})')
        print(f'  价格: {price}元, 数量: {shares}股')
        print(f'  成交额: {amount:.2f}元, 手续费: {commission + transfer_fee + stamp_duty:.2f}元')
        print(f'  实际收入: {total_income:.2f}元')
        print(f'  盈亏: {profit:.2f}元 ({profit_rate:+.2f}%)')
        print(f'  可用现金: {self.cash:.2f}元')
        
        return True
    
    def update_positions(self):
        """更新持仓价格"""
        if not self.positions:
            return
        
        print('\n更新持仓价格...')
        for code in self.positions:
            price = self.get_current_price(code)
            if price:
                self.positions[code]['current_price'] = price
    
    def get_account_value(self):
        """计算账户总资产"""
        self.update_positions()
        
        stock_value = 0
        for code, pos in self.positions.items():
            stock_value += pos['shares'] * pos['current_price']
        
        total_value = self.cash + stock_value
        profit = total_value - self.initial_capital
        profit_rate = profit / self.initial_capital * 100
        
        return {
            'cash': self.cash,
            'stock_value': stock_value,
            'total_value': total_value,
            'profit': profit,
            'profit_rate': profit_rate
        }
    
    def show_positions(self):
        """显示持仓"""
        if not self.positions:
            print('\n当前无持仓')
            return
        
        self.update_positions()
        
        print('\n' + '=' * 70)
        print('当前持仓')
        print('=' * 70)
        
        total_profit = 0
        for code, pos in self.positions.items():
            current_value = pos['shares'] * pos['current_price']
            cost_value = pos['shares'] * pos['cost_price']
            profit = current_value - cost_value
            profit_rate = profit / cost_value * 100
            total_profit += profit
            
            print(f'\n{pos["name"]}({code})')
            print(f'  持仓: {pos["shares"]}股')
            print(f'  成本价: {pos["cost_price"]}元, 现价: {pos["current_price"]}元')
            print(f'  市值: {current_value:.2f}元')
            print(f'  盈亏: {profit:.2f}元 ({profit_rate:+.2f}%)')
        
        print('\n' + '-' * 70)
        print(f'持仓总盈亏: {total_profit:.2f}元')
    
    def show_account(self):
        """显示账户信息"""
        value = self.get_account_value()
        
        print('\n' + '=' * 70)
        print(f'账户: {self.account_name}')
        print('=' * 70)
        print(f'初始资金: {self.initial_capital:.2f}元')
        print(f'可用现金: {value["cash"]:.2f}元')
        print(f'持仓市值: {value["stock_value"]:.2f}元')
        print(f'总资产: {value["total_value"]:.2f}元')
        print(f'总盈亏: {value["profit"]:.2f}元 ({value["profit_rate"]:+.2f}%)')
        print('=' * 70)
    
    def show_trades(self, limit=10):
        """显示交易记录"""
        if not self.trades:
            print('\n暂无交易记录')
            return
        
        print('\n' + '=' * 70)
        print(f'最近{limit}条交易记录')
        print('=' * 70)
        
        for trade in self.trades[-limit:]:
            print(f'\n{trade["time"]} - {trade["type"]}')
            print(f'{trade["name"]}({trade["code"]})')
            print(f'价格: {trade["price"]}元, 数量: {trade["shares"]}股')
            print(f'金额: {trade["amount"]:.2f}元')
            if trade["type"] == "买入":
                print(f'总成本: {trade["total_cost"]:.2f}元')
            else:
                print(f'盈亏: {trade["profit"]:.2f}元 ({trade["profit_rate"]:+.2f}%)')
            print(f'策略: {trade["strategy"]}')


class TradingStrategy:
    """交易策略"""
    
    def __init__(self, account):
        self.account = account
    
    def strategy_shortline(self, stocks_df):
        """
        短线策略
        
        参数:
            stocks_df: 股票DataFrame（从shortline_selection筛选结果）
        """
        print('\n' + '=' * 70)
        print('执行短线策略')
        print('=' * 70)
        
        # 账户信息
        value = self.account.get_account_value()
        print(f'可用资金: {value["cash"]:.2f}元')
        
        # 每只股票投入资金（总资金的10%）
        invest_per_stock = value["total_value"] * 0.1
        print(f'单只股票投入: {invest_per_stock:.2f}元')
        
        # 筛选技术形态最好的股票
        good_stocks = stocks_df[
            stocks_df['技术信号'].str.contains('均线多头') & 
            stocks_df['技术信号'].str.contains('站上均线')
        ].head(3)
        
        if len(good_stocks) == 0:
            print('\n没有符合条件的股票')
            return
        
        print(f'\n准备买入 {len(good_stocks)} 只股票')
        
        for _, row in good_stocks.iterrows():
            # 计算买入股数
            shares = int(invest_per_stock / row['价格'] / 100) * 100
            if shares >= 100:
                print(f'\n准备买入: {row["名称"]}({row["代码"]})')
                print(f'  价格: {row["价格"]}元, 数量: {shares}股')
                print(f'  涨幅: +{row["涨幅"]}%, 技术信号: {row["技术信号"]}')
                self.account.buy(row['代码'], row['名称'], shares, '短线策略')
    
    def strategy_sell_stop_loss(self, loss_rate=-3):
        """
        止损策略
        
        参数:
            loss_rate: 止损比例（默认-3%）
        """
        print('\n' + '=' * 70)
        print(f'执行止损策略 (亏损{loss_rate}%止损)')
        print('=' * 70)
        
        if not self.account.positions:
            print('当前无持仓')
            return
        
        sell_codes = []
        for code, pos in self.account.positions.items():
            profit_rate = (pos['current_price'] - pos['cost_price']) / pos['cost_price'] * 100
            
            if profit_rate <= loss_rate:
                print(f'\n触发止损: {pos["name"]}({code})')
                print(f'  成本价: {pos["cost_price"]}元, 现价: {pos["current_price"]}元')
                print(f'  亏损: {profit_rate:.2f}%')
                sell_codes.append(code)
        
        # 执行卖出
        for code in sell_codes:
            self.account.sell(code, strategy='止损策略')
    
    def strategy_sell_take_profit(self, profit_rate=10):
        """
        止盈策略
        
        参数:
            profit_rate: 止盈比例（默认10%）
        """
        print('\n' + '=' * 70)
        print(f'执行止盈策略 (盈利{profit_rate}%止盈)')
        print('=' * 70)
        
        if not self.account.positions:
            print('当前无持仓')
            return
        
        sell_codes = []
        for code, pos in self.account.positions.items():
            current_rate = (pos['current_price'] - pos['cost_price']) / pos['cost_price'] * 100
            
            if current_rate >= profit_rate:
                print(f'\n触发止盈: {pos["name"]}({code})')
                print(f'  成本价: {pos["cost_price"]}元, 现价: {pos["current_price"]}元')
                print(f'  盈利: {current_rate:.2f}%')
                sell_codes.append(code)
        
        # 执行卖出
        for code in sell_codes:
            self.account.sell(code, strategy='止盈策略')


def main():
    """主函数"""
    print('=' * 70)
    print('模拟交易系统')
    print('=' * 70)
    
    # 创建账户
    account = SimulatedTradingAccount(initial_capital=1000000, account_name='test_account')
    
    # 显示账户信息
    account.show_account()
    
    # 显示持仓
    account.show_positions()
    
    # 加载短线筛选结果
    shortline_file = 'output/shortline_selection_20260528_062205.csv'
    if os.path.exists(shortline_file):
        stocks_df = pd.read_csv(shortline_file, encoding='utf-8-sig')
        print(f'\n加载短线筛选结果: {len(stocks_df)}只股票')
        
        # 创建策略
        strategy = TradingStrategy(account)
        
        # 执行短线买入策略
        strategy.strategy_shortline(stocks_df)
        
        # 显示更新后的账户
        account.show_account()
        account.show_positions()
    else:
        print(f'\n未找到短线筛选结果: {shortline_file}')
        print('请先运行 shortline_selection.py')
    
    # 显示交易记录
    account.show_trades(limit=10)
    
    print('\n' + '=' * 70)
    print('模拟交易完成')
    print('=' * 70)
    
    print('\n使用说明:')
    print('1. 手动买入: account.buy("代码", "名称", 股数, "策略")')
    print('2. 手动卖出: account.sell("代码", 股数, "策略")')
    print('3. 查看账户: account.show_account()')
    print('4. 查看持仓: account.show_positions()')
    print('5. 查看交易: account.show_trades()')


if __name__ == '__main__':
    main()
