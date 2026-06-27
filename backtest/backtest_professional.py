#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Backtrader 专业回测示例
对今日推荐股票进行策略回测验证
"""

import backtrader as bt
import pymysql
import pandas as pd
from datetime import datetime

# 自定义数据源 - 从MySQL加载
class MySQLData(bt.feeds.PandasData):
    """从MySQL加载A股数据"""
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )


def load_stock_data(code, start_date='2025-01-01'):
    """从数据库加载股票数据"""
    conn = pymysql.connect(
        host='localhost', user='stock', password='12345678',
        database='instock', charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # 获取stock_id
    cursor.execute('SELECT id FROM stock_info WHERE code = %s', (code,))
    result = cursor.fetchone()
    if not result:
        return None
    stock_id = result[0]
    
    # 获取数据
    cursor.execute('''
        SELECT date, open, close, high, low, volume
        FROM stock_daily
        WHERE stock_id = %s AND date >= %s
        ORDER BY date
    ''', (stock_id, start_date))
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 30:
        return None
    
    df = pd.DataFrame(rows, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 转换Decimal为float
    for col in ['open', 'close', 'high', 'low', 'volume']:
        df[col] = df[col].astype(float)
    
    return df


# ============== 策略定义 ==============

class MAStrategy(bt.Strategy):
    """均线交叉策略"""
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('printlog', True),
    )
    
    def __init__(self):
        self.ma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.ma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)
        
        self.order = None
        self.buy_price = None
        self.buy_comm = None
    
    def next(self):
        if self.order:
            return
        
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
                if self.params.printlog:
                    self.log(f'买入信号, 价格: {self.data.close[0]:.2f}')
        else:
            if self.crossover < 0:
                self.order = self.sell()
                if self.params.printlog:
                    self.log(f'卖出信号, 价格: {self.data.close[0]:.2f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'[{dt.isoformat()}] {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            self.order = None


class BreakoutStrategy(bt.Strategy):
    """突破策略 - 突破N日高点买入"""
    params = (
        ('period', 20),
        ('printlog', True),
    )
    
    def __init__(self):
        self.high = bt.indicators.Highest(self.data.high, period=self.params.period)
        self.order = None
    
    def next(self):
        if self.order:
            return
        
        if not self.position:
            if self.data.close[0] > self.high[-1]:
                self.order = self.buy()
                if self.params.printlog:
                    self.log(f'突破买入, 价格: {self.data.close[0]:.2f}, 高点: {self.high[-1]:.2f}')
        else:
            # 跌破低点止损
            if self.data.close[0] < self.data.close[-5]:
                self.order = self.sell()
                if self.params.printlog:
                    self.log(f'止损卖出, 价格: {self.data.close[0]:.2f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'[{dt.isoformat()}] {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None


class TurtleStrategy(bt.Strategy):
    """海龟交易策略"""
    params = (
        ('entry_period', 20),
        ('exit_period', 10),
        ('printlog', True),
    )
    
    def __init__(self):
        self.entry_high = bt.indicators.Highest(self.data.high, period=self.params.entry_period)
        self.exit_low = bt.indicators.Lowest(self.data.low, period=self.params.exit_period)
        self.order = None
    
    def next(self):
        if self.order:
            return
        
        if not self.position:
            if self.data.close[0] > self.entry_high[-1]:
                self.order = self.buy()
                if self.params.printlog:
                    self.log(f'海龟买入, 价格: {self.data.close[0]:.2f}')
        else:
            if self.data.close[0] < self.exit_low[-1]:
                self.order = self.sell()
                if self.params.printlog:
                    self.log(f'海龟卖出, 价格: {self.data.close[0]:.2f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'[{dt.isoformat()}] {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None


def run_backtest(strategy_class, data, name, cash=100000):
    """运行回测"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)
    
    # 添加数据
    data_feed = MySQLData(dataname=data)
    cerebro.adddata(data_feed)
    
    # 设置资金
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=0.0003)  # 万三手续费
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print(f'\n{"="*60}')
    print(f'策略: {name}')
    print(f'初始资金: {cash:,.0f}')
    print(f'{"="*60}')
    
    results = cerebro.run()
    strat = results[0]
    
    # 获取分析结果
    final_value = cerebro.broker.getvalue()
    pnl = final_value - cash
    pnl_pct = (pnl / cash) * 100
    
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    print(f'\n回测结果:')
    print(f'  最终资金: {final_value:,.2f}')
    print(f'  净利润: {pnl:,.2f} ({pnl_pct:.2f}%)')
    print(f'  夏普比率: {sharpe.get("sharperatio", "N/A")}')
    print(f'  最大回撤: {drawdown.get("max", {}).get("drawdown", "N/A")}%')
    print(f'  总交易次数: {trades.get("total", {}).get("total", 0)}')
    if trades.get("total", {}).get("total", 0) > 0:
        won = trades.get("won", {}).get("total", 0)
        total = trades.get("total", {}).get("total", 1)
        print(f'  胜率: {won/total*100:.1f}%')
    
    return {
        'name': name,
        'final_value': final_value,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'sharpe': sharpe.get('sharperatio'),
        'max_drawdown': drawdown.get('max', {}).get('drawdown'),
        'trades': trades.get('total', {}).get('total', 0),
    }


def main():
    print("="*60)
    print("📊 Backtrader 专业回测验证")
    print("="*60)
    
    # 今日推荐股票
    stocks = [
        ('600969', '郴电国际'),
        ('601069', '西部黄金'),
        ('600255', '鑫科材料'),
    ]
    
    # 策略列表
    strategies = [
        (MAStrategy, '均线交叉策略'),
        (BreakoutStrategy, '突破策略'),
        (TurtleStrategy, '海龟交易策略'),
    ]
    
    all_results = []
    
    for code, name in stocks:
        print(f"\n{'#'*60}")
        print(f"# 股票: {name}({code})")
        print(f"{'#'*60}")
        
        # 加载数据
        data = load_stock_data(code, '2025-01-01')
        if data is None or len(data) < 30:
            print(f'  数据不足，跳过')
            continue
        
        print(f'  数据范围: {data.index[0].date()} ~ {data.index[-1].date()}')
        print(f'  数据条数: {len(data)}')
        
        # 运行各策略
        for strategy_class, strategy_name in strategies:
            try:
                result = run_backtest(strategy_class, data, f'{name} - {strategy_name}')
                result['code'] = code
                result['stock'] = name
                all_results.append(result)
            except Exception as e:
                print(f'  回测失败: {e}')
    
    # 汇总结果
    print("\n" + "="*60)
    print("📈 回测结果汇总")
    print("="*60)
    
    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values('pnl_pct', ascending=False)
        
        print(f"\n{'股票':<12} {'策略':<20} {'收益率':>10} {'最大回撤':>10} {'交易次数':>8}")
        print("-"*60)
        for _, row in df.iterrows():
            print(f"{row['stock']:<12} {row['name'].split(' - ')[-1]:<20} {row['pnl_pct']:>10.2f}% {row['max_drawdown']:>10.2f}% {row['trades']:>8}")
        
        print("\n" + "="*60)
        print("🏆 最佳策略组合")
        print("="*60)
        best = df.iloc[0]
        print(f"股票: {best['stock']}({best['code']})")
        print(f"策略: {best['name'].split(' - ')[-1]}")
        print(f"收益率: {best['pnl_pct']:.2f}%")
        print(f"最大回撤: {best['max_drawdown']:.2f}%")


if __name__ == '__main__':
    main()
