"""ตั้งค่า logging กลาง: เขียนลงไฟล์ + ส่งต่อให้ UI ผ่าน Qt signal

ทุกโมดูลใช้ logging.getLogger("deltam.xxx") ตามปกติ ไม่ต้องรู้จัก UI
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal

from config.constants import LOG_DIR


class LogBridge(QObject):
    """สะพานจาก logging ไปยัง UI (ปลอดภัยข้าม thread เพราะเป็น signal)"""
    message = Signal(str, str, str)     # level, เวลา, ข้อความ


class _QtHandler(logging.Handler):
    def __init__(self, bridge: LogBridge):
        super().__init__()
        self._bridge = bridge
        self._time = logging.Formatter(datefmt="%H:%M:%S")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._bridge.message.emit(
                record.levelname, self._time.formatTime(record, "%H:%M:%S"), record.getMessage()
            )
        except RuntimeError:
            pass    # UI ถูกปิดไปแล้ว


def setup_logging() -> LogBridge:
    bridge = LogBridge()
    root = logging.getLogger("deltam")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(_QtHandler(bridge))
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root.addHandler(file_handler)
    except OSError:
        pass
    return bridge
