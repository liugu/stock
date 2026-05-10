# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

InStock是一个A股量化分析系统，抓取每日股票/ETF数据，计算技术指标，识别K线形态，支持综合选股、策略回测和自动交易，并提供Web可视化界面。

## 常用命令

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

### 启动Web服务
```bash
cd instock/web && python web_service.py
# 访问地址：http://localhost:9988/
```

### 启动交易服务
```bash
cd instock/trade && python trade_service.py
```

## 项目架构

### 目录结构
- `instock/core/` - 核心业务逻辑
  - `crawling/` - 数据爬虫（从东方财富/新浪抓取股价、资金流向、分红、大宗交易等）
  - `indicator/` - 技术指标计算（使用TA-Lib计算MACD、KDJ、BOLL、RSI等32种指标）
  - `pattern/` - K线形态识别（通过TA-Lib识别61种形态）
  - `strategy/` - 选股策略（放量上涨、海龟交易、突破平台、回踩年线等10种策略）
  - `stockfetch.py` - 数据获取工具函数和股票过滤辅助方法
  - `tablestructure.py` - 数据库表结构定义（所有表的字段映射）
- `instock/job/` - 定时任务
  - `execute_daily_job.py` - 主入口，编排所有作业
- `instock/web/` - Web服务（基于Tornado）
  - `web_service.py` - Web服务器，端口9988
  - `dataTableHandler.py` - 数据表格API处理器
  - `dataIndicatorsHandler.py` - 指标API处理器
- `instock/trade/` - 自动交易系统
  - `trade_service.py` - 交易服务入口
  - `robot/engine/` - 交易引擎（事件驱动架构）
  - `robot/infrastructure/` - 策略模板和包装器
  - `strategies/` - 交易策略（如stagging.py自动打新）
- `instock/lib/` - 工具库
  - `database.py` - 数据库连接和操作（MySQL，使用PyMySQL/SQLAlchemy）
  - `trade_time.py` - 交易时间工具

### 核心设计模式
- **表驱动配置**：所有数据库表结构在`tablestructure.py`中定义，包含字段类型、中文名、显示宽度
- **策略模板模式**：交易策略继承`instock/trade/robot/infrastructure/strategy_template.py`中的`StrategyTemplate`
- **单例模式**：用于共享资源（`singleton_stock.py`、`singleton_trade_date.py`）
- **多线程处理**：作业使用`concurrent.futures.ThreadPoolExecutor`并行执行

### 数据库配置
配置位置：`instock/lib/database.py`
- 默认：localhost, root, 123456, instockdb, 端口3306
- 支持环境变量配置（Docker部署）：db_host, db_user, db_password, db_database, db_port

### 交易配置
配置文件：`instock/config/trade_client.json`
```json
{
  "user": "交易账号",
  "password": "交易密码",
  "exe_path": "券商下单程序路径"
}
```
券商类型在`trade_service.py`中配置（默认`gf_client`为广发证券），使用easytrader库对接券商。

## 依赖环境

- Python 3.11+
- MySQL/MariaDB
- TA-Lib（技术分析库，需单独安装）
- 主要包：pandas, numpy, tornado, sqlalchemy, pymysql, easytrader, bokeh, requests

## 注意事项

- 股票过滤：仅处理A股（代码以600/601/603/605/000/001/002/003/300/301开头），排除ST股票
- 数据缓存：历史数据缓存在`instock/cache/hist/`，以gzip压缩的pickle文件存储
- 日志文件：`instock/log/`目录下的`stock_execute_job.log`、`stock_web.log`、`stock_trade.log`
- Web界面：根据`tablestructure.py`中的表配置自动生成视图
