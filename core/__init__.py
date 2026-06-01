# 核心功能模块

from core.serial_manager import SerialManager, SerialConfig, ConnectionState
from core.data_recorder import DataRecorder, DataPoint, DataStatistics
from core.auto_tuner import PIDAutoTuner, TuningMethod, TuningResult
from core.pid_controller import PIDController, PIDParams
from core.protocol import (
    ProtocolParser, ProtocolFrame, CommandCode,
    PIDParams as ProtocolPIDParams, RealtimeData, StatusData
)
