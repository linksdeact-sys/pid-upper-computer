#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口模块 - 原生iOS/macOS风格
严格遵循Apple Human Interface Guidelines
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QAction, QToolBar, QStatusBar,
    QSplitter, QGroupBox, QLabel, QComboBox, QPushButton,
    QLineEdit, QFormLayout, QCheckBox, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QDockWidget, QTabWidget, QMessageBox, QFileDialog,
    QGraphicsDropShadowEffect, QFrame, QProgressBar,
    QButtonGroup, QSlider, QApplication, QAbstractSpinBox,
    QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QRect
from PyQt5.QtGui import (
    QIcon, QFont, QColor, QPalette, QLinearGradient, QPixmap,
    QPainter, QPainterPath
)

from core.serial_manager import SerialManager, SerialConfig, ConnectionState
from core.simulator import SimulatedSerialManager
from core.data_recorder import DataRecorder
from core.auto_tuner import PIDAutoTuner, TuningMethod
from core.pid_controller import PIDController, PIDParams
from core.protocol import PIDParams as ProtocolPIDParams
from core.alarm import AlarmManager, AlarmLevel, AlarmEvent
from core.data_player import DataPlayer, PlaybackState
from ui.chart_widget import RealtimeChart, DataStatsWidget
from ui.settings_dialog import SettingsDialog
from ui.stats_dialog import StatsDialog
from ui.help_dialog import HelpDialog
from ui.import_dialog import ImportDialog
from ui.export_dialog import ExportDialog
from ui.compare_dialog import CompareDialog
from utils.config import config_manager
from utils.logger import logger


class IOSSectionHeader(QLabel):
    """iOS分组列表的Section Header - 全大写灰色小字"""

    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("iosSectionHeader")
        self.setContentsMargins(16, 8, 16, 4)


class IOSCard(QFrame):
    """iOS风格卡片 - 白色背景、无边框、细腻阴影"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("iosCard")
        self.setFrameShape(QFrame.NoFrame)

        # 布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 16)
        self.layout.setSpacing(10)

        # 标题（section header风格）
        if title:
            title_label = QLabel(title.upper())
            title_label.setObjectName("cardSectionHeader")
            self.layout.addWidget(title_label)
            self.layout.addSpacing(8)


class MainWindow(QMainWindow):
    """主窗口类 - 原生iOS/macOS风格"""

    # Apple官方系统颜色（严格遵循HIG）
    COLORS = {
        # 操作颜色
        'blue': '#007AFF',       # 主蓝 - 操作按钮
        'green': '#34C759',      # 绿 - 启动/运行
        'orange': '#FF9500',     # 橙 - 自动调参
        'red': '#FF3B30',        # 红 - 停止/警报
        'yellow': '#FFCC00',     # 黄 - 警告
        'purple': '#AF52DE',     # 紫
        'pink': '#FF2D55',       # 粉
        'teal': '#5AC8FA',       # 青
        'indigo': '#5856D6',     # 靛蓝

        # 背景色
        'systemGroupedBackground': '#F2F2F7',        # 主背景
        'secondarySystemGroupedBackground': '#FFFFFF', # 卡片背景
        'systemBackground': '#FFFFFF',
        'secondarySystemBackground': '#F2F2F7',
        'tertiarySystemBackground': '#E5E5EA',

        # 文字颜色
        'label': '#000000',                          # 主文字
        'secondaryLabel': '#3C3C4399',               # 次级文字（60%透明）
        'tertiaryLabel': '#8E8E93',                  # 三级文字
        'quaternaryLabel': '#3C3C432D',              # 四级文字

        # 分隔线
        'separator': '#3C3C432E',                    # rgba(60,60,67,0.18)
        'opaqueSeparator': '#C6C6C8',

        # 填充色
        'systemFill': '#78788033',
        'secondarySystemFill': '#78788028',
        'tertiarySystemFill': '#7676801E',
        'quaternarySystemFill': '#74748014',

        # 输入框背景
        'inputBg': '#E5E5EA',

        # 暗色表面（日志区）
        'darkSurface': '#1C1C1E',
        'darkText': '#AEAEB2',
        'darkSecondary': '#636366',
    }

    # 线程安全信号：后台线程传递数据到主线程
    _realtime_data_signal = pyqtSignal(float, float, float)
    _auto_tune_progress_signal = pyqtSignal(float, str)
    _auto_tune_result_signal = pyqtSignal(object)
    _auto_tune_error_signal = pyqtSignal(str)
    _auto_tune_status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PID上位机 v1.0.0")
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "app_icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        # 初始化核心模块
        self.serial_manager = SerialManager()
        self.simulated_serial = SimulatedSerialManager()
        self.data_recorder = DataRecorder()
        self.auto_tuner = PIDAutoTuner()
        self.pid_controller = PIDController()
        self.alarm_manager = AlarmManager()
        self.data_player = DataPlayer()

        # 初始化变量
        self.serial_connected = False
        self.control_running = False
        self.data_recording = False
        self.simulation_mode = False  # 模拟模式
        self.log_messages = []

        # 设置回调
        self._setup_callbacks()

        # 初始化界面
        self.init_ui()

        # 初始化定时器
        self.init_timers()

        # 加载配置
        self._load_config()

        # 刷新串口列表
        self.refresh_serial_ports()

        # 记录日志
        self.log("应用程序启动")
        self.log("欢迎使用PID上位机")

    def _setup_callbacks(self):
        """设置回调函数"""
        # 线程安全信号连接
        self._realtime_data_signal.connect(self._handle_realtime_data)
        self._auto_tune_progress_signal.connect(self._handle_auto_tune_progress)
        self._auto_tune_result_signal.connect(self._handle_auto_tune_result)
        self._auto_tune_error_signal.connect(self._handle_auto_tune_error)
        self._auto_tune_status_signal.connect(self._handle_auto_tune_status)

        # 串口管理器回调
        self.serial_manager.set_on_connection_changed(self._on_connection_changed)
        self.serial_manager.set_on_pid_params_received(self._on_pid_params_received)
        self.serial_manager.set_on_realtime_data_received(self._on_realtime_data_received)
        self.serial_manager.set_on_error(self._on_serial_error)

        # 模拟串口回调
        self.simulated_serial.set_on_connection_changed(self._on_connection_changed)
        self.simulated_serial.set_on_realtime_data_received(self._on_realtime_data_received)
        self.simulated_serial.set_on_pid_params_received(self._on_pid_params_received)

        # 数据记录器回调
        self.data_recorder.set_on_data_added(self._on_data_added)

        # 自动调参器回调
        self.auto_tuner.set_on_progress(self._on_auto_tune_progress)
        self.auto_tuner.set_on_result(self._on_auto_tune_result)
        self.auto_tuner.set_on_error(self._on_auto_tune_error)
        self.auto_tuner.set_on_status(self._on_auto_tune_status)

        # 报警管理器回调
        self.alarm_manager.set_on_alarm(self._on_alarm)

        # 数据回放器回调
        self.data_player.set_on_data(self._on_playback_data)
        self.data_player.set_on_state_changed(self._on_playback_state_changed)
        self.data_player.set_on_progress(self._on_playback_progress)
        self.data_player.set_on_finished(self._on_playback_finished)

    def _load_config(self):
        """加载配置"""
        config_manager.load()

        # 恢复串口配置
        serial_config = config_manager.serial
        if serial_config.baudrate:
            self.baud_rate_combo.setCurrentText(str(serial_config.baudrate))

        # 恢复PID配置
        pid_config = config_manager.pid
        self.p_value_spin.setValue(pid_config.kp)
        self.i_value_spin.setValue(pid_config.ki)
        self.d_value_spin.setValue(pid_config.kd)
        self.target_value_spin.setValue(pid_config.target)

    def _save_config(self):
        """保存配置"""
        # 保存串口配置
        config_manager.serial.port = self.serial_port_combo.currentText()
        try:
            config_manager.serial.baudrate = int(self.baud_rate_combo.currentText())
        except ValueError:
            config_manager.serial.baudrate = 115200

        # 保存PID配置
        config_manager.pid.kp = self.p_value_spin.value()
        config_manager.pid.ki = self.i_value_spin.value()
        config_manager.pid.kd = self.d_value_spin.value()
        config_manager.pid.target = self.target_value_spin.value()

        config_manager.save()

    def init_ui(self):
        """初始化界面"""
        # 设置中心部件背景
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # 主垂直布局（包含导航栏、内容区、日志区、状态栏）
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === iOS导航栏 ===
        nav_bar = self.create_ios_nav_bar()
        root_layout.addWidget(nav_bar)

        # === 工具栏（Segmented Control风格）===
        toolbar = self.create_ios_toolbar()
        root_layout.addWidget(toolbar)

        # === 主内容区（左右分栏）===
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(12)

        # 左右面板使用QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # 左侧面板
        left_panel = self.create_left_panel()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(480)

        # 右侧面板
        right_panel = self.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 800])

        content_layout.addWidget(splitter)
        root_layout.addWidget(content_widget, 1)

        # === 底部日志区（暗色）===
        log_area = self.create_log_area()
        root_layout.addWidget(log_area)

        # === 状态栏 ===
        status_bar = self.create_status_bar()
        root_layout.addWidget(status_bar)

        # 创建菜单栏（隐藏，仅保留快捷键功能）
        self.create_menu_bar()
        self.menuBar().setVisible(False)

        # 应用iOS样式
        self.apply_ios_styles()

    def create_left_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        panel.setObjectName("leftPanel")

        # 使用滚动区域
        from PyQt5.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setObjectName("leftScrollArea")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 串口控制卡片
        serial_card = self.create_serial_card()
        layout.addWidget(serial_card)

        # PID参数卡片
        pid_card = self.create_pid_card()
        layout.addWidget(pid_card)

        # 控制卡片
        control_card = self.create_control_card()
        layout.addWidget(control_card)

        # 数据回放卡片
        playback_card = self.create_playback_card()
        layout.addWidget(playback_card)

        layout.addStretch()

        scroll_area.setWidget(scroll_content)

        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        return panel

    def create_serial_card(self):
        """创建串口控制卡片"""
        card = IOSCard("串口设置")
        layout = card.layout

        # 串口选择行
        row_widget = QWidget()
        row_widget.setFixedHeight(44)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(8)

        port_label = QLabel("串口")
        port_label.setObjectName("fieldLabel")
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.setObjectName("iosCombo")
        self.serial_port_combo.setMinimumWidth(160)

        row_layout.addWidget(port_label)
        row_layout.addStretch()
        row_layout.addWidget(self.serial_port_combo)

        layout.addWidget(row_widget)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E5E5EA; max-height: 1px; border: none;")
        layout.addWidget(separator)

        # 波特率行
        row_widget = QWidget()
        row_widget.setFixedHeight(44)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(8)

        baud_label = QLabel("波特率")
        baud_label.setObjectName("fieldLabel")
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.setObjectName("iosCombo")
        self.baud_rate_combo.setEditable(True)
        self.baud_rate_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600", "自定义"
        ])
        self.baud_rate_combo.setCurrentText("115200")
        self.baud_rate_combo.setMinimumWidth(160)

        row_layout.addWidget(baud_label)
        row_layout.addStretch()
        row_layout.addWidget(self.baud_rate_combo)

        layout.addWidget(row_widget)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E5E5EA; max-height: 1px; border: none;")
        layout.addWidget(separator)

        # 参数行（数据位、停止位、校验位）三列并排
        params_widget = QWidget()
        params_widget.setFixedHeight(70)
        params_layout = QHBoxLayout(params_widget)
        params_layout.setContentsMargins(0, 4, 0, 4)
        params_layout.setSpacing(8)

        # 数据位
        data_bits_widget = QWidget()
        data_bits_layout = QVBoxLayout(data_bits_widget)
        data_bits_layout.setContentsMargins(0, 0, 0, 0)
        data_bits_layout.setSpacing(2)
        data_bits_label = QLabel("数据位")
        data_bits_label.setObjectName("fieldLabel")
        data_bits_label.setStyleSheet("font-size: 12px; color: #8E8E93;")
        data_bits_layout.addWidget(data_bits_label)
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.setObjectName("iosCombo")
        self.data_bits_combo.setFixedHeight(36)
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText("8")
        data_bits_layout.addWidget(self.data_bits_combo)
        params_layout.addWidget(data_bits_widget)

        # 停止位
        stop_bits_widget = QWidget()
        stop_bits_layout = QVBoxLayout(stop_bits_widget)
        stop_bits_layout.setContentsMargins(0, 0, 0, 0)
        stop_bits_layout.setSpacing(2)
        stop_bits_label = QLabel("停止位")
        stop_bits_label.setObjectName("fieldLabel")
        stop_bits_label.setStyleSheet("font-size: 12px; color: #8E8E93;")
        stop_bits_layout.addWidget(stop_bits_label)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.setObjectName("iosCombo")
        self.stop_bits_combo.setFixedHeight(36)
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        self.stop_bits_combo.setCurrentText("1")
        stop_bits_layout.addWidget(self.stop_bits_combo)
        params_layout.addWidget(stop_bits_widget)

        # 校验位
        parity_widget = QWidget()
        parity_layout = QVBoxLayout(parity_widget)
        parity_layout.setContentsMargins(0, 0, 0, 0)
        parity_layout.setSpacing(2)
        parity_label = QLabel("校验位")
        parity_label.setObjectName("fieldLabel")
        parity_label.setStyleSheet("font-size: 12px; color: #8E8E93;")
        parity_layout.addWidget(parity_label)
        self.parity_combo = QComboBox()
        self.parity_combo.setObjectName("iosCombo")
        self.parity_combo.setFixedHeight(36)
        self.parity_combo.addItems(["无", "奇", "偶"])
        self.parity_combo.setCurrentText("无")
        parity_layout.addWidget(self.parity_combo)
        params_layout.addWidget(parity_widget)

        layout.addWidget(params_widget)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E5E5EA; max-height: 1px; border: none;")
        layout.addWidget(separator)

        # 模拟模式切换
        self.simulation_check = QCheckBox("模拟模式")
        self.simulation_check.setStyleSheet("")
        self.simulation_check.setChecked(False)
        self.simulation_check.setToolTip("启用模拟模式，无需实际硬件即可测试")
        self.simulation_check.stateChanged.connect(self._on_simulation_toggle)
        layout.addWidget(self.simulation_check)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E5E5EA; max-height: 1px; border: none;")
        layout.addWidget(separator)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.connect_button = QPushButton("连接")
        self.connect_button.setObjectName("primaryButton")
        self.connect_button.setFixedHeight(40)
        self.connect_button.setToolTip("连接/断开串口 (Ctrl+Shift+C)")
        self.connect_button.clicked.connect(self.toggle_serial_connection)

        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.setFixedHeight(40)
        refresh_button.setToolTip("刷新串口列表 (F5)")
        refresh_button.clicked.connect(self.refresh_serial_ports)

        btn_layout.addWidget(self.connect_button)
        btn_layout.addWidget(refresh_button)
        layout.addLayout(btn_layout)

        # 状态指示
        self.connection_indicator = QLabel("● 未连接")
        self.connection_indicator.setObjectName("statusDisconnected")
        layout.addWidget(self.connection_indicator)

        return card

    def create_pid_card(self):
        """创建PID参数卡片"""
        card = IOSCard("PID参数")
        layout = card.layout

        # PID参数输入
        params = [
            ("P (比例)", "p_value_spin", 1.0, 0.001, 1000.0),
            ("I (积分)", "i_value_spin", 0.1, 0.000, 1000.0),
            ("D (微分)", "d_value_spin", 0.01, 0.000, 1000.0),
        ]

        for label_text, attr_name, default_val, min_val, max_val in params:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 4, 0, 4)

            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            label.setFixedWidth(70)

            spin = QDoubleSpinBox()
            spin.setObjectName("iosSpinBox")
            spin.setRange(min_val, max_val)
            spin.setDecimals(3)
            spin.setSingleStep(0.1)
            spin.setValue(default_val)
            spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            spin.setAlignment(Qt.AlignRight)
            spin.valueChanged.connect(self._update_pid_params_label)
            setattr(self, attr_name, spin)

            btn_minus = QPushButton("−")   # 使用减号字符而不是连字符
            btn_minus.setObjectName("incrementButton")
            btn_minus.setFixedSize(32, 32)
            btn_minus.clicked.connect(lambda checked, s=spin: s.setValue(s.value() - s.singleStep()))

            btn_plus = QPushButton("+")
            btn_plus.setObjectName("incrementButton")
            btn_plus.setFixedSize(32, 32)
            btn_plus.clicked.connect(lambda checked, s=spin: s.setValue(s.value() + s.singleStep()))

            row.addWidget(label)
            row.addWidget(btn_minus)
            row.addWidget(spin)
            row.addWidget(btn_plus)
            layout.addLayout(row)

            # 分割线
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("background-color: #E5E5EA; max-height: 1px; border: none;")
            layout.addWidget(line)

        # 目标值
        target_row = QHBoxLayout()
        target_label = QLabel("目标值")
        target_label.setObjectName("fieldLabel")
        target_label.setFixedWidth(70)

        self.target_value_spin = QDoubleSpinBox()
        self.target_value_spin.setObjectName("iosSpinBox")
        self.target_value_spin.setRange(-10000, 10000)
        self.target_value_spin.setDecimals(2)
        self.target_value_spin.setSingleStep(10)
        self.target_value_spin.setValue(0)
        self.target_value_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.target_value_spin.setAlignment(Qt.AlignRight)

        target_row.addWidget(target_label)
        target_row.addWidget(self.target_value_spin)
        layout.addLayout(target_row)

        # 发送/读取按钮
        btn_layout = QHBoxLayout()

        send_btn = QPushButton("发送参数")
        send_btn.setObjectName("primaryButton")
        send_btn.clicked.connect(self.send_pid_parameters)

        read_btn = QPushButton("读取参数")
        read_btn.setObjectName("secondaryButton")
        read_btn.clicked.connect(self.read_pid_parameters)

        btn_layout.addWidget(send_btn)
        btn_layout.addWidget(read_btn)
        layout.addLayout(btn_layout)

        return card

    def create_control_card(self):
        """创建控制卡片"""
        card = IOSCard("控制")
        layout = card.layout

        # 启动/停止按钮
        self.start_button = QPushButton("▶ 启动控制")
        self.start_button.setObjectName("successButton")
        self.start_button.setFixedHeight(44)
        self.start_button.setToolTip("启动/停止PID控制 (Space)")
        self.start_button.clicked.connect(self.toggle_control)
        layout.addWidget(self.start_button)

        layout.addSpacing(8)

        # 自动调参按钮
        auto_tune_btn = QPushButton("⚡ 自动调参")
        auto_tune_btn.setObjectName("warningButton")
        auto_tune_btn.setFixedHeight(44)
        auto_tune_btn.setToolTip("自动调节PID参数 (Ctrl+T)")
        auto_tune_btn.clicked.connect(self.auto_tune)
        layout.addWidget(auto_tune_btn)

        layout.addSpacing(8)

        # 进度条（用于自动调参）
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("iosProgress")
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.tune_status_label = QLabel("")
        self.tune_status_label.setObjectName("tuneStatusLabel")
        self.tune_status_label.setVisible(False)
        layout.addWidget(self.tune_status_label)

        # 参数管理按钮
        param_layout = QHBoxLayout()

        save_btn = QPushButton("保存参数")
        save_btn.setObjectName("secondaryButton")
        save_btn.setToolTip("保存当前PID参数为预设")
        save_btn.clicked.connect(self.save_parameters)

        load_btn = QPushButton("加载参数")
        load_btn.setObjectName("secondaryButton")
        load_btn.setToolTip("加载已保存的PID参数预设")
        load_btn.clicked.connect(self.load_parameters)

        param_layout.addWidget(save_btn)
        param_layout.addWidget(load_btn)
        layout.addLayout(param_layout)

        return card

    def create_playback_card(self):
        """创建数据回放卡片"""
        card = IOSCard("数据回放")
        layout = card.layout

        # 回放按钮行
        playback_btn_layout = QHBoxLayout()
        playback_btn_layout.setSpacing(8)

        self.play_button = QPushButton("▶ 播放")
        self.play_button.setObjectName("primaryButton")
        self.play_button.setFixedHeight(32)
        self.play_button.setToolTip("播放数据")
        self.play_button.clicked.connect(self._play_data)

        self.pause_button = QPushButton("⏸ 暂停")
        self.pause_button.setObjectName("secondaryButton")
        self.pause_button.setFixedHeight(32)
        self.pause_button.setToolTip("暂停播放")
        self.pause_button.clicked.connect(self._pause_data)
        self.pause_button.setEnabled(False)

        self.stop_playback_button = QPushButton("⏹ 停止")
        self.stop_playback_button.setObjectName("dangerButton")
        self.stop_playback_button.setFixedHeight(32)
        self.stop_playback_button.setToolTip("停止播放")
        self.stop_playback_button.clicked.connect(self._stop_data)
        self.stop_playback_button.setEnabled(False)

        playback_btn_layout.addWidget(self.play_button)
        playback_btn_layout.addWidget(self.pause_button)
        playback_btn_layout.addWidget(self.stop_playback_button)
        layout.addLayout(playback_btn_layout)

        layout.addSpacing(8)

        # 回放速度
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(8)
        speed_label = QLabel("速度")
        speed_label.setObjectName("fieldLabel")
        speed_label.setFixedWidth(40)

        self.speed_combo = QComboBox()
        self.speed_combo.setObjectName("iosCombo")
        self.speed_combo.addItems(["0.5x", "1x", "2x", "5x", "10x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)

        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_combo)
        layout.addLayout(speed_layout)

        layout.addSpacing(8)

        # 加载数据按钮
        load_data_btn = QPushButton("加载数据文件")
        load_data_btn.setObjectName("secondaryButton")
        load_data_btn.setFixedHeight(36)
        load_data_btn.setToolTip("加载CSV或JSON数据文件进行回放")
        load_data_btn.clicked.connect(self._load_playback_data)
        layout.addWidget(load_data_btn)

        layout.addSpacing(8)

        # 回放进度条
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.playback_progress = QProgressBar()
        self.playback_progress.setObjectName("iosProgress")
        self.playback_progress.setRange(0, 100)
        self.playback_progress.setValue(0)
        self.playback_progress.setFixedHeight(8)

        self.playback_percent_label = QLabel(" 0%")
        self.playback_percent_label.setObjectName("statsLabel")
        self.playback_percent_label.setMinimumWidth(42)
        self.playback_percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_row.addWidget(self.playback_progress, 1)
        progress_row.addWidget(self.playback_percent_label, 0)
        layout.addLayout(progress_row)

        layout.addSpacing(4)

        # 回放时间显示
        self.playback_time_label = QLabel("00:00 / 00:00")
        self.playback_time_label.setObjectName("statsLabel")
        self.playback_time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.playback_time_label)

        return card

    def create_right_panel(self):
        """创建右侧显示区域"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 标签页
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setObjectName("iosTabs")

        # 实时图表标签页
        chart_tab = self.create_chart_tab()
        self.chart_tabs.addTab(chart_tab, "实时图表")

        # 数据表格标签页
        data_tab = self.create_data_tab()
        self.chart_tabs.addTab(data_tab, "数据记录")

        # 报警标签页
        alarm_tab = self.create_alarm_tab()
        self.chart_tabs.addTab(alarm_tab, "报警信息")

        layout.addWidget(self.chart_tabs)

        return panel

    def create_chart_tab(self):
        """创建图表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 图表控制栏
        control_bar = QWidget()
        control_bar.setObjectName("controlBar")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(12, 10, 12, 10)

        # 时间窗口
        control_layout.addWidget(QLabel("时间窗口:"))
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setObjectName("iosSpinBox")
        self.time_window_spin.setRange(1, 3600)
        self.time_window_spin.setValue(10)
        self.time_window_spin.setSuffix(" 秒")
        self.time_window_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.time_window_spin.valueChanged.connect(self._on_time_window_changed)
        control_layout.addWidget(self.time_window_spin)

        control_layout.addWidget(QLabel("|"))

        # 自动滚动
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)
        control_layout.addWidget(self.auto_scroll_check)

        control_layout.addStretch()

        # 操作按钮
        screenshot_btn = QPushButton("截图")
        screenshot_btn.setObjectName("secondaryButton")
        screenshot_btn.setToolTip("保存图表截图")
        screenshot_btn.clicked.connect(self.take_screenshot)

        clear_btn = QPushButton("清除")
        clear_btn.setObjectName("dangerButton")
        clear_btn.setToolTip("清除图表数据")
        clear_btn.clicked.connect(self.clear_chart)

        control_layout.addWidget(screenshot_btn)
        control_layout.addWidget(clear_btn)

        layout.addWidget(control_bar)

        # 实时图表
        self.chart_widget = RealtimeChart()
        layout.addWidget(self.chart_widget)

        # 数据统计
        self.data_stats = DataStatsWidget()
        layout.addWidget(self.data_stats)

        return tab

    def create_data_tab(self):
        """创建数据表格标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 数据控制栏
        control_bar = QWidget()
        control_bar.setObjectName("controlBar")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(12, 10, 12, 10)

        # 记录开关
        self.record_data_check = QCheckBox("自动记录")
        self.record_data_check.setChecked(True)
        self.record_data_check.stateChanged.connect(self._on_record_toggle)
        control_layout.addWidget(self.record_data_check)

        control_layout.addWidget(QLabel("|"))

        # 统计信息
        self.stats_label = QLabel("共 0 条记录")
        self.stats_label.setObjectName("statsLabel")
        control_layout.addWidget(self.stats_label)

        control_layout.addStretch()

        # 操作按钮
        stats_btn = QPushButton("统计")
        stats_btn.setObjectName("secondaryButton")
        stats_btn.setToolTip("查看数据统计信息")
        stats_btn.clicked.connect(self.show_statistics)

        import_btn = QPushButton("导入")
        import_btn.setObjectName("secondaryButton")
        import_btn.setToolTip("导入数据文件")
        import_btn.clicked.connect(self.import_data)

        export_btn = QPushButton("导出")
        export_btn.setObjectName("primaryButton")
        export_btn.setToolTip("导出数据到文件 (Ctrl+E)")
        export_btn.clicked.connect(self.export_data)

        clear_data_btn = QPushButton("清空")
        clear_data_btn.setObjectName("dangerButton")
        clear_data_btn.setToolTip("清空所有数据")
        clear_data_btn.clicked.connect(self.clear_data)

        control_layout.addWidget(stats_btn)
        control_layout.addWidget(import_btn)
        control_layout.addWidget(export_btn)
        control_layout.addWidget(clear_data_btn)

        layout.addWidget(control_bar)

        # 过滤栏
        filter_bar = QWidget()
        filter_bar.setObjectName("controlBar")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(12, 10, 12, 10)

        filter_layout.addWidget(QLabel("搜索:"))

        self.data_filter_edit = QLineEdit()
        self.data_filter_edit.setObjectName("iosCombo")
        self.data_filter_edit.setPlaceholderText("输入关键词搜索数据...")
        self.data_filter_edit.textChanged.connect(self._filter_data_table)
        filter_layout.addWidget(self.data_filter_edit)

        search_btn = QPushButton("搜索")
        search_btn.setObjectName("primaryButton")
        search_btn.setToolTip("搜索数据")
        search_btn.clicked.connect(self._search_data_table)
        filter_layout.addWidget(search_btn)

        clear_filter_btn = QPushButton("清除")
        clear_filter_btn.setObjectName("secondaryButton")
        clear_filter_btn.setToolTip("清除搜索条件")
        clear_filter_btn.clicked.connect(self._clear_data_filter)
        filter_layout.addWidget(clear_filter_btn)

        layout.addWidget(filter_bar)

        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setObjectName("iosTable")
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["时间", "设定值", "实际值", "输出值", "误差"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setRowCount(0)
        self.data_table.setSortingEnabled(True)

        # 设置列宽
        self.data_table.setColumnWidth(0, 150)  # 时间列
        self.data_table.setColumnWidth(1, 100)  # 设定值列
        self.data_table.setColumnWidth(2, 100)  # 实际值列
        self.data_table.setColumnWidth(3, 100)  # 输出值列
        # 误差列自动填充剩余空间

        # 设置行高
        self.data_table.verticalHeader().setDefaultSectionSize(30)
        self.data_table.verticalHeader().setMinimumSectionSize(25)

        # 设置右键菜单
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._show_data_table_context_menu)

        # 添加全选快捷键
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.data_table.selectAll)
        self.data_table.addAction(select_all_action)

        layout.addWidget(self.data_table)

        return tab

    def create_alarm_tab(self):
        """创建报警标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 报警控制栏
        control_bar = QWidget()
        control_bar.setObjectName("controlBar")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(12, 10, 12, 10)

        # 报警统计
        self.alarm_count_label = QLabel("报警: 0")
        self.alarm_count_label.setObjectName("statsLabel")
        control_layout.addWidget(self.alarm_count_label)

        control_layout.addWidget(QLabel("|"))

        # 活动报警
        self.active_alarm_label = QLabel("活动: 0")
        self.active_alarm_label.setObjectName("statsLabel")
        control_layout.addWidget(self.active_alarm_label)

        control_layout.addStretch()

        # 操作按钮
        ack_all_btn = QPushButton("全部确认")
        ack_all_btn.setObjectName("secondaryButton")
        ack_all_btn.setToolTip("确认所有报警")
        ack_all_btn.clicked.connect(self._acknowledge_all_alarms)

        clear_alarms_btn = QPushButton("清除报警")
        clear_alarms_btn.setObjectName("dangerButton")
        clear_alarms_btn.setToolTip("清除所有报警记录")
        clear_alarms_btn.clicked.connect(self._clear_alarms)

        control_layout.addWidget(ack_all_btn)
        control_layout.addWidget(clear_alarms_btn)

        layout.addWidget(control_bar)

        # 过滤栏
        filter_bar = QWidget()
        filter_bar.setObjectName("controlBar")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(12, 10, 12, 10)

        filter_layout.addWidget(QLabel("过滤:"))

        self.alarm_filter_combo = QComboBox()
        self.alarm_filter_combo.setObjectName("iosCombo")
        self.alarm_filter_combo.addItems(["全部", "信息", "警告", "错误", "严重"])
        self.alarm_filter_combo.currentTextChanged.connect(self._filter_alarm_table)
        filter_layout.addWidget(self.alarm_filter_combo)

        self.alarm_filter_edit = QLineEdit()
        self.alarm_filter_edit.setObjectName("iosCombo")
        self.alarm_filter_edit.setPlaceholderText("输入关键词过滤报警...")
        self.alarm_filter_edit.textChanged.connect(self._filter_alarm_table)
        filter_layout.addWidget(self.alarm_filter_edit)

        clear_filter_btn = QPushButton("清除")
        clear_filter_btn.setObjectName("secondaryButton")
        clear_filter_btn.setToolTip("清除过滤条件")
        clear_filter_btn.clicked.connect(self._clear_alarm_filter)
        filter_layout.addWidget(clear_filter_btn)

        layout.addWidget(filter_bar)

        # 报警表格
        self.alarm_table = QTableWidget()
        self.alarm_table.setObjectName("iosTable")
        self.alarm_table.setColumnCount(5)
        self.alarm_table.setHorizontalHeaderLabels(["时间", "级别", "类型", "消息", "状态"])
        self.alarm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.alarm_table.horizontalHeader().setStretchLastSection(True)
        self.alarm_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.alarm_table.setAlternatingRowColors(True)
        self.alarm_table.setRowCount(0)
        self.alarm_table.setSortingEnabled(True)

        # 设置列宽
        self.alarm_table.setColumnWidth(0, 150)  # 时间列
        self.alarm_table.setColumnWidth(1, 80)   # 级别列
        self.alarm_table.setColumnWidth(2, 100)  # 类型列
        # 消息列和状态列自动填充剩余空间

        # 设置行高
        self.alarm_table.verticalHeader().setDefaultSectionSize(30)
        self.alarm_table.verticalHeader().setMinimumSectionSize(25)

        # 设置右键菜单
        self.alarm_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.alarm_table.customContextMenuRequested.connect(self._show_alarm_table_context_menu)

        # 添加全选快捷键
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.alarm_table.selectAll)
        self.alarm_table.addAction(select_all_action)

        layout.addWidget(self.alarm_table)

        return tab

    def create_ios_nav_bar(self):
        """创建iOS风格导航栏 - 左侧标题，右侧图标按钮"""
        nav_bar = QWidget()
        nav_bar.setObjectName("iosNavBar")
        nav_bar.setFixedHeight(44)

        layout = QHBoxLayout(nav_bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # 左侧：App标题
        title_label = QLabel("PID 上位机")
        title_label.setObjectName("navTitle")
        layout.addWidget(title_label)

        layout.addStretch()

        # 右侧：图标按钮
        # 连接按钮
        self.nav_connect_btn = QPushButton("连接")
        self.nav_connect_btn.setObjectName("navTextButton")
        self.nav_connect_btn.clicked.connect(self.toggle_serial_connection)
        layout.addWidget(self.nav_connect_btn)

        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.setObjectName("navTextButton")
        settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(settings_btn)

        return nav_bar

    def create_ios_toolbar(self):
        """创建iOS风格工具栏 - Segmented Control胶囊选择器"""
        toolbar = QWidget()
        toolbar.setObjectName("iosToolbar")
        toolbar.setFixedHeight(44)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 0, 16, 0)

        # Segmented Control容器
        segment_container = QWidget()
        segment_container.setObjectName("segmentContainer")
        segment_container.setFixedHeight(32)

        segment_layout = QHBoxLayout(segment_container)
        segment_layout.setContentsMargins(2, 2, 2, 2)
        segment_layout.setSpacing(0)

        # 创建按钮组
        self.toolbar_btn_group = QButtonGroup(self)
        self.toolbar_btn_group.setExclusive(True)

        # Segmented Control按钮
        buttons = [
            ("连接", "connect"),
            ("启动", "control"),
            ("调参", "tune"),
            ("对比", "compare"),
            ("导出", "export"),
        ]

        self.toolbar_buttons = {}
        for i, (text, key) in enumerate(buttons):
            btn = QPushButton(text)
            btn.setObjectName("segmentButton")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            self.toolbar_btn_group.addButton(btn, i)
            segment_layout.addWidget(btn)
            self.toolbar_buttons[key] = btn

        # 默认选中第一个
        self.toolbar_buttons["connect"].setChecked(True)

        # 连接信号
        self.toolbar_buttons["connect"].clicked.connect(self.toggle_serial_connection)
        self.toolbar_buttons["control"].clicked.connect(self.toggle_control)
        self.toolbar_buttons["tune"].clicked.connect(self.auto_tune)
        self.toolbar_buttons["compare"].clicked.connect(self.compare_parameters)
        self.toolbar_buttons["export"].clicked.connect(self.export_data)

        layout.addWidget(segment_container)
        layout.addStretch()

        # 右侧：模式指示
        self.toolbar_mode_label = QLabel("实际模式")
        self.toolbar_mode_label.setObjectName("toolbarModeLabel")
        layout.addWidget(self.toolbar_mode_label)

        return toolbar

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setObjectName("iosMenuBar")

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        new_action = QAction("新建项目", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)

        open_action = QAction("打开项目", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)

        save_action = QAction("保存项目", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("导出数据", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")

        settings_action = QAction("偏好设置", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图")

        # 显示/隐藏工具栏
        toolbar_action = QAction("工具栏", self)
        toolbar_action.setCheckable(True)
        toolbar_action.setChecked(True)
        toolbar_action.triggered.connect(self._toggle_toolbar)
        view_menu.addAction(toolbar_action)

        # 显示/隐藏日志
        log_action = QAction("日志面板", self)
        log_action.setCheckable(True)
        log_action.setChecked(True)
        log_action.triggered.connect(self._toggle_log_panel)
        view_menu.addAction(log_action)

        view_menu.addSeparator()

        # 刷新串口
        refresh_action = QAction("刷新串口", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_serial_ports)
        view_menu.addAction(refresh_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具")

        auto_tune_action = QAction("自动调参", self)
        auto_tune_action.setShortcut("Ctrl+T")
        auto_tune_action.triggered.connect(self.auto_tune)
        tools_menu.addAction(auto_tune_action)

        compare_action = QAction("参数对比", self)
        compare_action.setShortcut("Ctrl+D")
        compare_action.triggered.connect(self.compare_parameters)
        tools_menu.addAction(compare_action)

        tools_menu.addSeparator()

        # 启动/停止控制
        control_action = QAction("启动/停止控制", self)
        control_action.setShortcut("Space")
        control_action.triggered.connect(self.toggle_control)
        tools_menu.addAction(control_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("工具栏")
        toolbar.setObjectName("iosToolBar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 连接按钮
        self.connect_tool_btn = QAction("连接", self)
        self.connect_tool_btn.setToolTip("连接/断开串口")
        self.connect_tool_btn.triggered.connect(self.toggle_serial_connection)
        toolbar.addAction(self.connect_tool_btn)

        toolbar.addSeparator()

        # 启动/停止按钮
        self.control_tool_btn = QAction("启动", self)
        self.control_tool_btn.setToolTip("启动/停止控制 (Space)")
        self.control_tool_btn.triggered.connect(self.toggle_control)
        toolbar.addAction(self.control_tool_btn)

        toolbar.addSeparator()

        # 自动调参按钮
        auto_tune_tool_btn = QAction("调参", self)
        auto_tune_tool_btn.setToolTip("自动调参 (Ctrl+T)")
        auto_tune_tool_btn.triggered.connect(self.auto_tune)
        toolbar.addAction(auto_tune_tool_btn)

        # 参数对比按钮
        compare_tool_btn = QAction("对比", self)
        compare_tool_btn.setToolTip("参数对比 (Ctrl+D)")
        compare_tool_btn.triggered.connect(self.compare_parameters)
        toolbar.addAction(compare_tool_btn)

        toolbar.addSeparator()

        # 导出按钮
        export_tool_btn = QAction("导出", self)
        export_tool_btn.setToolTip("导出数据 (Ctrl+E)")
        export_tool_btn.triggered.connect(self.export_data)
        toolbar.addAction(export_tool_btn)

        # 截图按钮
        screenshot_tool_btn = QAction("截图", self)
        screenshot_tool_btn.setToolTip("保存截图")
        screenshot_tool_btn.triggered.connect(self.take_screenshot)
        toolbar.addAction(screenshot_tool_btn)

        toolbar.addSeparator()

        # 设置按钮
        settings_tool_btn = QAction("设置", self)
        settings_tool_btn.setToolTip("打开设置 (Ctrl+,)")
        settings_tool_btn.triggered.connect(self.show_settings)
        toolbar.addAction(settings_tool_btn)

    def create_status_bar(self):
        """创建iOS风格状态栏 - 浅灰背景，13px文字"""
        status_bar = QWidget()
        status_bar.setObjectName("iosStatusBar")
        status_bar.setFixedHeight(24)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # 连接状态
        self.connection_indicator_status = QLabel("●")
        self.connection_indicator_status.setObjectName("statusDisconnected")
        layout.addWidget(self.connection_indicator_status)

        self.connection_status = QLabel("未连接")
        self.connection_status.setObjectName("statusFieldValue")
        layout.addWidget(self.connection_status)

        layout.addWidget(QLabel("  |  "))

        # 数据统计
        data_label = QLabel("数据:")
        data_label.setObjectName("statusFieldLabel")
        layout.addWidget(data_label)
        self.data_count_label = QLabel("0")
        self.data_count_label.setObjectName("statusFieldValue")
        layout.addWidget(self.data_count_label)

        layout.addWidget(QLabel("  |  "))

        # 报警
        alarm_label = QLabel("报警:")
        alarm_label.setObjectName("statusFieldLabel")
        layout.addWidget(alarm_label)
        self.alarm_status_label = QLabel("0")
        self.alarm_status_label.setObjectName("statusFieldValue")
        layout.addWidget(self.alarm_status_label)

        layout.addWidget(QLabel("  |  "))

        # 控制状态
        control_label = QLabel("控制:")
        control_label.setObjectName("statusFieldLabel")
        layout.addWidget(control_label)
        self.control_status_label = QLabel("停止")
        self.control_status_label.setObjectName("statusFieldValue")
        layout.addWidget(self.control_status_label)

        layout.addWidget(QLabel("  |  "))

        # PID参数
        pid_label = QLabel("PID:")
        pid_label.setObjectName("statusFieldLabel")
        layout.addWidget(pid_label)
        self.pid_params_label = QLabel("--")
        self.pid_params_label.setObjectName("statusFieldValue")
        layout.addWidget(self.pid_params_label)

        layout.addWidget(QLabel("  |  "))

        # 目标/实际值
        self.target_actual_label = QLabel("目标: -- 实际: --")
        self.target_actual_label.setObjectName("statusFieldValue")
        layout.addWidget(self.target_actual_label)

        layout.addStretch()

        # 内存使用
        mem_label = QLabel("内存:")
        mem_label.setObjectName("statusFieldLabel")
        layout.addWidget(mem_label)
        self.memory_label = QLabel("--")
        self.memory_label.setObjectName("statusFieldValue")
        layout.addWidget(self.memory_label)

        layout.addWidget(QLabel("  |  "))

        # 时间
        self.time_label = QLabel("00:00:00")
        self.time_label.setObjectName("statusTimeLabel")
        layout.addWidget(self.time_label)

        return status_bar

    def create_log_area(self):
        """创建iOS风格日志区域 - 暗色主题"""
        log_container = QWidget()
        log_container.setObjectName("logContainer")
        log_container.setFixedHeight(120)

        layout = QVBoxLayout(log_container)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)

        # 日志标题栏
        header = QWidget()
        header.setObjectName("logHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 12, 4)

        log_title = QLabel("日志")
        log_title.setObjectName("logTitle")
        header_layout.addWidget(log_title)

        header_layout.addStretch()

        # 清除按钮
        clear_log_btn = QPushButton("清除")
        clear_log_btn.setObjectName("logClearButton")
        clear_log_btn.setFixedSize(50, 24)
        clear_log_btn.clicked.connect(self._clear_log)
        header_layout.addWidget(clear_log_btn)

        layout.addWidget(header)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setObjectName("logTextEdit")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # 设置日志回调
        logger.set_on_log(self._on_log_message)

        return log_container

    def _clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.log_messages.clear()

    def apply_ios_styles(self):
        """应用iOS风格样式 - 参考Apple Human Interface Guidelines"""
        style = f"""
/* ===== 全局 ===== */
* {{
    font-family: "Microsoft YaHei UI", "PingFang SC", "Helvetica Neue", sans-serif;
    font-size: 13px;
    outline: none;
}}
QLabel {{
    font-size: 13px;
}}
QLabel#navTitle {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#fieldLabel {{
    font-size: 13px;
}}
QPushButton#primaryButton, QPushButton#secondaryButton,
QPushButton#successButton, QPushButton#warningButton,
QPushButton#dangerButton {{
    font-size: 13px;
    min-height: 34px;
}}
QPushButton#successButton, QPushButton#warningButton {{
    min-height: 40px;
}}

QMainWindow, QWidget#centralWidget {{
    background-color: #F2F2F7;
}}

/* ===== 左侧面板背景 ===== */
QWidget#leftPanel, QScrollArea#leftScrollArea,
QScrollArea#leftScrollArea > QWidget > QWidget {{
    background-color: #F2F2F7;
    border: none;
}}

/* ===== iOS卡片 ===== */
QFrame#iosCard {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 16px;
    margin: 0px;
}}

/* ===== Section Header ===== */
QLabel#cardSectionHeader, QLabel#iosSectionHeader {{
    color: #8E8E93;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
}}

/* ===== 字段标签 ===== */
QLabel#fieldLabel {{
    color: #000000;
    font-size: 14px;
    background: transparent;
}}

/* ===== ComboBox ===== */
QComboBox {{
    background-color: #E5E5EA;
    color: #000000;
    border: none;
    border-radius: 10px;
    padding: 5px 28px 5px 10px;
    font-size: 14px;
    min-height: 32px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}}
QComboBox:focus {{
    border: 2px solid #007AFF;
    background-color: #FFFFFF;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    width: 16px;
    height: 16px;
    image: url(ui/arrow_down.svg);
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 12px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
    padding: 6px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 8px;
    min-height: 28px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox:on {{
    border: 2px solid #007AFF;
    background-color: #FFFFFF;
    border-radius: 10px;
}}

/* ===== SpinBox（必须配合NoButtons使用）===== */
QSpinBox, QDoubleSpinBox {{
    background-color: #E5E5EA;
    color: #000000;
    border: none;
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 14px;
    min-height: 32px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid #007AFF;
    background-color: #FFFFFF;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0;
    height: 0;
    border: none;
    background: none;
}}

/* ===== LineEdit ===== */
QLineEdit {{
    background-color: #E5E5EA;
    color: #000000;
    border: none;
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 14px;
    min-height: 32px;
}}
QLineEdit:focus {{
    border: 2px solid #007AFF;
    background-color: #FFFFFF;
}}

/* ===== 主按钮（蓝色）===== */
QPushButton#primaryButton {{
    background-color: #007AFF;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
}}
QPushButton#primaryButton:hover {{ background-color: #0A84FF; }}
QPushButton#primaryButton:pressed {{ background-color: #0062CC; }}
QPushButton#primaryButton:disabled {{ background-color: #C7C7CC; color: #FFFFFF; }}

/* ===== 次要按钮（灰色背景蓝字）===== */
QPushButton#secondaryButton {{
    background-color: #E5E5EA;
    color: #007AFF;
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    min-height: 36px;
}}
QPushButton#secondaryButton:hover {{ background-color: #D1D1D6; }}
QPushButton#secondaryButton:pressed {{ background-color: #C7C7CC; }}

/* ===== 绿色按钮（启动控制）===== */
QPushButton#successButton {{
    background-color: #34C759;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    min-height: 44px;
}}
QPushButton#successButton:hover {{ background-color: #30D158; }}
QPushButton#successButton:pressed {{ background-color: #25A244; }}

/* ===== 橙色按钮（自动调参）===== */
QPushButton#warningButton {{
    background-color: #FF9500;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    min-height: 44px;
}}
QPushButton#warningButton:hover {{ background-color: #FFAA00; }}
QPushButton#warningButton:pressed {{ background-color: #CC7700; }}

/* ===== 危险按钮（红字透明背景）===== */
QPushButton#dangerButton {{
    background-color: transparent;
    color: #FF3B30;
    border: none;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    min-height: 36px;
}}
QPushButton#dangerButton:hover {{ background-color: #FF3B3015; }}
QPushButton#dangerButton:pressed {{ background-color: #FF3B3025; }}

/* ===== 圆形增量按钮（P/I/D旁边的+-）===== */
QPushButton#incrementButton {{
    background-color: #007AFF;
    color: #FFFFFF;
    border: none;
    border-radius: 16px;
    font-size: 18px;
    font-weight: 300;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px;
}}
QPushButton#incrementButton:hover {{ background-color: #0A84FF; }}
QPushButton#incrementButton:pressed {{ background-color: #0062CC; }}

/* ===== 导航栏 ===== */
QWidget#iosNavBar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid #C6C6C8;
    min-height: 44px;
    max-height: 44px;
}}
QLabel#navTitle {{
    font-size: 17px;
    font-weight: 600;
    color: #000000;
    background: transparent;
}}
QPushButton#navTextButton {{
    background: transparent;
    color: #007AFF;
    border: none;
    font-size: 15px;
    padding: 4px 8px;
    min-height: 28px;
}}
QPushButton#navTextButton:hover {{
    background-color: #F2F2F7;
    border-radius: 6px;
}}

/* ===== 工具栏（Segmented Control）===== */
QWidget#iosToolbar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid #C6C6C8;
    min-height: 44px;
    max-height: 44px;
}}
QWidget#segmentContainer {{
    background-color: #E5E5EA;
    border-radius: 8px;
    min-height: 32px;
    max-height: 32px;
}}
QPushButton#segmentButton {{
    background-color: transparent;
    color: #3C3C43;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 14px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#segmentButton:checked {{
    background-color: #FFFFFF;
    color: #000000;
    font-weight: 600;
}}
QPushButton#segmentButton:hover:!checked {{
    background-color: #D1D1D6;
}}
QLabel#toolbarModeLabel {{
    color: #FF9500;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}

/* ===== Tab标签页 ===== */
QTabWidget#iosTabs::pane {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 8px;
}}
QTabWidget#iosTabs::tab-bar {{
    padding-left: 12px;
}}
QTabBar::tab {{
    background: transparent;
    color: #8E8E93;
    padding: 10px 16px;
    margin-right: 6px;
    font-size: 14px;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    color: #007AFF;
    border-bottom: 2px solid #007AFF;
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: #3C3C43;
}}

/* ===== 表格 ===== */
QTableWidget#iosTable {{
    background-color: #FFFFFF;
    border: none;
    gridline-color: #E5E5EA;
    font-size: 13px;
    selection-background-color: #007AFF20;
    selection-color: #000000;
    alternate-background-color: #F9F9FB;
}}
QTableWidget#iosTable::item {{
    padding: 8px;
    border-bottom: 1px solid #E5E5EA;
    color: #000000;
}}
QTableWidget#iosTable::item:selected {{
    background-color: #007AFF20;
    color: #000000;
}}
QHeaderView::section {{
    background-color: #F2F2F7;
    color: #8E8E93;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #C6C6C8;
    font-size: 12px;
    font-weight: 600;
}}

/* ===== 控制栏背景 ===== */
QWidget#controlBar {{
    background-color: #FFFFFF;
    border-radius: 12px;
}}

/* ===== CheckBox（iOS开关样式）===== */
QCheckBox {{
    color: #000000;
    font-size: 14px;
    spacing: 10px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 44px;
    height: 26px;
    border-radius: 13px;
    border: none;
}}
QCheckBox::indicator:unchecked {{
    background-color: #E5E5EA;
}}
QCheckBox::indicator:checked {{
    background-color: #34C759;
}}

/* ===== 进度条 ===== */
QProgressBar#iosProgress {{
    background-color: #E5E5EA;
    border: none;
    border-radius: 4px;
    max-height: 8px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar#iosProgress::chunk {{
    background-color: #007AFF;
    border-radius: 4px;
}}

/* ===== 状态指示 ===== */
QLabel#statusDisconnected {{
    color: #FF3B30;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}
QLabel#statusConnected {{
    color: #34C759;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}

/* ===== 日志区域 ===== */
QWidget#logContainer {{
    background-color: #1C1C1E;
    border-radius: 12px;
    margin: 0px 16px 8px 16px;
}}
QLabel#logTitle {{
    color: #AEAEB2;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}}
QPushButton#logClearButton {{
    background-color: #3A3A3C;
    color: #AEAEB2;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    padding: 2px 8px;
    min-height: 22px;
    max-height: 22px;
}}
QPushButton#logClearButton:hover {{ background-color: #48484A; }}
QTextEdit#logTextEdit {{
    background-color: #2C2C2E;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #AEAEB2;
}}

/* ===== 状态栏 ===== */
QWidget#iosStatusBar {{
    background-color: #F2F2F7;
    border-top: 1px solid #C6C6C8;
    min-height: 24px;
    max-height: 24px;
}}
QLabel#statusFieldLabel {{
    color: #8E8E93;
    font-size: 11px;
    background: transparent;
}}
QLabel#statusFieldValue {{
    color: #000000;
    font-size: 11px;
    font-weight: 500;
    background: transparent;
}}
QLabel#statusTimeLabel {{
    color: #000000;
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #C7C7CC;
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #8E8E93; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #C7C7CC;
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: #8E8E93; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}

/* ===== 分割器 ===== */
QSplitter::handle {{
    background-color: #C6C6C8;
    width: 1px;
}}

/* ===== GroupBox（对话框里用）===== */
QGroupBox {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 12px;
    margin-top: 16px;
    padding-top: 8px;
    font-size: 12px;
    font-weight: 600;
    color: #8E8E93;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #8E8E93;
}}

/* ===== 杂项标签 ===== */
QLabel#statsLabel, QLabel#tuneStatusLabel {{
    color: #8E8E93;
    font-size: 12px;
    background: transparent;
}}
QLabel {{
    background: transparent;
}}
"""
        self.setStyleSheet(style)

        # 修复ComboBox下拉弹出框外层方角边框
        self._fix_combo_popup_frames()

    def _fix_combo_popup_frames(self):
        """去掉ComboBox下拉弹出框外层的方角边框"""
        for combo in self.findChildren(QComboBox):
            view = combo.view()
            if view:
                container = view.parentWidget()
                if container:
                    container.setStyleSheet(
                        "QFrame { border: none; border-radius: 12px; background-color: #FFFFFF; }"
                    )

    def init_timers(self):
        """初始化定时器"""
        # 时间更新定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

        # 数据更新定时器
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self._update_data_display)
        self.data_timer.start(100)  # 100ms更新一次

        # 状态栏更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(2000)  # 2秒更新一次

    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)

    def _update_status_bar(self):
        """更新状态栏"""
        # 更新内存使用
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_label.setText(f"内存: {memory_mb:.1f} MB")

    def log(self, message, level="INFO"):
        """记录日志"""
        logger.info(message)

    def _on_log_message(self, message, level):
        """日志消息回调"""
        self.log_messages.append(message)

        # 保持日志在合理范围内
        if len(self.log_messages) > 1000:
            self.log_messages = self.log_messages[-500:]

        # 更新日志显示
        if hasattr(self, 'log_text'):
            self.log_text.append(message)
            # 自动滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    # 串口相关方法

    def _on_simulation_toggle(self, state):
        """模拟模式切换"""
        self.simulation_mode = (state == Qt.Checked)
        if self.simulation_mode:
            self.log("已启用模拟模式")
            # 禁用串口选择
            self.serial_port_combo.setEnabled(False)
            self.baud_rate_combo.setEnabled(False)
            self.data_bits_combo.setEnabled(False)
            self.stop_bits_combo.setEnabled(False)
            self.parity_combo.setEnabled(False)
            # 更新工具栏模式指示
            if hasattr(self, 'toolbar_mode_label'):
                self.toolbar_mode_label.setText("模拟模式")
                self.toolbar_mode_label.setStyleSheet("color: #FF9500; font-weight: bold;")
        else:
            self.log("已禁用模拟模式")
            # 启用串口选择
            self.serial_port_combo.setEnabled(True)
            self.baud_rate_combo.setEnabled(True)
            self.data_bits_combo.setEnabled(True)
            self.stop_bits_combo.setEnabled(True)
            self.parity_combo.setEnabled(True)
            # 更新工具栏模式指示
            if hasattr(self, 'toolbar_mode_label'):
                self.toolbar_mode_label.setText("实际模式")
                self.toolbar_mode_label.setStyleSheet("")

    def _on_time_window_changed(self, value):
        """时间窗口改变"""
        if hasattr(self, 'chart_widget'):
            self.chart_widget.set_time_window(value)

    def _on_auto_scroll_changed(self, state):
        """自动滚动改变"""
        if hasattr(self, 'chart_widget'):
            self.chart_widget.set_auto_scroll(state == Qt.Checked)

    def _update_pid_params_label(self):
        """更新状态栏PID参数显示"""
        if hasattr(self, 'pid_params_label'):
            p = self.p_value_spin.value()
            i = self.i_value_spin.value()
            d = self.d_value_spin.value()
            self.pid_params_label.setText(f"PID: P={p:.2f} I={i:.2f} D={d:.2f}")

    def toggle_serial_connection(self):
        """切换串口连接状态"""
        if self.serial_connected:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        """连接串口"""
        if self.simulation_mode:
            # 模拟模式
            if self.simulated_serial.connect():
                self.log("模拟串口连接成功")
            return

        # 真实串口模式
        port = self.serial_port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "警告", "请选择串口")
            return

        # 获取配置
        config = SerialConfig()
        config.port = port
        try:
            config.baudrate = int(self.baud_rate_combo.currentText())
        except ValueError:
            config.baudrate = 115200
        config.bytesize = int(self.data_bits_combo.currentText())
        config.stopbits = float(self.stop_bits_combo.currentText())
        parity_map = {"无": "N", "奇": "O", "偶": "E"}
        config.parity = parity_map.get(self.parity_combo.currentText(), "N")

        # 连接
        if self.serial_manager.connect(config):
            self.log(f"串口 {port} 连接成功")
        else:
            QMessageBox.critical(self, "错误", "串口连接失败")

    def disconnect_serial(self):
        """断开串口"""
        if self.simulation_mode:
            self.simulated_serial.disconnect()
            self.log("模拟串口已断开")
        else:
            self.serial_manager.disconnect()
            self.log("串口已断开")

    def refresh_serial_ports(self):
        """刷新串口列表"""
        self.serial_port_combo.clear()
        ports = SerialManager.list_ports()
        for port_info in ports:
            self.serial_port_combo.addItem(port_info['port'])
        self.log(f"发现 {len(ports)} 个串口")

    def _on_connection_changed(self, state):
        """连接状态变化回调"""
        # 处理模拟模式的状态变化
        if isinstance(state, bool):
            connected = state
        else:
            connected = (state == ConnectionState.CONNECTED)

        if connected:
            self.serial_connected = True
            self.connect_button.setText("断开")
            self.connect_button.setObjectName("dangerButton")
            self.connect_button.style().unpolish(self.connect_button)
            self.connect_button.style().polish(self.connect_button)

            mode_text = "模拟" if self.simulation_mode else ""
            self.connection_indicator.setText(f"● {mode_text}已连接")
            self.connection_indicator.setObjectName("statusConnected")
            self.connection_indicator.style().unpolish(self.connection_indicator)
            self.connection_indicator.style().polish(self.connection_indicator)

            # 更新状态栏
            self.connection_indicator_status.setText("●")
            self.connection_indicator_status.setObjectName("statusConnected")
            self.connection_indicator_status.style().unpolish(self.connection_indicator_status)
            self.connection_indicator_status.style().polish(self.connection_indicator_status)
            self.connection_status.setText(f"{mode_text}已连接")

            # 更新导航栏按钮
            if hasattr(self, 'nav_connect_btn'):
                self.nav_connect_btn.setText("断开")

            # 更新工具栏按钮
            if hasattr(self, 'toolbar_buttons') and 'connect' in self.toolbar_buttons:
                self.toolbar_buttons['connect'].setText("断开")

            # 更新标题栏
            self.setWindowTitle(f"PID上位机 v1.0.0 - {mode_text}已连接")
        else:
            self.serial_connected = False
            self.connect_button.setText("连接")
            self.connect_button.setObjectName("primaryButton")
            self.connect_button.style().unpolish(self.connect_button)
            self.connect_button.style().polish(self.connect_button)

            self.connection_indicator.setText("● 未连接")
            self.connection_indicator.setObjectName("statusDisconnected")
            self.connection_indicator.style().unpolish(self.connection_indicator)
            self.connection_indicator.style().polish(self.connection_indicator)

            # 更新状态栏
            self.connection_indicator_status.setText("●")
            self.connection_indicator_status.setObjectName("statusDisconnected")
            self.connection_indicator_status.style().unpolish(self.connection_indicator_status)
            self.connection_indicator_status.style().polish(self.connection_indicator_status)
            self.connection_status.setText("未连接")

            # 更新导航栏按钮
            if hasattr(self, 'nav_connect_btn'):
                self.nav_connect_btn.setText("连接")

            # 更新工具栏按钮
            if hasattr(self, 'toolbar_buttons') and 'connect' in self.toolbar_buttons:
                self.toolbar_buttons['connect'].setText("连接")

            # 更新标题栏
            self.setWindowTitle("PID上位机 v1.0.0")

    def _on_serial_error(self, message):
        """串口错误回调"""
        self.log(f"串口错误: {message}", "ERROR")

    # PID参数相关方法

    def send_pid_parameters(self):
        """发送PID参数"""
        if not self.serial_connected:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return

        params = ProtocolPIDParams(
            p=self.p_value_spin.value(),
            i=self.i_value_spin.value(),
            d=self.d_value_spin.value()
        )

        if self.simulation_mode:
            if self.simulated_serial.write_pid_params(params):
                self.log(f"发送PID参数: P={params.p}, I={params.i}, D={params.d}")
        else:
            if self.serial_manager.write_pid_params(params):
                self.log(f"发送PID参数: P={params.p}, I={params.i}, D={params.d}")
            else:
                QMessageBox.critical(self, "错误", "发送PID参数失败")

    def read_pid_parameters(self):
        """读取PID参数"""
        if not self.serial_connected:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return

        if self.simulation_mode:
            self.simulated_serial.read_pid_params()
            self.log("读取PID参数")
        else:
            if self.serial_manager.read_pid_params():
                self.log("读取PID参数")
            else:
                QMessageBox.critical(self, "错误", "读取PID参数失败")

    def _on_pid_params_received(self, params):
        """PID参数接收回调"""
        self.p_value_spin.setValue(params.p)
        self.i_value_spin.setValue(params.i)
        self.d_value_spin.setValue(params.d)
        self.log(f"接收PID参数: P={params.p}, I={params.i}, D={params.d}")

        # 更新状态栏
        self.pid_params_label.setText(f"PID: P={params.p:.2f} I={params.i:.2f} D={params.d:.2f}")

    # 控制相关方法

    def toggle_control(self):
        """切换控制状态"""
        if self.control_running:
            self.stop_control()
        else:
            self.start_control()

    def start_control(self):
        """启动控制"""
        if not self.serial_connected:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return

        # 设置目标值
        target = self.target_value_spin.value()

        if self.simulation_mode:
            self.simulated_serial.set_target_value(target)
            self.log(f"设置目标值: {target}")

            if self.simulated_serial.start_control():
                self.control_running = True
                self.start_button.setText("⏹ 停止控制")
                self.start_button.setObjectName("dangerButton")
                self.start_button.style().unpolish(self.start_button)
                self.start_button.style().polish(self.start_button)

                # 更新状态栏
                self.control_status_label.setText("运行")

                # 更新工具栏按钮
                if hasattr(self, 'toolbar_buttons') and 'control' in self.toolbar_buttons:
                    self.toolbar_buttons['control'].setText("停止")

                # 更新标题栏
                mode_text = "模拟" if self.simulation_mode else ""
                self.setWindowTitle(f"PID上位机 v1.0.0 - {mode_text}已连接 - 控制中")

                self.log("启动控制")

                # 开始数据记录
                if self.record_data_check.isChecked():
                    self.data_recorder.start_recording()
        else:
            if self.serial_manager.set_target_value(target):
                self.log(f"设置目标值: {target}")

            if self.serial_manager.start_control():
                self.control_running = True
                self.start_button.setText("⏹ 停止控制")
                self.start_button.setObjectName("dangerButton")
                self.start_button.style().unpolish(self.start_button)
                self.start_button.style().polish(self.start_button)

                # 更新状态栏
                self.control_status_label.setText("运行")

                # 更新工具栏按钮
                if hasattr(self, 'toolbar_buttons') and 'control' in self.toolbar_buttons:
                    self.toolbar_buttons['control'].setText("停止")

                # 更新标题栏
                self.setWindowTitle("PID上位机 v1.0.0 - 已连接 - 控制中")

                self.log("启动控制")

                # 开始数据记录
                if self.record_data_check.isChecked():
                    self.data_recorder.start_recording()
            else:
                QMessageBox.critical(self, "错误", "启动控制失败")

    def stop_control(self):
        """停止控制"""
        success = False

        if self.simulation_mode:
            success = self.simulated_serial.stop_control()
        else:
            success = self.serial_manager.stop_control()

        if success:
            self.control_running = False
            self.start_button.setText("▶ 启动控制")
            self.start_button.setObjectName("successButton")
            self.start_button.style().unpolish(self.start_button)
            self.start_button.style().polish(self.start_button)

            # 更新状态栏
            self.control_status_label.setText("停止")

            # 更新工具栏按钮
            if hasattr(self, 'toolbar_buttons') and 'control' in self.toolbar_buttons:
                self.toolbar_buttons['control'].setText("启动")

            # 更新标题栏
            mode_text = "模拟" if self.simulation_mode else ""
            if self.serial_connected:
                self.setWindowTitle(f"PID上位机 v1.0.0 - {mode_text}已连接")
            else:
                self.setWindowTitle("PID上位机 v1.0.0")

            self.log("停止控制")

            # 停止数据记录
            self.data_recorder.stop_recording()
        else:
            QMessageBox.critical(self, "错误", "停止控制失败")

    # 自动调参相关方法

    def auto_tune(self):
        """自动调参"""
        if not self.serial_connected:
            QMessageBox.warning(self, "警告", "请先连接串口")
            return

        # 显示调参方法选择对话框
        methods = [
            ("Ziegler-Nichols", TuningMethod.ZIEGLER_NICHOLS),
            ("Cohen-Coon", TuningMethod.COHEN_COON),
            ("继电反馈法", TuningMethod.RELAY_FEEDBACK),
            ("AMIGO", TuningMethod.AMIGO)
        ]

        items = [m[0] for m in methods]
        item, ok = QMessageBox.getItem(
            self, "选择调参方法", "请选择自动调参方法:", items, 0, False
        )

        if ok and item:
            # 找到对应的方法
            method = None
            for name, m in methods:
                if name == item:
                    method = m
                    break

            if method:
                # 设置自动调参器参数
                self.auto_tuner.set_parameters(
                    target=self.target_value_spin.value(),
                    output_min=0,
                    output_max=100
                )

                # 设置读写回调
                self.auto_tuner.set_process_callbacks(
                    read_func=self._read_process_value,
                    write_func=self._write_output
                )

                # 显示进度条
                self.progress_bar.setVisible(True)
                self.tune_status_label.setVisible(True)
                self.progress_bar.setValue(0)

                # 开始调参
                self.auto_tuner.start(method)
                self.log(f"开始自动调参: {item}")

    def _read_process_value(self):
        """读取过程值（用于自动调参）"""
        if self.simulation_mode:
            return self.simulated_serial._simulator.current_value
        return 0.0

    def _write_output(self, output):
        """写入输出值（用于自动调参）"""
        if self.simulation_mode:
            self.simulated_serial._simulator._current_output = output

    def _on_auto_tune_progress(self, progress, message):
        """自动调参进度回调（可能在后台线程）"""
        self._auto_tune_progress_signal.emit(progress, message)

    def _on_auto_tune_result(self, result):
        """自动调参结果回调（可能在后台线程）"""
        self._auto_tune_result_signal.emit(result)

    def _on_auto_tune_error(self, message):
        """自动调参错误回调（可能在后台线程）"""
        self._auto_tune_error_signal.emit(message)

    def _on_auto_tune_status(self, message):
        """自动调参状态回调（可能在后台线程）"""
        self._auto_tune_status_signal.emit(message)

    @pyqtSlot(float, str)
    def _handle_auto_tune_progress(self, progress, message):
        """处理自动调参进度（主线程）"""
        self.progress_bar.setValue(int(progress))
        self.tune_status_label.setText(message)

    @pyqtSlot(object)
    def _handle_auto_tune_result(self, result):
        """处理自动调参结果（主线程）"""
        self.progress_bar.setVisible(False)
        self.tune_status_label.setVisible(False)

        self.p_value_spin.setValue(result.kp)
        self.i_value_spin.setValue(result.ki)
        self.d_value_spin.setValue(result.kd)

        self.log(f"自动调参完成: Kp={result.kp:.3f}, Ki={result.ki:.3f}, Kd={result.kd:.3f}")

        QMessageBox.information(
            self, "调参完成",
            f"调参方法: {result.method.value}\n"
            f"Kp = {result.kp:.3f}\n"
            f"Ki = {result.ki:.3f}\n"
            f"Kd = {result.kd:.3f}\n"
            f"置信度: {result.confidence:.0%}"
        )

    @pyqtSlot(str)
    def _handle_auto_tune_error(self, message):
        """处理自动调参错误（主线程）"""
        self.progress_bar.setVisible(False)
        self.tune_status_label.setVisible(False)
        self.log(f"自动调参失败: {message}", "ERROR")
        QMessageBox.critical(self, "调参失败", message)

    @pyqtSlot(str)
    def _handle_auto_tune_status(self, message):
        """处理自动调参状态（主线程）"""
        self.log(message)

    # 数据相关方法

    def _on_record_toggle(self, state):
        """记录开关切换"""
        if state == Qt.Checked:
            self.data_recording = True
            if self.control_running:
                self.data_recorder.start_recording()
        else:
            self.data_recording = False
            self.data_recorder.stop_recording()

    def _on_data_added(self, point):
        """数据添加回调"""
        # 更新数据计数
        count = self.data_recorder.data_count
        self.data_count_label.setText(f"数据: {count}")
        self.stats_label.setText(f"共 {count} 条记录")

    def _on_realtime_data_received(self, data):
        """实时数据接收回调（可能在后台线程调用）"""
        self._realtime_data_signal.emit(data.setpoint, data.actual, data.output)

    @pyqtSlot(float, float, float)
    def _handle_realtime_data(self, setpoint, actual, output):
        """处理实时数据（主线程）"""
        # 添加到图表
        if hasattr(self, 'chart_widget'):
            self.chart_widget.add_data(
                setpoint=setpoint,
                actual=actual,
                output=output
            )

        # 更新数据统计
        if hasattr(self, 'data_stats'):
            self.data_stats.add_value(actual)

        # 添加到数据记录器
        if self.data_recording:
            self.data_recorder.add_data(
                setpoint=setpoint,
                actual=actual,
                output=output
            )

        # 检查报警
        self.alarm_manager.check_value(actual, setpoint)

        # 更新状态栏
        if hasattr(self, 'target_actual_label'):
            self.target_actual_label.setText(
                f"目标: {setpoint:.2f} 实际: {actual:.2f}"
            )

    def _on_status_received(self, status):
        """状态接收回调"""
        pass

    def _update_data_display(self):
        """更新数据表格显示"""
        if not self.data_recorder.is_recording:
            return

        # 获取最近的数据
        recent_data = self.data_recorder.get_recent_data(100)

        # 更新表格
        self.data_table.setRowCount(len(recent_data))
        for i, point in enumerate(recent_data):
            self.data_table.setItem(i, 0, QTableWidgetItem(point.time_str))
            self.data_table.setItem(i, 1, QTableWidgetItem(f"{point.setpoint:.2f}"))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"{point.actual:.2f}"))
            self.data_table.setItem(i, 3, QTableWidgetItem(f"{point.output:.2f}"))
            self.data_table.setItem(i, 4, QTableWidgetItem(f"{point.error:.2f}"))

    def _filter_data_table(self, text):
        """过滤数据表格"""
        if not text:
            # 显示所有行
            for row in range(self.data_table.rowCount()):
                self.data_table.setRowHidden(row, False)
            return

        # 隐藏不匹配的行
        for row in range(self.data_table.rowCount()):
            match = False
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.data_table.setRowHidden(row, not match)

    def _clear_data_filter(self):
        """清除数据过滤"""
        self.data_filter_edit.clear()

    def _search_data_table(self):
        """搜索数据表格"""
        from PyQt5.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(self, "搜索数据", "请输入搜索关键词:")
        if not ok or not text:
            return

        # 清除之前的选择
        self.data_table.clearSelection()

        # 搜索并选中匹配的行
        found_rows = []
        for row in range(self.data_table.rowCount()):
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    found_rows.append(row)
                    break

        if found_rows:
            # 选中所有匹配的行
            for row in found_rows:
                self.data_table.selectRow(row)

            # 滚动到第一个匹配项
            self.data_table.scrollToItem(self.data_table.item(found_rows[0], 0))

            # 显示搜索结果
            self.statusBar().showMessage(f"找到 {len(found_rows)} 条匹配记录", 3000)
        else:
            self.statusBar().showMessage("未找到匹配记录", 3000)

    def _show_data_table_context_menu(self, position):
        """显示数据表格右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction

        # 获取点击的行
        row = self.data_table.rowAt(position.y())
        if row < 0:
            return

        # 选中该行
        self.data_table.selectRow(row)

        # 创建右键菜单
        menu = QMenu(self)

        # 复制行数据
        copy_action = QAction("复制行数据", self)
        copy_action.triggered.connect(lambda: self._copy_data_row(row))
        menu.addAction(copy_action)

        # 复制所有选中行
        copy_selected_action = QAction("复制选中行", self)
        copy_selected_action.triggered.connect(self._copy_selected_rows)
        menu.addAction(copy_selected_action)

        menu.addSeparator()

        # 导出选中行
        export_selected_action = QAction("导出选中行", self)
        export_selected_action.triggered.connect(self._export_selected_rows)
        menu.addAction(export_selected_action)

        menu.addSeparator()

        # 查看详细信息
        detail_action = QAction("查看详细信息", self)
        detail_action.triggered.connect(lambda: self._show_data_detail(row))
        menu.addAction(detail_action)

        menu.addSeparator()

        # 删除选中行
        delete_action = QAction("删除选中行", self)
        delete_action.triggered.connect(self._delete_selected_rows)
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec_(self.data_table.viewport().mapToGlobal(position))

    def _copy_data_row(self, row):
        """复制单行数据"""
        data = []
        for col in range(self.data_table.columnCount()):
            item = self.data_table.item(row, col)
            if item:
                data.append(item.text())

        # 复制到剪贴板
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText('\t'.join(data))

        self.log(f"已复制第 {row + 1} 行数据")

    def _copy_selected_rows(self):
        """复制所有选中行"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        # 收集数据
        data_lines = []
        for row in sorted(selected_rows):
            row_data = []
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                if item:
                    row_data.append(item.text())
            data_lines.append('\t'.join(row_data))

        # 复制到剪贴板
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(data_lines))

        self.log(f"已复制 {len(selected_rows)} 行数据")

    def _export_selected_rows(self):
        """导出选中行"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要导出的数据行")
            return

        # 获取保存路径
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出选中数据", "",
            "CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*)"
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8-sig') as f:
                    # 写入表头
                    headers = []
                    for col in range(self.data_table.columnCount()):
                        header_item = self.data_table.horizontalHeaderItem(col)
                        if header_item:
                            headers.append(header_item.text())
                    f.write(','.join(headers) + '\n')

                    # 写入数据
                    for row in sorted(selected_rows):
                        row_data = []
                        for col in range(self.data_table.columnCount()):
                            item = self.data_table.item(row, col)
                            if item:
                                row_data.append(item.text())
                            else:
                                row_data.append('')
                        f.write(','.join(row_data) + '\n')

                self.log(f"已导出 {len(selected_rows)} 行数据到: {filepath}")
                QMessageBox.information(self, "成功", f"已导出 {len(selected_rows)} 行数据")

            except Exception as e:
                self.log(f"导出数据失败: {str(e)}", "ERROR")
                QMessageBox.critical(self, "错误", f"导出数据失败: {str(e)}")

    def _show_data_detail(self, row):
        """显示数据详细信息"""
        data = []
        headers = ["时间", "设定值", "实际值", "输出值", "误差"]

        for col in range(self.data_table.columnCount()):
            item = self.data_table.item(row, col)
            if item:
                data.append(f"{headers[col]}: {item.text()}")

        detail_text = '\n'.join(data)
        QMessageBox.information(self, "数据详细信息", detail_text)

    def _delete_selected_rows(self):
        """删除选中行"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 行数据吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 从数据记录器中删除数据
            for row in sorted(selected_rows, reverse=True):
                if row < len(self.data_recorder._data):
                    self.data_recorder._data.pop(row)

            # 更新显示
            self._update_data_display()
            self.log(f"已删除 {len(selected_rows)} 行数据")

    def save_parameters(self):
        """保存参数"""
        # 弹出输入对话框
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "保存参数", "请输入预设名称:")

        if ok and name:
            from utils.config import PIDConfig
            pid_config = PIDConfig(
                kp=self.p_value_spin.value(),
                ki=self.i_value_spin.value(),
                kd=self.d_value_spin.value(),
                target=self.target_value_spin.value()
            )

            if config_manager.save_preset(name, pid_config):
                self.log(f"保存参数预设: {name}")
                QMessageBox.information(self, "成功", f"参数预设 '{name}' 已保存")
            else:
                QMessageBox.critical(self, "错误", "保存参数预设失败")

    def load_parameters(self):
        """加载参数"""
        # 获取预设列表
        presets = config_manager.list_presets()

        if not presets:
            QMessageBox.information(self, "提示", "没有保存的参数预设")
            return

        # 弹出选择对话框
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "加载参数", "请选择参数预设:", presets, 0, False
        )

        if ok and name:
            pid_config = config_manager.load_preset(name)
            if pid_config:
                self.p_value_spin.setValue(pid_config.kp)
                self.i_value_spin.setValue(pid_config.ki)
                self.d_value_spin.setValue(pid_config.kd)
                self.target_value_spin.setValue(pid_config.target)
                self.log(f"加载参数预设: {name}")
            else:
                QMessageBox.critical(self, "错误", "加载参数预设失败")

    def take_screenshot(self):
        """截图"""
        # 获取保存路径
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存截图", "", "PNG文件 (*.png);;JPEG文件 (*.jpg)"
        )

        if filepath:
            # 截取主窗口
            screenshot = self.grab()
            screenshot.save(filepath)
            self.log(f"截图已保存: {filepath}")

    def clear_chart(self):
        """清除图表"""
        self.data_recorder.clear()
        self.data_table.setRowCount(0)
        self.data_count_label.setText("数据: 0")
        self.stats_label.setText("共 0 条记录")

        if hasattr(self, 'chart_widget'):
            self.chart_widget.clear()

        if hasattr(self, 'data_stats'):
            self.data_stats.clear()

        self.log("清除图表数据")

    def clear_data(self):
        """清空数据"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有数据吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.data_recorder.clear()
            self.data_table.setRowCount(0)
            self.data_count_label.setText("数据: 0")
            self.stats_label.setText("共 0 条记录")
            self.log("清空数据")

    def import_data(self):
        """导入数据"""
        dialog = ImportDialog(self)
        if dialog.exec_() == ImportDialog.Accepted:
            imported_data = dialog.get_imported_data()

            if imported_data:
                # 如果需要清空现有数据
                if dialog.should_clear_existing():
                    self.data_recorder.clear()

                # 导入数据到记录器
                from core.data_recorder import DataPoint
                import time

                for item in imported_data:
                    try:
                        # 尝试从导入的数据创建DataPoint
                        timestamp = float(item.get('timestamp', time.time()))
                        setpoint = float(item.get('setpoint', 0))
                        actual = float(item.get('actual', 0))
                        output = float(item.get('output', 0))
                        error = float(item.get('error', setpoint - actual))

                        point = DataPoint(
                            timestamp=timestamp,
                            setpoint=setpoint,
                            actual=actual,
                            output=output,
                            error=error
                        )

                        # 手动添加到数据列表
                        self.data_recorder._data.append(point)
                    except (ValueError, TypeError) as e:
                        self.log(f"跳过无效数据行: {e}", "WARNING")

                # 更新显示
                count = self.data_recorder.data_count
                self.data_count_label.setText(f"数据: {count}")
                self.stats_label.setText(f"共 {count} 条记录")
                self.log(f"导入数据完成: {count} 条记录")
                QMessageBox.information(self, "成功", f"已导入 {count} 条数据记录")

                # 更新数据表格显示
                self._update_data_display()

    def export_data(self):
        """导出数据"""
        if self.data_recorder.data_count == 0:
            QMessageBox.information(self, "提示", "没有数据可导出")
            return

        # 显示导出对话框
        dialog = ExportDialog(self.data_recorder.data_count, self)
        if dialog.exec_() == ExportDialog.Accepted:
            filepath = dialog.get_export_filepath()
            format_type = dialog.get_export_format()

            if filepath:
                success = False
                if format_type == 'CSV':
                    success = self.data_recorder.export_csv(filepath)
                elif format_type == 'JSON':
                    success = self.data_recorder.export_json(filepath)
                elif format_type == 'TXT':
                    success = self._export_txt(filepath)
                elif format_type == 'EXCEL':
                    success = self._export_excel(filepath)

                if success:
                    self.log(f"导出数据: {filepath}")
                    QMessageBox.information(self, "成功", f"数据已导出为{format_type}文件")
                else:
                    self.log(f"导出数据失败: {filepath}", "ERROR")
                    QMessageBox.critical(self, "错误", f"导出{format_type}失败")

    def _export_txt(self, filepath):
        """导出为TXT文件"""
        try:
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                # 写入表头
                headers = ['时间', '设定值', '实际值', '输出值', '误差']
                f.write('\t'.join(headers) + '\n')

                # 写入数据
                for point in self.data_recorder.data:
                    row = [
                        point.time_str,
                        f"{point.setpoint:.2f}",
                        f"{point.actual:.2f}",
                        f"{point.output:.2f}",
                        f"{point.error:.2f}"
                    ]
                    f.write('\t'.join(row) + '\n')

            return True
        except Exception as e:
            self.log(f"导出TXT失败: {str(e)}", "ERROR")
            return False

    def _export_excel(self, filepath):
        """导出为Excel文件"""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill

            # 创建工作簿
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "PID数据"

            # 设置表头样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="007AFF", end_color="007AFF", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")

            # 写入表头
            headers = ['时间', '设定值', '实际值', '输出值', '误差']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment

            # 写入数据
            for i, point in enumerate(self.data_recorder.data, 2):
                ws.cell(row=i, column=1, value=point.time_str)
                ws.cell(row=i, column=2, value=point.setpoint)
                ws.cell(row=i, column=3, value=point.actual)
                ws.cell(row=i, column=4, value=point.output)
                ws.cell(row=i, column=5, value=point.error)

            # 调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column_letter].width = adjusted_width

            # 保存文件
            wb.save(filepath)
            return True

        except ImportError:
            self.log("导出Excel失败: 未安装openpyxl库", "ERROR")
            QMessageBox.warning(self, "警告", "导出Excel需要安装openpyxl库\n请运行: pip install openpyxl")
            return False
        except Exception as e:
            self.log(f"导出Excel失败: {str(e)}", "ERROR")
            return False

    def show_statistics(self):
        """显示数据统计对话框"""
        if self.data_recorder.data_count == 0:
            QMessageBox.information(self, "提示", "没有数据可统计")
            return

        stats = self.data_recorder.get_statistics()
        dialog = StatsDialog(stats, self)
        dialog.exec_()

    # 报警相关方法

    def _filter_alarm_table(self):
        """过滤报警表格"""
        level_filter = self.alarm_filter_combo.currentText()
        text_filter = self.alarm_filter_edit.text().lower()

        for row in range(self.alarm_table.rowCount()):
            show_row = True

            # 级别过滤
            if level_filter != "全部":
                level_item = self.alarm_table.item(row, 1)
                if level_item and level_item.text() != level_filter:
                    show_row = False

            # 文本过滤
            if text_filter and show_row:
                match = False
                for col in range(self.alarm_table.columnCount()):
                    item = self.alarm_table.item(row, col)
                    if item and text_filter in item.text().lower():
                        match = True
                        break
                if not match:
                    show_row = False

            self.alarm_table.setRowHidden(row, not show_row)

    def _clear_alarm_filter(self):
        """清除报警过滤"""
        self.alarm_filter_combo.setCurrentText("全部")
        self.alarm_filter_edit.clear()

    def _show_alarm_table_context_menu(self, position):
        """显示报警表格右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction

        # 获取点击的行
        row = self.alarm_table.rowAt(position.y())
        if row < 0:
            return

        # 选中该行
        self.alarm_table.selectRow(row)

        # 创建右键菜单
        menu = QMenu(self)

        # 确认报警
        ack_action = QAction("确认报警", self)
        ack_action.triggered.connect(lambda: self._acknowledge_alarm(row))
        menu.addAction(ack_action)

        # 确认所有报警
        ack_all_action = QAction("确认所有报警", self)
        ack_all_action.triggered.connect(self._acknowledge_all_alarms)
        menu.addAction(ack_all_action)

        menu.addSeparator()

        # 查看详细信息
        detail_action = QAction("查看详细信息", self)
        detail_action.triggered.connect(lambda: self._show_alarm_detail(row))
        menu.addAction(detail_action)

        menu.addSeparator()

        # 删除选中报警
        delete_action = QAction("删除选中报警", self)
        delete_action.triggered.connect(self._delete_selected_alarms)
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec_(self.alarm_table.viewport().mapToGlobal(position))

    def _acknowledge_alarm(self, row):
        """确认单个报警"""
        if row < len(self.alarm_manager.alarms):
            alarm = self.alarm_manager.alarms[row]
            self.alarm_manager.acknowledge_alarm(alarm)

            # 更新表格状态
            status_item = self.alarm_table.item(row, 4)
            if status_item:
                status_item.setText("已确认")

            self._update_alarm_stats()
            self.log(f"已确认报警: {alarm.message}")

    def _show_alarm_detail(self, row):
        """显示报警详细信息"""
        if row < len(self.alarm_manager.alarms):
            alarm = self.alarm_manager.alarms[row]

            detail_text = f"""
时间: {alarm.datetime_str}
级别: {alarm.level.value}
类型: {alarm.alarm_type.value}
消息: {alarm.message}
状态: {"已确认" if alarm.acknowledged else "未确认"}
"""
            if alarm.value is not None:
                detail_text += f"当前值: {alarm.value:.2f}\n"
            if alarm.limit is not None:
                detail_text += f"限制值: {alarm.limit:.2f}\n"

            QMessageBox.information(self, "报警详细信息", detail_text)

    def _delete_selected_alarms(self):
        """删除选中报警"""
        selected_rows = set()
        for item in self.alarm_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 条报警吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 从报警管理器中删除报警
            for row in sorted(selected_rows, reverse=True):
                if row < len(self.alarm_manager.alarms):
                    alarm = self.alarm_manager.alarms[row]
                    if alarm in self.alarm_manager._active_alarms:
                        self.alarm_manager._active_alarms.remove(alarm)
                    self.alarm_manager._alarms.pop(row)

            # 更新表格显示
            self.alarm_table.setRowCount(0)
            for alarm in self.alarm_manager.alarms:
                row = self.alarm_table.rowCount()
                self.alarm_table.insertRow(row)
                self.alarm_table.setItem(row, 0, QTableWidgetItem(alarm.datetime_str))
                level_item = QTableWidgetItem(alarm.level.value)
                level_item.setForeground(QColor(alarm.level_color))
                self.alarm_table.setItem(row, 1, level_item)
                self.alarm_table.setItem(row, 2, QTableWidgetItem(alarm.alarm_type.value))
                self.alarm_table.setItem(row, 3, QTableWidgetItem(alarm.message))
                self.alarm_table.setItem(row, 4, QTableWidgetItem("未确认" if not alarm.acknowledged else "已确认"))

            self._update_alarm_stats()
            self.log(f"已删除 {len(selected_rows)} 条报警")

    def _on_alarm(self, alarm):
        """报警回调"""
        # 添加到报警表格
        row = self.alarm_table.rowCount()
        self.alarm_table.insertRow(row)

        # 设置表格内容
        self.alarm_table.setItem(row, 0, QTableWidgetItem(alarm.datetime_str))

        level_item = QTableWidgetItem(alarm.level.value)
        level_item.setForeground(QColor(alarm.level_color))
        self.alarm_table.setItem(row, 1, level_item)

        self.alarm_table.setItem(row, 2, QTableWidgetItem(alarm.alarm_type.value))
        self.alarm_table.setItem(row, 3, QTableWidgetItem(alarm.message))
        self.alarm_table.setItem(row, 4, QTableWidgetItem("未确认" if not alarm.acknowledged else "已确认"))

        # 滚动到最新报警
        self.alarm_table.scrollToBottom()

        # 更新报警统计
        self._update_alarm_stats()

        # 记录日志
        self.log(f"报警: [{alarm.level.value}] {alarm.message}", "WARNING")

    def _acknowledge_all_alarms(self):
        """确认所有报警"""
        self.alarm_manager.acknowledge_all()

        # 更新表格状态
        for row in range(self.alarm_table.rowCount()):
            status_item = self.alarm_table.item(row, 4)
            if status_item and status_item.text() == "未确认":
                status_item.setText("已确认")

        self._update_alarm_stats()
        self.log("已确认所有报警")

    def _clear_alarms(self):
        """清除所有报警"""
        reply = QMessageBox.question(
            self, "确认清除", "确定要清除所有报警记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.alarm_manager.clear_alarms()
            self.alarm_table.setRowCount(0)
            self._update_alarm_stats()
            self.log("已清除所有报警")

    def _update_alarm_stats(self):
        """更新报警统计"""
        total = len(self.alarm_manager.alarms)
        active = len(self.alarm_manager.active_alarms)
        self.alarm_count_label.setText(f"报警: {total}")
        self.active_alarm_label.setText(f"活动: {active}")

        # 更新状态栏
        self.alarm_status_label.setText(f"报警: {active}")

    # 数据回放相关方法

    def _on_playback_data(self, point):
        """回放数据回调"""
        # 添加到图表
        if hasattr(self, 'chart_widget'):
            self.chart_widget.add_data(
                setpoint=point.setpoint,
                actual=point.actual,
                output=point.output,
                timestamp=point.timestamp
            )

        # 更新数据统计
        if hasattr(self, 'data_stats'):
            self.data_stats.add_value(point.actual)

    def _on_playback_state_changed(self, state):
        """回放状态变化回调"""
        if state == PlaybackState.PLAYING:
            self.log("数据回放: 播放中")
            self.play_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_playback_button.setEnabled(True)
        elif state == PlaybackState.PAUSED:
            self.log("数据回放: 已暂停")
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_playback_button.setEnabled(True)
        elif state == PlaybackState.STOPPED:
            self.log("数据回放: 已停止")
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_playback_button.setEnabled(False)
            # 重置进度条
            if hasattr(self, 'playback_progress'):
                self.playback_progress.setValue(0)
            if hasattr(self, 'playback_percent_label'):
                self.playback_percent_label.setText("0%")
            if hasattr(self, 'playback_time_label'):
                self.playback_time_label.setText("00:00 / 00:00")

    def _on_playback_progress(self, progress):
        """回放进度回调"""
        # 更新进度条
        if hasattr(self, 'playback_progress'):
            self.playback_progress.setValue(int(progress))
        if hasattr(self, 'playback_percent_label'):
            self.playback_percent_label.setText(f"{int(progress)}%")

        # 更新时间显示
        if hasattr(self, 'playback_time_label'):
            current = self.data_player.current_time
            total = self.data_player.total_time
            self.playback_time_label.setText(f"{current} / {total}")

    def _on_playback_finished(self):
        """回放完成回调"""
        self.log("数据回放完成")
        QMessageBox.information(self, "回放完成", "数据回放已完成")

    def _play_data(self):
        """播放数据"""
        if not self.data_player._data:
            QMessageBox.information(self, "提示", "请先加载数据文件")
            return

        self.data_player.play()
        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_playback_button.setEnabled(True)

    def _pause_data(self):
        """暂停数据"""
        self.data_player.pause()
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)

    def _stop_data(self):
        """停止数据"""
        self.data_player.stop()
        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_playback_button.setEnabled(False)

    def _on_speed_changed(self, text):
        """回放速度改变"""
        speed_map = {"0.5x": 0.5, "1x": 1.0, "2x": 2.0, "5x": 5.0, "10x": 10.0}
        speed = speed_map.get(text, 1.0)
        self.data_player.set_speed(speed)
        self.log(f"回放速度设置为: {text}")

    def _load_playback_data(self):
        """加载回放数据"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载数据文件", "",
            "CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*)"
        )

        if filepath:
            try:
                from core.data_recorder import DataPoint
                import json
                import csv

                data_points = []

                if filepath.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        for item in json_data:
                            point = DataPoint(
                                timestamp=item.get('timestamp', 0),
                                setpoint=item.get('setpoint', 0),
                                actual=item.get('actual', 0),
                                output=item.get('output', 0),
                                error=item.get('error', 0)
                            )
                            data_points.append(point)

                elif filepath.endswith('.csv'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            point = DataPoint(
                                timestamp=float(row.get('timestamp', 0)),
                                setpoint=float(row.get('setpoint', 0)),
                                actual=float(row.get('actual', 0)),
                                output=float(row.get('output', 0)),
                                error=float(row.get('error', 0))
                            )
                            data_points.append(point)

                if data_points:
                    self.data_player.load_data(data_points)
                    self.log(f"加载数据文件: {filepath} ({len(data_points)} 条记录)")
                    QMessageBox.information(self, "成功", f"已加载 {len(data_points)} 条数据记录")
                else:
                    QMessageBox.warning(self, "警告", "数据文件为空或格式不正确")

            except Exception as e:
                self.log(f"加载数据文件失败: {str(e)}", "ERROR")
                QMessageBox.critical(self, "错误", f"加载数据文件失败: {str(e)}")

    def _toggle_toolbar(self, checked):
        """切换工具栏显示"""
        toolbar = self.findChild(QWidget, "iosToolbar")
        if toolbar:
            toolbar.setVisible(checked)

    def _toggle_log_panel(self, checked):
        """切换日志面板显示"""
        log_container = self.findChild(QWidget, "logContainer")
        if log_container:
            log_container.setVisible(checked)

    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == SettingsDialog.Accepted:
            self.log("设置已更新")

    def compare_parameters(self):
        """参数对比"""
        # 获取当前PID参数
        current_params = {
            'kp': self.p_value_spin.value(),
            'ki': self.i_value_spin.value(),
            'kd': self.d_value_spin.value()
        }

        dialog = CompareDialog(current_params, self)
        dialog.exec_()

    def show_about(self):
        """显示帮助对话框"""
        dialog = HelpDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        """关闭事件"""
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setFixedSize(270, 170)

        # 主容器
        container = QFrame(dialog)
        container.setGeometry(0, 0, 270, 170)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(242,242,247,0.96);
                border-radius: 14px;
                border: 0.5px solid rgba(0,0,0,0.12);
            }
        """)

        # 毛玻璃阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 20, 16, 0)
        layout.setSpacing(0)

        # 标题
        title_label = QLabel("PID上位机")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1C1C1E; background: transparent; border: none;")
        layout.addWidget(title_label)

        layout.addSpacing(4)

        # 描述
        desc_label = QLabel("确定要退出吗？")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 13px; color: #636366; background: transparent; border: none;")
        layout.addWidget(desc_label)

        layout.addSpacing(18)

        # 分割线
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.HLine)
        sep_h.setStyleSheet("background-color: rgba(0,0,0,0.1); max-height: 0.5px; border: none;")
        layout.addWidget(sep_h)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #007AFF;
                border: none;
                border-right: 0.5px solid rgba(0,0,0,0.1);
                border-bottom-left-radius: 14px;
                font-size: 16px;
                font-weight: 400;
            }
            QPushButton:hover { background-color: rgba(0,0,0,0.04); }
            QPushButton:pressed { background-color: rgba(0,0,0,0.08); }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        confirm_btn = QPushButton("退出")
        confirm_btn.setFixedHeight(44)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FF3B30;
                border: none;
                border-bottom-right-radius: 14px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: rgba(255,59,48,0.06); }
            QPushButton:pressed { background-color: rgba(255,59,48,0.12); }
        """)
        confirm_btn.clicked.connect(dialog.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        reply = dialog.exec_()

        if reply == QDialog.Accepted:
            # 保存配置
            self._save_config()

            # 断开串口
            if self.serial_connected:
                if self.simulation_mode:
                    self.simulated_serial.disconnect()
                else:
                    self.serial_manager.disconnect()

            # 停止自动调参
            if self.auto_tuner.is_running:
                self.auto_tuner.stop()

            self.log("应用程序关闭")
            event.accept()
        else:
            event.ignore()
