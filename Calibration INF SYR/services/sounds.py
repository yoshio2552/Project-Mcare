"""เสียงของโปรแกรม: คลิกปุ่ม · เริ่ม/หยุด · ผล PASS/FAIL/INVALID · หน้าต่างถาม · บันทึกแล้ว · สัญญาณเตือนบีกเกอร์

ไฟล์เสียง ui/assets/sounds/*.wav สร้างด้วย tools/make_sounds.py (สังเคราะห์เอง)
ตั้งค่า (หน้าตั้งค่า → ทั่วไป): ui.sounds (เปิด/ปิดทั้งหมด) · ui.sound_clicks (เสียงคลิกปุ่ม) · ui.sound_volume (0–100)
· ui.sound_on_finish (เสียงตอนจบการทดสอบ — มีมาก่อน) · ui.sound_low_latency (ช่องเสียงหน่วงต่ำสำหรับคลิก)

ใช้: sounds.play("pass") จากที่ไหนก็ได้ · install_click_sounds(app) ครั้งเดียวตอนเริ่มโปรแกรม
เพิ่มเสียงใหม่ (Lego): ใส่ใน SOUNDS ของ tools/make_sounds.py -> รัน -> เพิ่มชื่อใน NAMES -> เรียก play("ชื่อ")
ไม่มีอุปกรณ์เสียง / โหลดไม่ได้ / offscreen: เงียบเฉยๆ ไม่ error

เสียงคลิกหน่วง (ผู้ใช้ 2026-11-20 "แอบดีเลย์แปลกๆ") — สาเหตุ 3 ข้อ แก้ทั้งหมด:
    1) เดิมเล่นตอน "ปล่อย" เมาส์ (MouseButtonRelease) — คนกดแล้วปล่อยห่างกัน 80–150 ms จึงได้ยินช้ากว่านิ้ว
       -> เล่นตอน "กด" (MouseButtonPress) เหมือนปุ่มจริง
    2) โหลดไฟล์ครั้งแรกตอนคลิกแรก (QSoundEffect โหลดแบบ async — คลิกแรกเงียบ/ช้า) -> โหลดล่วงหน้าตอนเปิดโปรแกรม
    3) QSoundEffect เปิดอุปกรณ์เสียงใหม่ทุกครั้งที่เล่นหลังเงียบไปนาน (Windows ~50–150 ms)
       -> คลิก/ติ๊ก ใช้ช่องเสียง QAudioSink ที่เปิดค้างไว้ (บัฟเฟอร์ ~40 ms) เขียนข้อมูลเสียงลงไปตรงๆ
          ใช้ไม่ได้ (ไม่มีอุปกรณ์/รูปแบบไม่รองรับ) -> กลับไปใช้ QSoundEffect อัตโนมัติ
"""
from __future__ import annotations

import logging
import os
import time
import wave
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QUrl

log = logging.getLogger("deltam.sounds")

SOUND_DIR = Path(__file__).resolve().parents[1] / "ui" / "assets" / "sounds"
NAMES = ("click", "toggle", "start", "stop", "pass", "fail", "invalid", "notify", "saved", "remind", "warn", "alarm")
FAST_NAMES = ("click", "toggle")    # เสียงสั้นที่ต้องตอบสนองทันที -> ช่องเสียงหน่วงต่ำ
ALARMS = ("remind", "warn", "alarm")  # สัญญาณเตือนความปลอดภัย: ไม่ถูกปิดด้วย "เสียงคลิก" และดังอย่างน้อย ALARM_MIN_VOLUME
ALARM_MIN_VOLUME = 0.7
CLICK_GAP_S = 0.04          # คลิกถี่กว่านี้ไม่เล่นซ้ำ (กดค้าง/ดับเบิลคลิก ไม่รัว)
FAST_BUFFER_S = 0.04        # ขนาดบัฟเฟอร์ของช่องเสียงหน่วงต่ำ


def _read_pcm(path: Path) -> tuple[bytes, int, int] | None:
    """อ่าน wav 16-bit -> (ข้อมูล, rate, channels)"""
    try:
        with wave.open(str(path), "rb") as f:
            if f.getsampwidth() != 2:
                return None
            return f.readframes(f.getnframes()), f.getframerate(), f.getnchannels()
    except Exception:
        return None


def _scaled(data: bytes, volume: float) -> bytes:
    """ปรับความดังของข้อมูล int16 (numpy — มีในโปรแกรมอยู่แล้ว)"""
    import numpy as np
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) * volume
    return np.clip(samples, -32768, 32767).astype("<i2").tobytes()


class _FastOutput:
    """ช่องเสียงที่เปิดค้างไว้ (QAudioSink แบบ push) — เขียนเสียงสั้นลงไปแล้วดังทันที ไม่ต้องเปิดอุปกรณ์ใหม่"""

    def __init__(self, rate: int, channels: int):
        from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
        fmt = QAudioFormat()
        fmt.setSampleRate(rate)
        fmt.setChannelCount(channels)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull() or not device.isFormatSupported(fmt):
            raise RuntimeError("default audio output does not support the click format")
        self._sink = QAudioSink(device, fmt)
        self._sink.setBufferSize(max(2048, int(rate * channels * 2 * FAST_BUFFER_S)))
        self._io = self._sink.start()
        if self._io is None:
            raise RuntimeError("audio output did not start")
        self._cache: dict[tuple[str, int], bytes] = {}

    def play(self, name: str, data: bytes, volume: float) -> bool:
        from PySide6.QtMultimedia import QtAudio
        if self._sink.state() == QtAudio.State.StoppedState or self._io is None:
            self._io = self._sink.start()
            if self._io is None:
                return False
        key = (name, int(volume * 100))
        if key not in self._cache:
            self._cache[key] = _scaled(data, volume)
        chunk = self._cache[key]
        written = self._io.write(chunk)
        return written > 0

    def close(self) -> None:
        try:
            self._sink.stop()
        except Exception:
            pass


class SoundPlayer:
    def __init__(self):
        self._effects: dict = {}
        self._pcm: dict[str, tuple[bytes, int, int]] = {}
        self._fast: _FastOutput | None = None
        self._fast_failed = False
        self._settings = None
        self._loaded = False
        self._last_click = 0.0

    def configure(self, settings) -> None:
        """ผูกกับ AppSettings (อ่านค่าเปิด/ปิด/ความดังทุกครั้งที่เล่น — เปลี่ยนในหน้าตั้งค่าแล้วมีผลทันที)"""
        self._settings = settings

    def _ui(self, name: str, default):
        ui = getattr(self._settings, "ui", None)
        return getattr(ui, name, default) if ui is not None else default

    @property
    def enabled(self) -> bool:
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":     # เทสต์/ตรวจแบบไม่มีจอ: ไม่ส่งเสียง
            return False
        return bool(self._ui("sounds", True))

    def preload(self) -> None:
        """โหลดทุกเสียงล่วงหน้า (ตอนเปิดโปรแกรม) — คลิกแรกต้องไม่เงียบ/ช้า"""
        if not self._loaded and self.enabled:
            self._load()
            fast = self._fast_output()
            if fast is not None:            # เตรียมข้อมูลเสียงที่ความดังปัจจุบันไว้ก่อน (คลิกแรกไม่ต้องคำนวณ)
                for name, (data, _, _) in self._pcm.items():
                    fast._cache[(name, int(self.volume_for(name) * 100))] = _scaled(data, self.volume_for(name))

    def _load(self) -> None:
        self._loaded = True
        try:
            from PySide6.QtMultimedia import QSoundEffect
        except Exception:
            return
        for name in NAMES:
            path = SOUND_DIR / f"{name}.wav"
            if not path.is_file():
                continue
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(path)))
            self._effects[name] = effect
            if name in FAST_NAMES:
                pcm = _read_pcm(path)
                if pcm is not None:
                    self._pcm[name] = pcm

    def _fast_output(self) -> _FastOutput | None:
        if self._fast is not None or self._fast_failed or not self._ui("sound_low_latency", True):
            return self._fast if self._ui("sound_low_latency", True) else None
        sample = next(iter(self._pcm.values()), None)
        if sample is None:
            self._fast_failed = True
            return None
        try:
            self._fast = _FastOutput(sample[1], sample[2])
        except Exception as exc:        # ไม่มีอุปกรณ์/ไม่รองรับ -> ใช้ QSoundEffect แทน
            self._fast_failed = True
            log.info("low-latency click output unavailable (%s) — using QSoundEffect", exc)
        return self._fast

    def volume_for(self, name: str) -> float:
        volume = max(0, min(100, int(self._ui("sound_volume", 60)))) / 100.0
        if name in ALARMS:
            return max(volume, ALARM_MIN_VOLUME)
        return volume * (0.6 if name == "click" else 1.0)

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        if not self._loaded:
            self._load()
        volume = self.volume_for(name)
        if name in self._pcm:
            fast = self._fast_output()
            if fast is not None:
                try:
                    if fast.play(name, self._pcm[name][0], volume):
                        return
                except Exception as exc:
                    log.info("low-latency click failed (%s) — using QSoundEffect", exc)
                    self._fast_failed, self._fast = True, None
        effect = self._effects.get(name)
        if effect is None:
            return
        if abs(effect.volume() - volume) > 1e-3:
            effect.setVolume(volume)
        effect.play()

    def click(self, name: str = "click") -> None:
        if not self._ui("sound_clicks", True):
            return
        now = time.monotonic()
        if now - self._last_click < CLICK_GAP_S:
            return
        self._last_click = now
        self.play(name)


player = SoundPlayer()


def play(name: str) -> None:
    player.play(name)


class _ClickFilter(QObject):
    """ดักการคลิกทั้งโปรแกรม: ปุ่ม/ช่องติ๊ก/แท็บ -> เสียงคลิก (ตอนกด) · หน้าต่างถาม (QMessageBox) เปิด -> เสียงแจ้ง"""

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.MouseButtonPress:
            from PySide6.QtWidgets import QAbstractButton, QCheckBox, QRadioButton, QTabBar
            if isinstance(obj, (QAbstractButton, QTabBar)) and obj.isEnabled() and obj.rect().contains(event.position().toPoint()):
                player.click("toggle" if isinstance(obj, (QCheckBox, QRadioButton)) else "click")
        elif kind == QEvent.Type.Show:
            from PySide6.QtWidgets import QMessageBox
            if isinstance(obj, QMessageBox):
                player.play("notify")
        return False


_filter: _ClickFilter | None = None


def install_click_sounds(app, settings) -> None:
    """เรียกครั้งเดียวหลังสร้าง QApplication — โหลดเสียงล่วงหน้าด้วย"""
    global _filter
    player.configure(settings)
    if _filter is None:
        _filter = _ClickFilter(app)
        app.installEventFilter(_filter)
    player.preload()
