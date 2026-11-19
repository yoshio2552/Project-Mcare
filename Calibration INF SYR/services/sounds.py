"""เสียงของโปรแกรม: คลิกปุ่ม · เริ่ม/หยุด · ผล PASS/FAIL/INVALID · หน้าต่างถาม · บันทึกแล้ว

ไฟล์เสียง ui/assets/sounds/*.wav สร้างด้วย tools/make_sounds.py (สังเคราะห์เอง) · เล่นด้วย QSoundEffect (หน่วงต่ำ)
ตั้งค่า (หน้าตั้งค่า → ทั่วไป): ui.sounds (เปิด/ปิดทั้งหมด) · ui.sound_clicks (เสียงคลิกปุ่ม) · ui.sound_volume (0–100)
· ui.sound_on_finish (เสียงตอนจบการทดสอบ — มีมาก่อน)

ใช้: sounds.play("pass") จากที่ไหนก็ได้ · install_click_sounds(app) ครั้งเดียวตอนเริ่มโปรแกรม
เพิ่มเสียงใหม่ (Lego): ใส่ใน SOUNDS ของ tools/make_sounds.py -> รัน -> เรียก play("ชื่อ")
ไม่มีอุปกรณ์เสียง / โหลดไม่ได้ / offscreen: เงียบเฉยๆ ไม่ error
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QUrl

SOUND_DIR = Path(__file__).resolve().parents[1] / "ui" / "assets" / "sounds"
NAMES = ("click", "toggle", "start", "stop", "pass", "fail", "invalid", "notify", "saved")
CLICK_GAP_S = 0.04          # คลิกถี่กว่านี้ไม่เล่นซ้ำ (กดค้าง/ดับเบิลคลิก ไม่รัว)


class SoundPlayer:
    def __init__(self):
        self._effects: dict = {}
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

    def _load(self) -> None:
        self._loaded = True
        try:
            from PySide6.QtMultimedia import QSoundEffect
        except Exception:
            return
        for name in NAMES:
            path = SOUND_DIR / f"{name}.wav"
            if path.is_file():
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                self._effects[name] = effect

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        if not self._loaded:
            self._load()
        effect = self._effects.get(name)
        if effect is None:
            return
        volume = max(0, min(100, int(self._ui("sound_volume", 60)))) / 100.0
        effect.setVolume(volume * (0.6 if name == "click" else 1.0))
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
    """ดักการคลิกทั้งโปรแกรม: ปุ่ม/ช่องติ๊ก/แท็บ -> เสียงคลิก · หน้าต่างถาม (QMessageBox) เปิด -> เสียงแจ้ง"""

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.MouseButtonRelease:
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
    """เรียกครั้งเดียวหลังสร้าง QApplication"""
    global _filter
    player.configure(settings)
    if _filter is None:
        _filter = _ClickFilter(app)
        app.installEventFilter(_filter)
