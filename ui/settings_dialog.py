#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设置对话框模块
提供应用程序设置界面
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QLineEdit, QDialogButtonBox, QSlider, QColorDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from utils.config import config_manager


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 配置数据
        self._config = config_manager

        # 初始化界面
        self._init_ui()

        # 加载当前设置
        self._load_settings()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标签页
        self.tab_widget = QTabWidget()

        # 通用设置标签页
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "通用")

        # 串口设置标签页
        serial_tab = self._create_serial_tab()
        self.tab_widget.addTab(serial_tab, "串口")

        # 图表设置标签页
        chart_tab = self._create_chart_tab()
        self.tab_widget.addTab(chart_tab, "图表")

        # 报警设置标签页
        alarm_tab = self._create_alarm_tab()
        self.tab_widget.addTab(alarm_tab, "报警")

        layout.addWidget(self.tab_widget)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(button_box)

    def _create_general_tab(self):
        """创建通用设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 界面设置组
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout()

        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "跟随系统"])
        ui_layout.addRow("主题:", self.theme_combo)

        # 语言选择
        self.language_combo = QComboBox()
        self.language_combo.addItems(["简体中文", "English"])
        ui_layout.addRow("语言:", self.language_combo)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(12)
        ui_layout.addRow("字体大小:", self.font_size_spin)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # 自动保存设置组
        save_group = QGroupBox("自动保存")
        save_layout = QFormLayout()

        self.auto_save_check = QCheckBox("启用自动保存")
        save_layout.addRow("", self.auto_save_check)

        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setValue(5)
        self.auto_save_interval.setSuffix(" 分钟")
        save_layout.addRow("保存间隔:", self.auto_save_interval)

        save_group.setLayout(save_layout)
        layout.addWidget(save_group)

        layout.addStretch()
        return tab

    def _create_serial_tab(self):
        """创建串口设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 默认配置组
        default_group = QGroupBox("默认串口配置")
        default_layout = QFormLayout()

        # 默认波特率
        self.default_baud_combo = QComboBox()
        self.default_baud_combo.setEditable(True)
        self.default_baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600"
        ])
        self.default_baud_combo.setCurrentText("115200")
        default_layout.addRow("默认波特率:", self.default_baud_combo)

        # 默认数据位
        self.default_data_bits = QComboBox()
        self.default_data_bits.addItems(["5", "6", "7", "8"])
        self.default_data_bits.setCurrentText("8")
        default_layout.addRow("数据位:", self.default_data_bits)

        # 默认停止位
        self.default_stop_bits = QComboBox()
        self.default_stop_bits.addItems(["1", "1.5", "2"])
        self.default_stop_bits.setCurrentText("1")
        default_layout.addRow("停止位:", self.default_stop_bits)

        # 默认校验位
        self.default_parity = QComboBox()
        self.default_parity.addItems(["无", "奇", "偶"])
        self.default_parity.setCurrentText("无")
        default_layout.addRow("校验位:", self.default_parity)

        default_group.setLayout(default_layout)
        layout.addWidget(default_group)

        # 自动重连设置组
        reconnect_group = QGroupBox("自动重连")
        reconnect_layout = QFormLayout()

        self.auto_reconnect_check = QCheckBox("启用自动重连")
        reconnect_layout.addRow("", self.auto_reconnect_check)

        self.reconnect_interval = QSpinBox()
        self.reconnect_interval.setRange(1, 30)
        self.reconnect_interval.setValue(3)
        self.reconnect_interval.setSuffix(" 秒")
        reconnect_layout.addRow("重连间隔:", self.reconnect_interval)

        reconnect_group.setLayout(reconnect_layout)
        layout.addWidget(reconnect_group)

        layout.addStretch()
        return tab

    def _create_chart_tab(self):
        """创建图表设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_layout = QFormLayout()

        # 默认时间窗口
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setRange(1, 3600)
        self.time_window_spin.setValue(10)
        self.time_window_spin.setSuffix(" 秒")
        display_layout.addRow("默认时间窗口:", self.time_window_spin)

        # 最大数据点数
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 10000)
        self.max_points_spin.setValue(1000)
        display_layout.addRow("最大数据点数:", self.max_points_spin)

        # 自动滚动
        self.auto_scroll_check = QCheckBox("默认启用自动滚动")
        display_layout.addRow("", self.auto_scroll_check)

        # 抗锯齿
        self.antialias_check = QCheckBox("启用抗锯齿")
        display_layout.addRow("", self.antialias_check)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # 曲线颜色设置组
        color_group = QGroupBox("曲线颜色")
        color_layout = QFormLayout()

        # 设定值颜色
        self.setpoint_color_btn = QPushButton()
        self.setpoint_color_btn.setFixedSize(60, 30)
        self.setpoint_color_btn.setStyleSheet("background-color: #007AFF;")
        self.setpoint_color_btn.clicked.connect(lambda: self._pick_color(self.setpoint_color_btn))
        color_layout.addRow("设定值:", self.setpoint_color_btn)

        # 实际值颜色
        self.actual_color_btn = QPushButton()
        self.actual_color_btn.setFixedSize(60, 30)
        self.actual_color_btn.setStyleSheet("background-color: #34C759;")
        self.actual_color_btn.clicked.connect(lambda: self._pick_color(self.actual_color_btn))
        color_layout.addRow("实际值:", self.actual_color_btn)

        # 输出值颜色
        self.output_color_btn = QPushButton()
        self.output_color_btn.setFixedSize(60, 30)
        self.output_color_btn.setStyleSheet("background-color: #FF9500;")
        self.output_color_btn.clicked.connect(lambda: self._pick_color(self.output_color_btn))
        color_layout.addRow("输出值:", self.output_color_btn)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        layout.addStretch()
        return tab

    def _create_alarm_tab(self):
        """创建报警设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 报警限制组
        limit_group = QGroupBox("报警限制")
        limit_layout = QFormLayout()

        self.value_high_spin = QDoubleSpinBox()
        self.value_high_spin.setRange(-10000, 10000)
        self.value_high_spin.setDecimals(2)
        self.value_high_spin.setValue(100.0)
        limit_layout.addRow("值上限:", self.value_high_spin)

        self.value_low_spin = QDoubleSpinBox()
        self.value_low_spin.setRange(-10000, 10000)
        self.value_low_spin.setDecimals(2)
        self.value_low_spin.setValue(-100.0)
        limit_layout.addRow("值下限:", self.value_low_spin)

        self.error_high_spin = QDoubleSpinBox()
        self.error_high_spin.setRange(0, 10000)
        self.error_high_spin.setDecimals(2)
        self.error_high_spin.setValue(10.0)
        limit_layout.addRow("误差上限:", self.error_high_spin)

        limit_group.setLayout(limit_layout)
        layout.addWidget(limit_group)

        # 报警延迟组
        delay_group = QGroupBox("报警延迟")
        delay_layout = QFormLayout()

        self.alarm_delay_spin = QDoubleSpinBox()
        self.alarm_delay_spin.setRange(0, 60)
        self.alarm_delay_spin.setDecimals(1)
        self.alarm_delay_spin.setValue(1.0)
        self.alarm_delay_spin.setSuffix(" 秒")
        delay_layout.addRow("报警延迟:", self.alarm_delay_spin)

        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)

        # 报警通知组
        notify_group = QGroupBox("报警通知")
        notify_layout = QFormLayout()

        self.sound_check = QCheckBox("启用声音报警")
        notify_layout.addRow("", self.sound_check)

        self.popup_check = QCheckBox("启用弹窗报警")
        notify_layout.addRow("", self.popup_check)

        notify_group.setLayout(notify_layout)
        layout.addWidget(notify_group)

        layout.addStretch()
        return tab

    def _pick_color(self, button):
        """选择颜色"""
        current_color = button.palette().button().color()
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()};")

    def _load_settings(self):
        """加载当前设置"""
        # 串口设置
        serial_config = self._config.serial
        self.default_baud_combo.setCurrentText(str(serial_config.baudrate))

        # 图表设置
        chart_config = self._config.chart
        self.time_window_spin.setValue(chart_config.time_window)
        self.max_points_spin.setValue(chart_config.max_points)
        self.auto_scroll_check.setChecked(chart_config.auto_scroll)

    def _save_settings(self):
        """保存设置"""
        # 串口设置
        try:
            self._config.serial.baudrate = int(self.default_baud_combo.currentText())
        except ValueError:
            pass

        # 图表设置
        self._config.chart.time_window = self.time_window_spin.value()
        self._config.chart.max_points = self.max_points_spin.value()
        self._config.chart.auto_scroll = self.auto_scroll_check.isChecked()

        # 保存到文件
        self._config.save()

    def _on_accept(self):
        """确定按钮点击"""
        self._save_settings()
        self.accept()

    def _on_apply(self):
        """应用按钮点击"""
        self._save_settings()
