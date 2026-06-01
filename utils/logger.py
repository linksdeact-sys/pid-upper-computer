#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime
from typing import Optional
from pathlib import Path


class AppLogger:
    """应用程序日志器"""

    _instance: Optional['AppLogger'] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not AppLogger._initialized:
            self._logger = logging.getLogger('PID上位机')
            self._logger.setLevel(logging.DEBUG)

            # 日志格式
            self._formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # 控制台处理器
            self._console_handler = logging.StreamHandler()
            self._console_handler.setLevel(logging.INFO)
            self._console_handler.setFormatter(self._formatter)
            self._logger.addHandler(self._console_handler)

            # 文件处理器
            self._file_handler: Optional[logging.FileHandler] = None

            # 日志缓存（用于UI显示）
            self._log_cache = []
            self._max_cache_size = 1000

            # 回调
            self._on_log = None

            AppLogger._initialized = True

    def set_log_dir(self, log_dir: str):
        """设置日志目录"""
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 创建日志文件
        log_file = log_path / f"pid_tuner_{datetime.now().strftime('%Y%m%d')}.log"

        # 移除旧的文件处理器
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)

        # 添加新的文件处理器
        self._file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(self._formatter)
        self._logger.addHandler(self._file_handler)

    def set_on_log(self, callback):
        """设置日志回调（用于UI显示）"""
        self._on_log = callback

    def _log(self, level: str, message: str):
        """记录日志"""
        # 写入日志
        log_func = getattr(self._logger, level.lower())
        log_func(message)

        # 添加到缓存
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self._log_cache.append(log_entry)

        # 限制缓存大小
        if len(self._log_cache) > self._max_cache_size:
            self._log_cache = self._log_cache[-self._max_cache_size:]

        # 通知回调
        if self._on_log:
            self._on_log(log_entry, level)

    def debug(self, message: str):
        """调试日志"""
        self._log('DEBUG', message)

    def info(self, message: str):
        """信息日志"""
        self._log('INFO', message)

    def warning(self, message: str):
        """警告日志"""
        self._log('WARNING', message)

    def error(self, message: str):
        """错误日志"""
        self._log('ERROR', message)

    def critical(self, message: str):
        """严重错误日志"""
        self._log('CRITICAL', message)

    def get_cache(self) -> list:
        """获取日志缓存"""
        return self._log_cache.copy()

    def clear_cache(self):
        """清空日志缓存"""
        self._log_cache.clear()

    def export_log(self, filepath: str) -> bool:
        """导出日志到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self._log_cache))
            return True
        except Exception as e:
            self.error(f"导出日志失败: {e}")
            return False


# 全局日志器实例
logger = AppLogger()
