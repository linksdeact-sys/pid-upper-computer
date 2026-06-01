# PID上位机

基于 PyQt5 的 PID 参数调节上位机软件，通过串口与下位机通信，支持实时图表、模拟控制、自动调参等功能。

## 功能特性

- **串口通信** - 自动检测串口，支持多种波特率，实时收发数据
- **实时图表** - 基于 pyqtgraph 的高性能实时曲线绘制，支持缩放、截图
- **PID参数调节** - 在线调节 Kp/Ki/Kd 参数和目标值
- **模拟控制** - 内置一阶加滞后模型，无需硬件即可测试 PID 控制效果
- **自动调参** - 支持 Ziegler-Nichols、Cohen-Coon、继电反馈法、AMIGO 四种算法
- **数据记录与导出** - 自动记录运行数据，支持 CSV/JSON 格式导入导出
- **报警管理** - 阈值报警、报警历史记录、分级过滤
- **数据回放** - 加载历史数据文件进行回放分析

## 界面风格

采用 iOS/macOS 设计风格，基于 Fusion 渲染引擎，遵循 Apple Human Interface Guidelines。

## 项目结构

```
├── main.py                 # 程序入口
├── core/                   # 核心功能模块
│   ├── serial_manager.py   # 串口通信管理
│   ├── protocol.py         # 通信协议解析
│   ├── pid_controller.py   # PID 控制器
│   ├── simulator.py        # 模拟器
│   ├── auto_tuner.py       # 自动调参
│   ├── data_recorder.py    # 数据记录
│   ├── data_player.py      # 数据回放
│   └── alarm.py            # 报警管理
├── ui/                     # 界面模块
│   ├── main_window.py      # 主窗口
│   ├── chart_widget.py     # 实时图表组件
│   ├── settings_dialog.py  # 设置对话框
│   ├── stats_dialog.py     # 统计对话框
│   ├── export_dialog.py    # 导出对话框
│   └── help_dialog.py      # 帮助对话框
└── utils/                  # 工具模块
    ├── config.py           # 配置管理
    ├── logger.py           # 日志模块
    └── helpers.py          # 辅助函数
```

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- PyQt5
- pyqtgraph
- pyserial
- numpy

## 运行

```bash
python main.py
```

## 打包为 exe

```bash
pyinstaller --noconfirm --onefile --windowed --icon=ui/app_icon.ico --name=PID上位机 --add-data="ui/app_icon.ico;ui" --add-data="ui/arrow_down.svg;ui" main.py
```

打包后的可执行文件在 `dist/` 目录下。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+E | 导出数据 |
| Ctrl+I | 导入数据 |
| Ctrl+T | 自动调参 |
| Ctrl+S | 保存参数 |
| Ctrl+, | 打开设置 |
| F1     | 帮助 |

## 许可证

MIT License
