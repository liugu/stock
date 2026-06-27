# AI增强量化选股系统

## 模块概述

本系统整合了多种量化工具，提供完整的选股、回测、因子挖掘功能。

## 文件结构

```
stock/
├── ai_factor_mining.py      # AI因子挖掘模块
├── ai_stock_selection.py    # AI增强选股模块
├── quant_workflow.py        # 完整选股流程
├── backtest_professional.py # Backtrader回测模块
└── docs/
    └── tool_integration_plan.md  # 工具集成方案
```

---

## 1. AI因子挖掘模块 (`ai_factor_mining.py`)

### 功能
- 计算23个技术因子
- 计算52个机器学习特征
- 因子IC值评估
- Qlib因子接口（需安装pyqlib）

### 使用示例

```python
from ai_factor_mining import calculate_technical_factors, calculate_ml_features

# 计算技术因子
df_with_factors = calculate_technical_factors(stock_data)

# 计算ML特征
df_with_ml = calculate_ml_features(stock_data)

# 查看因子列表
print(df_with_ml.columns.tolist())
```

### 因子列表

**技术因子 (23个)**
- 收益率: return_1d, return_5d, return_10d, return_20d
- 均线: ma5, ma10, ma20, ma60, ma5_ma20, price_ma20
- 波动: volatility_10d, volatility_20d
- 量能: volume_ma5, volume_ma20, volume_ratio
- 动量: momentum_5d, momentum_10d, momentum_20d
- 位置: high_20d, low_20d, price_position
- 振幅: amplitude, amplitude_ma5

**ML特征 (52个)**
- 滞后特征: close_lag1-10, volume_lag1-10, return_lag1-10
- 滚动统计: return_mean/std/skew_5/10/20, volume_mean_5/10/20
- 交互特征: price_volume_corr, return_volume_corr

---

## 2. AI增强选股模块 (`ai_stock_selection.py`)

### 功能
- 综合评分系统（满分100分）
- 6大因子维度评分
- 自动筛选高评分股票

### 评分体系

| 因子 | 满分 | 评分标准 |
|------|------|----------|
| 动量 | 20 | 10日涨幅 >10%: 20分, >5%: 15分, >0%: 10分 |
| 趋势 | 20 | 均线多头排列: 最高20分 |
| 量能 | 15 | 量比 >2: 15分, >1.5: 12分, >1: 8分 |
| 位置 | 15 | 接近20日高点: 最高15分 |
| 波动 | 10 | 适中波动(2-4%): 10分 |
| 突破 | 20 | 接近/突破20日高点: 最高20分 |

### 使用示例

```python
from ai_stock_selection import run_stock_selection, format_results

# 执行选股
results = run_stock_selection(limit=100, top_n=10)

# 格式化输出
print(format_results(results))
```

### 输出示例

```
【1. 模拟股票3】(600003)
  价格: 12.35元, 涨幅: +2.5%, 换手率: 3.5%
  综合评分: 73/100
  因子详情:
    动量: 20/20
    趋势: 15/20
    量能: 8/15
    位置: 15/15
    波动: 5/10
    突破: 10/20
```

---

## 3. 完整选股流程 (`quant_workflow.py`)

### 功能
- 数据获取（akshare）
- 三种策略并行筛选
- 综合评分排序

### 策略说明

1. **突破策略**: 价格突破20日高点 + 放量
2. **均线交叉**: MA5上穿MA20金叉
3. **海龟交易**: 创20日新高信号

### 使用示例

```python
from quant_workflow import screen_stocks

# 执行选股
results = screen_stocks(limit=50)

# 结果处理
for r in results:
    print(f"{r['name']}: 评分 {r['score']}/3")
```

---

## 4. Backtrader回测模块 (`backtest_professional.py`)

### 功能
- 三种策略回测
- 完整绩效指标
- 可视化输出

### 回测指标
- 总收益率
- 年化收益率
- 夏普比率
- 最大回撤
- 胜率
- 交易次数

### 使用示例

```python
from backtest_professional import run_backtest

# 运行回测
result = run_backtest(
    code='000001',
    strategy='ma_cross',  # 或 'breakout', 'turtle'
    start_date='2023-01-01',
    end_date='2024-12-31'
)

print(f"收益率: {result['total_return']:.2%}")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
```

---

## 5. 工具集成方案 (`docs/tool_integration_plan.md`)

### 已集成工具

| 工具 | Star | 用途 | 状态 |
|------|------|------|------|
| Backtrader | 20.5K | 策略回测 | ✓ |
| OpenBB | 62.3K | 宏观数据 | ✓ 已安装 |
| akshare | - | A股数据 | ✓ |
| TA-Lib | - | 技术指标 | ✓ |

### 待集成工具

| 工具 | Star | 用途 | 状态 |
|------|------|------|------|
| Qlib | 37.9K | AI因子挖掘 | 安装中 |
| FinRL | 14.1K | 强化学习 | 待定 |

---

## 快速开始

### 1. 环境准备

```bash
cd E:/量化研究/workspace/stock
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
pip install openbb pyqlib  # 可选
```

### 2. 运行选股

```python
# 简单选股
from ai_stock_selection import run_stock_selection
results = run_stock_selection(limit=50, top_n=10)

# 完整流程
from quant_workflow import screen_stocks
results = screen_stocks(limit=100)
```

### 3. 运行回测

```python
from backtest_professional import run_backtest
result = run_backtest('000001', 'ma_cross')
```

---

## 注意事项

1. **数据源**: 优先使用数据库数据，akshare作为备选
2. **网络限制**: akshare可能被限流，建议使用本地数据库
3. **因子计算**: 需要至少60日历史数据
4. **评分阈值**: 默认40分入选，可根据需要调整

---

## 更新日志

### 2026-05-27
- ✓ 创建 AI因子挖掘模块
- ✓ 创建 AI增强选股模块
- ✓ 完善评分系统
- ✓ 模拟数据测试通过
- ⏳ Qlib 安装中
