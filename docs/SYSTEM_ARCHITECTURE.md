# AI增强量化选股系统架构

## 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                    AI增强量化选股系统                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  数据层                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  AkShare    │  │   OpenBB    │  │   MySQL     │        │
│  │  (A股数据)   │  │ (宏观数据)   │  │ (历史数据)   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┴────────────────┘                │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│  因子层                  ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ai_factor_mining.py                      │  │
│  │  • 技术因子 (23个): 收益率、均线、波动、量能、动量      │  │
│  │  • ML特征 (52个): 滞后、滚动统计、交互特征             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          qlib_akshare_provider.py                     │  │
│  │  • Qlib风格因子 (45个): 位置、波动、均线、量能、RSI    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          instock/core/indicator/                      │  │
│  │  • TA-Lib指标 (32种): MACD, KDJ, BOLL, RSI, ATR...   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│  策略层                  ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         instock/core/strategy/ (18种策略)             │  │
│  │  • 放量上涨 (enter.py)                                │  │
│  │  • 海龟交易 (turtle_trade.py)                         │  │
│  │  • 均线多头 (keep_increasing.py)                       │  │
│  │  • 突破平台 (breakthrough_platform.py)                │  │
│  │  • 创新高 (new_high.py)                               │  │
│  │  • ... 更多策略                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          ai_stock_selection.py                        │  │
│  │  • AI评分系统 (100分制)                               │  │
│  │  • 6维度评分: 动量+趋势+量能+位置+波动+突破           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│  整合层                  ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        ai_integrated_selection.py                     │  │
│  │  • 整合传统策略 + AI因子 + Qlib因子                    │  │
│  │  • 综合评分: AI(40) + Qlib(30) + 策略(30) = 100分    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│  回测层                  ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        backtest_professional.py                       │  │
│  │  • Backtrader回测框架                                 │  │
│  │  • 三种策略: 均线交叉、突破、海龟                      │  │
│  │  • 绩效指标: 收益率、夏普、最大回撤、胜率              │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
├──────────────────────────┼──────────────────────────────────┤
│  输出层                  ▼                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Web服务    │  │  飞书推送   │  │  Excel报告  │        │
│  │  (Tornado)  │  │  (定时任务) │  │  (选股结果) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块详细说明

### 1. 数据层

| 数据源 | 用途 | 状态 |
|--------|------|------|
| **AkShare** | A股实时/历史数据 | ✓ 主要数据源 |
| **OpenBB** | 宏观经济数据、美股、商品 | ✓ 已安装 |
| **MySQL** | 本地历史数据存储 | ✓ 已配置 |
| **Baostock** | 本地数据备选 | ✓ 已集成 |

### 2. 因子层

#### 2.1 技术因子 (ai_factor_mining.py)

```python
# 收益率因子
return_1d, return_5d, return_10d, return_20d

# 均线因子
ma5, ma10, ma20, ma60, ma5_ma20, price_ma20

# 波动因子
volatility_10d, volatility_20d

# 量能因子
volume_ma5, volume_ma20, volume_ratio

# 动量因子
momentum_5d, momentum_10d, momentum_20d

# 位置因子
high_20d, low_20d, price_position

# 振幅因子
amplitude, amplitude_ma5
```

#### 2.2 ML特征 (ai_factor_mining.py)

```python
# 滞后特征
close_lag1~10, volume_lag1~10, return_lag1~10

# 滚动统计
return_mean/std/skew_5/10/20, volume_mean_5/10/20

# 交互特征
price_volume_corr, return_volume_corr
```

#### 2.3 Qlib风格因子 (qlib_akshare_provider.py)

```python
# 收益率因子
return_0, return_1, return_2, return_5d, return_10d, return_20d, return_30d

# 位置因子
high_n, low_n, price_pos_n (n=10,20,30)

# 波动因子
volatility_n, range_n (n=5,10,20)

# 均线因子
ma_n, ma_bias_n, ma_slope_n (n=5,10,20,30,60)

# 量能因子
volume_ratio, volume_ma_n, volume_std_n (n=5,10,20)

# 动量因子
rsi_14

# 交互因子
price_volume_corr_n (n=10,20)
```

#### 2.4 TA-Lib指标 (calculate_indicator.py)

```python
# 趋势指标
MACD, KDJ, BOLL, TRIX, CR, VR, ATR, DMI(ADX/PDI/MDI)

# 震荡指标
RSI(6,12,14,24)

# 能量指标
OBV, VR

# 均线系统
MA5, MA10, MA20, MA30, MA60
```

### 3. 策略层

| 策略名称 | 文件 | 核心逻辑 | 评分权重 |
|----------|------|----------|----------|
| 放量上涨 | enter.py | 涨幅≥2%，量比≥2 | 10分 |
| 海龟交易 | turtle_trade.py | 创N日新高 | 10分 |
| 均线多头 | keep_increasing.py | MA30向上 | 5分 |
| 突破平台 | breakthrough_platform.py | 60日突破 | 10分 |
| 创新高 | new_high.py | 多周期新高 | 10分/周期 |
| 停机坪 | parking_apron.py | 高开窄幅整理 | 5分 |
| 回踩年线 | backtrace_ma250.py | 年线回踩缩量 | 5分 |
| 无大幅回撤 | low_backtrace_increase.py | 60日回撤<40% | 5分 |
| 高而窄旗形 | high_tight_flag.py | 60日涨幅≥90% | 10分 |
| 放量跌停 | climax_limitdown.py | 跌>9.5%，量比≥4 | 5分 |
| 低ATR成长 | low_atr.py | 高低比≥1.1 | 5分 |
| BOLL策略 | boll_strategy.py | 布林带突破 | 5分 |
| KDJ策略 | kdj_strategy.py | KDJ金叉 | 5分 |
| 北向资金 | northbound_flow.py | 北向流入 | 5分 |
| 连续小阳 | consecutive_small_bullish.py | 连续阳线 | 5分 |
| 基本面筛选 | financial_filter.py | PE/PB/ROE | 5分 |

### 4. AI评分系统

#### 4.1 ai_stock_selection.py (100分制)

```
综合评分 = 动量(20) + 趋势(20) + 量能(15) + 位置(15) + 波动(10) + 突破(20)
```

#### 4.2 ai_integrated_selection.py (整合版)

```
综合评分 = AI因子(40) + Qlib因子(30) + 策略信号(30)
```

**AI因子评分 (40分)**:
- 动量因子: 10分
- 趋势因子: 10分
- 量能因子: 10分
- 突破因子: 10分

**Qlib因子评分 (30分)**:
- 收益率因子: 10分
- 波动因子: 10分
- RSI因子: 10分

**策略信号评分 (30分)**:
- 海龟交易信号: 10分
- 放量上涨信号: 10分
- 多周期新高: 10分 (均分)

---

## 使用示例

### 1. 基础选股

```python
from ai_stock_selection import run_stock_selection
results = run_stock_selection(limit=100, top_n=10)
```

### 2. AI整合选股

```python
from ai_integrated_selection import comprehensive_ai_score

# 计算单只股票评分
score, details = comprehensive_ai_score(stock_data)
print(f"综合评分: {score}")
print(f"详情: {details}")
```

### 3. 回测验证

```python
from backtest_professional import run_backtest
result = run_backtest('000001', 'ma_cross', '2023-01-01', '2024-12-31')
```

### 4. 因子计算

```python
from ai_factor_mining import calculate_ml_features
from qlib_akshare_provider import calculate_qlib_style_factors

# 计算ML特征
df_ml = calculate_ml_features(stock_data)

# 计算Qlib因子
df_qlib = calculate_qlib_style_factors(stock_data)
```

---

## 总因子统计

| 因子类别 | 数量 | 来源 |
|----------|------|------|
| 技术因子 | 23 | ai_factor_mining.py |
| ML特征 | 52 | ai_factor_mining.py |
| Qlib风格 | 45 | qlib_akshare_provider.py |
| TA-Lib指标 | 32 | calculate_indicator.py |
| **总计** | **152** | - |

---

## 系统优势

1. **多源数据**: AkShare + OpenBB + MySQL + Baostock
2. **丰富因子**: 152个因子覆盖技术、统计、形态
3. **策略多样**: 18种策略可组合
4. **AI增强**: 机器学习特征 + 深度学习预留
5. **回测验证**: Backtrader专业回测
6. **实时推送**: 飞书/微信/Telegram

---

## 扩展方向

1. **深度学习**: LSTM/Transformer预测模型
2. **强化学习**: FinRL择时优化
3. **因子挖掘**: 自动化因子生成与筛选
4. **组合优化**: 风险模型 + 优化器
5. **实盘对接**: 券商API自动交易

---

## 文件清单

```
stock/
├── ai_factor_mining.py           # AI因子挖掘
├── ai_stock_selection.py         # AI选股评分
├── ai_integrated_selection.py    # 整合选股系统
├── qlib_akshare_provider.py      # Qlib风格因子
├── quant_workflow.py             # 完整选股流程
├── backtest_professional.py      # 回测模块
├── test_qlib.py                  # Qlib测试
├── instock/
│   ├── core/
│   │   ├── strategy/             # 18种策略
│   │   ├── indicator/            # TA-Lib指标
│   │   └── pattern/              # K线形态
│   └── lib/
│       └── database.py           # 数据库配置
└── docs/
    ├── AI_STOCK_SELECTION_GUIDE.md
    ├── UPDATE_SUMMARY.md
    └── SYSTEM_ARCHITECTURE.md    # 本文档
```

---

更新日期: 2026-05-27
