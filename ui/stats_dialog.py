#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据统计对话框
显示详细的数据统计信息
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QGroupBox, QFormLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core.data_recorder import DataStatistics


class StatsDialog(QDialog):
    """数据统计对话框"""

    def __init__(self, stats: DataStatistics, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据统计")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._stats = stats

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标签页
        tab_widget = QTabWidget()

        # 基本统计标签页
        basic_tab = self._create_basic_tab()
        tab_widget.addTab(basic_tab, "基本统计")

        # 性能指标标签页
        performance_tab = self._create_performance_tab()
        tab_widget.addTab(performance_tab, "性能指标")

        # 详细数据标签页
        detail_tab = self._create_detail_tab()
        tab_widget.addTab(detail_tab, "详细数据")

        layout.addWidget(tab_widget)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _create_basic_tab(self):
        """创建基本统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 数据概览组
        overview_group = QGroupBox("数据概览")
        overview_layout = QFormLayout()

        overview_layout.addRow("数据点数量:", QLabel(str(self._stats.count)))
        overview_layout.addRow("记录时长:", QLabel(f"{self._stats.duration:.2f} 秒"))

        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group)

        # 设定值统计组
        setpoint_group = QGroupBox("设定值统计")
        setpoint_layout = QFormLayout()

        setpoint_layout.addRow("最小值:", QLabel(f"{self._stats.setpoint_min:.3f}"))
        setpoint_layout.addRow("最大值:", QLabel(f"{self._stats.setpoint_max:.3f}"))
        setpoint_layout.addRow("平均值:", QLabel(f"{self._stats.setpoint_avg:.3f}"))

        setpoint_group.setLayout(setpoint_layout)
        layout.addWidget(setpoint_group)

        # 实际值统计组
        actual_group = QGroupBox("实际值统计")
        actual_layout = QFormLayout()

        actual_layout.addRow("最小值:", QLabel(f"{self._stats.actual_min:.3f}"))
        actual_layout.addRow("最大值:", QLabel(f"{self._stats.actual_max:.3f}"))
        actual_layout.addRow("平均值:", QLabel(f"{self._stats.actual_avg:.3f}"))

        actual_group.setLayout(actual_layout)
        layout.addWidget(actual_group)

        layout.addStretch()
        return tab

    def _create_performance_tab(self):
        """创建性能指标标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 误差统计组
        error_group = QGroupBox("误差统计")
        error_layout = QFormLayout()

        error_layout.addRow("最小误差:", QLabel(f"{self._stats.error_min:.3f}"))
        error_layout.addRow("最大误差:", QLabel(f"{self._stats.error_max:.3f}"))
        error_layout.addRow("平均误差:", QLabel(f"{self._stats.error_avg:.3f}"))
        error_layout.addRow("均方根误差:", QLabel(f"{self._stats.error_rms:.3f}"))

        error_group.setLayout(error_layout)
        layout.addWidget(error_group)

        # 性能指标组
        performance_group = QGroupBox("性能指标")
        performance_layout = QFormLayout()

        performance_layout.addRow("超调量:", QLabel(f"{self._stats.overshoot:.2f}%"))
        performance_layout.addRow("上升时间:", QLabel(f"{self._stats.rise_time:.3f} 秒"))
        performance_layout.addRow("稳定时间:", QLabel(f"{self._stats.settling_time:.3f} 秒"))

        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)

        # 评估组
        evaluation_group = QGroupBox("性能评估")
        evaluation_layout = QVBoxLayout()

        # 计算评估分数
        score = self._calculate_score()
        score_label = QLabel(f"综合评分: {score:.1f}/100")
        score_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #007AFF;")
        evaluation_layout.addWidget(score_label)

        # 添加评估说明
        if score >= 90:
            evaluation = "优秀 - 系统响应快速且稳定"
        elif score >= 70:
            evaluation = "良好 - 系统响应基本满足要求"
        elif score >= 50:
            evaluation = "一般 - 系统响应有待改进"
        else:
            evaluation = "较差 - 系统响应需要优化"

        eval_label = QLabel(evaluation)
        eval_label.setStyleSheet("font-size: 14px; color: #8E8E93;")
        evaluation_layout.addWidget(eval_label)

        evaluation_group.setLayout(evaluation_layout)
        layout.addWidget(evaluation_group)

        layout.addStretch()
        return tab

    def _create_detail_tab(self):
        """创建详细数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 创建表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["指标", "值"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)

        # 添加数据行
        data = [
            ("数据点数量", str(self._stats.count)),
            ("记录时长", f"{self._stats.duration:.2f} 秒"),
            ("设定值最小值", f"{self._stats.setpoint_min:.3f}"),
            ("设定值最大值", f"{self._stats.setpoint_max:.3f}"),
            ("设定值平均值", f"{self._stats.setpoint_avg:.3f}"),
            ("实际值最小值", f"{self._stats.actual_min:.3f}"),
            ("实际值最大值", f"{self._stats.actual_max:.3f}"),
            ("实际值平均值", f"{self._stats.actual_avg:.3f}"),
            ("误差最小值", f"{self._stats.error_min:.3f}"),
            ("误差最大值", f"{self._stats.error_max:.3f}"),
            ("误差平均值", f"{self._stats.error_avg:.3f}"),
            ("均方根误差", f"{self._stats.error_rms:.3f}"),
            ("超调量", f"{self._stats.overshoot:.2f}%"),
            ("上升时间", f"{self._stats.rise_time:.3f} 秒"),
            ("稳定时间", f"{self._stats.settling_time:.3f} 秒"),
        ]

        table.setRowCount(len(data))
        for i, (name, value) in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(value))

        layout.addWidget(table)
        return tab

    def _calculate_score(self):
        """计算综合评分"""
        score = 100.0

        # 根据超调量扣分
        if self._stats.overshoot > 10:
            score -= min(30, self._stats.overshoot * 2)

        # 根据稳定时间扣分
        if self._stats.settling_time > 5:
            score -= min(20, (self._stats.settling_time - 5) * 2)

        # 根据误差扣分
        if self._stats.error_rms > 1:
            score -= min(20, self._stats.error_rms * 5)

        return max(0, score)
