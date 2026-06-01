#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模拟器模块
用于在没有实际硬件时模拟PID控制系统
"""

import time
import math
import random
import threading
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class PlantModel:
    """被控对象模型"""
    gain: float = 1.0           # 增益
    time_constant: float = 2.0  # 时间常数（秒）
    delay: float = 0.5          # 死区时间（秒）
    noise_level: float = 0.02   # 噪声水平
    disturbance: float = 0.0    # 扰动


class PIDSimulator:
    """PID模拟器"""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sample_time: float = 0.01  # 10ms

        # PID参数
        self._kp: float = 1.0
        self._ki: float = 0.0
        self._kd: float = 0.0

        # 控制参数
        self._target: float = 100.0
        self._output_min: float = 0.0
        self._output_max: float = 100.0

        # 被控对象
        self._plant = PlantModel()

        # PID内部状态
        self._last_error: float = 0.0
        self._integral: float = 0.0
        self._integral_limit: float = 100.0

        # 过程值
        self._current_value: float = 0.0
        self._current_output: float = 0.0
        self._last_time: Optional[float] = None

        # 延迟缓冲
        self._delay_buffer: list = []
        self._delay_steps: int = 0

        # 回调
        self._on_data: Optional[Callable] = None

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    @property
    def current_value(self) -> float:
        """获取当前值"""
        return self._current_value

    @property
    def current_output(self) -> float:
        """获取当前输出"""
        return self._current_output

    def set_on_data(self, callback: Callable):
        """设置数据回调"""
        self._on_data = callback

    def set_pid_params(self, kp: float, ki: float, kd: float):
        """设置PID参数"""
        self._kp = kp
        self._ki = ki
        self._kd = kd

    def set_target(self, target: float):
        """设置目标值"""
        self._target = target

    def set_output_limits(self, min_val: float, max_val: float):
        """设置输出限制"""
        self._output_min = min_val
        self._output_max = max_val

    def set_plant_model(self, gain: float, time_constant: float, delay: float,
                        noise_level: float = 0.02):
        """设置被控对象模型"""
        self._plant.gain = gain
        self._plant.time_constant = time_constant
        self._plant.delay = delay
        self._plant.noise_level = noise_level

        # 计算延迟步数
        self._delay_steps = int(delay / self._sample_time)
        self._delay_buffer = [0.0] * max(1, self._delay_steps)

    def set_sample_time(self, sample_time: float):
        """设置采样时间"""
        self._sample_time = sample_time

    def start(self):
        """启动模拟"""
        if self._running:
            return

        self._running = True
        self._last_time = time.time()
        self._integral = 0.0
        self._last_error = 0.0

        self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止模拟"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def reset(self):
        """重置模拟"""
        self._current_value = 0.0
        self._current_output = 0.0
        self._integral = 0.0
        self._last_error = 0.0
        self._delay_buffer = [0.0] * max(1, self._delay_steps)

    def _simulation_loop(self):
        """模拟循环"""
        while self._running:
            current_time = time.time()
            dt = current_time - self._last_time

            if dt >= self._sample_time:
                self._update(dt)
                self._last_time = current_time

            time.sleep(0.001)  # 1ms sleep

    def _update(self, dt: float):
        """更新模拟"""
        # 计算误差
        error = self._target - self._current_value

        # PID计算
        # 比例项
        p_term = self._kp * error

        # 积分项
        self._integral += error * dt
        self._integral = max(-self._integral_limit,
                             min(self._integral_limit, self._integral))
        i_term = self._ki * self._integral

        # 微分项
        if dt > 0:
            derivative = (error - self._last_error) / dt
        else:
            derivative = 0.0
        d_term = self._kd * derivative

        # 计算输出
        output = p_term + i_term + d_term

        # 限制输出范围
        output = max(self._output_min, min(self._output_max, output))

        # 保存误差
        self._last_error = error
        self._current_output = output

        # 更新被控对象
        self._update_plant(output, dt)

        # 通知回调
        if self._on_data:
            self._on_data(
                setpoint=self._target,
                actual=self._current_value,
                output=output,
                p_term=p_term,
                i_term=i_term,
                d_term=d_term
            )

    def _update_plant(self, input_value: float, dt: float):
        """更新被控对象模型（一阶加滞后）"""
        # 将输入加入延迟缓冲
        self._delay_buffer.append(input_value)
        delayed_input = self._delay_buffer.pop(0)

        # 一阶系统响应
        # dx/dt = (K*u - x) / tau
        tau = self._plant.time_constant
        k = self._plant.gain

        if tau > 0:
            alpha = dt / (tau + dt)
            self._current_value += alpha * (k * delayed_input - self._current_value)
        else:
            self._current_value = k * delayed_input

        # 添加噪声
        if self._plant.noise_level > 0:
            noise = random.gauss(0, self._plant.noise_level)
            self._current_value += noise

        # 添加扰动
        if self._plant.disturbance != 0:
            self._current_value += self._plant.disturbance * dt


class SimulatedSerialManager:
    """模拟串口管理器"""

    def __init__(self):
        self._connected = False
        self._simulator = PIDSimulator()

        # 回调
        self._on_connection_changed: Optional[Callable] = None
        self._on_realtime_data_received: Optional[Callable] = None
        self._on_pid_params_received: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # 模拟的PID参数
        self._pid_params = type('PIDParams', (), {'p': 1.0, 'i': 0.1, 'd': 0.01})()

        # 信号节流
        self._last_emit_time: float = 0.0
        self._emit_interval: float = 0.05  # 50ms，约20fps

        # 设置模拟器回调
        self._simulator.set_on_data(self._on_simulator_data)

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def set_on_connection_changed(self, callback: Callable):
        """设置连接状态变化回调"""
        self._on_connection_changed = callback

    def set_on_realtime_data_received(self, callback: Callable):
        """设置实时数据接收回调"""
        self._on_realtime_data_received = callback

    def set_on_pid_params_received(self, callback: Callable):
        """设置PID参数接收回调"""
        self._on_pid_params_received = callback

    def set_on_error(self, callback: Callable):
        """设置错误回调"""
        self._on_error = callback

    def connect(self, config=None) -> bool:
        """连接（模拟）"""
        self._connected = True
        if self._on_connection_changed:
            self._on_connection_changed(True)
        return True

    def disconnect(self):
        """断开（模拟）"""
        self._simulator.stop()
        self._connected = False
        if self._on_connection_changed:
            self._on_connection_changed(False)

    def read_pid_params(self) -> bool:
        """读取PID参数（模拟）"""
        if self._on_pid_params_received:
            self._on_pid_params_received(self._pid_params)
        return True

    def write_pid_params(self, params) -> bool:
        """写入PID参数（模拟）"""
        self._pid_params = params
        self._simulator.set_pid_params(params.p, params.i, params.d)
        return True

    def set_target_value(self, target: float) -> bool:
        """设置目标值（模拟）"""
        self._simulator.set_target(target)
        return True

    def start_control(self) -> bool:
        """启动控制（模拟）"""
        self._simulator.set_pid_params(
            self._pid_params.p,
            self._pid_params.i,
            self._pid_params.d
        )
        self._simulator.start()
        return True

    def stop_control(self) -> bool:
        """停止控制（模拟）"""
        # 先清回调，再停止，避免停止过程中还发信号
        self._simulator.set_on_data(None)
        self._simulator.stop()
        # 重新绑定回调
        self._simulator.set_on_data(self._on_simulator_data)
        return True

    def _on_simulator_data(self, setpoint, actual, output, p_term, i_term, d_term):
        """模拟器数据回调（带节流）"""
        now = time.time()
        if now - self._last_emit_time < self._emit_interval:
            return
        self._last_emit_time = now

        if self._on_realtime_data_received:
            data = type('RealtimeData', (), {
                'setpoint': setpoint,
                'actual': actual,
                'output': output
            })()
            self._on_realtime_data_received(data)

    @staticmethod
    def list_ports() -> list:
        """列出串口（模拟）"""
        return [
            {'port': 'SIM_COM1', 'description': '模拟串口 1'},
            {'port': 'SIM_COM2', 'description': '模拟串口 2'},
        ]
