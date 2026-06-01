#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图表模块
使用pyqtgraph实现实时图表显示
"""

import time
from collections import deque
from typing import Optional, List

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor


class RealtimeChart(QWidget):
    """实时图表组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 数据缓冲区
        self._max_points = 1000
        self._time_data = deque(maxlen=self._max_points)
        self._setpoint_data = deque(maxlen=self._max_points)
        self._actual_data = deque(maxlen=self._max_points)
        self._output_data = deque(maxlen=self._max_points)
        self._error_data = deque(maxlen=self._max_points)

        # 时间窗口（秒）
        self._time_window = 10.0

        # 开始时间
        self._start_time: Optional[float] = None

        # 自动滚动
        self._auto_scroll = True

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图表
        pg.setConfigOptions(antialias=True)

        # 主图表（设定值和实际值）
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground('#F8F8FA')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel('left', '值', color='#1C1C1E')
        self._plot_widget.setLabel('bottom', '时间 (秒)', color='#1C1C1E')
        self._plot_widget.addLegend()

        # 设置画笔颜色（iOS风格）
        self._setpoint_pen = pg.mkPen(color='#007AFF', width=2, style=Qt.DashLine)
        self._actual_pen = pg.mkPen(color='#34C759', width=2)
        self._output_pen = pg.mkPen(color='#FF9500', width=1, style=Qt.DotLine)

        # 创建曲线
        self._setpoint_curve = self._plot_widget.plot(
            pen=self._setpoint_pen, name='设定值'
        )
        self._actual_curve = self._plot_widget.plot(
            pen=self._actual_pen, name='实际值'
        )

        layout.addWidget(self._plot_widget)

        # 输出图表（单独显示）
        self._output_plot = pg.PlotWidget()
        self._output_plot.setBackground('#F8F8FA')
        self._output_plot.showGrid(x=True, y=True, alpha=0.3)
        self._output_plot.setLabel('left', '输出', color='#1C1C1E')
        self._output_plot.setLabel('bottom', '时间 (秒)', color='#1C1C1E')
        self._output_plot.setFixedHeight(150)

        self._output_curve = self._output_plot.plot(
            pen=self._output_pen, name='输出'
        )

        layout.addWidget(self._output_plot)

    def set_time_window(self, seconds: float):
        """设置时间窗口"""
        self._time_window = seconds

    def set_auto_scroll(self, enabled: bool):
        """设置自动滚动"""
        self._auto_scroll = enabled

    def add_data(self, setpoint: float, actual: float, output: float,
                 timestamp: Optional[float] = None):
        """添加数据点"""
        if timestamp is None:
            timestamp = time.time()

        if self._start_time is None:
            self._start_time = timestamp

        # 计算相对时间
        relative_time = timestamp - self._start_time

        # 添加数据
        self._time_data.append(relative_time)
        self._setpoint_data.append(setpoint)
        self._actual_data.append(actual)
        self._output_data.append(output)
        self._error_data.append(setpoint - actual)

        # 更新图表
        self._update_plot()

    def _update_plot(self):
        """更新图表显示"""
        if not self._time_data:
            return

        # 转换为numpy数组
        time_array = np.array(self._time_data)
        setpoint_array = np.array(self._setpoint_data)
        actual_array = np.array(self._actual_data)
        output_array = np.array(self._output_data)

        # 更新曲线数据
        self._setpoint_curve.setData(time_array, setpoint_array)
        self._actual_curve.setData(time_array, actual_array)
        self._output_curve.setData(time_array, output_array)

        # 自动滚动
        if self._auto_scroll and len(time_array) > 0:
            x_max = time_array[-1]
            x_min = max(0, x_max - self._time_window)
            self._plot_widget.setXRange(x_min, x_max, padding=0)
            self._output_plot.setXRange(x_min, x_max, padding=0)

    def clear(self):
        """清除数据"""
        self._time_data.clear()
        self._setpoint_data.clear()
        self._actual_data.clear()
        self._output_data.clear()
        self._error_data.clear()
        self._start_time = None

        # 清除曲线
        self._setpoint_curve.clear()
        self._actual_curve.clear()
        self._output_curve.clear()

    def get_screenshot(self):
        """获取截图"""
        return self._plot_widget.grab()


class DataStatsWidget(QWidget):
    """数据统计组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 数据
        self._data_count = 0
        self._min_value = float('inf')
        self._max_value = float('-inf')
        self._sum_value = 0.0
        self._last_value = 0.0

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # 创建统计标签
        self._count_label = QLabel("数据: 0")
        self._min_label = QLabel("最小: --")
        self._max_label = QLabel("最大: --")
        self._avg_label = QLabel("平均: --")
        self._last_label = QLabel("当前: --")

        labels = [self._count_label, self._min_label, self._max_label,
                  self._avg_label, self._last_label]

        for i, label in enumerate(labels):
            label.setStyleSheet("color: #8E8E93; font-size: 12px;")
            layout.addWidget(label)
            if i < len(labels) - 1:
                layout.addWidget(QLabel("|"))

        layout.addStretch()

    def add_value(self, value: float):
        """添加值"""
        self._data_count += 1
        self._sum_value += value
        self._last_value = value

        if value < self._min_value:
            self._min_value = value
        if value > self._max_value:
            self._max_value = value

        self._update_labels()

    def _update_labels(self):
        """更新标签"""
        self._count_label.setText(f"数据: {self._data_count}")

        if self._data_count > 0:
            self._min_label.setText(f"最小: {self._min_value:.2f}")
            self._max_label.setText(f"最大: {self._max_value:.2f}")
            self._avg_label.setText(f"平均: {self._sum_value / self._data_count:.2f}")
            self._last_label.setText(f"当前: {self._last_value:.2f}")

    def clear(self):
        """清除数据"""
        self._data_count = 0
        self._min_value = float('inf')
        self._max_value = float('-inf')
        self._sum_value = 0.0
        self._last_value = 0.0

        self._count_label.setText("数据: 0")
        self._min_label.setText("最小: --")
        self._max_label.setText("最大: --")
        self._avg_label.setText("平均: --")
        self._last_label.setText("当前: --")
