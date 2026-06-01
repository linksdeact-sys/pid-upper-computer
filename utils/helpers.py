#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
辅助函数模块
提供各种实用工具函数
"""

import os
import sys
import hashlib
import time
from datetime import datetime
from typing import Any, Optional, Union
from pathlib import Path


def get_app_dir() -> Path:
    """获取应用程序目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的exe
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent.parent


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件路径"""
    base_path = get_app_dir()
    return base_path / 'resources' / relative_path


def format_number(value: float, decimals: int = 3) -> str:
    """格式化数字"""
    if abs(value) < 0.001 and value != 0:
        return f"{value:.{decimals}e}"
    return f"{value:.{decimals}f}"


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(timestamp).strftime(format_str)


def format_bytes(size: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def calculate_checksum(data: bytes) -> int:
    """计算校验和"""
    return sum(data) & 0xFF


def clamp(value: float, min_value: float, max_value: float) -> float:
    """限制数值范围"""
    return max(min_value, min(max_value, value))


def lerp(start: float, end: float, t: float) -> float:
    """线性插值"""
    return start + (end - start) * t


def map_range(value: float, in_min: float, in_max: float,
              out_min: float, out_max: float) -> float:
    """映射数值范围"""
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def is_valid_port(port: str) -> bool:
    """检查串口名称是否有效"""
    import re
    pattern = r'^COM\d+$|^/dev/tty[A-Z]+\d+$'
    return bool(re.match(pattern, port, re.IGNORECASE))


def get_file_hash(filepath: str) -> str:
    """计算文件MD5哈希"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def ensure_dir(dir_path: str) -> Path:
    """确保目录存在"""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_unique_filename(filepath: str) -> str:
    """获取唯一文件名（避免覆盖）"""
    path = Path(filepath)
    if not path.exists():
        return filepath

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return str(new_path)
        counter += 1


class Timer:
    """计时器"""

    def __init__(self):
        self._start_time: Optional[float] = None
        self._elapsed: float = 0.0

    def start(self):
        """开始计时"""
        self._start_time = time.time()

    def stop(self) -> float:
        """停止计时并返回经过的时间"""
        if self._start_time is not None:
            self._elapsed = time.time() - self._start_time
            self._start_time = None
        return self._elapsed

    def reset(self):
        """重置计时器"""
        self._start_time = None
        self._elapsed = 0.0

    @property
    def elapsed(self) -> float:
        """获取经过的时间"""
        if self._start_time is not None:
            return time.time() - self._start_time
        return self._elapsed

    @property
    def is_running(self) -> bool:
        """是否正在计时"""
        return self._start_time is not None


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_rate: float):
        """
        初始化速率限制器
        max_rate: 每秒最大调用次数
        """
        self._min_interval = 1.0 / max_rate
        self._last_call = 0.0

    def allow(self) -> bool:
        """检查是否允许调用"""
        current_time = time.time()
        if current_time - self._last_call >= self._min_interval:
            self._last_call = current_time
            return True
        return False

    def wait(self):
        """等待直到可以调用"""
        current_time = time.time()
        elapsed = current_time - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()


class CircularBuffer:
    """环形缓冲区"""

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._buffer = [None] * capacity
        self._head = 0
        self._tail = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        """容量"""
        return self._capacity

    @property
    def size(self) -> int:
        """当前大小"""
        return self._size

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return self._size == 0

    @property
    def is_full(self) -> bool:
        """是否已满"""
        return self._size == self._capacity

    def push(self, item: Any):
        """添加元素"""
        self._buffer[self._head] = item
        self._head = (self._head + 1) % self._capacity

        if self.is_full:
            self._tail = (self._tail + 1) % self._capacity
        else:
            self._size += 1

    def pop(self) -> Optional[Any]:
        """弹出元素"""
        if self.is_empty:
            return None

        item = self._buffer[self._tail]
        self._buffer[self._tail] = None
        self._tail = (self._tail + 1) % self._capacity
        self._size -= 1

        return item

    def peek(self) -> Optional[Any]:
        """查看队首元素"""
        if self.is_empty:
            return None
        return self._buffer[self._tail]

    def clear(self):
        """清空缓冲区"""
        self._buffer = [None] * self._capacity
        self._head = 0
        self._tail = 0
        self._size = 0

    def to_list(self) -> list:
        """转换为列表"""
        result = []
        if self.is_empty:
            return result

        index = self._tail
        for _ in range(self._size):
            result.append(self._buffer[index])
            index = (index + 1) % self._capacity

        return result
