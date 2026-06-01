#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据回放模块
用于回放历史数据
"""

import time
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from core.data_recorder import DataPoint


class PlaybackState(Enum):
    """回放状态"""
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class DataPlayer:
    """数据回放器"""

    def __init__(self):
        self._state = PlaybackState.STOPPED
        self._data: List[DataPoint] = []
        self._current_index: int = 0
        self._speed: float = 1.0  # 回放速度倍数
        self._thread: Optional[threading.Thread] = None

        # 回调
        self._on_data: Optional[Callable] = None
        self._on_state_changed: Optional[Callable] = None
        self._on_finished: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None

    @property
    def state(self) -> PlaybackState:
        """获取回放状态"""
        return self._state

    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._state == PlaybackState.PLAYING

    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._state == PlaybackState.PAUSED

    @property
    def progress(self) -> float:
        """获取播放进度（0-100）"""
        if not self._data:
            return 0.0
        return (self._current_index / len(self._data)) * 100

    @property
    def current_time(self) -> str:
        """获取当前时间"""
        if not self._data or self._current_index >= len(self._data):
            return "00:00:00"
        return self._data[self._current_index].time_str

    @property
    def total_time(self) -> str:
        """获取总时间"""
        if not self._data:
            return "00:00:00"
        return self._data[-1].time_str

    def set_on_data(self, callback: Callable):
        """设置数据回调"""
        self._on_data = callback

    def set_on_state_changed(self, callback: Callable):
        """设置状态变化回调"""
        self._on_state_changed = callback

    def set_on_finished(self, callback: Callable):
        """设置完成回调"""
        self._on_finished = callback

    def set_on_progress(self, callback: Callable):
        """设置进度回调"""
        self._on_progress = callback

    def load_data(self, data: List[DataPoint]):
        """加载数据"""
        self.stop()
        self._data = data.copy()
        self._current_index = 0

    def set_speed(self, speed: float):
        """设置回放速度"""
        self._speed = max(0.1, min(10.0, speed))

    def play(self):
        """开始播放"""
        if not self._data:
            return

        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            self._notify_state_changed()
            return

        if self._state == PlaybackState.STOPPED:
            self._current_index = 0
            self._state = PlaybackState.PLAYING
            self._notify_state_changed()

            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()

    def pause(self):
        """暂停播放"""
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
            self._notify_state_changed()

    def stop(self):
        """停止播放"""
        self._state = PlaybackState.STOPPED
        self._current_index = 0
        self._notify_state_changed()

    def seek(self, progress: float):
        """跳转到指定位置"""
        if not self._data:
            return

        self._current_index = int(len(self._data) * progress / 100)
        self._current_index = max(0, min(len(self._data) - 1, self._current_index))

    def _playback_loop(self):
        """播放循环"""
        while self._state == PlaybackState.PLAYING and self._current_index < len(self._data):
            # 获取当前数据点
            point = self._data[self._current_index]

            # 通知数据回调
            if self._on_data:
                self._on_data(point)

            # 通知进度回调
            if self._on_progress:
                self._on_progress(self.progress)

            # 更新索引
            self._current_index += 1

            # 计算等待时间
            if self._current_index < len(self._data):
                next_point = self._data[self._current_index]
                dt = next_point.timestamp - point.timestamp
                wait_time = dt / self._speed
                time.sleep(max(0.001, wait_time))

        # 播放完成
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.STOPPED
            self._notify_state_changed()

            if self._on_finished:
                self._on_finished()

    def _notify_state_changed(self):
        """通知状态变化"""
        if self._on_state_changed:
            self._on_state_changed(self._state)
