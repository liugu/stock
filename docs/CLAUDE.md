# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

InStock是一个A股量化分析系统，抓取每日股票/ETF数据，计算技术指标，识别K线形态，支持综合选股、策略回测和自动交易，并提供Web可视化界面。

## 常用命令

### 安装依赖
```bash
# TA-Lib 需先系统级安装（参考 README.md）
pip install -r requirements.txt
```

### 运行数据作业
```bash
# 完整每日作业（抓取、计算指标、形态识别、策略选股、回测）
cd instock/job && python execute_daily_job.py

# 单个日期
python execute_daily_job.py 2023-03-01

# 多个日期（逗号分隔）
python execute_daily_job.py 2023-03-01,2023-03-02

# 日期区间
python execute_daily_job.py 2023-03-01 2023-03-21

# 单独作业
python init_job.py                    # 初始化数据库
python selection_data_daily_job.py    # 综合选股数据
python basic_data_daily_job.py        # 基础实时数据
python indicators_data_daily_job.py   # 技术指标数据
python klinepattern_data_daily_job.py # K线形态数据
python strategy_data_daily_job.py     # 策略选股数据
python backtest_data_daily_job.py     # 回测数据
```

### 自动化任务（cron目录）
```bash
# 每日选股任务（数据更新+策略选股+消息推送）
cd /home/liugu/workspace/stock && python cron/daily_task.py

# 跳过数据更新（仅选股和推送）
python cron/daily_task.py --no-update

# 指定日期
python cron/daily_task.py --date 2024-01-15

# 启动后台守护进程（每30分钟检查，交易日15:30自动选股）
bash cron/daemon.sh &

# 消息面分析（新闻抓取+AI分析）
python cron/news_analysis.py --push

# 优化版每日任务（减少不必要的抓取）
python cron/optimized_daily.py

# 历史数据下载
python cron/download_hist_data.py

# 板块分析
python cron/sector_analysis.py

# 盈亏计算
python cron/profit_loss_calc.py
```

### 启动Web服务
```bash
cd instock/web && python web_service.py
# 访问地址：http://localhost:9988/
```

### 启动交易服务
```bash
cd instock/trade && python trade_service.py
# 交易日10:00会自动触发打新策略
```

## 项目架构

### 目录结构
- `instock/core/` - 核心业务逻辑
  - `crawling/` - 数据爬虫层
    - `data_adapter.py` - **数据源自动切换层**：新浪 → 东方财富 → AkShare → Baostock
    - `data_adapter_baostock.py` - Baostock本地数据适配器
    - `rate_limiter.py` - 请求限流器，防止被封IP
    - 各独立爬虫模块：`stock_hist_em.py`, `stock_fund_em.py`, `stock_lhb_em.py` 等
  - `indicator/` - 技术指标计算（使用TA-Lib计算MACD、KDJ、BOLL、RSI等32种指标）
  - `pattern/` - K线形态识别（通过TA-Lib识别61种形态）
  - `strategy/` - 选股策略
  - `stockfetch.py` - 数据获取工具函数和股票过滤辅助方法
  - `tablestructure.py` - **数据库表结构定义**（所有表的字段类型、中文名、显示宽度，表驱动配置）
  - `singleton_stock_web_module_data.py` - 单例模式共享资源
- `instock/job/` - 定时任务编排
  - `execute_daily_job.py` - 主入口，编排所有作业
- `instock/web/` - Web服务（基于Tornado）
  - `web_service.py` - Web服务器，端口9988
  - `dataTableHandler.py` - 数据表格API处理器
  - `dataIndicatorsHandler.py` - 指标API处理器
- `instock/trade/` - 自动交易系统
  - `trade_service.py` - 交易服务入口
  - `robot/engine/` - 交易引擎（事件驱动架构）
  - `robot/infrastructure/` - 策略模板和包装器
  - `strategies/` - 交易策略（如 stagging.py 自动打新）
- `instock/lib/` - 工具库
  - `database.py` - 数据库连接和操作（MySQL，使用PyMySQL/SQLAlchemy）
  - `trade_time.py` - 交易时间工具
- `cron/` - 自动化任务脚本
  - `daily_task.py` - 每日选股任务主脚本
  - `daily_task_config.json` - 任务配置（策略列表、推送方式）
  - `daemon.sh` - 后台守护进程脚本
  - `optimized_daily.py` / `simple_daily.py` - 优化/简化版每日任务
  - `news_analysis.py` - 消息面分析脚本
  - `send_email.py` / `send_telegram.py` / `send_wechat.py` / `send_push.py` - 消息推送模块
  - `sync_data.py` / `download_hist_data.py` - 数据同步和下载
  - `sector_analysis.py` - 板块分析
  - `profit_loss_calc.py` - 盈亏计算
- `docs/` - 文档目录

### 数据流架构

```
数据源层（自动切换）:
  新浪 → 东方财富 → AkShare → Baostock(本地)
      ↓
crawling/ (data_adapter.py)
      ↓
MySQL (instockdb)
      ↓
indicator/ + pattern/ + strategy/
      ↓
Web (Tornado 9988) + 消息推送 + 交易服务
```

### 核心设计模式
- **表驱动配置**：所有数据库表结构在`tablestructure.py`中定义，包含字段类型、中文名、显示宽度
- **策略模板模式**：交易策略继承`instock/trade/robot/infrastructure/strategy_template.py`中的`StrategyTemplate`
- **数据源自动切换**：`data_adapter.py` 在多个数据源间自动降级（新浪→东方财富→AkShare→Baostock）
- **请求限流**：`rate_limiter.py` 统一控制爬虫请求频率
- **单例模式**：用于共享资源（`singleton_stock.py`、`singleton_trade_date.py`）
- **多线程处理**：作业使用`concurrent.futures.ThreadPoolExecutor`并行执行

### 选股策略说明

策略文件位于`instock/core/strategy/`，每个策略提供`check(code_name, data, date, ...)`函数：

| 策略 | 文件 | 核心逻辑 |
|------|------|----------|
| 放量上涨 | `enter.py` | 涨幅>=2%，成交额>=2亿，量比>=2 |
| 均线多头 | `keep_increasing.py` | MA30向上，长期趋势向上 |
| 停机坪 | `parking_apron.py` | 最近15日有大涨后高开窄幅整理 |
| 回踩年线 | `backtrace_ma250.py` | 年线(250日)下方突破回踩缩量 |
| 突破平台 | `breakthrough_platform.py` | 60日突破均线放量上涨 |
| 海龟交易 | `turtle_trade.py` | 创N日新高，支持`check_enter_multi()`多周期 |
| 创新高 | `new_high.py` | 60/120/250日新高、历史新高，支持量比确认 |
| 无大幅回撤 | `low_backtrace_increase.py` | 60日回撤<40%，无单日暴跌 |
| 高而窄旗形 | `high_tight_flag.py` | 上市后60日+10日内涨幅>=90% |
| 放量跌停 | `climax_limitdown.py` | 跌>9.5%，成交额>=2亿，量比>=4 |
| 低ATR成长 | `low_atr.py` | 上市后250日+10日高低比>=1.1 |
| 基本面筛选 | `financial_filter.py` | PE<=20, PB<=10, ROE>=15 |
| BOLL策略 | `boll_strategy.py` | 布林带突破策略 |

## 依赖环境

- Python 3.11+
- MySQL/MariaDB (UTF8MB4)
- TA-Lib（技术分析C库，需单独安装）
- 主要依赖：`requirements.txt`

## 配置文件

### 数据库配置
配置位置：`instock/lib/database.py`
- 默认：localhost, root, 123456, instockdb, 端口3306
- 支持环境变量：`db_host`, `db_user`, `db_password`, `db_database`, `db_port`

### 自动化任务配置
配置位置：`cron/daily_task_config.json`
- 策略列表：`strategies` 数组控制选股策略
- 推送方式：`push_method` 可选 `serverchan`/`telegram`/`wechat`
- 各推送渠道配置：`wechat_webhook`, `serverchan_key`, `telegram_token`+`telegram_chat_id`

### 交易配置
配置文件：`instock/config/trade_client.json`
- 券商类型在 `trade_service.py` 中配置（默认 `gf_client` 广发证券）
- 使用 easytrader 库对接券商

## 注意事项

- 股票过滤：仅处理A股（代码以600/601/603/605/000/001/002/003/300/301开头），排除ST股票
- 数据缓存：历史数据缓存在`instock/cache/hist/`，以gzip压缩的pickle文件存储
- 日志文件：`instock/log/`目录下的 `stock_execute_job.log`、`stock_web.log`、`stock_trade.log`
- Web界面：根据`tablestructure.py`中的表配置自动生成视图
- 消息推送：支持Telegram、企业微信、Server酱三种方式
- **数据源问题**：如果东方财富接口不稳定，可在调用 `get_stock_hist()` 时设置 `skip_em=True`，或安装 `akshare` 包作为备选数据源
