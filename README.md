# InStock A股量化分析系统

InStock 是一个开源的A股量化分析系统，支持数据抓取、技术指标计算、K线形态识别、综合选股、策略回测和Web可视化。

基于 [myhhub/stock](https://github.com/myhhub/stock) 二次开发，适配本地环境并扩展了选股策略和数据源。

---

## 目录结构

```
stock/
├── instock/                    # 核心量化框架 (基于原版 InStock)
│   ├── core/
│   │   ├── crawling/           # 数据爬虫层 (自动切换数据源)
│   │   ├── indicator/          # 技术指标计算 (TA-Lib, 32种指标)
│   │   ├── pattern/            # K线形态识别 (61种形态)
│   │   ├── strategy/           # 选股策略 (13+策略)
│   │   └── stockfetch.py       # 数据获取工具
│   ├── job/                    # 定时任务编排
│   ├── web/                    # Tornado Web服务 (端口9988)
│   ├── trade/                  # 自动交易系统 (easytrader)
│   └── lib/                    # 工具库 (数据库连接、交易时间)
├── scripts/                    # 实用脚本 (按功能分类)
│   ├── selection/              # 选股策略脚本
│   ├── ai/                     # AI分析脚本
│   ├── data/                   # 数据下载更新脚本
│   ├── check/                  # 环境检查/诊断脚本
│   └── workflow/               # 工作流/自动化脚本
├── backtest/                   # 回测脚本
├── trade/                      # 交易相关脚本
│   ├── realtime_trading.py     # 实盘交易
│   ├── ths_trading.py          # 同花顺自动交易
│   └── trading_console.py      # 交易控制台
├── cron/                       # 定时任务
│   ├── daily_task.py           # 每日选股主任务
│   ├── news_analysis.py        # 消息面分析
│   └── daemon.sh               # 后台守护进程
├── web/                        # 前端 (Vue 3 + Element Plus)
│   ├── src/                    # Vue源码
│   └── server/                 # 后端API (Python)
├── config/                     # 配置文件
│   ├── requirements.txt        # Python依赖
│   ├── hot.json / limit.json   # 选股结果导出
│   └── instock_db.sql          # 数据库初始化SQL
├── output/                     # 选股结果输出
├── docs/                       # 文档
└── data/                       # 数据缓存
```

## 快速开始

### 环境要求

- Python 3.11+
- MySQL/MariaDB 8.0+
- TA-Lib (技术分析库)

### 安装

```bash
# 1. 安装依赖
pip install -r config/requirements.txt

# 2. 配置数据库 (默认配置见下方)
#   编辑 instock/lib/database.py

# 3. 初始化数据库表
cd instock/job && python init_job.py
```

### 数据库配置

`instock/lib/database.py` 默认配置：

| 参数 | 默认值 | 环境变量 |
|------|--------|---------|
| 主机 | localhost | db_host |
| 用户 | stock | db_user |
| 密码 | 12345678 | db_password |
| 库名 | instock | db_database |
| 端口 | 3306 | db_port |

## 使用指南

### 选股

```bash
# 选股入口
python scripts/selection/select_stocks.py
python scripts/selection/quick_select.py

# 多种策略同时运行
python scripts/selection/run_all_strategies.py

# 短线选股
python scripts/selection/shortline_selection.py
python scripts/selection/quick_select_fast.py
```

### 数据更新

```bash
# Baostock 数据源 (推荐 - 稳定、无限流)
python scripts/data/download_baostock.py

# 补充/修复历史数据
python scripts/data/supplement_data.py

# 增量更新每日行情
python scripts/update_stock_daily.py
```

### 回测验证

```bash
python backtest/backtest_strategy.py
python backtest/backtest_professional.py
python backtest/quick_backtest.py
```

### 消息面分析

```bash
# AI新闻分析选股
python scripts/ai/analyze_news.py
python scripts/ai/ai_stock_selection.py
python scripts/ai/expert_analysis.py
```

### 定时任务

```bash
# 每日选股 (数据更新 + 策略选股 + 消息推送)
python cron/daily_task.py

# 跳过数据更新，仅选股和推送
python cron/daily_task.py --no-update

# 消息面分析 + 推送
python cron/news_analysis.py --push

# 启动后台守护 (每30分钟检查，交易日15:30自动选股)
bash cron/daemon.sh &
```

### 环境检查

```bash
# 检查依赖是否完整
python scripts/check/check_env.py

# 检查数据库连接
python scripts/check/check_db.py

# 检查依赖版本
python scripts/check/test_deps.py
```

### Web服务

```bash
# 启动后端
cd instock/web && python web_service.py
# 访问: http://localhost:9988/

# 启动前端 (Vue 3)
cd web && npm run dev
```

### 自动交易

```bash
# 启动交易服务 (交易日10:00自动打新)
cd instock/trade && python trade_service.py

# 启动同花顺交易
python trade/ths_trading.py
```

## 选股策略

| 策略 | 核心逻辑 | 文件 |
|------|---------|------|
| 放量上涨 | 涨幅>=2%，成交额>=2亿，量比>=2 | `enter.py` |
| 均线多头 | MA30向上，长期趋势向上 | `keep_increasing.py` |
| 停机坪 | 大涨后高开窄幅整理 | `parking_apron.py` |
| 回踩年线 | 年线突破后回踩缩量 | `backtrace_ma250.py` |
| 突破平台 | 60日突破均线放量上涨 | `breakthrough_platform.py` |
| 海龟交易 | 创N日新高 | `turtle_trade.py` |
| 创新高 | 60/120/250日新高，量比确认 | `new_high.py` |
| 无大幅回撤 | 60日回撤<40%，无暴跌 | `low_backtrace_increase.py` |
| 高而窄旗形 | 上市后区间涨幅>=90% | `high_tight_flag.py` |
| 放量跌停 | 跌>9.5%，量比>=4 | `climax_limitdown.py` |
| 低ATR成长 | 上市后高低比>=1.1 | `low_atr.py` |
| 连续小阳线 | 连续放量小阳线上涨 | `consecutive_small_bullish.py` |
| BOLL策略 | 布林带突破策略 | `boll_strategy.py` |

## 数据架构

```
数据源: Baostock (主) / 东方财富 / AkShare
           ↓
    crawling/data_adapter.py  (自动降级切换)
           ↓
    MySQL (instock 数据库)
           ↓
    indicator + pattern + strategy
           ↓
    Web (9988) + 消息推送 + 交易
```

## 消息推送

支持多种推送渠道：

- **Server酱** - 微信推送 (配置 `serverchan_key`)
- **企业微信机器人** - Webhook推送
- **飞书机器人** - 机器人消息推送
- **Telegram** - 机器人消息推送

配置位置：`cron/daily_task_config.json`

## 注意事项

- **股票过滤**：仅处理A股，排除ST股
- **科创板(688xxx)**：数据包含但不参与选股（无法普通账户买入）
- **数据缓存**：历史数据缓存在 `instock/cache/hist/`
- **日志文件**：`instock/log/` 下的 `stock_execute_job.log`、`stock_web.log`、`stock_trade.log`

## 相关文档

- `docs/CLAUDE.md` - 项目开发指南
- `docs/SYSTEM_ARCHITECTURE.md` - 系统架构说明
- `docs/AI_STOCK_SELECTION_GUIDE.md` - AI选股指南
- `docs/THS_GUIDE.md` - 同花顺交易配置
