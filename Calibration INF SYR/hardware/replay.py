"""เล่นซ้ำไฟล์ข้อมูลดิบ (raw.csv: t_s, weight_g) เหมือนเป็นตราชั่งจริง

ใช้ปรับ/ทดสอบอัลกอริทึมกับข้อมูลจากเครื่องจริงโดยไม่ต้องเดินปั๊มใหม่
(เลือกไฟล์และความเร็วที่ ตั้งค่า → แหล่งข้อมูล = Replay)
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

from config.settings import ReplaySettings
from core.models import Sample
from hardware.base import SOURCES, BalanceSource


def load_samples(path: str | Path) -> list[tuple[float, float]]:
    """อ่านไฟล์ 2 คอลัมน์ (เวลา, น้ำหนัก) — ข้ามบรรทัดหัวตารางและบรรทัดที่อ่านไม่ออก"""
    samples = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                samples.append((float(row[0]), float(row[1])))
            except (ValueError, IndexError):
                continue
    return samples


class ReplayBalance(BalanceSource):
    def __init__(self, settings: ReplaySettings):
        self._settings = settings
        self._samples: list[tuple[float, float]] = []
        self._index = 0
        self._wall_start = 0.0
        self.description = f"Replay x{settings.speed:g} · {Path(settings.path).name or '—'}"

    def open(self) -> None:
        if not self._settings.path:
            raise IOError("No replay file selected (Settings → Replay file)")
        self._samples = load_samples(self._settings.path)
        if not self._samples:
            raise IOError("The replay file has no readable data")
        self._index = 0
        self._wall_start = time.perf_counter()

    def read(self) -> Sample | None:
        if self._index >= len(self._samples):
            time.sleep(0.1)                 # ข้อมูลหมดแล้ว: เงียบเหมือนตราชั่งหยุดส่ง
            return None
        t, weight = self._samples[self._index]
        due = self._wall_start + (t - self._samples[0][0]) / max(self._settings.speed, 0.01)
        delay = due - time.perf_counter()
        if delay > 0:
            time.sleep(min(delay, 0.2))
            if due - time.perf_counter() > 0:
                return None
        self._index += 1
        return Sample(t, weight)

    def close(self) -> None:
        pass


@SOURCES.register("replay", label="Replay recorded file")
def _create(settings, config) -> ReplayBalance:
    return ReplayBalance(settings.replay)
