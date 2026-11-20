"""ตั้งค่า → ใบรายงาน → ลายเซ็น (ผู้ใช้ 2026-11-20)

- ผู้ลงนาม: เพิ่ม/แก้/ลบ · เลือกภาพลายเซ็น PNG พื้นใสด้วยปุ่ม "เลือกไฟล์…" (ไม่ต้องพิมพ์ path) · ภาพถูกคัดลอกเข้า
  data/signatures/ (ภาพพื้นขาวทำให้โปร่งใสให้เอง + ตัดขอบว่าง) · ชื่อ-นามสกุลไทย/อังกฤษใต้ลายเซ็น
- ช่องลายเซ็นของใบ Inspection (หน้า 1) และใบรับรอง Calibration (หน้า 2): บทบาท ตำแหน่ง (ไทย/อังกฤษ) ใครลงนาม แสดง/ซ่อน
ค่าเก็บใน AppSettings.report (people, sign_inspection, sign_calibration) — ตรรกะอยู่ที่ services/report/signatures.py
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from config.i18n import tr
from services.report import signatures
from services.report.signatures import Person, SignSlot
from ui.widgets.common import Card, label

MAX_HEIGHT_PX = 300         # ภาพลายเซ็นในใบสูง ~40 px — เก็บ 300 px พอสำหรับพิมพ์ 300 dpi และไฟล์เล็ก
MAX_WIDTH_PX = 1200
SLOT_TITLES = {
    "inspection": ("Inspection report — signature boxes",
                   "Page 1 of the Inspection report (also page 1 of the Calibration report)"),
    "calibration": ("Calibration certificate — signature boxes", "Page 2 of the Calibration report"),
}


def signature_dir() -> Path:
    """โฟลเดอร์เก็บภาพลายเซ็นของโปรแกรม (data/signatures) — เทสต์แทนที่ฟังก์ชันนี้ได้"""
    from config.constants import DATA_DIR
    return DATA_DIR / signatures.SIGNATURE_FOLDER


def prepare_signature(image: QImage) -> tuple[QImage | None, bool]:
    """ภาพลายเซ็นพร้อมใช้: พื้นขาวทึบ -> โปร่งใส (ขอบนุ่ม) · ตัดขอบว่าง · ย่อให้ไม่ใหญ่เกิน
    คืน (ภาพ | None ถ้าไม่มีเส้นลายเซ็นเลย, ทำพื้นใสให้หรือไม่)"""
    img = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = img.width(), img.height()
    if w == 0 or h == 0:
        return None, False
    raw = np.frombuffer(img.constBits(), dtype=np.uint8, count=img.sizeInBytes())
    arr = raw.reshape(h, img.bytesPerLine())[:, :w * 4].reshape(h, w, 4).copy()
    removed = False
    if int(arr[..., 3].min()) >= 250:           # ไม่มีพื้นใส: สีขาว/เกือบขาว -> ใส · หมึก -> ทึบ (ไล่ระดับที่ขอบเส้น)
        lum = arr[..., :3].astype(np.float32).mean(axis=2)
        arr[..., 3] = np.clip((245.0 - lum) * 255.0 / 75.0, 0, 255).astype(np.uint8)
        removed = True
    mask = arr[..., 3] > 12
    if not mask.any():
        return None, removed
    ys, xs = np.where(mask)
    pad = 4
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
    arr = np.ascontiguousarray(arr[y0:y1, x0:x1])
    out = QImage(arr.data, arr.shape[1], arr.shape[0], arr.shape[1] * 4, QImage.Format.Format_RGBA8888).copy()
    if out.height() > MAX_HEIGHT_PX:
        out = out.scaledToHeight(MAX_HEIGHT_PX, Qt.TransformationMode.SmoothTransformation)
    if out.width() > MAX_WIDTH_PX:
        out = out.scaledToWidth(MAX_WIDTH_PX, Qt.TransformationMode.SmoothTransformation)
    return out, removed


def signature_pixmap(path: str, width: int, height: int) -> QPixmap | None:
    file = signatures.image_file(path, signature_dir().parent)
    if not file or not Path(file).is_file():
        return None
    pixmap = QPixmap(file)
    if pixmap.isNull():
        return None
    return pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def _paper(widget: QLabel) -> None:
    """พื้นขาวแบบกระดาษ (ภาพลายเซ็นพื้นใส หมึกเข้ม — บนธีมมืดต้องมีพื้นขาวจึงมองเห็น)"""
    widget.setStyleSheet("background: #FFFFFF; border: 1px solid #CBD2D9; border-radius: 6px; color: #8A939D;")
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)


class PersonDialog(QDialog):
    """เพิ่ม/แก้ผู้ลงนาม: ภาพลายเซ็น (เลือกไฟล์) + ชื่อ-นามสกุล ไทย/อังกฤษ + ชื่ออื่นที่พิมพ์ในช่องผู้ทดสอบ"""

    def __init__(self, parent: QWidget | None, person: Person | None = None):
        super().__init__(parent)
        self.person = copy.deepcopy(person) if person else Person(id=signatures.new_id())
        self._new_image: QImage | None = None
        self.setWindowTitle(tr("Signer"))
        self.setModal(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(label(tr("Signature"), "cardTitle"))
        self.preview = QLabel()
        self.preview.setFixedSize(380, 120)
        _paper(self.preview)
        root.addWidget(self.preview)
        buttons = QHBoxLayout()
        self.btn_choose = QPushButton(tr("Choose PNG file…"))
        self.btn_choose.setProperty("variant", "primary")
        self.btn_remove = QPushButton(tr("No signature image"))
        buttons.addWidget(self.btn_choose)
        buttons.addWidget(self.btn_remove)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self.note = label(tr("PNG with a transparent background is best. A white background is made transparent "
                             "automatically. The file is copied into the program's data folder."), "hint")
        self.note.setWordWrap(True)
        root.addWidget(self.note)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.name_th, self.name_en, self.aliases = QLineEdit(self.person.name_th), QLineEdit(self.person.name_en), \
            QLineEdit(self.person.aliases)
        self.name_th.setPlaceholderText(tr("e.g. สมชาย ตั้งใจ"))
        self.name_en.setPlaceholderText(tr("e.g. Somchai Tangjai"))
        self.aliases.setPlaceholderText(tr("e.g. Somchai, Chai"))
        rows = [(tr("Full name (Thai)"), self.name_th), (tr("Full name (English)"), self.name_en),
                (tr("Other names typed as Operator"), self.aliases)]
        for index, (text, edit) in enumerate(rows):
            grid.addWidget(label(text, "fieldLabel"), index, 0)
            grid.addWidget(edit, index, 1)
        root.addLayout(grid)
        hint = label(tr("The name under the signature: the Thai report uses the Thai name and the English report the "
                        "English name (one is enough). A test whose Operator matches one of these names gets this "
                        "signature."), "hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton(tr("Cancel"))
        self.btn_ok = QPushButton(tr("Done"))
        self.btn_ok.setProperty("variant", "primary")
        actions.addWidget(cancel)
        actions.addWidget(self.btn_ok)
        root.addLayout(actions)
        cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._accept)
        self.btn_choose.clicked.connect(self._choose)
        self.btn_remove.clicked.connect(self._remove_image)
        self._show_preview()

    # ---------------------------------------------------------------- ภาพ
    def _show_preview(self) -> None:
        if self._new_image is not None:
            pixmap = QPixmap.fromImage(self._new_image).scaled(
                360, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            pixmap = signature_pixmap(self.person.image, 360, 100)
        if pixmap is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText(tr("No signature image — signed by hand on paper"))
        else:
            self.preview.setPixmap(pixmap)
        self.btn_remove.setEnabled(pixmap is not None)

    def _choose(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Choose the signature image"), str(Path.home()),
                                              tr("PNG image (*.png)") + ";;" + tr("Image (*.png *.jpg *.jpeg)"))
        if path:
            self.load_image(path)

    def load_image(self, path: str) -> bool:
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, tr("Signature"), tr("This file could not be opened as an image."))
            return False
        prepared, removed = prepare_signature(image)
        if prepared is None:
            QMessageBox.warning(self, tr("Signature"), tr("No signature was found in this image."))
            return False
        self._new_image = prepared
        self.note.setText(tr("The white background was made transparent automatically.") if removed
                          else tr("Transparent background — ready to use."))
        self._show_preview()
        return True

    def _remove_image(self) -> None:
        self._new_image = None
        self.person.image = ""
        self._show_preview()

    # ---------------------------------------------------------------- ตกลง
    def _accept(self) -> None:
        self.person.name_th = " ".join(self.name_th.text().split())
        self.person.name_en = " ".join(self.name_en.text().split())
        self.person.aliases = ", ".join(a.strip() for a in self.aliases.text().split(",") if a.strip())
        if not (self.person.name_th or self.person.name_en):
            QMessageBox.information(self, tr("Signer"), tr("Enter the full name in Thai or English."))
            return
        if self._new_image is not None:
            folder = signature_dir()
            folder.mkdir(parents=True, exist_ok=True)
            name = f"{self.person.id}-{signatures.new_id()}.png"
            if not self._new_image.save(str(folder / name), "PNG"):
                QMessageBox.warning(self, tr("Signature"), tr("Could not save the signature image."))
                return
            self.person.image = f"{signatures.SIGNATURE_FOLDER}/{name}"     # สัมพัทธ์กับ data/ (ย้ายเครื่องได้)
        self.accept()


class _SlotRows:
    """แถวตั้งค่าช่องลายเซ็นของใบ 1 ชนิด"""

    def __init__(self, kind: str, grid: QGridLayout, row0: int):
        self.kind = kind
        self.rows: list[dict] = []
        for index in range(signatures.MAX_SLOTS[kind]):
            row = dict(show=QCheckBox(), role_th=QLineEdit(), role_en=QLineEdit(), pos_th=QLineEdit(),
                       pos_en=QLineEdit(), who=QComboBox())
            row["show"].setToolTip(tr("Show this box on the report"))
            row["who"].setMinimumWidth(170)
            for col, key in enumerate(("show", "role_th", "role_en", "pos_th", "pos_en", "who")):
                grid.addWidget(row[key], row0 + index, col)
            self.rows.append(row)

    def set(self, slots: list[SignSlot], people: list[Person]) -> None:
        padded = list(slots) + [SignSlot(who="blank", show=False)] * (len(self.rows) - len(slots))
        for row, slot in zip(self.rows, padded):
            row["show"].setChecked(bool(slot.show))
            for key in ("role_th", "role_en", "pos_th", "pos_en"):
                row[key].setText(getattr(slot, key))
            self._fill_who(row["who"], people, slot.who)

    def refresh_people(self, people: list[Person]) -> None:
        for row in self.rows:
            self._fill_who(row["who"], people, row["who"].currentData())

    @staticmethod
    def _fill_who(combo: QComboBox, people: list[Person], value: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("Operator of the test"), "operator")
        for person in people:
            combo.addItem(person.label(), f"person:{person.id}")
        combo.addItem(tr("Blank — sign by hand"), "blank")
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else combo.findData("blank"))
        combo.blockSignals(False)

    def values(self) -> list[SignSlot]:
        return [SignSlot(role_th=r["role_th"].text().strip(), role_en=r["role_en"].text().strip(),
                         pos_th=r["pos_th"].text().strip(), pos_en=r["pos_en"].text().strip(),
                         who=r["who"].currentData() or "blank", show=r["show"].isChecked()) for r in self.rows]


class SignatureSettings(QWidget):
    """หน้าย่อย "ลายเซ็น" ของตั้งค่าใบรายงาน — load(report) / store(report) ตามแบบหน้าตั้งค่า"""

    def __init__(self):
        super().__init__()
        self.people: list[Person] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # ---- ผู้ลงนาม
        card = Card(tr("Signers"))
        hint = label(tr("People whose signature and name appear on reports. Choose each signature image with the "
                        "button — no need to type a file path."), "hint")
        hint.setWordWrap(True)
        card.body.addWidget(hint)
        self._people_box = QVBoxLayout()
        self._people_box.setSpacing(6)
        card.body.addLayout(self._people_box)
        add_row = QHBoxLayout()
        self.btn_add = QPushButton("+  " + tr("Add signer"))
        self.btn_add.setProperty("variant", "primary")
        add_row.addWidget(self.btn_add)
        add_row.addStretch(1)
        card.body.addLayout(add_row)
        root.addWidget(card)
        self.btn_add.clicked.connect(self._add_person)

        # ---- ช่องลายเซ็นของแต่ละใบ
        self.slots: dict[str, _SlotRows] = {}
        for kind in signatures.KINDS:
            title, where = SLOT_TITLES[kind]
            card = Card(tr(title))
            sub = label(tr(where), "hint")
            sub.setWordWrap(True)
            card.body.addWidget(sub)
            grid = QGridLayout()
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(6)
            for col, text in enumerate(("Show", "Role (Thai)", "Role (English)", "Position (Thai)",
                                        "Position (English)", "Signed by")):
                grid.addWidget(label(tr(text), "fieldLabel"), 0, col)
            for col in (1, 2, 3, 4):
                grid.setColumnStretch(col, 1)
            self.slots[kind] = _SlotRows(kind, grid, 1)
            card.body.addLayout(grid)
            reset_row = QHBoxLayout()
            reset = QPushButton(tr("Restore default boxes"))
            reset.setProperty("variant", "ghost")
            reset.clicked.connect(lambda _=False, k=kind: self.slots[k].set(signatures.default_slots(k), self.people))
            reset_row.addStretch(1)
            reset_row.addWidget(reset)
            card.body.addLayout(reset_row)
            root.addWidget(card)
        root.addStretch(1)

    # ------------------------------------------------------------ ค่าตั้ง
    def load(self, report) -> None:
        signatures.migrate(report)                  # ค่าเก่า -> ผู้ลงนาม (ในหน่วยความจำ บันทึกเมื่อกด Save)
        self.people = signatures.people_from(report.people)
        self._render_people()
        self.slots["inspection"].set(signatures.slots_from(report.sign_inspection, "inspection"), self.people)
        self.slots["calibration"].set(signatures.slots_from(report.sign_calibration, "calibration"), self.people)

    def store(self, report) -> None:
        report.people = signatures.to_dicts(self.people)
        report.people_migrated = True
        report.sign_inspection = signatures.to_dicts(self.slots["inspection"].values())
        report.sign_calibration = signatures.to_dicts(self.slots["calibration"].values())

    # ------------------------------------------------------------ รายชื่อ
    def _render_people(self) -> None:
        while self._people_box.count():
            item = self._people_box.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()                # ซ่อนทันที (deleteLater ลบตอนวนกลับ event loop)
                item.widget().deleteLater()
        if not self.people:
            empty = label(tr("No signers yet — reports leave the boxes blank to sign by hand."), "hint")
            self._people_box.addWidget(empty)
        for person in self.people:
            self._people_box.addWidget(self._person_row(person))
        for rows in self.slots.values() if hasattr(self, "slots") else ():
            rows.refresh_people(self.people)

    def _person_row(self, person: Person) -> QWidget:
        row = QFrame()
        row.setProperty("card", True)
        box = QHBoxLayout(row)
        box.setContentsMargins(8, 6, 8, 6)
        box.setSpacing(12)
        thumb = QLabel()
        thumb.setFixedSize(150, 46)
        _paper(thumb)
        pixmap = signature_pixmap(person.image, 140, 40)
        if pixmap is None:
            thumb.setText(tr("no image"))
        else:
            thumb.setPixmap(pixmap)
        box.addWidget(thumb)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label(person.name_th or person.name_en, "cardTitle"))
        second = " · ".join(p for p in (person.name_en if person.name_th else "", person.aliases) if p)
        if second:
            names.addWidget(label(second, "hint"))
        box.addLayout(names, 1)
        edit = QPushButton(tr("Edit"))
        remove = QPushButton(tr("Remove"))
        remove.setProperty("variant", "ghost")
        edit.clicked.connect(lambda _=False, p=person: self._edit_person(p))
        remove.clicked.connect(lambda _=False, p=person: self._remove_person(p))
        box.addWidget(edit)
        box.addWidget(remove)
        return row

    def _open_dialog(self, person: Person | None) -> Person | None:
        dialog = PersonDialog(self, person)
        return dialog.person if dialog.exec() == QDialog.DialogCode.Accepted else None

    def _add_person(self) -> None:
        person = self._open_dialog(None)
        if person is not None:
            self.people.append(person)
            self._render_people()

    def _edit_person(self, person: Person) -> None:
        edited = self._open_dialog(person)
        if edited is not None:
            self.people[self.people.index(person)] = edited
            self._render_people()

    def _remove_person(self, person: Person) -> None:
        answer = QMessageBox.question(self, tr("Remove signer"),
                                      tr("Remove {name} from the signers? Signature boxes that use this person "
                                         "become blank. Reports already saved as PDF are not changed.",
                                         name=person.label()))
        if answer == QMessageBox.StandardButton.Yes:
            self.people.remove(person)
            self._render_people()
