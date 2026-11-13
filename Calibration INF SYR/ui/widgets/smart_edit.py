"""SmartLineEdit: ช่องกรอกที่ "เสนอ" ค่าเป็นตัวอักษรจาง (ghost) + รายการให้เลือก — ไม่กรอกให้เอง

    ┌──────────────────────────────────────────┐
    │ TER│UMO                          Tab ↹   │   ← พิมพ์ "TER" เห็น "UMO" จางๆ
    └──────────────────────────────────────────┘
    Tab     รับคำแนะนำ แล้วไปช่องถัดไป (ไม่มีคำแนะนำ = Tab ปกติ)
    Enter   รับคำแนะนำ อยู่ช่องเดิม
    ↓       เปิดรายการคำแนะนำทั้งหมด (เลือกด้วยลูกศร แล้ว Enter/Tab)
    Esc     ไม่เอาคำแนะนำนี้ (จนกว่าจะพิมพ์ใหม่)
รับแล้วได้การสะกดตามที่เคยบันทึก (ตัวพิมพ์ใหญ่เล็ก ช่องว่าง) — ลดการพิมพ์ผิดจนข้อมูลแตกเป็นหลายชื่อ
คำแนะนำแสดงเฉพาะช่องที่กำลังพิมพ์ (ช่องอื่นไม่รก) และคำนวณใหม่ทุกครั้งที่เข้าช่อง (ใช้ข้อมูลช่องอื่นล่าสุด)
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QStringListModel, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QCompleter, QLineEdit

from config.i18n import tr
from ui.theme import Color


class SmartLineEdit(QLineEdit):
    accepted = Signal(str)          # ผู้ใช้รับคำแนะนำ
    confirmed = Signal()            # ผู้ใช้กด Tab หรือ Enter ในช่องนี้ (หลังจัดการคำแนะนำแล้ว) — ใช้ยืนยันค่าที่เติมให้ช่องอื่น

    def __init__(self, provider: Callable[[str], list[str]] | None = None):
        super().__init__()
        self._provider = provider
        self._suggestions: list[str] = []
        self._ghost = ""                # คำแนะนำเต็มที่กำลังแสดง ("" = ไม่มี)
        self._dismissed = False
        self._placeholder = ""
        self._preview = ""              # ค่าที่ระบบเสนอให้ช่องนี้ (แสดงจางตอนช่องว่าง) — ช่องอื่นเป็นผู้ตั้ง
        self._model = QStringListModel(self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setMaxVisibleItems(8)
        self._completer.setWidget(self)
        self._completer.activated[str].connect(self._take)
        self.textEdited.connect(self._on_edited)
        self.cursorPositionChanged.connect(lambda *_: self.update())

    # ------------------------------------------------------------ สาธารณะ
    def setPlaceholderText(self, text: str) -> None:        # จำไว้ เพื่อซ่อนชั่วคราวตอนมี ghost
        self._placeholder = text
        super().setPlaceholderText(self._preview or text)

    @property
    def preview(self) -> str:
        return self._preview

    def set_preview(self, value: str) -> None:
        """แสดงค่าที่เสนอเป็นตัวจางในช่องว่าง (ยังไม่กรอกจนกว่าจะยืนยัน) · "" = เอาออก
        ค่านี้ขึ้นเป็นคำแนะนำแรกด้วย — เข้าช่องแล้วกด Tab/Enter ก็รับได้"""
        self._preview = value or ""
        super().setPlaceholderText(self._preview or self._placeholder)
        self.update()

    def take_preview(self) -> bool:
        """รับค่าที่เสนอ (ถ้ามี) คืน True เมื่อกรอกให้"""
        if not self._preview:
            return False
        self._take(self._preview)
        return True

    @property
    def ghost(self) -> str:
        """ส่วนที่ยังไม่ได้พิมพ์ของคำแนะนำ (แสดงจาง)"""
        if not self._ghost or self._dismissed or not self.hasFocus():
            return ""
        typed = self.text()
        if not self._ghost.lower().startswith(typed.lower()) or len(self._ghost) == len(typed):
            return ""
        return self._ghost[len(typed):]

    def suggestions(self) -> list[str]:
        return list(self._suggestions)

    def refresh(self) -> None:
        """คำนวณคำแนะนำใหม่จากข้อความตอนนี้ (และบริบทของช่องอื่น)"""
        self._suggestions = self._provider(self.text()) if self._provider else []
        typed = self.text().lower()
        if self._preview and self._preview.lower().startswith(typed) and self._preview.lower() != typed:
            self._suggestions = [self._preview] + [s for s in self._suggestions if s.lower() != self._preview.lower()]
        self._ghost = next((s for s in self._suggestions if s.lower().startswith(typed)), "")
        self._model.setStringList(self._suggestions)
        super().setPlaceholderText("" if (self.ghost and not self.text()) else (self._preview or self._placeholder))
        self.update()

    def accept_ghost(self) -> bool:
        if not self.ghost:
            return False
        self._take(self._ghost)
        return True

    # ------------------------------------------------------------ ภายใน
    def _take(self, value: str) -> None:
        self.setText(value)
        self._completer.popup().hide()
        self._ghost = ""
        self._preview = ""
        super().setPlaceholderText(self._placeholder)
        self.update()
        self.accepted.emit(value)

    def _on_edited(self, _text: str) -> None:
        self._dismissed = False
        self.refresh()
        popup = self._completer.popup()
        if self._suggestions and self.text():
            self._completer.complete()
            popup.setCurrentIndex(self._model.index(-1, 0))      # ไม่เลือกรายการให้เอง
        else:
            popup.hide()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._dismissed = False
        self.refresh()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        super().setPlaceholderText(self._preview or self._placeholder)
        self.update()

    def event(self, event) -> bool:
        # Tab ถูกใช้เปลี่ยนช่องก่อนถึง keyPressEvent จึงดักที่นี่: มีคำแนะนำ = รับ แล้วปล่อยให้ไปช่องถัดไปตามปกติ
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab \
                and not self._completer.popup().isVisible():
            self.accept_ghost()
            self.confirmed.emit()
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        popup_open = self._completer.popup().isVisible()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not popup_open:
            accepted = self.accept_ghost()
            self.confirmed.emit()
            if accepted:
                return
        if key == Qt.Key.Key_Escape and not popup_open and self.ghost:
            self._dismissed = True
            super().setPlaceholderText(self._placeholder)
            self.update()
            return
        if key == Qt.Key.Key_Down and not popup_open and self._suggestions:
            self._completer.complete()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        ghost = self.ghost
        if not ghost:
            return
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        rect = self.cursorRect()
        x = rect.center().x() + 1
        baseline = rect.center().y() + (metrics.ascent() - metrics.descent()) // 2
        painter.setPen(QColor(Color.TEXT_FAINT))
        available = self.width() - x - 56
        painter.drawText(x, baseline, metrics.elidedText(ghost, Qt.TextElideMode.ElideRight, max(0, available)))
        hint = "Tab"
        small = self.font()
        small.setPointSizeF(max(6.0, small.pointSizeF() * 0.8))
        painter.setFont(small)
        painter.setPen(QColor(Color.ACCENT))
        hint_width = QFontMetrics(small).horizontalAdvance(hint)
        painter.drawText(self.width() - hint_width - 10, baseline, hint)
        painter.end()
