#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据记录模块
负责PID运行数据的记录、存储和导出
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from utils.logger import logger


@dataclass
class DataPoint:
    """数据点"""
    timestamp: float                    # 时间戳
    setpoint: float = 0.0              # 设定值
    actual: float = 0.0                # 实际值
    output: float = 0.0                # 输出值
    error: float = 0.0                 # 误差
    p_term: float = 0.0                # P项
    i_term: float = 0.0                # I项
    d_term: float = 0.0                # D项

    @property
    def datetime_str(self) -> str:
        """格式化时间字符串"""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @property
    def time_str(self) -> str:
        """简短时间字符串"""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S.%f")[:-3]

    @property
    def relative_time(self) -> float:
        """相对时间（从记录开始）"""
        return self.timestamp


@dataclass
class DataStatistics:
    """数据统计"""
    count: int = 0                      # 数据点数量
    duration: float = 0.0              # 持续时间
    setpoint_min: float = 0.0          # 设定值最小值
    setpoint_max: float = 0.0          # 设定值最大值
    setpoint_avg: float = 0.0          # 设定值平均值
    actual_min: float = 0.0            # 实际值最小值
    actual_max: float = 0.0            # 实际值最大值
    actual_avg: float = 0.0            # 实际值平均值
    error_min: float = 0.0             # 误差最小值
    error_max: float = 0.0             # 误差最大值
    error_avg: float = 0.0             # 误差平均值
    error_rms: float = 0.0             # 误差均方根
    overshoot: float = 0.0             # 超调量
    settling_time: float = 0.0         # 稳定时间
    rise_time: float = 0.0             # 上升时间


class DataRecorder:
    """数据记录器"""

    def __init__(self, max_points: int = 100000):
        self._max_points = max_points
        self._data: List[DataPoint] = []
        self._recording = False
        self._start_time: Optional[float] = None
        self._current_setpoint: float = 0.0

        # 回调
        self._on_data_added = None
        self._on_statistics_updated = None

    @property
    def is_recording(self) -> bool:
        """是否正在记录"""
        return self._recording

    @property
    def data_count(self) -> int:
        """数据点数量"""
        return len(self._data)

    @property
    def duration(self) -> float:
        """记录持续时间"""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def data(self) -> List[DataPoint]:
        """获取所有数据"""
        return self._data.copy()

    def set_on_data_added(self, callback):
        """设置数据添加回调"""
        self._on_data_added = callback

    def set_on_statistics_updated(self, callback):
        """设置统计更新回调"""
        self._on_statistics_updated = callback

    def start_recording(self):
        """开始记录"""
        self._recording = True
        self._start_time = time.time()
        self._data.clear()

    def stop_recording(self):
        """停止记录"""
        self._recording = False

    def clear(self):
        """清空数据"""
        self._data.clear()
        self._start_time = None

    def set_setpoint(self, setpoint: float):
        """设置当前设定值"""
        self._current_setpoint = setpoint

    def add_data(self, setpoint: float, actual: float, output: float,
                 p_term: float = 0.0, i_term: float = 0.0, d_term: float = 0.0):
        """添加数据点"""
        if not self._recording:
            return

        timestamp = time.time()
        error = setpoint - actual

        point = DataPoint(
            timestamp=timestamp,
            setpoint=setpoint,
            actual=actual,
            output=output,
            error=error,
            p_term=p_term,
            i_term=i_term,
            d_term=d_term
        )

        self._data.append(point)

        # 限制数据点数量
        if len(self._data) > self._max_points:
            self._data = self._data[-self._max_points:]

        # 通知回调
        if self._on_data_added:
            self._on_data_added(point)

    def get_recent_data(self, count: int = 100) -> List[DataPoint]:
        """获取最近的数据点"""
        return self._data[-count:]

    def get_data_in_range(self, start_time: float, end_time: float) -> List[DataPoint]:
        """获取指定时间范围内的数据"""
        return [p for p in self._data if start_time <= p.timestamp <= end_time]

    def get_statistics(self) -> DataStatistics:
        """获取数据统计"""
        stats = DataStatistics()

        if not self._data:
            return stats

        stats.count = len(self._data)

        # 计算时间范围
        if self._start_time:
            stats.duration = self._data[-1].timestamp - self._start_time

        # 提取数据列
        setpoints = [p.setpoint for p in self._data]
        actuals = [p.actual for p in self._data]
        errors = [p.error for p in self._data]

        # 设定值统计
        stats.setpoint_min = min(setpoints)
        stats.setpoint_max = max(setpoints)
        stats.setpoint_avg = sum(setpoints) / len(setpoints)

        # 实际值统计
        stats.actual_min = min(actuals)
        stats.actual_max = max(actuals)
        stats.actual_avg = sum(actuals) / len(actuals)

        # 误差统计
        stats.error_min = min(errors)
        stats.error_max = max(errors)
        stats.error_avg = sum(errors) / len(errors)
        stats.error_rms = (sum(e**2 for e in errors) / len(errors)) ** 0.5

        # 超调量计算
        if setpoints[-1] != 0:
            overshoot_candidates = [
                (abs(p.actual - p.setpoint) / abs(p.setpoint)) * 100
                for p in self._data
                if p.setpoint != 0
            ]
            if overshoot_candidates:
                stats.overshoot = max(overshoot_candidates)

        # 上升时间（10%到90%）
        stats.rise_time = self._calculate_rise_time()

        # 稳定时间（误差在±2%以内）
        stats.settling_time = self._calculate_settling_time()

        return stats

    def _calculate_rise_time(self) -> float:
        """计算上升时间"""
        if len(self._data) < 2:
            return 0.0

        setpoint = self._data[-1].setpoint
        if setpoint == 0:
            return 0.0

        # 找到10%和90%的点
        target_10 = setpoint * 0.1
        target_90 = setpoint * 0.9

        time_10 = None
        time_90 = None

        for point in self._data:
            if time_10 is None and point.actual >= target_10:
                time_10 = point.timestamp
            if time_90 is None and point.actual >= target_90:
                time_90 = point.timestamp
                break

        if time_10 and time_90:
            return time_90 - time_10
        return 0.0

    def _calculate_settling_time(self, tolerance: float = 0.02) -> float:
        """计算稳定时间"""
        if len(self._data) < 2:
            return 0.0

        setpoint = self._data[-1].setpoint
        if setpoint == 0:
            return 0.0

        threshold = abs(setpoint * tolerance)
        start_time = self._start_time or self._data[0].timestamp

        # 从后往前找最后一个超出范围的点
        settling_time = 0.0
        for point in reversed(self._data):
            if abs(point.error) > threshold:
                settling_time = point.timestamp - start_time
                break

        return settling_time

    def export_csv(self, filepath: str) -> bool:
        """导出为CSV文件"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 写入表头
                writer.writerow([
                    '时间戳', '时间', '设定值', '实际值', '输出值',
                    '误差', 'P项', 'I项', 'D项'
                ])

                # 写入数据
                for point in self._data:
                    writer.writerow([
                        point.timestamp,
                        point.datetime_str,
                        point.setpoint,
                        point.actual,
                        point.output,
                        point.error,
                        point.p_term,
                        point.i_term,
                        point.d_term
                    ])

            return True
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False

    def export_json(self, filepath: str) -> bool:
        """导出为JSON文件"""
        try:
            data = {
                'metadata': {
                    'start_time': self._start_time,
                    'count': len(self._data),
                    'duration': self.duration
                },
                'statistics': asdict(self.get_statistics()),
                'data': [asdict(p) for p in self._data]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            return False

    def import_csv(self, filepath: str) -> bool:
        """从CSV文件导入"""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self._data.clear()

                for row in reader:
                    point = DataPoint(
                        timestamp=float(row['时间戳']),
                        setpoint=float(row['设定值']),
                        actual=float(row['实际值']),
                        output=float(row['输出值']),
                        error=float(row['误差']),
                        p_term=float(row.get('P项', 0)),
                        i_term=float(row.get('I项', 0)),
                        d_term=float(row.get('D项', 0))
                    )
                    self._data.append(point)

                if self._data:
                    self._start_time = self._data[0].timestamp

            return True
        except Exception as e:
            logger.error(f"导入CSV失败: {e}")
            return False

    def import_json(self, filepath: str) -> bool:
        """从JSON文件导入"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._data.clear()
            for item in data.get('data', []):
                point = DataPoint(**item)
                self._data.append(point)

            metadata = data.get('metadata', {})
            self._start_time = metadata.get('start_time')

            return True
        except Exception as e:
            logger.error(f"导入JSON失败: {e}")
            return False

    def save_session(self, filepath: str) -> bool:
        """保存会话"""
        return self.export_json(filepath)

    def load_session(self, filepath: str) -> bool:
        """加载会话"""
        return self.import_json(filepath)
