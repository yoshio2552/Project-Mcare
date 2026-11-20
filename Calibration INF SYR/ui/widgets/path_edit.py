"""ช่องเลือกไฟล์/โฟลเดอร์แบบโปรแกรมทั่วไป: ช่องแสดง path + ปุ่ม "เลือก…" (ไม่ต้องพิมพ์ path เอง — ผู้ใช้ 2026-11-20)

kind: "folder" | "image" (PNG/JPG) | "file" (ไฟล์ข้อมูลดิบ) · พิมพ์เองก็ยังได้ · ปุ่ม × ล้างค่า
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from config.i18n import tr

FILTERS = {
    "image": "Image (*.png *.jpg *.jpeg)",
    "png": "PNG image (*.png)",
    "file": "Raw data (*.csv *.gz *.txt);;All files (*)",
}


class PathEdit(QWidget):
    changed = Signal(str)

    def __init__(self, kind: str = "file", placeholder: str = ""):
        super().__init__()
        self.kind = kind
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.browse = QPushButton(tr("Browse…"))
        self.browse.setToolTip(tr("Choose a folder") if kind == "folder" else tr("Choose a file"))
        self.clear = QPushButton("×")
        self.clear.setToolTip(tr("Clear"))
        self.clear.setFixedWidth(30)
        row.addWidget(self.edit, 1)
        row.addWidget(self.browse)
        row.addWidget(self.clear)
        self.browse.clicked.connect(self._browse)
        self.clear.clicked.connect(lambda: self.setText(""))
        self.edit.textChanged.connect(self.changed)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, text: str) -> None:
        self.edit.setText(str(text or ""))

    def _start_dir(self) -> str:
        current = Path(self.text()) if self.text() else None
        if current is not None:
            return str(current if current.is_dir() else current.parent)
        return str(Path.home())

    def _browse(self) -> None:
        if self.kind == "folder":
            chosen = QFileDialog.getExistingDirectory(self, tr("Choose a folder"), self._start_dir())
        else:
            chosen, _ = QFileDialog.getOpenFileName(self, tr("Choose a file"), self._start_dir(),
                                                    tr(FILTERS.get(self.kind, FILTERS["file"])))
        if chosen:
            self.setText(str(Path(chosen)))
