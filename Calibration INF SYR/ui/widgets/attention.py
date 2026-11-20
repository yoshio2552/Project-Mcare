"""เตือนให้กลับมาที่จอ (ผู้ใช้ 2026-11-20): หน้าต่างที่รอคนตัดสิน (เช่น "เก็บผลนี้ไหม?" หลังทดสอบจบ) ไม่มีใครกด
-> เสียงเตือนนุ่มเป็นจังหวะ + กะพริบไอคอนบนแถบงาน (taskbar) — ใช้เป็นจุดตรวจด้วยว่าคนอยู่หน้าจอหรือไม่

    จังหวะ ui.attention_every_s (ค่าเริ่มต้น 30 s, 0 = ปิด) · ไม่มีคนกดเกิน ESCALATE_AFTER ครั้ง = เปลี่ยนเป็นเสียง warn (ชัดขึ้น)
    เขียน log ว่ารอมานานเท่าไร (ย้อนดูได้ว่าตอนนั้นมีคนอยู่หน้าจอไหม)
หยุดเองเมื่อหน้าต่างปิด (finished)
"""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QDialog

from config.i18n import tr
from services import sounds

log = logging.getLogger("deltam.attention")

ESCALATE_AFTER = 4


class AttentionReminder(QObject):
    def __init__(self, dialog: QDialog, every_s: float, what: str):
        super().__init__(dialog)
        self._dialog = dialog
        self._what = what
        self._count = 0
        self._started = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if every_s and every_s > 0:
            self._timer.start(int(max(5.0, float(every_s)) * 1000))
        dialog.finished.connect(self._stop)

    def _tick(self) -> None:
        self._count += 1
        waited = time.monotonic() - self._started
        sounds.play("warn" if self._count >= ESCALATE_AFTER else "remind")
        QApplication.alert(self._dialog.window(), 0)        # กะพริบบนแถบงานจนกว่าจะมีคนมาที่หน้าต่าง
        if self._count in (1, ESCALATE_AFTER) or self._count % 10 == 0:
            log.info(tr("Waiting for someone at the screen: {what} — no answer for {min:.1f} min",
                        what=self._what, min=waited / 60.0))

    def _stop(self, *_):
        if self._timer.isActive() and self._count:
            log.info(tr("Answered after {min:.1f} min ({n} reminders)",
                        min=(time.monotonic() - self._started) / 60.0, n=self._count))
        self._timer.stop()

    @property
    def count(self) -> int:
        return self._count
