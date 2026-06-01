#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数对比对话框
用于对比不同的PID参数组合
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QGroupBox, QFormLayout,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class CompareDialog(QDialog):
    """参数对比对话框"""

    def __init__(self, current_params=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("参数对比")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 当前参数
        self._current_params = current_params or {'kp': 0, 'ki': 0, 'kd': 0}

        # 参数集合列表
        self._param_sets = []
        self._param_sets.append({
            'name': '当前参数',
            'kp': self._current_params.get('kp', 0),
            'ki': self._current_params.get('ki', 0),
            'kd': self._current_params.get('kd', 0)
        })

        # 初始化界面
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标签页
        tab_widget = QTabWidget()

        # 参数输入标签页
        input_tab = self._create_input_tab()
        tab_widget.addTab(input_tab, "输入参数")

        # 对比表格标签页
        compare_tab = self._create_compare_tab()
        tab_widget.addTab(compare_tab, "参数对比")

        # 评估标签页
        eval_tab = self._create_eval_tab()
        tab_widget.addTab(eval_tab, "性能评估")

        layout.addWidget(tab_widget)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _create_input_tab(self):
        """创建参数输入标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 当前参数显示
        current_group = QGroupBox("当前参数")
        current_layout = QFormLayout()

        self.current_kp_label = QLabel(f"{self._current_params.get('kp', 0):.3f}")
        self.current_ki_label = QLabel(f"{self._current_params.get('ki', 0):.3f}")
        self.current_kd_label = QLabel(f"{self._current_params.get('kd', 0):.3f}")

        current_layout.addRow("Kp:", self.current_kp_label)
        current_layout.addRow("Ki:", self.current_ki_label)
        current_layout.addRow("Kd:", self.current_kd_label)

        current_group.setLayout(current_layout)
        layout.addWidget(current_group)

        # 添加新参数组
        add_group = QGroupBox("添加对比参数")
        add_layout = QFormLayout()

        self.name_edit = QPushButton("参数组 1")
        self.name_edit.clicked.connect(self._edit_name)

        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0, 10000)
        self.kp_spin.setDecimals(3)
        self.kp_spin.setValue(self._current_params.get('kp', 0))

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0, 10000)
        self.ki_spin.setDecimals(3)
        self.ki_spin.setValue(self._current_params.get('ki', 0))

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0, 10000)
        self.kd_spin.setDecimals(3)
        self.kd_spin.setValue(self._current_params.get('kd', 0))

        add_layout.addRow("名称:", self.name_edit)
        add_layout.addRow("Kp:", self.kp_spin)
        add_layout.addRow("Ki:", self.ki_spin)
        add_layout.addRow("Kd:", self.kd_spin)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # 添加按钮
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("添加到对比")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_param_set)

        clear_btn = QPushButton("清空所有")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._clear_param_sets)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        return tab

    def _create_compare_tab(self):
        """创建对比表格标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 对比表格
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(4)
        self.compare_table.setHorizontalHeaderLabels(["参数组", "Kp", "Ki", "Kd"])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.compare_table.setAlternatingRowColors(True)

        # 更新表格
        self._update_compare_table()

        layout.addWidget(self.compare_table)

        # 操作按钮
        btn_layout = QHBoxLayout()

        remove_btn = QPushButton("删除选中")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._remove_selected)

        btn_layout.addStretch()
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        return tab

    def _create_eval_tab(self):
        """创建性能评估标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 评估说明
        info_label = QLabel("根据PID参数特性进行理论评估（仅供参考）")
        info_label.setStyleSheet("color: #8E8E93; font-size: 13px;")
        layout.addWidget(info_label)

        # 评估表格
        self.eval_table = QTableWidget()
        self.eval_table.setColumnCount(5)
        self.eval_table.setHorizontalHeaderLabels([
            "参数组", "响应速度", "稳定性", "超调风险", "综合评分"
        ])
        self.eval_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.eval_table.setAlternatingRowColors(True)

        layout.addWidget(self.eval_table)

        # 评估按钮
        eval_btn = QPushButton("重新评估")
        eval_btn.setObjectName("primaryButton")
        eval_btn.clicked.connect(self._evaluate_params)
        layout.addWidget(eval_btn)

        return tab

    def _edit_name(self):
        """编辑参数组名称"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "参数组名称", "请输入名称:")
        if ok and name:
            self.name_edit.setText(name)

    def _add_param_set(self):
        """添加参数组"""
        param_set = {
            'name': self.name_edit.text(),
            'kp': self.kp_spin.value(),
            'ki': self.ki_spin.value(),
            'kd': self.kd_spin.value()
        }

        self._param_sets.append(param_set)

        # 更新名称
        count = len(self._param_sets)
        self.name_edit.setText(f"参数组 {count}")

        # 更新表格
        self._update_compare_table()

        QMessageBox.information(self, "成功", f"已添加参数组: {param_set['name']}")

    def _clear_param_sets(self):
        """清空参数组"""
        if len(self._param_sets) <= 1:
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有对比参数组吗？（保留当前参数）",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._param_sets = [self._param_sets[0]]
            self._update_compare_table()

    def _remove_selected(self):
        """删除选中的参数组"""
        selected_rows = set()
        for item in self.compare_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        # 不允许删除第一行（当前参数）
        if 0 in selected_rows:
            QMessageBox.warning(self, "警告", "不能删除当前参数组")
            selected_rows.discard(0)

        if not selected_rows:
            return

        # 删除选中的参数组
        for row in sorted(selected_rows, reverse=True):
            if row < len(self._param_sets):
                self._param_sets.pop(row)

        self._update_compare_table()

    def _update_compare_table(self):
        """更新对比表格"""
        self.compare_table.setRowCount(len(self._param_sets))

        for i, param_set in enumerate(self._param_sets):
            self.compare_table.setItem(i, 0, QTableWidgetItem(param_set['name']))
            self.compare_table.setItem(i, 1, QTableWidgetItem(f"{param_set['kp']:.3f}"))
            self.compare_table.setItem(i, 2, QTableWidgetItem(f"{param_set['ki']:.3f}"))
            self.compare_table.setItem(i, 3, QTableWidgetItem(f"{param_set['kd']:.3f}"))

    def _evaluate_params(self):
        """评估参数"""
        self.eval_table.setRowCount(len(self._param_sets))

        for i, param_set in enumerate(self._param_sets):
            kp = param_set['kp']
            ki = param_set['ki']
            kd = param_set['kd']

            # 简单的理论评估
            # 响应速度：主要由Kp决定
            speed_score = min(100, kp * 10)
            if speed_score < 30:
                speed_text = "慢"
            elif speed_score < 70:
                speed_text = "中"
            else:
                speed_text = "快"

            # 稳定性：Ki和Kd影响
            stability_score = 100 - (ki * 5 + kd * 2)
            stability_score = max(0, min(100, stability_score))
            if stability_score < 40:
                stability_text = "差"
            elif stability_score < 70:
                stability_text = "中"
            else:
                stability_text = "好"

            # 超调风险：Kp和Kd影响
            overshoot_risk = kp * 3 + kd * 1
            overshoot_risk = min(100, overshoot_risk)
            if overshoot_risk < 30:
                overshoot_text = "低"
            elif overshoot_risk < 70:
                overshoot_text = "中"
            else:
                overshoot_text = "高"

            # 综合评分
            total_score = (speed_score * 0.4 + stability_score * 0.4 +
                          (100 - overshoot_risk) * 0.2)

            self.eval_table.setItem(i, 0, QTableWidgetItem(param_set['name']))
            self.eval_table.setItem(i, 1, QTableWidgetItem(speed_text))
            self.eval_table.setItem(i, 2, QTableWidgetItem(stability_text))
            self.eval_table.setItem(i, 3, QTableWidgetItem(overshoot_text))
            self.eval_table.setItem(i, 4, QTableWidgetItem(f"{total_score:.0f}"))

    def get_param_sets(self):
        """获取所有参数组"""
        return self._param_sets.copy()
