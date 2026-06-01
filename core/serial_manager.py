#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串口管理模块
负责串口的检测、连接、数据收发
"""

import time
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

import serial
import serial.tools.list_ports

from core.protocol import (
    ProtocolParser, ProtocolFrame, CommandCode,
    PIDParams, RealtimeData, StatusData, ControlCommand,
    build_read_pid_params_frame, build_write_pid_params_frame,
    build_read_realtime_data_frame, build_start_stop_frame,
    build_set_target_frame, build_read_status_frame,
    build_auto_tune_start_frame, build_auto_tune_stop_frame,
    parse_pid_params_response, parse_realtime_data_response,
    parse_status_response, parse_auto_tune_result
)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


@dataclass
class SerialConfig:
    """串口配置"""
    port: str = ''
    baudrate: int = 115200
    bytesize: int = 8
    stopbits: float = 1
    parity: str = 'N'
    timeout: float = 0.1


class SerialManager:
    """串口管理器"""

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._config = SerialConfig()
        self._state = ConnectionState.DISCONNECTED
        self._parser = ProtocolParser()
        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 回调函数
        self._on_data_received: Optional[Callable] = None
        self._on_connection_changed: Optional[Callable] = None
        self._on_pid_params_received: Optional[Callable] = None
        self._on_realtime_data_received: Optional[Callable] = None
        self._on_status_received: Optional[Callable] = None
        self._on_auto_tune_result: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # 统计信息
        self._bytes_sent = 0
        self._bytes_received = 0
        self._frames_sent = 0
        self._frames_received = 0

    @property
    def state(self) -> ConnectionState:
        """获取连接状态"""
        return self._state

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._state == ConnectionState.CONNECTED

    @property
    def bytes_sent(self) -> int:
        """发送字节数"""
        return self._bytes_sent

    @property
    def bytes_received(self) -> int:
        """接收字节数"""
        return self._bytes_received

    @property
    def frames_sent(self) -> int:
        """发送帧数"""
        return self._frames_sent

    @property
    def frames_received(self) -> int:
        """接收帧数"""
        return self._frames_received

    def reset_statistics(self):
        """重置统计信息"""
        self._bytes_sent = 0
        self._bytes_received = 0
        self._frames_sent = 0
        self._frames_received = 0

    # 回调设置

    def set_on_data_received(self, callback: Callable):
        """设置数据接收回调"""
        self._on_data_received = callback

    def set_on_connection_changed(self, callback: Callable):
        """设置连接状态变化回调"""
        self._on_connection_changed = callback

    def set_on_pid_params_received(self, callback: Callable):
        """设置PID参数接收回调"""
        self._on_pid_params_received = callback

    def set_on_realtime_data_received(self, callback: Callable):
        """设置实时数据接收回调"""
        self._on_realtime_data_received = callback

    def set_on_status_received(self, callback: Callable):
        """设置状态接收回调"""
        self._on_status_received = callback

    def set_on_auto_tune_result(self, callback: Callable):
        """设置自动调参结果回调"""
        self._on_auto_tune_result = callback

    def set_on_error(self, callback: Callable):
        """设置错误回调"""
        self._on_error = callback

    # 串口操作

    @staticmethod
    def list_ports() -> List[dict]:
        """列出可用串口"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'manufacturer': port.manufacturer,
                'product': port.product,
            })
        return ports

    def connect(self, config: Optional[SerialConfig] = None) -> bool:
        """连接串口"""
        if config is not None:
            self._config = config

        if not self._config.port:
            self._set_state(ConnectionState.ERROR)
            self._notify_error("未指定串口")
            return False

        try:
            self._set_state(ConnectionState.CONNECTING)

            self._serial = serial.Serial(
                port=self._config.port,
                baudrate=self._config.baudrate,
                bytesize=self._config.bytesize,
                stopbits=self._config.stopbits,
                parity=self._config.parity,
                timeout=self._config.timeout
            )

            if self._serial.is_open:
                self._running = True
                self._parser.clear()
                self._start_read_thread()
                self._set_state(ConnectionState.CONNECTED)
                return True
            else:
                self._set_state(ConnectionState.ERROR)
                self._notify_error("无法打开串口")
                return False

        except Exception as e:
            self._set_state(ConnectionState.ERROR)
            self._notify_error(f"连接失败: {str(e)}")
            return False

    def disconnect(self):
        """断开串口"""
        self._running = False

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass

        self._serial = None
        self._set_state(ConnectionState.DISCONNECTED)

    def _start_read_thread(self):
        """启动读取线程"""
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self):
        """读取循环"""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if data:
                        with self._lock:
                            self._bytes_received += len(data)
                        self._process_received_data(data)
                else:
                    time.sleep(0.01)
            except serial.SerialException:
                if self._running:
                    self._set_state(ConnectionState.ERROR)
                    self._notify_error("串口连接断开")
                break
            except Exception as e:
                if self._running:
                    self._notify_error(f"读取错误: {str(e)}")
                break

    def _process_received_data(self, data: bytes):
        """处理接收到的数据"""
        # 通知原始数据接收
        if self._on_data_received:
            self._on_data_received(data)

        # 喂入协议解析器
        self._parser.feed(data)

        # 处理解析到的帧
        while True:
            frame = self._parser.get_frame()
            if frame is None:
                break

            with self._lock:
                self._frames_received += 1
            self._process_frame(frame)

    def _process_frame(self, frame: ProtocolFrame):
        """处理协议帧"""
        if frame.command == CommandCode.READ_PID_PARAMS:
            params = parse_pid_params_response(frame)
            if params and self._on_pid_params_received:
                self._on_pid_params_received(params)

        elif frame.command == CommandCode.REALTIME_DATA_RESP:
            data = parse_realtime_data_response(frame)
            if data and self._on_realtime_data_received:
                self._on_realtime_data_received(data)

        elif frame.command == CommandCode.STATUS_RESPONSE:
            status = parse_status_response(frame)
            if status and self._on_status_received:
                self._on_status_received(status)

        elif frame.command == CommandCode.AUTO_TUNE_RESULT:
            params = parse_auto_tune_result(frame)
            if params and self._on_auto_tune_result:
                self._on_auto_tune_result(params)

    def _send_data(self, data: bytes) -> bool:
        """发送数据"""
        if not self.is_connected or not self._serial:
            self._notify_error("未连接串口")
            return False

        try:
            with self._lock:
                self._serial.write(data)
                self._bytes_sent += len(data)
                self._frames_sent += 1
            return True
        except Exception as e:
            self._notify_error(f"发送失败: {str(e)}")
            return False

    # 协议命令发送

    def read_pid_params(self) -> bool:
        """读取PID参数"""
        data = build_read_pid_params_frame()
        return self._send_data(data)

    def write_pid_params(self, params: PIDParams) -> bool:
        """写入PID参数"""
        data = build_write_pid_params_frame(params)
        return self._send_data(data)

    def read_realtime_data(self) -> bool:
        """读取实时数据"""
        data = build_read_realtime_data_frame()
        return self._send_data(data)

    def start_control(self) -> bool:
        """启动控制"""
        data = build_start_stop_frame(ControlCommand.START)
        return self._send_data(data)

    def stop_control(self) -> bool:
        """停止控制"""
        data = build_start_stop_frame(ControlCommand.STOP)
        return self._send_data(data)

    def reset_control(self) -> bool:
        """复位控制"""
        data = build_start_stop_frame(ControlCommand.RESET)
        return self._send_data(data)

    def set_target_value(self, target: float) -> bool:
        """设置目标值"""
        data = build_set_target_frame(target)
        return self._send_data(data)

    def read_status(self) -> bool:
        """读取状态"""
        data = build_read_status_frame()
        return self._send_data(data)

    def start_auto_tune(self) -> bool:
        """开始自动调参"""
        data = build_auto_tune_start_frame()
        return self._send_data(data)

    def stop_auto_tune(self) -> bool:
        """停止自动调参"""
        data = build_auto_tune_stop_frame()
        return self._send_data(data)

    # 内部方法

    def _set_state(self, state: ConnectionState):
        """设置连接状态"""
        if self._state != state:
            self._state = state
            if self._on_connection_changed:
                self._on_connection_changed(state)

    def _notify_error(self, message: str):
        """通知错误"""
        if self._on_error:
            self._on_error(message)
