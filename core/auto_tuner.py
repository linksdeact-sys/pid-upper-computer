#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动调参模块
实现多种PID自动调参算法
"""

import time
import math
import threading
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TuningMethod(Enum):
    """调参方法"""
    ZIEGLER_NICHOLS = "Ziegler-Nichols"
    COHEN_COON = "Cohen-Coon"
    RELAY_FEEDBACK = "Relay Feedback"
    AMIGO = "AMIGO"


@dataclass
class TuningResult:
    """调参结果"""
    method: TuningMethod
    kp: float
    ki: float
    kd: float
    ku: float = 0.0        # 临界增益
    tu: float = 0.0        # 临界周期
    gain: float = 0.0      # 过程增益
    tau: float = 0.0       # 时间常数
    delay: float = 0.0     # 死区时间
    confidence: float = 0.0  # 置信度
    description: str = ""


@dataclass
class ProcessModel:
    """过程模型"""
    gain: float = 1.0       # 过程增益 K
    tau: float = 1.0        # 时间常数 τ
    delay: float = 0.1      # 死区时间 θ


class PIDAutoTuner:
    """PID自动调参器"""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_method: Optional[TuningMethod] = None

        # 回调函数
        self._on_progress: Optional[Callable] = None
        self._on_result: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_status: Optional[Callable] = None

        # 调参参数
        self._target_value: float = 100.0
        self._output_min: float = 0.0
        self._output_max: float = 100.0
        self._sample_time: float = 0.1

        # 读写回调
        self._read_process_value: Optional[Callable] = None
        self._write_output: Optional[Callable] = None

    # 回调设置

    def set_on_progress(self, callback: Callable):
        """设置进度回调"""
        self._on_progress = callback

    def set_on_result(self, callback: Callable):
        """设置结果回调"""
        self._on_result = callback

    def set_on_error(self, callback: Callable):
        """设置错误回调"""
        self._on_error = callback

    def set_on_status(self, callback: Callable):
        """设置状态回调"""
        self._on_status = callback

    def set_process_callbacks(self, read_func: Callable, write_func: Callable):
        """设置过程读写回调"""
        self._read_process_value = read_func
        self._write_output = write_func

    def set_parameters(self, target: float, output_min: float, output_max: float,
                       sample_time: float = 0.1):
        """设置调参参数"""
        self._target_value = target
        self._output_min = output_min
        self._output_max = output_max
        self._sample_time = sample_time

    @property
    def is_running(self) -> bool:
        """是否正在调参"""
        return self._running

    def stop(self):
        """停止调参"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def start(self, method: TuningMethod):
        """开始调参"""
        if self._running:
            self._notify_error("调参正在进行中")
            return

        self._running = True
        self._current_method = method

        self._thread = threading.Thread(target=self._run_tuning, args=(method,), daemon=True)
        self._thread.start()

    def _run_tuning(self, method: TuningMethod):
        """运行调参"""
        try:
            self._notify_status(f"开始 {method.value} 调参...")

            if method == TuningMethod.ZIEGLER_NICHOLS:
                result = self._ziegler_nichols_method()
            elif method == TuningMethod.COHEN_COON:
                result = self._cohen_coon_method()
            elif method == TuningMethod.RELAY_FEEDBACK:
                result = self._relay_feedback_method()
            elif method == TuningMethod.AMIGO:
                result = self._amigo_method()
            else:
                raise ValueError(f"不支持的调参方法: {method}")

            if result and self._running:
                self._notify_result(result)
                self._notify_status(f"调参完成: Kp={result.kp:.3f}, Ki={result.ki:.3f}, Kd={result.kd:.3f}")

        except Exception as e:
            self._notify_error(f"调参失败: {str(e)}")
        finally:
            self._running = False

    # Ziegler-Nichols方法

    def _ziegler_nichols_method(self) -> Optional[TuningResult]:
        """
        Ziegler-Nichols临界比例法
        1. 仅使用比例控制
        2. 逐渐增加增益直到系统产生等幅振荡
        3. 记录临界增益Ku和振荡周期Tu
        4. 根据公式计算PID参数
        """
        if not self._read_process_value or not self._write_output:
            self._notify_error("未设置过程读写回调")
            return None

        self._notify_status("阶段1: 寻找临界增益...")

        # 初始增益
        kp = 0.5
        max_kp = 100.0
        step = 0.5

        # 存储振荡数据
        last_values = []
        target = self._target_value

        while self._running and kp < max_kp:
            # 设置纯比例控制
            self._write_output(kp * (target - self._read_process_value()))

            time.sleep(self._sample_time)

            current = self._read_process_value()
            last_values.append(current)

            # 检测振荡
            if len(last_values) > 20:
                last_values = last_values[-20:]

                # 检测过零点
                zero_crossings = 0
                for i in range(1, len(last_values)):
                    if (last_values[i-1] - target) * (last_values[i] - target) < 0:
                        zero_crossings += 1

                # 如果有足够的过零点，认为产生了振荡
                if zero_crossings >= 4:
                    # 计算振荡周期
                    periods = []
                    crossing_times = []
                    for i in range(1, len(last_values)):
                        if (last_values[i-1] - target) * (last_values[i] - target) < 0:
                            crossing_times.append(i * self._sample_time)

                    if len(crossing_times) >= 3:
                        for i in range(1, len(crossing_times)):
                            periods.append(crossing_times[i] - crossing_times[i-1])

                        if periods:
                            tu = sum(periods) / len(periods) * 2  # 完整周期
                            ku = kp

                            self._notify_progress(50, f"找到临界增益: Ku={ku:.2f}, Tu={tu:.2f}s")

                            # Ziegler-Nichols公式
                            result = TuningResult(
                                method=TuningMethod.ZIEGLER_NICHOLS,
                                kp=0.6 * ku,
                                ki=1.2 * ku / tu,
                                kd=0.075 * ku * tu,
                                ku=ku,
                                tu=tu,
                                confidence=0.7,
                                description="Ziegler-Nichols临界比例法"
                            )

                            self._notify_progress(100, "调参完成")
                            return result

            # 增加增益
            kp += step
            self._notify_progress(min(40, kp / max_kp * 40), f"当前增益: {kp:.2f}")

        self._notify_error("无法找到临界增益")
        return None

    # Cohen-Coon方法

    def _cohen_coon_method(self) -> Optional[TuningResult]:
        """
        Cohen-Coon方法
        1. 进行阶跃响应测试
        2. 识别过程模型参数（增益K、时间常数τ、死区时间θ）
        3. 根据公式计算PID参数
        """
        if not self._read_process_value or not self._write_output:
            self._notify_error("未设置过程读写回调")
            return None

        self._notify_status("阶段1: 阶跃响应测试...")

        # 记录初始值
        initial_output = self._output_max * 0.5
        step_size = self._output_max * 0.2

        # 施加阶跃
        self._write_output(initial_output)
        time.sleep(2.0)  # 等待稳定
        initial_value = self._read_process_value()

        # 施加阶跃变化
        self._write_output(initial_output + step_size)
        step_time = time.time()

        # 记录响应
        response_data = []
        test_duration = 30.0  # 测试持续时间

        while self._running and (time.time() - step_time) < test_duration:
            current_time = time.time() - step_time
            current_value = self._read_process_value()
            response_data.append((current_time, current_value))

            progress = current_time / test_duration * 60
            self._notify_progress(progress, f"记录响应数据: {current_time:.1f}s")

            time.sleep(self._sample_time)

        # 恢复输出
        self._write_output(initial_output)

        if not response_data:
            self._notify_error("未收集到响应数据")
            return None

        self._notify_status("阶段2: 识别过程模型...")

        # 识别过程模型
        model = self._identify_process_model(response_data, initial_value, step_size)

        if model is None:
            self._notify_error("过程模型识别失败")
            return None

        self._notify_progress(70, f"模型参数: K={model.gain:.3f}, τ={model.tau:.3f}, θ={model.delay:.3f}")

        # Cohen-Coon公式
        k = model.gain
        tau = model.tau
        theta = model.delay

        if theta == 0:
            theta = 0.01  # 避免除零

        r = theta / tau  # 死区时间比

        kp = (1 / k) * (tau / theta) * (1 + r / 3)
        ki = kp / (theta * (32 + 6 * r) / (13 + 8 * r))
        kd = kp * theta * 4 / (11 + 2 * r)

        result = TuningResult(
            method=TuningMethod.COHEN_COON,
            kp=kp,
            ki=ki,
            kd=kd,
            gain=k,
            tau=tau,
            delay=theta,
            confidence=0.8,
            description="Cohen-Coon阶跃响应法"
        )

        self._notify_progress(100, "调参完成")
        return result

    def _identify_process_model(self, response_data: List[Tuple[float, float]],
                                 initial_value: float, step_size: float) -> Optional[ProcessModel]:
        """识别过程模型（一阶加滞后）"""
        if len(response_data) < 10:
            return None

        # 找到63.2%响应点（时间常数）
        final_value = response_data[-1][1]
        total_change = final_value - initial_value

        if abs(total_change) < 0.001:
            return None

        target_63 = initial_value + total_change * 0.632

        tau_time = None
        delay_time = None

        for t, v in response_data:
            if delay_time is None and v > initial_value + total_change * 0.05:
                delay_time = t
            if tau_time is None and v >= target_63:
                tau_time = t
                break

        if tau_time is None:
            tau_time = response_data[-1][0]

        # 计算模型参数
        gain = total_change / step_size
        tau = tau_time - (delay_time or 0)
        delay = delay_time or 0.01

        if tau <= 0:
            tau = 0.1

        return ProcessModel(gain=gain, tau=tau, delay=delay)

    # 继电反馈法

    def _relay_feedback_method(self) -> Optional[TuningResult]:
        """
        继电反馈法（Åström-Hägglund）
        1. 使用继电（bang-bang）控制
        2. 测量产生的极限环振荡
        3. 从振荡中提取临界增益和周期
        """
        if not self._read_process_value or not self._write_output:
            self._notify_error("未设置过程读写回调")
            return None

        self._notify_status("阶段1: 继电反馈测试...")

        target = self._target_value
        relay_amplitude = (self._output_max - self._output_min) * 0.25
        relay_offset = (self._output_max + self._output_min) / 2
        hysteresis = relay_amplitude * 0.1

        # 记录振荡数据
        oscillation_data = []
        test_duration = 60.0  # 测试持续时间
        start_time = time.time()

        relay_high = True
        last_switch_time = start_time

        while self._running and (time.time() - start_time) < test_duration:
            current_value = self._read_process_value()
            current_time = time.time() - start_time
            error = target - current_value

            # 继电控制
            if relay_high:
                output = relay_offset + relay_amplitude
                if error < -hysteresis:
                    relay_high = False
                    last_switch_time = time.time()
            else:
                output = relay_offset - relay_amplitude
                if error > hysteresis:
                    relay_high = True
                    last_switch_time = time.time()

            self._write_output(output)
            oscillation_data.append((current_time, current_value, output))

            progress = current_time / test_duration * 60
            self._notify_progress(progress, f"继电测试: {current_time:.1f}s")

            time.sleep(self._sample_time)

        # 恢复输出
        self._write_output(relay_offset)

        if len(oscillation_data) < 50:
            self._notify_error("振荡数据不足")
            return None

        self._notify_status("阶段2: 分析振荡数据...")

        # 分析振荡
        values = [d[1] for d in oscillation_data]

        # 找到峰值
        peaks = []
        troughs = []
        for i in range(2, len(values) - 2):
            if values[i] > values[i-1] and values[i] > values[i+1] and \
               values[i] > values[i-2] and values[i] > values[i+2]:
                peaks.append((oscillation_data[i][0], values[i]))
            elif values[i] < values[i-1] and values[i] < values[i+1] and \
                 values[i] < values[i-2] and values[i] < values[i+2]:
                troughs.append((oscillation_data[i][0], values[i]))

        if len(peaks) < 2 or len(troughs) < 2:
            self._notify_error("无法检测到足够的振荡峰值")
            return None

        # 计算振荡幅度和周期
        peak_values = [p[1] for p in peaks]
        trough_values = [t[1] for t in troughs]

        amplitude = (sum(peak_values) / len(peak_values) - sum(trough_values) / len(trough_values)) / 2

        # 计算周期
        periods = []
        for i in range(1, len(peaks)):
            periods.append(peaks[i][0] - peaks[i-1][0])

        if not periods:
            self._notify_error("无法计算振荡周期")
            return None

        tu = sum(periods) / len(periods)

        # 计算临界增益 (Åström-Hägglund公式)
        ku = (4 * relay_amplitude) / (math.pi * amplitude)

        self._notify_progress(80, f"临界增益: Ku={ku:.3f}, 周期: Tu={tu:.3f}s")

        # 使用Ziegler-Nichols公式
        kp = 0.6 * ku
        ki = 1.2 * ku / tu
        kd = 0.075 * ku * tu

        result = TuningResult(
            method=TuningMethod.RELAY_FEEDBACK,
            kp=kp,
            ki=ki,
            kd=kd,
            ku=ku,
            tu=tu,
            confidence=0.85,
            description="继电反馈法 (Åström-Hägglund)"
        )

        self._notify_progress(100, "调参完成")
        return result

    # AMIGO方法

    def _amigo_method(self) -> Optional[TuningResult]:
        """
        AMIGO方法 (Approximate M-constrained Integral Gain Optimization)
        基于阶跃响应的调参方法
        """
        if not self._read_process_value or not self._write_output:
            self._notify_error("未设置过程读写回调")
            return None

        self._notify_status("阶段1: 阶跃响应测试...")

        # 阶跃响应测试（与Cohen-Coon类似）
        initial_output = self._output_max * 0.5
        step_size = self._output_max * 0.2

        self._write_output(initial_output)
        time.sleep(2.0)
        initial_value = self._read_process_value()

        self._write_output(initial_output + step_size)
        step_time = time.time()

        response_data = []
        test_duration = 30.0

        while self._running and (time.time() - step_time) < test_duration:
            current_time = time.time() - step_time
            current_value = self._read_process_value()
            response_data.append((current_time, current_value))

            progress = current_time / test_duration * 50
            self._notify_progress(progress, f"记录响应: {current_time:.1f}s")

            time.sleep(self._sample_time)

        self._write_output(initial_output)

        if not response_data:
            self._notify_error("未收集到响应数据")
            return None

        self._notify_status("阶段2: 计算PID参数...")

        # 识别模型
        model = self._identify_process_model(response_data, initial_value, step_size)

        if model is None:
            self._notify_error("过程模型识别失败")
            return None

        k = model.gain
        tau = model.tau
        theta = model.delay

        if theta == 0:
            theta = 0.01

        # AMIGO公式
        kp = (0.2 + 0.45 * tau / theta) / k
        ki = kp / (theta * (0.4 * theta + 0.8 * tau) / (theta + 0.1 * tau))
        kd = kp * (0.5 * theta * tau) / (0.3 * theta + tau)

        result = TuningResult(
            method=TuningMethod.AMIGO,
            kp=kp,
            ki=ki,
            kd=kd,
            gain=k,
            tau=tau,
            delay=theta,
            confidence=0.85,
            description="AMIGO方法 (Approximate M-constrained Integral Gain Optimization)"
        )

        self._notify_progress(100, "调参完成")
        return result

    # 通知方法

    def _notify_progress(self, progress: float, message: str = ""):
        """通知进度"""
        if self._on_progress:
            self._on_progress(progress, message)

    def _notify_result(self, result: TuningResult):
        """通知结果"""
        if self._on_result:
            self._on_result(result)

    def _notify_error(self, message: str):
        """通知错误"""
        if self._on_error:
            self._on_error(message)

    def _notify_status(self, message: str):
        """通知状态"""
        if self._on_status:
            self._on_status(message)
