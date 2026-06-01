#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
帮助对话框
显示快捷键列表和使用说明
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QGroupBox, QFormLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextBrowser
)
from PyQt5.QtCore import Qt


class HelpDialog(QDialog):
    """帮助对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("帮助")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标签页
        tab_widget = QTabWidget()

        # 快捷键标签页
        shortcuts_tab = self._create_shortcuts_tab()
        tab_widget.addTab(shortcuts_tab, "快捷键")

        # 使用说明标签页
        usage_tab = self._create_usage_tab()
        tab_widget.addTab(usage_tab, "使用说明")

        # 关于标签页
        about_tab = self._create_about_tab()
        tab_widget.addTab(about_tab, "关于")

        layout.addWidget(tab_widget)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _create_shortcuts_tab(self):
        """创建快捷键标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 创建表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["快捷键", "功能"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)

        # 快捷键数据
        shortcuts = [
            ("Ctrl+N", "新建项目"),
            ("Ctrl+O", "打开项目"),
            ("Ctrl+S", "保存项目"),
            ("Ctrl+E", "导出数据"),
            ("Ctrl+Q", "退出程序"),
            ("Ctrl+,", "打开设置"),
            ("Ctrl+T", "自动调参"),
            ("Ctrl+D", "参数对比"),
            ("Space", "启动/停止控制"),
            ("F5", "刷新串口"),
        ]

        table.setRowCount(len(shortcuts))
        for i, (shortcut, description) in enumerate(shortcuts):
            table.setItem(i, 0, QTableWidgetItem(shortcut))
            table.setItem(i, 1, QTableWidgetItem(description))

        layout.addWidget(table)
        return tab

    def _create_usage_tab(self):
        """创建使用说明标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 创建文本浏览器
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        # 使用说明内容
        usage_html = """
        <h2>PID上位机使用说明</h2>

        <h3>1. 连接设备</h3>
        <ol>
            <li>选择串口号（或启用模拟模式）</li>
            <li>设置波特率和其他串口参数</li>
            <li>点击"连接"按钮</li>
        </ol>

        <h3>2. PID参数调节</h3>
        <ol>
            <li>在PID参数区域设置P、I、D参数</li>
            <li>设置目标值</li>
            <li>点击"发送参数"将参数发送到设备</li>
            <li>点击"读取参数"从设备读取当前参数</li>
        </ol>

        <h3>3. 控制操作</h3>
        <ol>
            <li>点击"启动控制"开始PID控制</li>
            <li>观察实时图表中的响应曲线</li>
            <li>根据需要调整PID参数</li>
            <li>点击"停止控制"结束控制</li>
        </ol>

        <h3>4. 自动调参</h3>
        <ol>
            <li>点击"自动调参"按钮</li>
            <li>选择调参方法（Ziegler-Nichols、Cohen-Coon等）</li>
            <li>等待调参过程完成</li>
            <li>查看调参结果并应用</li>
        </ol>

        <h3>5. 数据记录与导出</h3>
        <ol>
            <li>启用"自动记录"功能</li>
            <li>数据将自动记录到表格中</li>
            <li>点击"导出"将数据保存为CSV或JSON文件</li>
            <li>点击"统计"查看详细的数据统计信息</li>
        </ol>

        <h3>6. 报警功能</h3>
        <ol>
            <li>在设置中配置报警限制</li>
            <li>当值超出限制时会自动触发报警</li>
            <li>在报警标签页查看报警历史</li>
            <li>可以确认或清除报警</li>
        </ol>
        """

        browser.setHtml(usage_html)
        layout.addWidget(browser)
        return tab

    def _create_about_tab(self):
        """创建关于标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 创建文本浏览器
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        # 关于内容
        about_html = """
        <h2>PID上位机 v1.0.0</h2>

        <p>用于调节PID参数的上位机软件</p>
        <p>通过串口与下位机通信</p>

        <h3>技术栈</h3>
        <ul>
            <li>Python 3.8+</li>
            <li>PyQt5 - GUI框架</li>
            <li>pyserial - 串口通信</li>
            <li>pyqtgraph - 实时图表</li>
            <li>numpy - 数据处理</li>
        </ul>

        <h3>功能特点</h3>
        <ul>
            <li>iOS风格界面设计</li>
            <li>实时PID响应曲线显示</li>
            <li>多种自动调参方法</li>
            <li>数据记录与导出</li>
            <li>报警管理</li>
            <li>模拟模式支持</li>
        </ul>

        <h3>联系方式</h3>
        <p>如有问题或建议，请联系开发者。</p>
        """

        browser.setHtml(about_html)
        layout.addWidget(browser)
        return tab
