#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟实时交易演示系统

使用数据库中的最新数据模拟实时行情

功能：
1. 模拟实时行情推送
2. 实时监控持仓
3. 自动止盈止损
4. 策略交易

作者: Hermes
日期: 2026/5/28
"""

import pymysql
import pandas as pd
import time
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, 'E:/量化研究/workspace/stock')
from simulated_trading import SimulatedTradingAccount

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}

class MockRealtimeTrader:
    """模拟实时交易系统"""
    
    def __init__(self, account_name='test_account'):
        """初始化"""
        self.account = SimulatedTradingAccount(initial_capital=1000000, account_name=account_name)
        self.db_conn = pymysql.connect(**DB_CONFIG)
        
        print('=' * 80)
        print('模拟实时交易系统')
        print('=' * 80)
        print('\n系统说明:')
        print('- 使用数据库最新数据模拟实时行情')
        print('- 支持实时监控、止盈止损、策略交易')
        print('- 所有交易为模拟交易，仅供学习测试')
        print()
        
        self.account.show_account()
    
    def get_latest_quotes(self, codes=None):
        """
        获取最新行情（从数据库）
        
        参数:
            codes: 股票代码列表，None表示全部
        """
        try:
            if codes:
                codes_str = "','".join(codes)
                sql = f"""
                SELECT code, name, new_price, change_rate, turnoverrate, 
                       volume_ratio, deal_amount, amplitude, pe
                FROM cn_stock_spot
                WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
                AND code IN ('{codes_str}')
                """
            else:
                sql = """
                SELECT code, name, new_price, change_rate, turnoverrate, 
                       volume_ratio, deal_amount, amplitude, pe
                FROM cn_stock_spot
                WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
                """
            
            df = pd.read_sql(sql, self.db_conn)
            return df
        except Exception as e:
            print(f'获取行情失败: {e}')
            return pd.DataFrame()
    
    def update_positions(self):
        """更新持仓价格"""
        if not self.account.positions:
            return
        
        codes = list(self.account.positions.keys())
        quotes = self.get_latest_quotes(codes)
        
        if quotes.empty:
            return
        
        for _, row in quotes.iterrows():
            code = row['code']
            if code in self.account.positions:
                old_price = self.account.positions[code]['current_price']
                new_price = float(row['new_price'])
                
                # 模拟价格波动
                import random
                fluctuation = random.uniform(-0.02, 0.02)  # ±2%波动
                new_price = new_price * (1 + fluctuation)
                
                self.account.positions[code]['current_price'] = round(new_price, 2)
        
        self.account.save_account()
    
    def monitor_positions(self, duration=60, interval=5):
        """
        实时监控持仓
        
        参数:
            duration: 监控时长（秒）
            interval: 刷新间隔（秒）
        """
        if not self.account.positions:
            print('当前无持仓')
            return
        
        print(f'\n开始监控持仓 (时长{duration}秒, 每{interval}秒刷新)')
        print('按 Ctrl+C 提前停止\n')
        
        start_time = time.time()
        iteration = 0
        
        try:
            while time.time() - start_time < duration:
                iteration += 1
                
                print('\n' + '=' * 80)
                print(f'实时持仓监控 #{iteration} - {datetime.now().strftime("%H:%M:%S")}')
                print('=' * 80)
                
                # 更新价格
                self.update_positions()
                
                # 显示持仓
                total_profit = 0
                total_value = 0
                
                for code, pos in self.account.positions.items():
                    current_price = pos['current_price']
                    cost_price = pos['cost_price']
                    shares = pos['shares']
                    
                    profit = (current_price - cost_price) * shares
                    profit_rate = (current_price - cost_price) / cost_price * 100
                    current_value = current_price * shares
                    
                    total_profit += profit
                    total_value += current_value
                    
                    # 显示
                    print(f'\n{pos["name"]}({code})')
                    print(f'  持仓: {shares}股')
                    print(f'  成本: {cost_price}元 → 现价: {current_price}元')
                    print(f'  市值: {current_value:.2f}元')
                    if profit >= 0:
                        print(f'  盈亏: +{profit:.2f}元 (+{profit_rate:.2f}%)')
                    else:
                        print(f'  盈亏: {profit:.2f}元 ({profit_rate:.2f}%)')
                
                # 账户总览
                print('\n' + '-' * 80)
                account_value = self.account.cash + total_value
                print(f'持仓市值: {total_value:.2f}元')
                print(f'可用现金: {self.account.cash:.2f}元')
                print(f'总资产: {account_value:.2f}元')
                print(f'持仓盈亏: {total_profit:.2f}元')
                
                # 检查止盈止损
                self.check_stop_loss_profit()
                
                # 如果已平仓，停止监控
                if not self.account.positions:
                    print('\n所有持仓已平仓')
                    break
                
                remaining = int(duration - (time.time() - start_time))
                if remaining > 0:
                    print(f'\n剩余监控时间: {remaining}秒...')
                    time.sleep(interval)
                
        except KeyboardInterrupt:
            print('\n\n监控已停止')
    
    def check_stop_loss_profit(self, stop_loss=-3, take_profit=10):
        """检查止盈止损"""
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
    
    def scan_opportunities(self, limit=20):
        """扫描交易机会"""
        print('\n扫描交易机会...')
        
        # 获取涨幅TOP
        sql = """
        SELECT code, name, new_price, change_rate, turnoverrate, deal_amount, pe
        FROM cn_stock_spot
        WHERE date = (SELECT MAX(date) FROM cn_stock_spot)
        AND change_rate BETWEEN 2 AND 10
        AND turnoverrate BETWEEN 1 AND 20
        AND deal_amount > 100000000
        AND name NOT LIKE '%ST%'
        AND name NOT LIKE '%退%'
        ORDER BY change_rate DESC
        LIMIT 50
        """
        
        df = pd.read_sql(sql, self.db_conn)
        
        if df.empty:
            print('没有找到符合条件的股票')
            return df
        
        print(f'\n找到 {len(df)} 只符合条件的股票\n')
        print(f'TOP{min(limit, len(df))}:')
        print('-' * 80)
        
        for i, row in df.head(limit).iterrows():
            pe_str = f'{row["pe"]:.2f}' if pd.notna(row["pe"]) else 'N/A'
            print(f'{row["name"]}({row["code"]}): {row["change_rate"]:+.2f}%, '
                  f'换手率: {row["turnoverrate"]:.2f}%, '
                  f'成交额: {row["deal_amount"]/100000000:.2f}亿, '
                  f'PE: {pe_str}')
        
        return df
    
    def strategy_buy_top_gainers(self, top_n=3, amount_per_stock=100000):
        """
        策略：买入涨幅TOP股票
        
        参数:
            top_n: 买入前N只
            amount_per_stock: 每只股票投入金额
        """
        print(f'\n执行策略: 买入涨幅TOP{top_n}')
        print('=' * 80)
        
        opportunities = self.scan_opportunities(limit=top_n)
        
        if opportunities.empty:
            return
        
        for _, row in opportunities.head(top_n).iterrows():
            code = row['code']
            name = row['name']
            price = row['new_price']
            
            # 计算股数
            shares = int(amount_per_stock / price / 100) * 100
            
            if shares >= 100:
                print(f'\n准备买入: {name}({code})')
                print(f'  价格: {price}元, 数量: {shares}股')
                self.account.buy(code, name, shares, '涨幅TOP策略')
    
    def demo_auto_trading(self):
        """演示自动交易"""
        print('\n' + '=' * 80)
        print('自动交易演示')
        print('=' * 80)
        
        print('\n步骤1: 扫描交易机会')
        opportunities = self.scan_opportunities(limit=5)
        
        if opportunities.empty:
            print('没有找到机会')
            return
        
        print('\n步骤2: 买入TOP3股票')
        self.strategy_buy_top_gainers(top_n=3, amount_per_stock=100000)
        
        print('\n步骤3: 显示持仓')
        self.account.show_positions()
        
        print('\n步骤4: 模拟价格波动并监控')
        print('模拟3次价格更新...')
        
        for i in range(3):
            print(f'\n--- 第{i+1}次更新 ---')
            self.update_positions()
            
            # 显示持仓盈亏
            for code, pos in self.account.positions.items():
                profit_rate = (pos['current_price'] - pos['cost_price']) / pos['cost_price'] * 100
                print(f'{pos["name"]}: {profit_rate:+.2f}%')
            
            time.sleep(2)
        
        print('\n步骤5: 执行止盈止损检查')
        self.check_stop_loss_profit()
        
        print('\n步骤6: 显示最终结果')
        self.account.show_account()
        self.account.show_positions()
        self.account.show_trades()


def main():
    """主函数"""
    trader = MockRealtimeTrader(account_name='demo_account')
    
    while True:
        print('\n' + '=' * 80)
        print('模拟实时交易菜单')
        print('=' * 80)
        print('1. 查看账户')
        print('2. 查看持仓')
        print('3. 扫描机会')
        print('4. 买入股票')
        print('5. 卖出股票')
        print('6. 实时监控')
        print('7. 策略买入')
        print('8. 自动交易演示')
        print('9. 查看交易记录')
        print('0. 退出')
        print()
        
        choice = input('请选择 (0-9): ').strip()
        
        if choice == '0':
            print('\n再见！')
            break
        
        elif choice == '1':
            trader.account.show_account()
        
        elif choice == '2':
            trader.update_positions()
            trader.account.show_positions()
        
        elif choice == '3':
            limit = input('显示数量 (默认20): ').strip()
            limit = int(limit) if limit else 20
            trader.scan_opportunities(limit)
        
        elif choice == '4':
            code = input('股票代码: ').strip()
            name = input('股票名称: ').strip()
            shares = input('买入股数: ').strip()
            try:
                shares = int(shares)
                trader.account.buy(code, name, shares, '手动买入')
            except:
                print('输入无效')
        
        elif choice == '5':
            code = input('股票代码: ').strip()
            shares = input('卖出股数 (回车全部): ').strip()
            shares = int(shares) if shares else None
            trader.account.sell(code, shares, '手动卖出')
        
        elif choice == '6':
            duration = input('监控时长秒数 (默认60): ').strip()
            duration = int(duration) if duration else 60
            interval = input('刷新间隔秒数 (默认5): ').strip()
            interval = int(interval) if interval else 5
            trader.monitor_positions(duration, interval)
        
        elif choice == '7':
            top_n = input('买入TOP几只 (默认3): ').strip()
            top_n = int(top_n) if top_n else 3
            amount = input('每只投入金额 (默认100000): ').strip()
            amount = float(amount) if amount else 100000
            trader.strategy_buy_top_gainers(top_n, amount)
        
        elif choice == '8':
            trader.demo_auto_trading()
        
        elif choice == '9':
            limit = input('显示条数 (默认10): ').strip()
            limit = int(limit) if limit else 10
            trader.account.show_trades(limit)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n已退出')
    except Exception as e:
        print(f'\n错误: {e}')
