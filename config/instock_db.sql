
-- 创建数据库
CREATE DATABASE IF NOT EXISTS `instock` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `instock`;

-- 股票信息表
CREATE TABLE IF NOT EXISTS `stock_info` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(50) NOT NULL COMMENT '股票名称',
  `market` VARCHAR(10) COMMENT '市场 sh/sz',
  `create_date` DATE COMMENT '上市日期',
  `industry` VARCHAR(50) COMMENT '所属行业',
  `area` VARCHAR(50) COMMENT '地区',
  `total_mv` DECIMAL(20,2) COMMENT '总市值',
  `circulating_mv` DECIMAL(20,2) COMMENT '流通市值',
  `round` VARCHAR(20) COMMENT '轮次',
  `price` DECIMAL(10,2) COMMENT '当前价',
  `change_percent` DECIMAL(6,4) COMMENT '涨跌幅',
  `volume` BIGINT COMMENT '成交量',
  `amount` DECIMAL(20,2) COMMENT '成交额',
  `pe_ttm` DECIMAL(10,2) COMMENT '市盈率TTM',
  `pb` DECIMAL(10,2) COMMENT '市净率',
  `update_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_code` (`code`),
  INDEX `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票信息表';

-- 股票历史行情表
CREATE TABLE IF NOT EXISTS `stock_daily` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `stock_id` INT NOT NULL COMMENT '股票ID',
  `date` DATE NOT NULL COMMENT '日期',
  `open` DECIMAL(10,4) COMMENT '开盘价',
  `close` DECIMAL(10,4) COMMENT '收盘价',
  `high` DECIMAL(10,4) COMMENT '最高价',
  `low` DECIMAL(10,4) COMMENT '最低价',
  `volume` BIGINT COMMENT '成交量',
  `amount` DECIMAL(20,2) COMMENT '成交额',
  `change_percent` DECIMAL(6,4) COMMENT '涨跌幅',
  `change_amount` DECIMAL(10,4) COMMENT '涨跌额',
  `amplitude` DECIMAL(6,4) COMMENT '振幅',
  `turnover_rate` DECIMAL(6,4) COMMENT '换手率',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_id`, `date`),
  INDEX `idx_date` (`date`),
  FOREIGN KEY (`stock_id`) REFERENCES `stock_info`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日线行情表';

-- 策略表
CREATE TABLE IF NOT EXISTS `strategy` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL COMMENT '策略名称',
  `code` VARCHAR(50) NOT NULL COMMENT '策略代码',
  `description` TEXT COMMENT '策略描述',
  `parameters` TEXT COMMENT '策略参数',
  `is_active` TINYINT DEFAULT 1 COMMENT '是否启用',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选股策略表';

-- 选股结果表
CREATE TABLE IF NOT EXISTS `stock_selection` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `strategy_id` INT NOT NULL COMMENT '策略ID',
  `stock_id` INT NOT NULL COMMENT '股票ID',
  `stock_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(50) NOT NULL COMMENT '股票名称',
  `score` DECIMAL(10,2) COMMENT '评分',
  `rank` INT COMMENT '排名',
  `selection_date` DATE NOT NULL COMMENT '选股日期',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_strategy_date` (`strategy_id`, `selection_date`),
  INDEX `idx_stock_code` (`stock_code`),
  FOREIGN KEY (`strategy_id`) REFERENCES `strategy`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选股结果表';

-- 龙虎榜数据表
CREATE TABLE IF NOT EXISTS `stock_lhb` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `date` DATE NOT NULL COMMENT '日期',
  `stock_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(50) NOT NULL COMMENT '股票名称',
  `close_price` DECIMAL(10,2) COMMENT '收盘价',
  `change_percent` DECIMAL(6,4) COMMENT '涨跌幅',
  `net_amount` DECIMAL(12,2) COMMENT '净额',
  `total_amount` DECIMAL(14,2) COMMENT '总额',
  `buyer1` VARCHAR(100) COMMENT '买一营业部',
  `buyer1_amount` DECIMAL(12,2) COMMENT '买一金额',
  `seller1` VARCHAR(100) COMMENT '卖一营业部',
  `seller1_amount` DECIMAL(12,2) COMMENT '卖一金额',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_date` (`date`),
  INDEX `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜数据表';

-- 消息面分析表
CREATE TABLE IF NOT EXISTS `news_analysis` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL COMMENT '标题',
  `source` VARCHAR(50) COMMENT '来源',
  `pub_time` DATETIME COMMENT '发布时间',
  `content` TEXT COMMENT '内容',
  `sentiment` DECIMAL(3,2) COMMENT '情感得分',
  `sentiment_label` VARCHAR(20) COMMENT '情感标签',
  `related_stocks` VARCHAR(500) COMMENT '相关股票',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_pub_time` (`pub_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息面分析表';
