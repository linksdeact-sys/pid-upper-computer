#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块
负责应用程序配置的加载、保存和管理
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, field, asdict

from utils.logger import logger


@dataclass
class SerialConfig:
    """串口配置"""
    port: str = ''
    baudrate: int = 115200
    bytesize: int = 8
    stopbits: float = 1
    parity: str = 'N'
    timeout: float = 0.1


@dataclass
class PIDConfig:
    """PID参数配置"""
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.01
    target: float = 0.0
    output_min: float = 0.0
    output_max: float = 100.0


@dataclass
class ChartConfig:
    """图表配置"""
    time_window: int = 10
    auto_scroll: bool = True
    show_setpoint: bool = True
    show_actual: bool = True
    show_output: bool = True
    show_error: bool = False
    line_width: int = 2
    antialias: bool = True


@dataclass
class UIConfig:
    """界面配置"""
    theme: str = 'ios'
    language: str = 'zh_CN'
    window_width: int = 1400
    window_height: int = 900
    log_visible: bool = True
    log_height: int = 150


@dataclass
class AppConfig:
    """应用程序配置"""
    serial: SerialConfig = field(default_factory=SerialConfig)
    pid: PIDConfig = field(default_factory=PIDConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # 最近使用的配置文件
    recent_files: list = field(default_factory=list)

    # 自动保存
    auto_save: bool = True
    auto_save_interval: int = 60  # 秒


class ConfigManager:
    """配置管理器"""

    _instance: Optional['ConfigManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._config = AppConfig()
            self._config_dir = Path.home() / '.pid_tuner'
            self._config_file = self._config_dir / 'config.json'
            self._presets_dir = self._config_dir / 'presets'
            self._initialized = True

    @property
    def config(self) -> AppConfig:
        """获取配置"""
        return self._config

    @property
    def serial(self) -> SerialConfig:
        """获取串口配置"""
        return self._config.serial

    @property
    def pid(self) -> PIDConfig:
        """获取PID配置"""
        return self._config.pid

    @property
    def chart(self) -> ChartConfig:
        """获取图表配置"""
        return self._config.chart

    @property
    def ui(self) -> UIConfig:
        """获取界面配置"""
        return self._config.ui

    def ensure_dirs(self):
        """确保配置目录存在"""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._presets_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> bool:
        """加载配置"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 更新配置
                self._update_config_from_dict(data)
                return True
            return False
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False

    def save(self) -> bool:
        """保存配置"""
        try:
            self.ensure_dirs()

            data = asdict(self._config)

            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def _update_config_from_dict(self, data: dict):
        """从字典更新配置"""
        if 'serial' in data:
            for key, value in data['serial'].items():
                if hasattr(self._config.serial, key):
                    setattr(self._config.serial, key, value)

        if 'pid' in data:
            for key, value in data['pid'].items():
                if hasattr(self._config.pid, key):
                    setattr(self._config.pid, key, value)

        if 'chart' in data:
            for key, value in data['chart'].items():
                if hasattr(self._config.chart, key):
                    setattr(self._config.chart, key, value)

        if 'ui' in data:
            for key, value in data['ui'].items():
                if hasattr(self._config.ui, key):
                    setattr(self._config.ui, key, value)

        if 'recent_files' in data:
            self._config.recent_files = data['recent_files']

    def reset(self):
        """重置为默认配置"""
        self._config = AppConfig()

    def save_preset(self, name: str, pid_config: Optional[PIDConfig] = None) -> bool:
        """保存PID预设"""
        try:
            self.ensure_dirs()

            config = pid_config or self._config.pid
            preset_file = self._presets_dir / f"{name}.json"

            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2)

            return True
        except Exception as e:
            logger.error(f"保存预设失败: {e}")
            return False

    def load_preset(self, name: str) -> Optional[PIDConfig]:
        """加载PID预设"""
        try:
            preset_file = self._presets_dir / f"{name}.json"

            if preset_file.exists():
                with open(preset_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                return PIDConfig(**data)

            return None
        except Exception as e:
            logger.error(f"加载预设失败: {e}")
            return None

    def delete_preset(self, name: str) -> bool:
        """删除PID预设"""
        try:
            preset_file = self._presets_dir / f"{name}.json"

            if preset_file.exists():
                preset_file.unlink()
                return True

            return False
        except Exception as e:
            logger.error(f"删除预设失败: {e}")
            return False

    def list_presets(self) -> list:
        """列出所有预设"""
        try:
            self.ensure_dirs()

            presets = []
            for file in self._presets_dir.glob('*.json'):
                presets.append(file.stem)

            return sorted(presets)
        except Exception as e:
            logger.error(f"列出预设失败: {e}")
            return []

    def add_recent_file(self, filepath: str):
        """添加到最近文件列表"""
        if filepath in self._config.recent_files:
            self._config.recent_files.remove(filepath)

        self._config.recent_files.insert(0, filepath)

        # 限制数量
        if len(self._config.recent_files) > 10:
            self._config.recent_files = self._config.recent_files[:10]

    def get_recent_files(self) -> list:
        """获取最近文件列表"""
        return self._config.recent_files.copy()


# 全局配置管理器实例
config_manager = ConfigManager()
