"""ตัวเลือกชนิดเครื่อง Infusion / Syringe แบบการ์ดใหญ่ + สีประจำชนิด

ทำให้ "เลือกผิด" สังเกตได้ทันที: การ์ดที่เลือกเปลี่ยนพื้นและขอบเป็นสีของชนิดนั้น มีไอคอน + ชื่อ + เครื่องหมายถูก
(ไม่พึ่งสีอย่างเดียว — คนตาบอดสีก็แยกได้จากไอคอนและข้อความ) และใช้สีเดียวกันกับป้าย (PumpBadge) ทุกหน้า

    selector = PumpTypeSelector()
    selector.changed.connect(...)               # ส่งค่า "infusion" | "syringe"
    selector.currentData() / findData(v) / setCurrentIndex(i)   (หน้าตาเหมือน QComboBox — ใช้แทนกันได้)
คีย์บอร์ด: Tab มาที่การ์ด แล้วกด ← → หรือ Space
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config.i18n import tr
from ui.theme import PUMP_COLORS, Color, set_property
from ui.widgets.common import label

# key -> (ชื่อ, คำอธิบาย)
PUMP_TYPES = {
    "infusion": ("Infusion pump", "Volumetric pump with an IV set · peak detection by default"),
    "syringe": ("Syringe pump", "Syringe driver · time-based intervals by default"),
}


def pump_name(key: str) -> str:
    return tr(PUMP_TYPES.get(key, PUMP_TYPES["infusion"])[0])


class PumpIcon(QWidget):
    """ไอคอนเส้นแบบเรียบ (วาดเอง ไม่ต้องใช้ไฟล์รูป) — infusion = ตัวเครื่อง + ถุงน้ำเกลือ, syringe = กระบอกฉีดยา"""

    def __init__(self, kind: str, size: int = 44):
        super().__init__()
        self.kind = kind
        self.color = Color.TEXT_MUTED
        self.setFixedSize(size, size)

    def set_color(self, color: str) -> None:
        self.color = color
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width() / 44.0
        p.scale(s, s)
        pen = QPen(QColor(self.color), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        fill = QColor(self.color)
        fill.setAlpha(40)
        if self.kind == "syringe":
            p.translate(22, 22)
            p.rotate(-35)
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(-12, -6, 22, 12), 2, 2)          # กระบอก
            p.setBrush(Qt.BrushStyle.NoBrush)
            for x in (-6, -1, 4):                                     # ขีดบอกปริมาตร
                p.drawLine(QPointF(x, -6), QPointF(x, -2))
            p.drawLine(QPointF(-12, 0), QPointF(-19, 0))              # ก้านลูกสูบ
            p.drawLine(QPointF(-19, -5), QPointF(-19, 5))             # ที่กด
            p.drawLine(QPointF(-16, -9), QPointF(-16, 9))             # ปีกกระบอก
            p.drawLine(QPointF(10, 0), QPointF(19, 0))                # เข็ม
        else:
            p.setBrush(fill)
            bag = QPainterPath()                                      # ถุงน้ำเกลือ
            bag.addRoundedRect(QRectF(5, 3, 12, 15), 4, 4)
            p.drawPath(bag)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(11, 18), QPointF(11, 24))              # สาย
            p.drawLine(QPointF(11, 24), QPointF(18, 24))
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(18, 13, 22, 27), 4, 4)           # ตัวเครื่อง
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(22, 17, 14, 8), 1.5, 1.5)        # จอ
            for x in (24, 29, 34):                                    # ปุ่ม
                p.drawPoint(QPointF(x, 32))
            p.drawLine(QPointF(29, 40), QPointF(29, 43))              # สายออก
        p.end()


class PumpTypeCard(QFrame):
    clicked = Signal()

    def __init__(self, key: str):
        super().__init__()
        self.key = key
        self.setProperty("pumpCard", True)
        self.setProperty("pump", key)
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(78)
        title, description = PUMP_TYPES[key]
        self.setAccessibleName(tr(title))

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 14, 10)
        row.setSpacing(14)
        self.icon = PumpIcon(key)
        row.addWidget(self.icon)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = label(tr(title).upper(), "pumpTitle")
        self.title.setProperty("pump", key)
        self.title.setProperty("selected", False)
        text.addWidget(self.title)
        hint = label(tr(description), "hint")
        hint.setWordWrap(True)
        text.addWidget(hint)
        row.addLayout(text, 1)
        self.check = QLabel()
        self.check.setFixedWidth(24)
        self.check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.check)

    def set_selected(self, selected: bool) -> None:
        color = PUMP_COLORS[self.key]
        set_property(self, "selected", selected)
        set_property(self.title, "selected", selected)
        self.icon.set_color(color if selected else Color.TEXT_MUTED)
        self.check.setText("✓" if selected else "")
        self.check.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 800;")

    def set_suggested(self, suggested: bool) -> None:
        """ระบบเสนอชนิดนี้จากรุ่นที่กรอก (ขอบประ + ไอคอนสีจาง) — รอผู้ใช้ยืนยันด้วย Tab/Enter"""
        set_property(self, "suggested", suggested)
        if suggested:
            self.icon.set_color(PUMP_COLORS[self.key])
            self.check.setText("?")
            self.check.setStyleSheet(f"color: {PUMP_COLORS[self.key]}; font-size: 16px; font-weight: 800;")
        else:
            self.set_selected(self.property("selected") is True)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class PumpTypeSelector(QWidget):
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self._keys = list(PUMP_TYPES)
        self._cards = [PumpTypeCard(key) for key in self._keys]
        for index, card in enumerate(self._cards):
            card.clicked.connect(lambda i=index: self.setCurrentIndex(i))
            row.addWidget(card, 1)
        self._index = -1
        self.setCurrentIndex(0)

    # ---- หน้าตาแบบ QComboBox (โค้ดเดิมเรียกใช้ได้ทันที)
    def currentIndex(self) -> int:
        return self._index

    def currentData(self) -> str:
        return self._keys[self._index]

    def findData(self, value: str) -> int:
        return self._keys.index(value) if value in self._keys else -1

    def setCurrentIndex(self, index: int) -> None:
        index = max(0, min(len(self._keys) - 1, index))
        changed = index != self._index
        self._index = index
        for i, card in enumerate(self._cards):
            set_property(card, "suggested", False)
            card.set_selected(i == index)
        if changed:
            self.changed.emit(self._keys[index])

    def suggest(self, key: str | None) -> None:
        """แสดงชนิดที่ระบบเสนอ (None = ไม่มี) — ชนิดที่เลือกอยู่แล้วไม่ต้องเสนอ"""
        for card in self._cards:
            card.set_suggested(key is not None and card.key == key and key != self.currentData())

    def suggested(self) -> str | None:
        return next((card.key for card in self._cards if card.property("suggested") is True), None)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = -1 if event.key() == Qt.Key.Key_Left else 1
            self.setCurrentIndex(self._index + step)
            self._cards[self._index].setFocus()
        else:
            super().keyPressEvent(event)


class PumpBadge(QLabel):
    """ป้ายชนิดเครื่องสีประจำชนิด (ใช้บนหัว wizard และแผนทดสอบ)"""

    def __init__(self, key: str = "infusion"):
        super().__init__()
        self.setProperty("role", "pumpBadge")
        self.set_pump(key)

    def set_pump(self, key: str) -> None:
        self.setText("●  " + pump_name(key).upper())
        set_property(self, "pump", key)


class PumpBar(QFrame):
    """แถบสีบางๆ ประจำชนิดเครื่อง (บนสุดของหน้าต่าง)"""

    def __init__(self, key: str = "infusion"):
        super().__init__()
        self.setProperty("pumpBar", True)
        self.set_pump(key)

    def set_pump(self, key: str) -> None:
        set_property(self, "pump", key)
