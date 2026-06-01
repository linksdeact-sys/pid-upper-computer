#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID控制器模块
实现PID控制算法
"""

import time
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class PIDParams:
    """PID参数"""
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0


class PIDController:
    """PID控制器"""

    def __init__(self):
        self._params = PIDParams()
        self._target: float = 0.0
        self._output_min: float = -1000.0
        self._output_max: float = 1000.0
        self._integral_limit: float = 1000.0

        # 内部状态
        self._last_error: float = 0.0
        self._integral: float = 0.0
        self._last_time: Optional[float] = None
        self._last_output: float = 0.0

        # 回调
        self._on_output: Optional[Callable] = None

    @property
    def params(self) -> PIDParams:
        """获取PID参数"""
        return self._params

    @params.setter
    def params(self, value: PIDParams):
        """设置PID参数"""
        self._params = value

    @property
    def target(self) -> float:
        """获取目标值"""
        return self._target

    @target.setter
    def target(self, value: float):
        """设置目标值"""
        self._target = value

    @property
    def output_limits(self) -> tuple:
        """获取输出限制"""
        return (self._output_min, self._output_max)

    @output_limits.setter
    def output_limits(self, limits: tuple):
        """设置输出限制"""
        self._output_min, self._output_max = limits

    @property
    def last_output(self) -> float:
        """获取上次输出"""
        return self._last_output

    def set_on_output(self, callback: Callable):
        """设置输出回调"""
        self._on_output = callback

    def reset(self):
        """重置控制器"""
        self._last_error = 0.0
        self._integral = 0.0
        self._last_time = None
        self._last_output = 0.0

    def update(self, current_value: float, dt: Optional[float] = None) -> float:
        """
        更新PID控制器
        current_value: 当前值
        dt: 时间间隔（秒），如果为None则自动计算
        返回: 控制输出
        """
        # 计算时间间隔
        current_time = time.time()
        if dt is None:
            if self._last_time is None:
                dt = 0.01  # 默认10ms
            else:
                dt = current_time - self._last_time
                if dt <= 0:
                    dt = 0.001  # 防止除零

        self._last_time = current_time

        # 计算误差
        error = self._target - current_value

        # 比例项
        p_term = self._params.kp * error

        # 积分项
        self._integral += error * dt
        self._integral = max(-self._integral_limit,
                             min(self._integral_limit, self._integral))
        i_term = self._params.ki * self._integral

        # 微分项
        if dt > 0:
            derivative = (error - self._last_error) / dt
        else:
            derivative = 0.0
        d_term = self._params.kd * derivative

        # 计算输出
        output = p_term + i_term + d_term

        # 限制输出范围
        output = max(self._output_min, min(self._output_max, output))

        # 保存状态
        self._last_error = error
        self._last_output = output

        # 通知回调
        if self._on_output:
            self._on_output(output, p_term, i_term, d_term)

        return output

    def get_components(self, current_value: float) -> tuple:
        """获取PID各项值（用于显示）"""
        error = self._target - current_value

        p_term = self._params.kp * error
        i_term = self._params.ki * self._integral
        d_term = self._params.kd * (error - self._last_error)

        return (p_term, i_term, d_term)
