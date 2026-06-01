#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID上位机 - 主程序入口
用于调节PID参数的上位机软件，通过串口与下位机通信
"""

import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QIcon
from ui.main_window import MainWindow

def main():
    """主函数"""
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建应用程序
    app = QApplication(sys.argv)

    # 强制使用 Fusion 风格
    app.setStyle(QStyleFactory.create("Fusion"))

    # 设置Fusion调色板，防止系统颜色污染QSS
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor('#F2F2F7'))
    palette.setColor(QPalette.WindowText, QColor('#000000'))
    palette.setColor(QPalette.Base, QColor('#FFFFFF'))
    palette.setColor(QPalette.AlternateBase, QColor('#F2F2F7'))
    palette.setColor(QPalette.Button, QColor('#E5E5EA'))
    palette.setColor(QPalette.ButtonText, QColor('#000000'))
    palette.setColor(QPalette.Highlight, QColor('#007AFF'))
    palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))
    app.setPalette(palette)

    # 设置应用程序信息和图标
    app.setApplicationName("PID上位机")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PID上位机")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "app_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    # Windows任务栏图标
    if sys.platform == 'win32':
        myappid = 'pid.tuner.v1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
