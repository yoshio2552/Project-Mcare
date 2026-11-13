"""รายการติ๊กของขั้น "ตรวจเครื่อง" (wizard ขั้น 2) — 2 แบบที่หน้าตาต่างกันชัด

    ┃ 📦 อุปกรณ์ที่ติดมากับเครื่อง        3 / 12     ← แถบซ้าย + ไอคอน + สีฟ้าอมเขียว (RECEIVED)
    ┃ 🔧 อะไหล่ที่เปลี่ยน                 1 / 9      ← แถบซ้าย + ไอคอน + สีส้มอำพัน (REPLACED)
    ┃ ┌ ค้นหา… พิมพ์แล้ว Tab/Enter = ติ๊ก ┐           ← ช่องค้นอัจฉริยะอยู่บนสุด (รายการเยอะก็ไม่ต้องเลื่อนหา)
    ┃ [Battery ✕] [Pump ⛨ประกัน ✕]                  ← ที่ติ๊กแล้วเป็นชิป (อะไหล่กดสลับ "ประกัน" ได้ที่ชิป)
    ┃ รายการทั้งหมด (★ = รุ่นนี้เคยใช้) คลิกทั้งแถวเพื่อติ๊ก

ช่องค้น: พิมพ์ส่วนใดของชื่อก็ได้ (ขึ้นต้นตรงกันมาก่อน) รายการด้านล่างกรองตามทันที
    Tab / Enter  ติ๊กรายการที่เสนอ (ตัวจาง) แล้วล้างช่องรอตัวถัดไป — ยังอยู่ช่องเดิม
    ↓            เลือกจากรายการที่ตรง · Esc ล้างช่อง
    ชื่อที่ไม่มีในรายการ: Enter แล้วต้องยืนยันก่อนเพิ่ม (กันชื่อสะกดผิดเข้าระบบ)
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from config.i18n import tr
from ui.theme import Color, set_property
from ui.widgets.common import label
from ui.widgets.smart_edit import SmartLineEdit

KIND_COLORS = {"received": Color.RECEIVED, "replaced": Color.REPLACED}


def _n(text: str) -> str:
    return " ".join(str(text or "").lower().split())


class FlowLayout(QLayout):
    """วางชิปเรียงซ้ายไปขวา ขึ้นบรรทัดใหม่เมื่อเต็ม"""

    def __init__(self, parent=None, spacing: int = 6):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() and line > 0:
                x, y, line = rect.x(), y + line + self._spacing, 0
            if apply:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x += hint.width() + self._spacing
            line = max(line, hint.height())
        return y + line - rect.y()


class KindIcon(QWidget):
    """ไอคอนเส้นวาดเอง: received = กล่อง, replaced = ประแจ"""

    def __init__(self, kind: str, size: int = 22):
        super().__init__()
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / 22.0, self.height() / 22.0)
        color = QColor(KIND_COLORS[self.kind])
        p.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        fill = QColor(color)
        fill.setAlpha(45)
        if self.kind == "received":
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(3, 7, 16, 12), 2, 2)            # ตัวกล่อง
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(3, 7), QPointF(6, 3))
            p.drawLine(QPointF(19, 7), QPointF(16, 3))
            p.drawLine(QPointF(6, 3), QPointF(16, 3))
            p.drawLine(QPointF(9, 11), QPointF(13, 11))              # ที่จับ
        else:
            path = QPainterPath()                                     # ประแจ
            path.moveTo(5, 17)
            path.lineTo(12, 10)
            p.drawPath(path)
            p.setBrush(fill)
            p.drawEllipse(QRectF(11, 3, 8, 8))
            p.setBrush(QColor(Color.SURFACE))
            p.drawEllipse(QRectF(14, 4, 3.5, 3.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(4, 18), QPointF(6, 16))
        p.end()


class _Chip(QFrame):
    """ชิปของรายการที่ติ๊กแล้ว: ชื่อ · (อะไหล่) ปุ่มประกัน · ✕"""
    removed = Signal(str)
    warranty_toggled = Signal(str, bool)

    def __init__(self, name: str, kind: str, warranty: bool | None = None):
        super().__init__()
        self.name = name
        self.setProperty("chip", kind)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 2, 4, 2)
        row.setSpacing(4)
        text = QLabel(name)
        text.setProperty("role", "chipText")
        row.addWidget(text)
        self.warranty: QPushButton | None = None
        if warranty is not None:                        # อะไหล่: สลับ "ประกัน" ได้ที่ชิป
            self.warranty = QPushButton()
            self.warranty.setProperty("variant", "warrantyToggle")
            self.warranty.setCheckable(True)
            self.warranty.setChecked(warranty)
            self.warranty.setCursor(Qt.CursorShape.PointingHandCursor)
            self.warranty.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.warranty.toggled.connect(self._on_warranty)
            self._paint_warranty(warranty)
            row.addWidget(self.warranty)
        close = QPushButton("✕")
        close.setProperty("variant", "chipClose")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close.setToolTip(tr("Untick"))
        close.clicked.connect(lambda: self.removed.emit(self.name))
        row.addWidget(close)

    def _paint_warranty(self, on: bool) -> None:
        self.warranty.setText(("⛨ " if on else "") + (tr("Warranty ✓") if on else tr("Warranty?")))
        self.warranty.setToolTip(tr("Replaced under warranty — click to change") if on
                                 else tr("Click if this part is replaced under warranty"))
        set_property(self, "warranty", on)

    def _on_warranty(self, on: bool) -> None:
        self._paint_warranty(on)
        self.warranty_toggled.emit(self.name, on)


class _QuickPick(SmartLineEdit):
    """ช่องค้น: Tab/Enter ติ๊กรายการที่เสนอแล้ว "อยู่ช่องเดิม" (ไม่ข้ามไปช่องถัดไป)"""
    picked = Signal(str)
    add_requested = Signal(str)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab \
                and not self._completer.popup().isVisible() and self.text().strip():
            self._commit()
            return True                                 # กินปุ่ม Tab — ยังพิมพ์ตัวถัดไปต่อได้ทันที
        # ข้ามพฤติกรรม Tab ของ SmartLineEdit (รับคำแนะนำแล้วย้ายช่อง) — ช่องค้นต้องอยู่ช่องเดิม
        return QLineEdit.event(self, event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not self._completer.popup().isVisible():
            self._commit()
            return
        if key == Qt.Key.Key_Escape and self.text():
            self.clear()
            self.refresh()
            self.textEdited.emit("")
            return
        super().keyPressEvent(event)

    def _commit(self) -> None:
        typed = self.text().strip()
        if not typed:
            return
        value = self._ghost if (self._ghost and self._ghost.lower().startswith(typed.lower())) else ""
        exact = next((s for s in self._suggestions if _n(s) == _n(typed)), "")
        target = exact or value or (self._suggestions[0] if len(self._suggestions) == 1 else "")
        if target:
            self.picked.emit(target)
        else:
            self.add_requested.emit(typed)

    def _take(self, value: str) -> None:               # เลือกจากรายการ ↓ แล้ว Enter
        self._completer.popup().hide()
        self.picked.emit(value)


class Checklist(QFrame):
    """รายการติ๊กของ "รุ่นนี้" — kind = "received" (อุปกรณ์ที่ติดมา) | "replaced" (อะไหล่ที่เปลี่ยน)

    รายการที่รุ่นนี้เคยใช้ขึ้นก่อน (★ ใช้บ่อยสุดอยู่บน) ตามด้วยรายการกลางจากหน้าตั้งค่า · คลิกขวาที่ ★ เพื่อลบออกจากรุ่น
    """
    forget_requested = Signal(str)
    changed = Signal()

    def __init__(self, title: str, kind: str):
        super().__init__()
        self.kind = kind
        self.setProperty("checkCard", kind)
        self._color = KIND_COLORS[kind]
        body = QVBoxLayout(self)
        body.setContentsMargins(16, 12, 14, 12)
        body.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(KindIcon(kind))
        title_label = label(title, "checkTitle")
        title_label.setStyleSheet(f"color: {self._color};")
        header.addWidget(title_label)
        header.addStretch()
        self.header = header
        self._count = label("", "checkCount")
        self._count.setStyleSheet(f"color: {self._color}; border-color: {self._color};")
        header.addWidget(self._count)
        body.addLayout(header)

        self._source = label("", "hint")
        self._source.setWordWrap(True)
        body.addWidget(self._source)

        self.search = _QuickPick(self._matches)
        self.search.setPlaceholderText(tr("Search — Tab or Enter ticks it, then type the next one…"))
        self.search.setClearButtonEnabled(True)
        self.search.setProperty("checkSearch", kind)
        body.addWidget(self.search)

        self._chips_box = QWidget()
        self._chips = FlowLayout(self._chips_box)
        self._chips_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        body.addWidget(self._chips_box)
        self._empty = label(tr("Nothing ticked yet"), "hint")
        body.addWidget(self._empty)

        self.list = QListWidget()
        self.list.setProperty("checkList", kind)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        body.addWidget(self.list, 1)

        tools = QHBoxLayout()
        select_all = QPushButton(tr("Select all"))
        clear = QPushButton(tr("Clear"))
        for button in (select_all, clear):
            button.setProperty("variant", "ghost")
            tools.addWidget(button)
        tools.addStretch()
        self.tools = tools
        body.addLayout(tools)

        self._custom: list[str] = []
        self._model_items: set[str] = set()
        self._warranty: set[str] = set()            # (อะไหล่) ชื่อที่เปลี่ยนแบบเคลมประกัน (ตัวเล็ก)
        self.search.picked.connect(self._on_picked)
        self.search.add_requested.connect(self._on_add_requested)
        self.search.textEdited.connect(self._filter)
        self.list.itemClicked.connect(self._toggle)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        select_all.clicked.connect(lambda: self._set_all(True))
        clear.clicked.connect(lambda: self._set_all(False))

    # ------------------------------------------------------------ เติมรายการ
    def set_items(self, device: str, model_items: list[tuple[str, int]], catalog: list[str], checked: list[str],
                  warranty: list[str] | None = None) -> None:
        self.list.clear()
        self._model_items = {name for name, _ in model_items}
        self._warranty = {_n(name) for name in (warranty or [])}
        uses = dict(model_items)
        for name in dict.fromkeys([*uses, *catalog, *self._custom, *checked]):
            self._add(name, name in checked, uses.get(name))
        if not device:
            self._source.setText(tr("Enter brand and model in step 1 to keep a list for each model."))
        elif model_items:
            self._source.setText(tr("★ = used with {device} before ({n} items). Right-click a ★ item to remove it from this model.",
                                    device=device, n=len(model_items)))
        else:
            self._source.setText(tr("First time for {device} — what you tick or add is remembered for this model.", device=device))
        self._refresh()

    def _add(self, name: str, checked: bool, uses: int | None = None) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setData(Qt.ItemDataRole.UserRole + 1, uses)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)   # กล่องไม่รับคลิกเอง (กันติ๊กซ้อน)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        if uses is not None:
            item.setToolTip(tr("Ticked {n} times for this model", n=uses))
        self.list.addItem(item)
        self._paint(item)
        return item

    def _paint(self, item: QListWidgetItem) -> None:
        name, uses = item.data(Qt.ItemDataRole.UserRole), item.data(Qt.ItemDataRole.UserRole + 1)
        checked = item.checkState() == Qt.CheckState.Checked
        item.setText(f"★  {name}   ·  {uses}×" if uses else f"★  {name}" if uses is not None else name)
        font = item.font()
        font.setBold(checked)
        item.setFont(font)
        item.setForeground(QColor(self._color if checked else Color.TEXT))

    def _items(self):
        return [self.list.item(i) for i in range(self.list.count())]

    def _find(self, name: str) -> QListWidgetItem | None:
        return next((i for i in self._items() if _n(i.data(Qt.ItemDataRole.UserRole)) == _n(name)), None)

    # ------------------------------------------------------------ ติ๊ก
    def _toggle(self, item: QListWidgetItem) -> None:
        checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)
        if checked:
            self._warranty.discard(_n(item.data(Qt.ItemDataRole.UserRole)))
        self._paint(item)
        self.list.clearSelection()
        self._refresh()

    def tick(self, name: str, warranty: bool | None = None) -> None:
        """ติ๊กรายการ (ไม่มีในรายการ = เพิ่มใหม่) · warranty: True/False ตั้งสถานะประกัน, None = คงเดิม"""
        item = self._find(name)
        if item is None:
            self._custom.append(name)
            item = self._add(name, True)
        elif item.checkState() != Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Checked)
            self._paint(item)
        if warranty is not None:
            (self._warranty.add if warranty else self._warranty.discard)(_n(item.data(Qt.ItemDataRole.UserRole)))
        self._refresh()

    def untick(self, name: str) -> None:
        item = self._find(name)
        if item is not None and item.checkState() == Qt.CheckState.Checked:
            self._toggle(item)

    def _set_all(self, checked: bool) -> None:
        for item in self._items():
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._paint(item)
        if not checked:
            self._warranty.clear()
        self._refresh()

    def _on_picked(self, name: str) -> None:
        self.tick(name)
        self.search.clear()
        self._filter("")
        self.search.refresh()

    def _on_add_requested(self, text: str) -> None:
        """ชื่อที่ไม่มีในรายการ: ถามก่อนเพิ่ม (กันพิมพ์ผิด)"""
        answer = QMessageBox.question(
            self, tr("Add a new item?"),
            tr("\"{name}\" is not in the list.\n\nAdd it as a new item? It will be remembered for this model.", name=text))
        if answer == QMessageBox.StandardButton.Yes:
            self._on_picked(text)

    def _matches(self, typed: str) -> list[str]:
        """รายการที่ยังไม่ได้ติ๊กซึ่งตรงกับที่พิมพ์ (ขึ้นต้นตรงกันก่อน แล้วจึงมีคำนั้นอยู่ข้างใน)"""
        key = _n(typed)
        names = [i.data(Qt.ItemDataRole.UserRole) for i in self._items() if i.checkState() != Qt.CheckState.Checked]
        if not key:
            return []
        prefix = [n for n in names if _n(n).startswith(key)]
        inside = [n for n in names if key in _n(n) and n not in prefix]
        return (prefix + inside)[:10]

    def _filter(self, text: str) -> None:
        key = _n(text)
        for item in self._items():
            item.setHidden(bool(key) and key not in _n(item.data(Qt.ItemDataRole.UserRole)))

    # ------------------------------------------------------------ ชิป
    def _refresh(self) -> None:
        while self._chips.count():
            widget = self._chips.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        values = self.values()
        for name in values:
            chip = _Chip(name, self.kind, (_n(name) in self._warranty) if self.kind == "replaced" else None)
            chip.removed.connect(self.untick)
            chip.warranty_toggled.connect(self._on_warranty_toggled)
            self._chips.addWidget(chip)
        self._empty.setVisible(not values)
        self._chips_box.setVisible(bool(values))
        self._chips_box.updateGeometry()
        self._count.setText(f"{len(values)} / {self.list.count()}")
        self.changed.emit()

    def _on_warranty_toggled(self, name: str, on: bool) -> None:
        (self._warranty.add if on else self._warranty.discard)(_n(name))
        self.changed.emit()

    # ------------------------------------------------------------ เมนูคลิกขวา
    def _on_context_menu(self, position) -> None:
        item = self.list.itemAt(position)
        if item is None or item.data(Qt.ItemDataRole.UserRole) not in self._model_items:
            return
        menu = QMenu(self)
        remove = menu.addAction(tr("Remove from this model"))
        if menu.exec(self.list.mapToGlobal(position)) is remove:
            name = item.data(Qt.ItemDataRole.UserRole)
            self._model_items.discard(name)
            self.list.takeItem(self.list.row(item))
            self.forget_requested.emit(name)
            self._refresh()

    # ------------------------------------------------------------ ผลลัพธ์
    def values(self) -> list[str]:
        return [i.data(Qt.ItemDataRole.UserRole) for i in self._items() if i.checkState() == Qt.CheckState.Checked]

    def warranty_values(self) -> list[str]:
        """(อะไหล่) รายการที่ติ๊กและเป็นการเคลมประกัน"""
        return [name for name in self.values() if _n(name) in self._warranty]

    def custom_items(self) -> list[str]:
        return list(self._custom)
