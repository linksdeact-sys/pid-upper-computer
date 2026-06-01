#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导出对话框
用于导出CSV和JSON格式的数据
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QComboBox, QCheckBox, QDialogButtonBox,
    QMessageBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt


class ExportDialog(QDialog):
    """数据导出对话框"""

    def __init__(self, data_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出数据")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._data_count = data_count
        self._export_filepath = None
        self._export_format = None

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 数据信息组
        info_group = QGroupBox("数据信息")
        info_layout = QVBoxLayout()

        info_label = QLabel(f"当前共有 {self._data_count} 条数据记录")
        info_label.setStyleSheet("font-size: 14px; color: #1C1C1E;")
        info_layout.addWidget(info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 导出格式组
        format_group = QGroupBox("导出格式")
        format_layout = QVBoxLayout()

        # 格式选择
        self.format_group = QButtonGroup()

        self.csv_radio = QRadioButton("CSV格式 (*.csv)")
        self.csv_radio.setChecked(True)
        self.csv_radio.setToolTip("导出为逗号分隔的文本文件，可用Excel打开")
        self.format_group.addButton(self.csv_radio, 0)
        format_layout.addWidget(self.csv_radio)

        self.json_radio = QRadioButton("JSON格式 (*.json)")
        self.json_radio.setToolTip("导出为JSON格式，便于程序读取")
        self.format_group.addButton(self.json_radio, 1)
        format_layout.addWidget(self.json_radio)

        self.txt_radio = QRadioButton("文本格式 (*.txt)")
        self.txt_radio.setToolTip("导出为制表符分隔的文本文件")
        self.format_group.addButton(self.txt_radio, 2)
        format_layout.addWidget(self.txt_radio)

        self.excel_radio = QRadioButton("Excel格式 (*.xlsx)")
        self.excel_radio.setToolTip("导出为Excel文件（需要安装openpyxl）")
        self.format_group.addButton(self.excel_radio, 3)
        format_layout.addWidget(self.excel_radio)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # 导出选项组
        options_group = QGroupBox("导出选项")
        options_layout = QVBoxLayout()

        # 编码选择
        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(QLabel("文件编码:"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312"])
        encoding_layout.addWidget(self.encoding_combo)
        encoding_layout.addStretch()
        options_layout.addLayout(encoding_layout)

        # 包含表头
        self.include_header_check = QCheckBox("包含表头")
        self.include_header_check.setChecked(True)
        self.include_header_check.setToolTip("在CSV文件中包含列标题")
        options_layout.addWidget(self.include_header_check)

        # 包含统计信息
        self.include_stats_check = QCheckBox("包含统计信息")
        self.include_stats_check.setChecked(True)
        self.include_stats_check.setToolTip("在JSON文件中包含数据统计信息")
        options_layout.addWidget(self.include_stats_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 保存位置组
        save_group = QGroupBox("保存位置")
        save_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择保存位置...")
        self.file_path_edit.setReadOnly(True)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_save_path)

        save_layout.addWidget(self.file_path_edit)
        save_layout.addWidget(browse_btn)
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText("导出")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self._on_export)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _browse_save_path(self):
        """浏览保存路径"""
        # 获取当前选择的格式
        if self.csv_radio.isChecked():
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "",
                "CSV文件 (*.csv);;所有文件 (*)"
            )
        elif self.json_radio.isChecked():
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "",
                "JSON文件 (*.json);;所有文件 (*)"
            )
        elif self.txt_radio.isChecked():
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "",
                "文本文件 (*.txt);;所有文件 (*)"
            )
        elif self.excel_radio.isChecked():
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "",
                "Excel文件 (*.xlsx);;所有文件 (*)"
            )
        else:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "",
                "所有文件 (*)"
            )

        if filepath:
            self.file_path_edit.setText(filepath)

    def _on_export(self):
        """导出数据"""
        filepath = self.file_path_edit.text()
        if not filepath:
            QMessageBox.warning(self, "警告", "请先选择保存位置")
            return

        # 检查文件扩展名
        if self.csv_radio.isChecked():
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self._export_format = 'CSV'
        elif self.json_radio.isChecked():
            if not filepath.endswith('.json'):
                filepath += '.json'
            self._export_format = 'JSON'
        elif self.txt_radio.isChecked():
            if not filepath.endswith('.txt'):
                filepath += '.txt'
            self._export_format = 'TXT'
        elif self.excel_radio.isChecked():
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            self._export_format = 'EXCEL'
        else:
            self._export_format = 'CSV'

        # 检查文件是否存在
        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"文件 {os.path.basename(filepath)} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self._export_filepath = filepath
        self.accept()

    def get_export_filepath(self):
        """获取导出文件路径"""
        return self._export_filepath

    def get_export_format(self):
        """获取导出格式"""
        return self._export_format

    def get_encoding(self):
        """获取编码"""
        return self.encoding_combo.currentText()

    def should_include_header(self):
        """是否包含表头"""
        return self.include_header_check.isChecked()

    def should_include_stats(self):
        """是否包含统计信息"""
        return self.include_stats_check.isChecked()
