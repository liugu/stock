# 限流优化实施计划

## 背景
当前数据获取模块无请求限流控制，容易触发东方财富API封禁。需要统一添加限流、重试、随机延迟机制。

## 已完成
- [x] `instock/core/crawling/rate_limiter.py` - 限流模块
  - 请求间隔控制（随机延迟）
  - 自动重试机制
  - 请求统计
  - 全局单例 `limiter`

## 待实现

### 1. 修改爬虫模块
替换所有 `requests.get/post` 为 `limiter.get/post`

| 文件 | 函数 | 改动内容 |
|------|------|----------|
| `stock_hist_em.py` | `stock_zh_a_spot_em()` | `requests.get` → `limiter.get` |
| `stock_hist_em.py` | `code_id_map_em()` | 3次请求，每次需等待 |
| `stock_hist_em.py` | `stock_zh_a_hist()` | `requests.get` → `limiter.get` |
| `stock_hist_em.py` | `stock_zh_a_hist_min_em()` | `requests.get` → `limiter.get` |
| `stock_hist_em.py` | `stock_zh_a_hist_pre_min_em()` | `requests.get` → `limiter.get` |
| `stock_fund_em.py` | `stock_individual_fund_flow_rank()` | `requests.get` → `limiter.get` |
| `stock_fund_em.py` | `stock_sector_fund_flow_rank()` | `requests.get` → `limiter.get` |
| `fund_etf_em.py` | `fund_etf_spot_em()` | `requests.get` → `limiter.get` |
| `stock_lhb_em.py` | 各龙虎榜函数 | `requests.get` → `limiter.get` |
| `stock_dzjy_em.py` | 大宗交易函数 | `requests.get` → `limiter.get` |
| `stock_fhps_em.py` | 分红配送函数 | `requests.get` → `limiter.get` |

### 2. 导入语句
每个文件头部添加：
```python
import logging
from instock.core.crawling.rate_limiter import limiter

logger = logging.getLogger(__name__)
```

### 3. 请求替换模式
```python
# 原代码
r = requests.get(url, params=params)

# 新代码
r = limiter.get(url, params=params)
```

### 4. 配置化（可选）
在 `daily_task_config.json` 添加限流配置：
```json
{
  "rate_limiter": {
    "min_interval": 0.5,
    "max_interval": 1.5,
    "max_retries": 3,
    "retry_delay": 2.0,
    "timeout": 30
  }
}
```

## 默认配置
- 最小请求间隔: 0.5秒
- 最大请求间隔: 1.5秒
- 最大重试次数: 3次
- 重试延迟: 2秒
- 请求超时: 30秒

## 验证方法
```bash
cd ~/workspace/stock
python -c "
from instock.core.crawling.stock_hist_em import stock_zh_a_spot_em
from instock.core.crawling.rate_limiter import limiter

df = stock_zh_a_spot_em()
print(f'获取 {len(df)} 只股票')
print(f'请求统计: {limiter.stats()}')
"
```

## 注意事项
1. 保持原有函数签名不变
2. 不影响 `lru_cache` 缓存逻辑
3. 日志使用 `logging` 模块，不打印到控制台
