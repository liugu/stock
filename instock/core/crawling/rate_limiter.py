#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
请求限流模块
功能：
1. 请求间隔控制
2. 重试机制
3. 随机延迟
4. 请求统计
"""
import time
import random
import logging
from functools import wraps
from typing import Callable, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RateLimiter:
    """请求限流器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 默认配置
        self.min_interval = 0.3  # 最小请求间隔(秒) - 降低频次
        self.max_interval = 0.8  # 最大请求间隔(秒)
        self.max_retries = 3     # 最大重试次数
        self.retry_delay = 2.0   # 重试延迟(秒)
        self.timeout = 15        # 请求超时(秒) - 缩短超时
        
        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
        
        # 创建带重试的session
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建带重试机制的session"""
        session = requests.Session()
        
        # 禁用代理（WSL环境下代理可能导致连接问题）
        session.trust_env = False
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _wait(self):
        """等待随机时间"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        # 随机延迟
        delay = random.uniform(self.min_interval, self.max_interval)
        
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        self.last_request_time = time.time()
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        发送请求(带限流和重试)
        
        Args:
            method: 请求方法 GET/POST
            url: 请求URL
            **kwargs: requests参数
            
        Returns:
            Response对象
        """
        # 设置超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # 等待限流
                self._wait()
                
                # 发送请求
                self.request_count += 1
                response = self.session.request(method, url, **kwargs)
                
                # 检查状态码
                if response.status_code == 429:
                    # 被限流，等待更长时间
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    logger.warning(f"请求被限流，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.error_count += 1
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        raise last_exception or requests.exceptions.RequestException("请求失败")
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.request("GET", url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.request("POST", url, **kwargs)
    
    def get_json(self, url: str, **kwargs) -> dict:
        """GET请求并返回JSON"""
        response = self.get(url, **kwargs)
        return response.json()
    
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count)
        }


# 全局限流器实例
limiter = RateLimiter()


def rate_limited(func: Callable) -> Callable:
    """
    限流装饰器
    用于包装请求函数，自动添加限流和重试
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 在调用前等待
        limiter._wait()
        
        last_exception = None
        for attempt in range(limiter.max_retries):
            try:
                limiter.request_count += 1
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                limiter.error_count += 1
                last_exception = e
                logger.warning(f"函数调用失败 (尝试 {attempt + 1}/{limiter.max_retries}): {e}")
                
                if attempt < limiter.max_retries - 1:
                    wait_time = limiter.retry_delay * (attempt + 1)
                    time.sleep(wait_time)
        
        raise last_exception
    
    return wrapper


def configure_limiter(
    min_interval: float = 0.5,
    max_interval: float = 1.5,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    timeout: int = 30
):
    """
    配置限流器参数
    
    Args:
        min_interval: 最小请求间隔(秒)
        max_interval: 最大请求间隔(秒)
        max_retries: 最大重试次数
        retry_delay: 重试延迟(秒)
        timeout: 请求超时(秒)
    """
    limiter.min_interval = min_interval
    limiter.max_interval = max_interval
    limiter.max_retries = max_retries
    limiter.retry_delay = retry_delay
    limiter.timeout = timeout
    
    logger.info(f"限流器配置: interval=[{min_interval}, {max_interval}], retries={max_retries}, timeout={timeout}")


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    # 测试请求
    try:
        data = limiter.get_json("https://push2.eastmoney.com/api/qt/clist/get", params={
            "pn": "1",
            "pz": "10",
            "po": "1",
            "np": "1",
            "fields": "f12,f14"
        })
        print(f"测试成功: {len(data.get('data', {}).get('diff', []))} 条记录")
        print(f"统计: {limiter.stats()}")
    except Exception as e:
        print(f"测试失败: {e}")
