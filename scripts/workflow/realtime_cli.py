#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时交易命令行工具

用法:
    python realtime_cli.py scan                    # 扫描机会
    python realtime_cli.py monitor [duration]      # 监控持仓
    python realtime_cli.py buy <code> <amount>     # 买入
    python realtime_cli.py sell <code> [shares]    # 卖出
    python realtime_cli.py account                 # 查看账户
    python realtime_cli.py positions               # 查看持仓
    python realtime_cli.py trades [limit]          # 交易记录
    python realtime_cli.py auto                    # 自动交易演示

作者: Hermes
日期: 2026/5/28
"""

import sys
import os
sys.path.insert(0, 'E:/量化研究/workspace/stock')

from demo_realtime_trading import MockRealtimeTrader

def print_usage():
    """打印使用说明"""
    print('''
================================================================================
实时交易命令行工具
================================================================================

用法:
    python realtime_cli.py scan                    # 扫描交易机会
    python realtime_cli.py monitor [duration]      # 监控持仓(秒)
    python realtime_cli.py buy <code> <amount>     # 买入股票
    python realtime_cli.py sell <code> [shares]    # 卖出股票
    python realtime_cli.py account                 # 查看账户
    python realtime_cli.py positions               # 查看持仓
    python realtime_cli.py trades [limit]          # 交易记录
    python realtime_cli.py auto                    # 自动交易演示
    python realtime_cli.py strategy [top_n]        # 策略买入TOP N

示例:
    python realtime_cli.py scan                    # 扫描机会
    python realtime_cli.py monitor 300            # 监控5分钟
    python realtime_cli.py buy 603533 100000      # 买入10万元
    python realtime_cli.py sell 603533            # 全部卖出
    python realtime_cli.py strategy 5             # 买入TOP5

================================================================================
''')


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    trader = MockRealtimeTrader(account_name='realtime_account')
    
    if command == 'scan':
        # 扫描机会
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        trader.scan_opportunities(limit)
    
    elif command == 'monitor':
        # 监控持仓
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        trader.monitor_positions(duration, interval)
    
    elif command == 'buy':
        # 买入
        if len(sys.argv) < 4:
            print('用法: python realtime_cli.py buy <code> <amount>')
            return
        
        code = sys.argv[2]
        amount = float(sys.argv[3])
        
        # 获取股票信息
        quotes = trader.get_latest_quotes([code])
        if quotes.empty:
            print(f'未找到股票 {code}')
            return
        
        row = quotes.iloc[0]
        name = row['name']
        price = row['new_price']
        shares = int(amount / price / 100) * 100
        
        if shares < 100:
            print(f'金额不足，至少需要 {price * 100:.2f}元')
            return
        
        trader.account.buy(code, name, shares, '命令行买入')
    
    elif command == 'sell':
        # 卖出
        if len(sys.argv) < 3:
            print('用法: python realtime_cli.py sell <code> [shares]')
            return
        
        code = sys.argv[2]
        shares = int(sys.argv[3]) if len(sys.argv) > 3 else None
        trader.account.sell(code, shares, '命令行卖出')
    
    elif command == 'account':
        # 查看账户
        trader.account.show_account()
    
    elif command == 'positions':
        # 查看持仓
        trader.update_positions()
        trader.account.show_positions()
    
    elif command == 'trades':
        # 交易记录
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        trader.account.show_trades(limit)
    
    elif command == 'auto':
        # 自动交易演示
        trader.demo_auto_trading()
    
    elif command == 'strategy':
        # 策略买入
        top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 100000
        trader.strategy_buy_top_gainers(top_n, amount)
    
    elif command in ['help', '-h', '--help']:
        print_usage()
    
    else:
        print(f'未知命令: {command}')
        print_usage()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n已退出')
    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()
