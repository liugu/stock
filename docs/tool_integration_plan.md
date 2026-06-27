# 量化工具集成方案

## 工具对比与选择

| 工具 | Star | 核心定位 | 推荐用途 |
|------|------|----------|----------|
| **OpenBB** | 62.3K | 全能金融数据终端 | 宏观数据、全球行情、财报分析 |
| **Backtrader** | 20.5K | 经典回测框架 | 已集成 ✓ 策略回测验证 |
| **Microsoft Qlib** | 37.9K | AI量化框架 | 因子挖掘、机器学习选股 |
| **yfinance** | 21.8K | 美股数据爬虫 | 美股数据补充 |
| **FinRL** | 14.1K | 强化学习交易 | 深度学习择时 |
| **ML for Trading** | 16.7K | 机器学习实战 | LSTM预测、特征工程 |

---

## 已完成集成

### 1. Backtrader 回测框架 ✓

**文件**: `backtest_professional.py`

**支持策略**:
- 均线交叉策略 (MA5/MA20)
- 突破策略 (20日高点突破)
- 海龟交易策略 (Turtle)

**回测指标**:
- 收益率、夏普比率
- 最大回撤、胜率
- 交易次数统计

---

## 待集成工具

### 2. OpenBB 数据增强

**用途**: 获取宏观经济数据、美股行情、商品期货

**安装**: `pip install openbb`

**关键数据源**:
- 美联储利率、CPI、GDP
- 美股指数 (S&P500, NASDAQ)
- 商品期货 (黄金、原油、铝)
- 中国宏观数据

### 3. Microsoft Qlib AI因子挖掘

**用途**: 因子挖掘、机器学习选股

**安装**: `pip install pyqlib`

**核心功能**:
- 因子生成与筛选
- 因子组合优化
- LSTM预测模型
- 模型训练与评估

### 4. ML for Trading 特征工程

**用途**: 时间序列预测、技术指标增强

**关键技术**:
- LSTM股价预测
- Transformer模型
- 特征工程框架
- 多因子模型

---

## 整合方案

### 阶段1: 数据增强 (Week 1)

```python
# 示例: 获取铝期货价格
from openbb import obb
al_price = obb.equity.price("AL")  # 铝期货
gold_price = obb.equity.price("GC")  # 黄金
```

### 阶段2: AI因子挖掘 (Week 2)

```python
# 示例: Qlib因子挖掘
import qlib
from qlib.contrib.data.handler import Alpha360

# 生成360个技术因子
handler = Alpha360()
factors = handler.fetch()
```

### 阶段3: 深度学习预测 (Week 3)

```python
# 示例: LSTM预测
from ml_for_trading.models import LSTMPredictor

model = LSTMPredictor(
    features=['close', 'volume', 'ma5', 'ma20'],
    lookback=30,
    forecast=5
)
model.train(train_data)
predictions = model.predict(test_data)
```

---

## 实战流程

```
数据获取:
  akshare (A股) + OpenBB (宏观/美股) → MySQL
  
因子生成:
  技术指标 + Qlib因子 + 特征工程
  
策略开发:
  选股策略 → Backtrader回测 → 参数优化
  
AI增强:
  因子组合 → LSTM预测 → 强化学习择时
  
实盘执行:
  选股结果 → 飞书推送 → 监控跟踪
```

---

## 下一步行动

1. **安装OpenBB**: 获取铝期货、黄金实时数据验证消息面选股
2. **集成Qlib**: 开发AI因子增强选股准确率
3. **完善回测**: 添加滑点、手续费、仓位管理
4. **飞书推送**: 实盘选股结果自动推送

---

## 今日验证结论

**回测结果**: 三只推荐股票历史回测表现平稳，突破策略胜率较高

**建议操作**:
- 郴电国际: 海龟策略持有，等待突破
- 西部黄金: 突破策略已买入，观望
- 鑫科材料: 等待均线多头再入场

**风险提示**: 回测数据滞后，需结合实时行情判断