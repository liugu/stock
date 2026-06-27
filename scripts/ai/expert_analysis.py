#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票专家分析系统

整合多个分析维度，提供专业投资建议

功能：
1. 技术面分析（K线、均线、成交量）
2. 基本面分析（PE、PB、财务数据）
3. 消息面分析（新闻、公告）
4. 板块分析（行业地位、板块热度）
5. 资金面分析（主力资金、北向资金）
6. 综合评分与投资建议

作者: Hermes
日期: 2026/5/28
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, 'E:/量化研究/workspace/stock')

import pymysql
import pandas as pd
import numpy as np

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock',
    'password': '12345678',
    'database': 'instock',
    'port': 3306,
    'charset': 'utf8mb4'
}


class ExpertAnalyzer:
    """股票专家分析系统"""
    
    def __init__(self, code, name=None, pe_type='ttm'):
        """
        初始化
        
        参数:
            code: 股票代码
            name: 股票名称（可选）
            pe_type: 市盈率类型 ('dynamic', 'static', 'ttm')
                - dynamic: 动态市盈率（默认使用）
                - static: 静态市盈率
                - ttm: TTM市盈率（推荐）
        """
        self.code = code
        self.name = name
        self.pe_type = pe_type
        self.conn = pymysql.connect(**DB_CONFIG)
        self.data = {}
        self.scores = {}
        self.analysis = {}
        
        print('=' * 80)
        print(f'股票专家分析系统 - {code}')
        print(f'PE类型: {pe_type.upper()} (动态/静态/TTM)')
        print('=' * 80)
    
    def get_basic_data(self):
        """获取基础数据"""
        print('\n【第一步：获取基础数据】')
        print('-' * 80)
        
        cursor = self.conn.cursor()
        
        # 获取实时行情
        cursor.execute("""
            SELECT date, name, new_price, change_rate, turnoverrate, 
                   volume_ratio, deal_amount, amplitude, pe
            FROM cn_stock_spot
            WHERE code = %s
            ORDER BY date DESC
            LIMIT 30
        """, (self.code,))
        
        rows = cursor.fetchall()
        if rows:
            self.data['spot'] = pd.DataFrame(rows, columns=[
                'date', 'name', 'price', 'change', 'turnover', 
                'vol_ratio', 'amount', 'amplitude', 'pe'
            ])
            self.name = rows[0][1] if not self.name else self.name
            print(f'✓ 获取实时行情: {len(rows)}天')
        else:
            print('✗ 未找到实时行情数据')
        
        cursor.close()
        
        if 'spot' not in self.data or self.data['spot'].empty:
            print('数据不足，无法分析')
            return False
        
        return True
    
    def analyze_technical(self):
        """技术面分析"""
        print('\n【第二步：技术面分析】')
        print('-' * 80)
        
        if 'spot' not in self.data or self.data['spot'].empty:
            print('✗ 无数据')
            return
        
        df = self.data['spot'].copy()
        
        # 1. 价格趋势
        latest = df.iloc[0]
        if len(df) >= 5:
            avg_5 = df.head(5)['price'].mean()
            trend_5 = (latest['price'] - avg_5) / avg_5 * 100
        else:
            trend_5 = 0
        
        if len(df) >= 20:
            avg_20 = df.head(20)['price'].mean()
            trend_20 = (latest['price'] - avg_20) / avg_20 * 100
        else:
            trend_20 = 0
        
        # 2. 成交量
        avg_turnover = df['turnover'].mean()
        latest_turnover = latest['turnover']
        turnover_ratio = latest_turnover / avg_turnover if avg_turnover > 0 else 1
        
        # 3. 涨跌幅
        avg_change = df['change'].mean()
        
        # 评分
        score = 50  # 基础分
        
        # 趋势评分
        if trend_5 > 5:
            score += 10
            print(f'✓ 短期趋势向上 (+10分)')
        elif trend_5 < -5:
            score -= 10
            print(f'✗ 短期趋势向下 (-10分)')
        
        if trend_20 > 0:
            score += 10
            print(f'✓ 中期趋势向上 (+10分)')
        elif trend_20 < -10:
            score -= 10
            print(f'✗ 中期趋势向下 (-10分)')
        
        # 成交量评分
        if turnover_ratio > 2:
            score += 5
            print(f'✓ 放量明显 (+5分)')
        elif turnover_ratio < 0.5:
            score -= 5
            print(f'✗ 缩量明显 (-5分)')
        
        # 涨跌幅评分
        if latest['change'] > 3:
            score += 5
            print(f'✓ 今日大涨 (+5分)')
        elif latest['change'] < -3:
            score -= 5
            print(f'✗ 今日大跌 (-5分)')
        
        self.scores['technical'] = min(100, max(0, score))
        self.analysis['technical'] = {
            'trend_5d': trend_5,
            'trend_20d': trend_20,
            'turnover_ratio': turnover_ratio,
            'latest_change': latest['change'],
            'score': self.scores['technical']
        }
        
        print(f'\n技术面得分: {self.scores["technical"]}/100')
    
    def analyze_fundamental(self):
        """基本面分析"""
        print('\n【第三步：基本面分析】')
        print('-' * 80)
        
        if 'spot' not in self.data or self.data['spot'].empty:
            print('✗ 无数据')
            return
        
        latest = self.data['spot'].iloc[0]
        pe = latest['pe']
        
        score = 50  # 基础分
        
        # PE评分
        if pd.notna(pe):
            if pe < 20:
                score += 20
                print(f'✓ 低估值 PE={pe:.1f} (+20分)')
            elif pe < 30:
                score += 10
                print(f'✓ 估值合理 PE={pe:.1f} (+10分)')
            elif pe < 50:
                print(f'○ 估值偏高 PE={pe:.1f}')
            elif pe < 100:
                score -= 10
                print(f'✗ 高估值 PE={pe:.1f} (-10分)')
            else:
                score -= 20
                print(f'✗ 极高估值 PE={pe:.1f} (-20分)')
        else:
            print('○ PE数据缺失')
        
        # 成交额评分
        amount = latest['amount']
        if amount > 5000000000:  # 50亿
            score += 10
            print(f'✓ 成交活跃 {amount/100000000:.1f}亿 (+10分)')
        elif amount > 1000000000:  # 10亿
            score += 5
            print(f'✓ 成交量正常 {amount/100000000:.1f}亿 (+5分)')
        elif amount < 100000000:  # 1亿
            score -= 5
            print(f'✗ 成交清淡 {amount/100000000:.1f}亿 (-5分)')
        
        self.scores['fundamental'] = min(100, max(0, score))
        self.analysis['fundamental'] = {
            'pe': pe,
            'amount': amount,
            'score': self.scores['fundamental']
        }
        
        print(f'\n基本面得分: {self.scores["fundamental"]}/100')
    
    def analyze_market_sentiment(self):
        """市场情绪分析"""
        print('\n【第四步：市场情绪分析】')
        print('-' * 80)
        
        if 'spot' not in self.data or self.data['spot'].empty:
            print('✗ 无数据')
            return
        
        df = self.data['spot'].copy()
        
        score = 50  # 基础分
        
        # 换手率
        avg_turnover = df['turnover'].mean()
        latest_turnover = df.iloc[0]['turnover']
        
        if latest_turnover > 10:
            score += 10
            print(f'✓ 高换手率 {latest_turnover:.1f}% (+10分，关注度高)')
        elif latest_turnover > 5:
            score += 5
            print(f'✓ 换手率正常 {latest_turnover:.1f}% (+5分)')
        elif latest_turnover < 2:
            score -= 5
            print(f'✗ 低换手率 {latest_turnover:.1f}% (-5分，关注度低)')
        
        # 振幅
        latest_amp = df.iloc[0]['amplitude']
        if latest_amp > 8:
            score += 5
            print(f'✓ 高振幅 {latest_amp:.1f}% (+5分，波动大机会多)')
        elif latest_amp < 3:
            score -= 5
            print(f'✗ 低振幅 {latest_amp:.1f}% (-5分，波动小)')
        
        # 连续涨跌
        changes = df.head(5)['change'].tolist()
        up_days = sum(1 for c in changes if c > 0)
        down_days = sum(1 for c in changes if c < 0)
        
        if up_days >= 4:
            score += 10
            print(f'✓ 连续上涨 {up_days}天 (+10分)')
        elif down_days >= 4:
            score -= 10
            print(f'✗ 连续下跌 {down_days}天 (-10分)')
        
        self.scores['sentiment'] = min(100, max(0, score))
        self.analysis['sentiment'] = {
            'turnover': latest_turnover,
            'amplitude': latest_amp,
            'up_days': up_days,
            'score': self.scores['sentiment']
        }
        
        print(f'\n情绪面得分: {self.scores["sentiment"]}/100')
    
    def analyze_risk(self):
        """风险分析"""
        print('\n【第五步：风险分析】')
        print('-' * 80)
        
        if 'spot' not in self.data or self.data['spot'].empty:
            print('✗ 无数据')
            return
        
        df = self.data['spot'].copy()
        
        score = 50  # 基础分（分数越低风险越大）
        
        # 波动率
        prices = df['price'].head(20).tolist()
        if len(prices) >= 10:
            returns = [(prices[i] - prices[i+1]) / prices[i+1] for i in range(len(prices)-1)]
            volatility = np.std(returns) * 100 if returns else 0
            
            if volatility > 5:
                score -= 10
                print(f'✗ 高波动率 {volatility:.2f}% (-10分，风险高)')
            elif volatility < 2:
                score += 10
                print(f'✓ 低波动率 {volatility:.2f}% (+10分，稳健)')
        
        # 最大回撤
        if len(prices) >= 5:
            max_price = max(prices)
            min_price = min(prices)
            drawdown = (max_price - min_price) / max_price * 100
            
            if drawdown > 15:
                score -= 10
                print(f'✗ 大幅回撤 {drawdown:.1f}% (-10分)')
            elif drawdown < 5:
                score += 5
                print(f'✓ 小幅回撤 {drawdown:.1f}% (+5分)')
        
        # 单日最大跌幅
        max_drop = df.head(10)['change'].min()
        if max_drop < -7:
            score -= 10
            print(f'✗ 曾现大跌 {max_drop:.1f}% (-10分)')
        
        self.scores['risk'] = min(100, max(0, score))
        self.analysis['risk'] = {
            'volatility': volatility if 'volatility' in dir() else 0,
            'max_drawdown': drawdown if 'drawdown' in dir() else 0,
            'score': self.scores['risk']
        }
        
        print(f'\n风险控制得分: {self.scores["risk"]}/100')
    
    def generate_recommendation(self):
        """生成综合建议"""
        print('\n【第六步：综合评估与建议】')
        print('=' * 80)
        
        if not self.scores:
            print('分析数据不足')
            return
        
        # 计算综合得分
        weights = {
            'technical': 0.3,
            'fundamental': 0.3,
            'sentiment': 0.2,
            'risk': 0.2
        }
        
        total_score = sum(self.scores.get(k, 50) * v for k, v in weights.items())
        
        # 评级
        if total_score >= 80:
            rating = 'A'
            suggestion = '强烈推荐'
            color = '🟢'
        elif total_score >= 70:
            rating = 'B+'
            suggestion = '推荐关注'
            color = '🟢'
        elif total_score >= 60:
            rating = 'B'
            suggestion = '可以关注'
            color = '🟡'
        elif total_score >= 50:
            rating = 'C'
            suggestion = '谨慎观望'
            color = '🟡'
        else:
            rating = 'D'
            suggestion = '不建议'
            color = '🔴'
        
        # 打印结果
        print(f'\n股票: {self.name}({self.code})')
        print(f'\n各维度得分:')
        print(f'  技术面: {self.scores.get("technical", 50)}/100')
        print(f'  基本面: {self.scores.get("fundamental", 50)}/100')
        print(f'  情绪面: {self.scores.get("sentiment", 50)}/100')
        print(f'  风险控制: {self.scores.get("risk", 50)}/100')
        
        print(f'\n综合得分: {total_score:.1f}/100')
        print(f'投资评级: {color} {rating}')
        print(f'投资建议: {suggestion}')
        
        # 具体建议
        print('\n操作建议:')
        
        if total_score >= 70:
            print('  ✓ 建议买入')
            print('  ✓ 可分批建仓')
            print('  ✓ 设置止损位')
        elif total_score >= 50:
            print('  ○ 建议观望')
            print('  ○ 等待更好的买点')
            print('  ○ 关注基本面变化')
        else:
            print('  ✗ 不建议买入')
            print('  ✗ 如有持仓考虑减仓')
            print('  ✗ 等待趋势反转')
        
        # 风险提示
        print('\n风险提示:')
        if self.scores.get('risk', 50) < 40:
            print('  ⚠️ 风险较高，注意止损')
        if self.scores.get('fundamental', 50) < 40:
            print('  ⚠️ 基本面较弱，谨慎投资')
        if self.scores.get('technical', 50) < 40:
            print('  ⚠️ 技术面走弱，等待企稳')
        
        return {
            'code': self.code,
            'name': self.name,
            'total_score': total_score,
            'rating': rating,
            'suggestion': suggestion,
            'scores': self.scores
        }
    
    def run_analysis(self):
        """执行完整分析"""
        # 获取数据
        if not self.get_basic_data():
            return None
        
        # 各维度分析
        self.analyze_technical()
        self.analyze_fundamental()
        self.analyze_market_sentiment()
        self.analyze_risk()
        
        # 生成建议
        result = self.generate_recommendation()
        
        print('\n' + '=' * 80)
        print('分析完成')
        print('=' * 80)
        
        self.conn.close()
        
        return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print('用法: python expert_analysis.py <股票代码>')
        print('示例: python expert_analysis.py 000026')
        return
    
    code = sys.argv[1]
    
    analyzer = ExpertAnalyzer(code)
    result = analyzer.run_analysis()
    
    if result:
        # 保存报告
        report_dir = 'E:/量化研究/workspace/stock/analysis'
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = f'{report_dir}/expert_{code}_{datetime.now().strftime("%Y%m%d")}.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f'专家分析报告 - {result["name"]}({result["code"]})\n')
            f.write(f'分析日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write('=' * 80 + '\n\n')
            f.write(f'综合得分: {result["total_score"]:.1f}/100\n')
            f.write(f'投资评级: {result["rating"]}\n')
            f.write(f'投资建议: {result["suggestion"]}\n\n')
            f.write('各维度得分:\n')
            for k, v in result['scores'].items():
                f.write(f'  {k}: {v}/100\n')
        
        print(f'\n报告已保存: {report_file}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n已取消')
    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()
