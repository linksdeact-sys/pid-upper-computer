#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报警管理模块
负责参数超限报警、通信异常报警等
"""

import time
from enum import Enum
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime


class AlarmLevel(Enum):
    """报警级别"""
    INFO = "信息"
    WARNING = "警告"
    ERROR = "错误"
    CRITICAL = "严重"


class AlarmType(Enum):
    """报警类型"""
    VALUE_HIGH = "值过高"
    VALUE_LOW = "值过低"
    ERROR_HIGH = "误差过大"
    COMM_ERROR = "通信异常"
    PARAM_ERROR = "参数异常"
    SYSTEM_ERROR = "系统错误"


@dataclass
class AlarmEvent:
    """报警事件"""
    timestamp: float
    level: AlarmLevel
    alarm_type: AlarmType
    message: str
    value: Optional[float] = None
    limit: Optional[float] = None
    acknowledged: bool = False

    @property
    def datetime_str(self) -> str:
        """格式化时间"""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def level_color(self) -> str:
        """报警级别颜色"""
        colors = {
            AlarmLevel.INFO: "#007AFF",
            AlarmLevel.WARNING: "#FF9500",
            AlarmLevel.ERROR: "#FF3B30",
            AlarmLevel.CRITICAL: "#FF2D55"
        }
        return colors.get(self.level, "#8E8E93")


class AlarmManager:
    """报警管理器"""

    def __init__(self):
        # 报警配置
        self._value_high_limit: Optional[float] = None
        self._value_low_limit: Optional[float] = None
        self._error_high_limit: Optional[float] = None

        # 报警状态
        self._alarms: List[AlarmEvent] = []
        self._max_alarms = 1000
        self._active_alarms: List[AlarmEvent] = []

        # 回调
        self._on_alarm: Optional[Callable] = None
        self._on_alarm_cleared: Optional[Callable] = None

        # 报警延迟（防止抖动）
        self._alarm_delay: float = 1.0  # 秒
        self._last_alarm_time: dict = {}

    @property
    def alarms(self) -> List[AlarmEvent]:
        """获取所有报警"""
        return self._alarms.copy()

    @property
    def active_alarms(self) -> List[AlarmEvent]:
        """获取活动报警"""
        return self._active_alarms.copy()

    @property
    def has_active_alarms(self) -> bool:
        """是否有活动报警"""
        return len(self._active_alarms) > 0

    def set_on_alarm(self, callback: Callable):
        """设置报警回调"""
        self._on_alarm = callback

    def set_on_alarm_cleared(self, callback: Callable):
        """设置报警清除回调"""
        self._on_alarm_cleared = callback

    def set_limits(self, value_high: Optional[float] = None,
                   value_low: Optional[float] = None,
                   error_high: Optional[float] = None):
        """设置报警限制"""
        self._value_high_limit = value_high
        self._value_low_limit = value_low
        self._error_high_limit = error_high

    def set_alarm_delay(self, delay: float):
        """设置报警延迟"""
        self._alarm_delay = delay

    def check_value(self, value: float, setpoint: float = 0.0):
        """检查值是否超限"""
        error = abs(setpoint - value)

        # 检查值过高
        if self._value_high_limit is not None and value > self._value_high_limit:
            self._trigger_alarm(
                level=AlarmLevel.WARNING,
                alarm_type=AlarmType.VALUE_HIGH,
                message=f"当前值 {value:.2f} 超过上限 {self._value_high_limit:.2f}",
                value=value,
                limit=self._value_high_limit
            )

        # 检查值过低
        if self._value_low_limit is not None and value < self._value_low_limit:
            self._trigger_alarm(
                level=AlarmLevel.WARNING,
                alarm_type=AlarmType.VALUE_LOW,
                message=f"当前值 {value:.2f} 低于下限 {self._value_low_limit:.2f}",
                value=value,
                limit=self._value_low_limit
            )

        # 检查误差过大
        if self._error_high_limit is not None and error > self._error_high_limit:
            self._trigger_alarm(
                level=AlarmLevel.WARNING,
                alarm_type=AlarmType.ERROR_HIGH,
                message=f"误差 {error:.2f} 超过限制 {self._error_high_limit:.2f}",
                value=error,
                limit=self._error_high_limit
            )

    def trigger_comm_error(self, message: str):
        """触发通信异常报警"""
        self._trigger_alarm(
            level=AlarmLevel.ERROR,
            alarm_type=AlarmType.COMM_ERROR,
            message=message
        )

    def trigger_param_error(self, message: str):
        """触发参数异常报警"""
        self._trigger_alarm(
            level=AlarmLevel.WARNING,
            alarm_type=AlarmType.PARAM_ERROR,
            message=message
        )

    def trigger_system_error(self, message: str):
        """触发系统错误报警"""
        self._trigger_alarm(
            level=AlarmLevel.CRITICAL,
            alarm_type=AlarmType.SYSTEM_ERROR,
            message=message
        )

    def _trigger_alarm(self, level: AlarmLevel, alarm_type: AlarmType,
                       message: str, value: Optional[float] = None,
                       limit: Optional[float] = None):
        """触发报警"""
        # 检查报警延迟
        alarm_key = f"{alarm_type.value}_{message}"
        current_time = time.time()

        if alarm_key in self._last_alarm_time:
            if current_time - self._last_alarm_time[alarm_key] < self._alarm_delay:
                return

        self._last_alarm_time[alarm_key] = current_time

        # 创建报警事件
        alarm = AlarmEvent(
            timestamp=current_time,
            level=level,
            alarm_type=alarm_type,
            message=message,
            value=value,
            limit=limit
        )

        # 添加到报警列表
        self._alarms.append(alarm)
        self._active_alarms.append(alarm)

        # 限制报警数量
        if len(self._alarms) > self._max_alarms:
            self._alarms = self._alarms[-self._max_alarms:]

        # 通知回调
        if self._on_alarm:
            self._on_alarm(alarm)

    def acknowledge_alarm(self, alarm: AlarmEvent):
        """确认报警"""
        alarm.acknowledged = True
        if alarm in self._active_alarms:
            self._active_alarms.remove(alarm)

    def acknowledge_all(self):
        """确认所有报警"""
        for alarm in self._active_alarms:
            alarm.acknowledged = True
        self._active_alarms.clear()

    def clear_alarms(self):
        """清除所有报警"""
        self._alarms.clear()
        self._active_alarms.clear()
        self._last_alarm_time.clear()

    def get_alarm_count(self) -> dict:
        """获取报警统计"""
        counts = {level: 0 for level in AlarmLevel}
        for alarm in self._alarms:
            counts[alarm.level] += 1
        return counts
