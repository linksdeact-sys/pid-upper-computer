#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通信协议模块
定义PID上位机与下位机的通信协议
"""

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple

# 协议常量
FRAME_HEADER = 0xAA55      # 帧头
FRAME_TAIL = 0x0D0A        # 帧尾
FRAME_HEADER_BYTES = b'\x55\xAA'  # 帧头字节（小端）
FRAME_TAIL_BYTES = b'\x0A\x0D'    # 帧尾字节（小端）


class CommandCode(IntEnum):
    """命令码定义"""
    READ_PID_PARAMS = 0x01      # 读取PID参数
    WRITE_PID_PARAMS = 0x02     # 写入PID参数
    READ_REALTIME_DATA = 0x03   # 读取实时数据
    REALTIME_DATA_RESP = 0x04   # 实时数据响应
    START_STOP_CONTROL = 0x05   # 启动/停止控制
    SET_TARGET_VALUE = 0x06     # 设置目标值
    READ_STATUS = 0x07          # 读取状态
    STATUS_RESPONSE = 0x08      # 状态响应
    AUTO_TUNE_START = 0x09      # 开始自动调参
    AUTO_TUNE_STOP = 0x0A       # 停止自动调参
    AUTO_TUNE_RESULT = 0x0B     # 自动调参结果


class ControlCommand(IntEnum):
    """控制命令"""
    STOP = 0x00     # 停止
    START = 0x01    # 启动
    RESET = 0x02    # 复位


class StatusFlag(IntEnum):
    """状态标志位"""
    RUNNING = 0x01          # 运行中
    AUTO_TUNING = 0x02      # 自动调参中
    ERROR = 0x04            # 错误
    PARAMS_LOADED = 0x08    # 参数已加载


@dataclass
class PIDParams:
    """PID参数数据类"""
    p: float = 0.0
    i: float = 0.0
    d: float = 0.0

    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('<fff', self.p, self.i, self.d)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PIDParams':
        """从字节解析"""
        if len(data) < 12:
            raise ValueError("数据长度不足")
        p, i, d = struct.unpack('<fff', data[:12])
        return cls(p=p, i=i, d=d)


@dataclass
class RealtimeData:
    """实时数据类"""
    setpoint: float = 0.0      # 设定值
    actual: float = 0.0        # 实际值
    output: float = 0.0        # 输出值

    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('<fff', self.setpoint, self.actual, self.output)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RealtimeData':
        """从字节解析"""
        if len(data) < 12:
            raise ValueError("数据长度不足")
        setpoint, actual, output = struct.unpack('<fff', data[:12])
        return cls(setpoint=setpoint, actual=actual, output=output)


@dataclass
class StatusData:
    """状态数据类"""
    status_flags: int = 0       # 状态标志
    error_code: int = 0         # 错误码

    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('<BB', self.status_flags, self.error_code)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'StatusData':
        """从字节解析"""
        if len(data) < 2:
            raise ValueError("数据长度不足")
        status_flags, error_code = struct.unpack('<BB', data[:2])
        return cls(status_flags=status_flags, error_code=error_code)


@dataclass
class ProtocolFrame:
    """协议帧数据类"""
    command: int                # 命令码
    data: bytes = b''           # 数据

    def calculate_checksum(self) -> int:
        """计算校验和"""
        checksum = self.command
        length = len(self.data)
        checksum += (length >> 8) & 0xFF
        checksum += length & 0xFF
        for byte in self.data:
            checksum += byte
        return checksum & 0xFF

    def to_bytes(self) -> bytes:
        """转换为字节帧"""
        length = len(self.data)
        checksum = self.calculate_checksum()

        frame = bytearray()
        frame.extend(FRAME_HEADER_BYTES)                    # 帧头
        frame.append(self.command)                           # 命令
        frame.extend(struct.pack('>H', length))             # 长度（大端）
        frame.extend(self.data)                              # 数据
        frame.append(checksum)                               # 校验
        frame.extend(FRAME_TAIL_BYTES)                      # 帧尾

        return bytes(frame)

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['ProtocolFrame']:
        """从字节解析帧"""
        if len(data) < 8:
            return None

        # 检查帧头
        if data[0:2] != FRAME_HEADER_BYTES:
            return None

        # 检查帧尾
        if data[-2:] != FRAME_TAIL_BYTES:
            return None

        # 解析命令
        command = data[2]

        # 解析长度
        length = struct.unpack('>H', data[3:5])[0]

        # 检查数据长度
        if len(data) < 7 + length:
            return None

        # 提取数据
        frame_data = data[5:5+length]

        # 提取校验和
        checksum = data[5+length]

        # 验证校验和
        frame = cls(command=command, data=frame_data)
        if frame.calculate_checksum() != checksum:
            return None

        return frame


class ProtocolParser:
    """协议解析器"""

    def __init__(self):
        self.buffer = bytearray()
        self.frames = []

    def feed(self, data: bytes):
        """喂入数据"""
        self.buffer.extend(data)
        self._parse_buffer()

    def _parse_buffer(self):
        """解析缓冲区"""
        while len(self.buffer) >= 8:
            # 查找帧头
            header_pos = self.buffer.find(FRAME_HEADER_BYTES)
            if header_pos == -1:
                # 没有找到帧头，保留最后1个字节
                self.buffer = self.buffer[-1:]
                break

            # 移除帧头之前的数据
            if header_pos > 0:
                self.buffer = self.buffer[header_pos:]

            # 检查是否有足够的数据
            if len(self.buffer) < 5:
                break

            # 解析长度
            length = struct.unpack('>H', self.buffer[3:5])[0]

            # 检查完整帧长度
            frame_length = 7 + length
            if len(self.buffer) < frame_length:
                break

            # 提取完整帧
            frame_bytes = bytes(self.buffer[:frame_length])

            # 解析帧
            frame = ProtocolFrame.from_bytes(frame_bytes)
            if frame is not None:
                self.frames.append(frame)

            # 移除已解析的帧
            self.buffer = self.buffer[frame_length:]

    def get_frame(self) -> Optional[ProtocolFrame]:
        """获取解析到的帧"""
        if self.frames:
            return self.frames.pop(0)
        return None

    def get_all_frames(self) -> list:
        """获取所有解析到的帧"""
        frames = self.frames.copy()
        self.frames.clear()
        return frames

    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()
        self.frames.clear()


# 工具函数

def build_read_pid_params_frame() -> bytes:
    """构建读取PID参数帧"""
    frame = ProtocolFrame(command=CommandCode.READ_PID_PARAMS)
    return frame.to_bytes()


def build_write_pid_params_frame(params: PIDParams) -> bytes:
    """构建写入PID参数帧"""
    frame = ProtocolFrame(command=CommandCode.WRITE_PID_PARAMS, data=params.to_bytes())
    return frame.to_bytes()


def build_read_realtime_data_frame() -> bytes:
    """构建读取实时数据帧"""
    frame = ProtocolFrame(command=CommandCode.READ_REALTIME_DATA)
    return frame.to_bytes()


def build_start_stop_frame(command: ControlCommand) -> bytes:
    """构建启动/停止控制帧"""
    data = struct.pack('<B', command)
    frame = ProtocolFrame(command=CommandCode.START_STOP_CONTROL, data=data)
    return frame.to_bytes()


def build_set_target_frame(target: float) -> bytes:
    """构建设置目标值帧"""
    data = struct.pack('<f', target)
    frame = ProtocolFrame(command=CommandCode.SET_TARGET_VALUE, data=data)
    return frame.to_bytes()


def build_read_status_frame() -> bytes:
    """构建读取状态帧"""
    frame = ProtocolFrame(command=CommandCode.READ_STATUS)
    return frame.to_bytes()


def build_auto_tune_start_frame() -> bytes:
    """构建开始自动调参帧"""
    frame = ProtocolFrame(command=CommandCode.AUTO_TUNE_START)
    return frame.to_bytes()


def build_auto_tune_stop_frame() -> bytes:
    """构建停止自动调参帧"""
    frame = ProtocolFrame(command=CommandCode.AUTO_TUNE_STOP)
    return frame.to_bytes()


def parse_pid_params_response(frame: ProtocolFrame) -> Optional[PIDParams]:
    """解析PID参数响应"""
    if frame.command != CommandCode.READ_PID_PARAMS:
        return None
    try:
        return PIDParams.from_bytes(frame.data)
    except (ValueError, struct.error):
        return None


def parse_realtime_data_response(frame: ProtocolFrame) -> Optional[RealtimeData]:
    """解析实时数据响应"""
    if frame.command != CommandCode.REALTIME_DATA_RESP:
        return None
    try:
        return RealtimeData.from_bytes(frame.data)
    except (ValueError, struct.error):
        return None


def parse_status_response(frame: ProtocolFrame) -> Optional[StatusData]:
    """解析状态响应"""
    if frame.command != CommandCode.STATUS_RESPONSE:
        return None
    try:
        return StatusData.from_bytes(frame.data)
    except (ValueError, struct.error):
        return None


def parse_auto_tune_result(frame: ProtocolFrame) -> Optional[PIDParams]:
    """解析自动调参结果"""
    if frame.command != CommandCode.AUTO_TUNE_RESULT:
        return None
    try:
        return PIDParams.from_bytes(frame.data)
    except (ValueError, struct.error):
        return None
