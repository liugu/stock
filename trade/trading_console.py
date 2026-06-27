#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式交易界面

功能：
1. 查看账户
2. 查看持仓
3. 买入股票
4. 卖出股票
5. 执行策略
6. 查看交易记录

作者: Hermes
日期: 2026/5/28
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, 'E:/量化研究/workspace/stock')

from simulated_trading import SimulatedTradingAccount, TradingStrategy
import pandas as pd

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    """显示菜单"""
    print('\n' + '=' * 70)
    print('模拟交易系统 - 交互界面')
    print('=' * 70)
    print('\n1. 查看账户信息')
    print('2. 查看持仓详情')
    print('3. 买入股票')
    print('4. 卖出股票')
    print('5. 执行买入策略')
    print('6. 执行止损策略')
    print('7. 执行止盈策略')
    print('8. 查看交易记录')
    print('9. 重新初始化账户')
    print('0. 退出系统')
    print()

def main():
    """主函数"""
    # 创建账户
    account = SimulatedTradingAccount(initial_capital=1000000, account_name='test_account')
    strategy = TradingStrategy(account)
    
    while True:
        show_menu()
        choice = input('请选择操作 (0-9): ').strip()
        
        if choice == '0':
            print('\n感谢使用，再见！')
            break
        
        elif choice == '1':
            # 查看账户
            account.show_account()
        
        elif choice == '2':
            # 查看持仓
            account.show_positions()
        
        elif choice == '3':
            # 买入股票
            print('\n' + '-' * 70)
            code = input('请输入股票代码: ').strip()
            name = input('请输入股票名称: ').strip()
            shares = input('请输入买入股数 (100的整数倍): ').strip()
            
            try:
                shares = int(shares)
                if shares % 100 != 0:
                    print('股数必须是100的整数倍')
                else:
                    strategy_name = input('请输入策略名称 (回车默认"手动买入"): ').strip()
                    if not strategy_name:
                        strategy_name = '手动买入'
                    account.buy(code, name, shares, strategy_name)
            except ValueError:
                print('输入无效，请输入数字')
        
        elif choice == '4':
            # 卖出股票
            print('\n' + '-' * 70)
            if not account.positions:
                print('当前无持仓')
            else:
                print('当前持仓:')
                for code, pos in account.positions.items():
                    print(f'  {pos["name"]}({code}): {pos["shares"]}股')
                print()
                
                code = input('请输入股票代码: ').strip()
                shares = input('请输入卖出股数 (回车全部卖出): ').strip()
                strategy_name = input('请输入策略名称 (回车默认"手动卖出"): ').strip()
                
                if not strategy_name:
                    strategy_name = '手动卖出'
                
                if shares:
                    try:
                        shares = int(shares)
                        account.sell(code, shares, strategy_name)
                    except ValueError:
                        print('输入无效，请输入数字')
                else:
                    account.sell(code, strategy=strategy_name)
        
        elif choice == '5':
            # 执行买入策略
            shortline_file = 'output/shortline_selection_20260528_062205.csv'
            if os.path.exists(shortline_file):
                stocks_df = pd.read_csv(shortline_file, encoding='utf-8-sig')
                print(f'\n加载短线筛选结果: {len(stocks_df)}只股票')
                strategy.strategy_shortline(stocks_df)
            else:
                print(f'\n未找到短线筛选结果: {shortline_file}')
                print('请先运行 shortline_selection.py')
        
        elif choice == '6':
            # 执行止损策略
            loss_rate = input('请输入止损比例 (默认-3): ').strip()
            try:
                loss_rate = float(loss_rate) if loss_rate else -3
                strategy.strategy_sell_stop_loss(loss_rate)
            except ValueError:
                print('输入无效')
        
        elif choice == '7':
            # 执行止盈策略
            profit_rate = input('请输入止盈比例 (默认10): ').strip()
            try:
                profit_rate = float(profit_rate) if profit_rate else 10
                strategy.strategy_sell_take_profit(profit_rate)
            except ValueError:
                print('输入无效')
        
        elif choice == '8':
            # 查看交易记录
            limit = input('显示最近几条记录 (默认10): ').strip()
            try:
                limit = int(limit) if limit else 10
                account.show_trades(limit)
            except ValueError:
                print('输入无效')
        
        elif choice == '9':
            # 重新初始化
            confirm = input('确认要重新初始化账户吗？(yes/no): ').strip().lower()
            if confirm == 'yes':
                account_file = f'output/trading_accounts/test_account.json'
                if os.path.exists(account_file):
                    os.remove(account_file)
                account = SimulatedTradingAccount(initial_capital=1000000, account_name='test_account')
                strategy = TradingStrategy(account)
                print('账户已重新初始化')
            else:
                print('已取消')
        
        else:
            print('\n无效选择，请重新输入')
        
        input('\n按回车键继续...')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n程序已退出')
    except Exception as e:
        print(f'\n发生错误: {e}')
