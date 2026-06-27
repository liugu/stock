#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股全量K线数据下载脚本
使用新浪财经接口下载所有A股日K线数据到本地
"""

import os
import time
import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# 配置
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "kline"
OUTPUT_FORMAT = "csv"  # parquet 或 csv
DELAY = 0.3  # 每次请求后的延迟（秒）
DAYS = 730  # 下载最近多少天的数据


def get_stock_list_from_file():
    """从本地文件获取股票列表"""
    # 尝试从现有数据或配置文件读取
    stock_file = Path(__file__).parent.parent / "data" / "stock_list.json"
    if stock_file.exists():
        with open(stock_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_stock_list_sina():
    """从新浪获取完整股票列表"""
    print("正在从新浪获取股票列表...")
    
    # 使用新浪行情接口获取所有股票
    url = "http://hq.sinajs.cn/list="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://finance.sina.com.cn/",
    }
    
    # 先获取沪深300成分股作为基础
    # 或者使用预设的股票代码范围
    codes = []
    
    # 沪市主板: 600000-605999
    for prefix in ["600", "601", "603", "605"]:
        print(f"  扫描{prefix}开头...")
        for i in range(0, 1000, 50):
            batch = [f"{prefix}{str(j).zfill(3)}" for j in range(i, min(i+50, 1000))]
            symbols = [f"sh{code}" for code in batch]
            
            try:
                r = requests.get(url + ",".join(symbols), headers=headers, timeout=10)
                # 解析返回数据
                for line in r.text.split(";"):
                    if 'hq_str_' in line and '=""' not in line:
                        # 提取代码
                        parts = line.split('"')
                        if len(parts) > 1 and parts[1]:
                            code = line.split("hq_str_")[1].split('"')[0][2:]
                            codes.append(code)
                time.sleep(0.1)
            except:
                pass
    
    # 深市主板: 000001-002999, 创业板: 300001-301999
    for prefix in ["000", "001", "002", "003", "300", "301"]:
        print(f"  扫描{prefix}开头...")
        for i in range(0, 1000, 50):
            batch = [f"{prefix}{str(j).zfill(3)}" for j in range(i, min(i+50, 1000))]
            symbols = [f"sz{code}" for code in batch]
            
            try:
                r = requests.get(url + ",".join(symbols), headers=headers, timeout=10)
                for line in r.text.split(";"):
                    if 'hq_str_' in line and '=""' not in line:
                        parts = line.split('"')
                        if len(parts) > 1 and parts[1]:
                            code = line.split("hq_str_")[1].split('"')[0][2:]
                            codes.append(code)
                time.sleep(0.1)
            except:
                pass
    
    # 去重
    codes = list(set(codes))
    codes.sort()
    
    print(f"获取到 {len(codes)} 只股票")
    return codes


def get_stock_list_simple():
    """简单方式：生成所有可能的股票代码，然后验证"""
    print("生成股票代码列表...")
    codes = []
    
    # 沪市
    for prefix in ["600", "601", "603", "605"]:
        for i in range(10000):
            codes.append(f"{prefix}{str(i).zfill(3)}")
    
    # 深市
    for prefix in ["000", "001", "002", "003"]:
        for i in range(10000):
            codes.append(f"{prefix}{str(i).zfill(3)}")
    
    # 创业板
    for prefix in ["300", "301"]:
        for i in range(10000):
            codes.append(f"{prefix}{str(i).zfill(3)}")
    
    print(f"生成 {len(codes)} 个可能的股票代码")
    return codes


def download_kline_sina(code, days=730):
    """下载单只股票的K线数据（新浪接口）"""
    market = "sh" if code.startswith("6") else "sz"
    url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
    params = {
        "symbol": f"{market}{code}",
        "scale": "240",  # 日K
        "ma": "no",
        "datalen": str(days),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 200 and r.text:
            data = json.loads(r.text)
            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                # 重命名列
                column_map = {
                    "day": "日期",
                    "open": "开盘",
                    "high": "最高",
                    "low": "最低",
                    "close": "收盘",
                    "volume": "成交量",
                }
                df = df.rename(columns=column_map)
                # 转换数值类型
                for col in ["开盘", "最高", "最低", "收盘", "成交量"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return {"code": code, "success": True, "data": df, "count": len(df)}
        
        return {"code": code, "success": False, "error": "无数据"}
    except Exception as e:
        return {"code": code, "success": False, "error": str(e)[:50]}


def save_kline(result, output_dir, output_format="parquet"):
    """保存K线数据到文件"""
    if not result["success"]:
        return False
    
    code = result["code"]
    df = result["data"]
    
    # 添加股票代码列
    df["股票代码"] = code
    
    # 保存
    file_path = output_dir / f"{code}.{output_format}"
    try:
        if output_format == "parquet":
            df.to_parquet(file_path, index=False, compression="gzip")
        else:
            df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return True
    except Exception as e:
        print(f"  保存{code}失败: {e}")
        return False


def download_all_stocks(codes, output_dir, output_format="parquet", delay=0.3):
    """下载所有股票的K线数据"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total = len(codes)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    failed_codes = []
    
    start_time = time.time()
    
    print(f"开始下载 {total} 只股票的K线数据...")
    print(f"数据范围: 最近 {DAYS} 天")
    print("-" * 50)
    
    for i, code in enumerate(codes, 1):
        # 检查是否已下载
        file_path = output_dir / f"{code}.{output_format}"
        if file_path.exists():
            skipped_count += 1
            continue
        
        try:
            result = download_kline_sina(code, DAYS)
            if result["success"]:
                if save_kline(result, output_dir, output_format):
                    success_count += 1
                else:
                    failed_count += 1
            else:
                # 无数据可能是股票已退市或代码无效，不记录为失败
                if "无数据" not in result.get("error", ""):
                    failed_count += 1
                    failed_codes.append({"code": code, "error": result.get("error", "未知错误")})
            
            # 进度显示
            processed = i
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                speed = processed / elapsed
                eta = (total - processed) / speed / 60
                print(f"进度: {processed}/{total} ({processed/total*100:.1f}%) | "
                      f"成功: {success_count} | 跳过: {skipped_count} | "
                      f"速度: {speed:.1f}只/秒 | 预计剩余: {eta:.1f}分钟")
            
            time.sleep(delay)
            
        except KeyboardInterrupt:
            print("\n用户中断，保存已下载数据...")
            break
        except Exception as e:
            failed_count += 1
            failed_codes.append({"code": code, "error": str(e)[:50]})
    
    # 汇总
    elapsed = time.time() - start_time
    print("-" * 50)
    print(f"下载完成!")
    print(f"总耗时: {elapsed/60:.1f} 分钟")
    print(f"成功: {success_count}, 跳过: {skipped_count}, 失败: {failed_count}")
    
    # 保存失败记录
    if failed_codes:
        failed_file = output_dir / "failed_codes.json"
        with open(failed_file, "w", encoding="utf-8") as f:
            json.dump(failed_codes, f, ensure_ascii=False, indent=2)
        print(f"失败记录已保存到: {failed_file}")
    
    # 统计数据量
    total_files = sum(1 for _ in output_dir.glob(f"*.{output_format}"))
    total_size = sum(f.stat().st_size for f in output_dir.glob(f"*.{output_format}"))
    print(f"数据文件: {total_files} 个")
    print(f"总大小: {total_size / 1024 / 1024:.1f} MB")
    
    return success_count, failed_count


def main():
    print("=" * 50)
    print("A股全量K线数据下载工具（新浪接口）")
    print("=" * 50)
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"输出格式: {OUTPUT_FORMAT}")
    print(f"下载数据: 最近 {DAYS} 天")
    print()
    
    # 尝试从文件读取股票列表
    codes = get_stock_list_from_file()
    
    if not codes:
        # 使用简单方式生成代码列表
        codes = get_stock_list_simple()
    
    # 下载
    download_all_stocks(codes, OUTPUT_DIR, OUTPUT_FORMAT, DELAY)


if __name__ == "__main__":
    main()
