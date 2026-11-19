"""กรอบหน้าต่างของ Windows: ไอคอนโปรแกรม · ไอคอนบนแถบงาน · แถบหัวหน้าต่างสีเข้มตามธีม

ปัญหาเดิม (ผู้ใช้ 2026-11-19): หัวหน้าต่างไม่มีโลโก้และเป็นสีขาวทั้งที่ธีมมืด · แถบงานแสดงไอคอน Python
    · ไอคอน: ui/assets/deltam.svg (แบบ C ชั่วคราว — tools/make_icon.py สร้าง .ico ให้ exe ของ Nuitka)
    · แถบงาน: Windows จัดกลุ่มตาม python.exe -> ต้องตั้ง AppUserModelID ของเราเองก่อนสร้างหน้าต่าง
    · หัวหน้าต่างสีเข้ม: DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE) ทุกหน้าต่างที่เปิด (รวม popup)
      Windows 10 1809+ / 11 — รุ่นเก่ากว่าไม่มีผล (ไม่ error)
ใช้: install(app, settings) ครั้งเดียวหลังสร้าง QApplication (main.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize
from PySide6.QtGui import QIcon

ASSETS = Path(__file__).resolve().parent / "assets"
APP_USER_MODEL_ID = "MCare.DeltaM.Calibration"
_DARK_ATTRIBUTES = (20, 19)     # DWMWA_USE_IMMERSIVE_DARK_MODE (Win11/10 20H1+) แล้วค่าเก่า (10 1809–1909)


def app_icon() -> QIcon:
    """ไอคอนโปรแกรมหลายขนาด (svg คมทุกขนาด · ไม่มี svg ใช้ .ico)"""
    icon = QIcon()
    svg = ASSETS / "deltam.svg"
    if svg.is_file():
        for size in (16, 20, 24, 32, 48, 64, 128, 256):
            icon.addFile(str(svg), QSize(size, size))
    elif (ASSETS / "deltam.ico").is_file():
        icon.addFile(str(ASSETS / "deltam.ico"))
    return icon


def set_app_identity() -> None:
    """ให้แถบงานของ Windows แสดงไอคอนของเรา ไม่ใช่ของ python.exe (เรียกก่อนสร้างหน้าต่างแรก)"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def set_dark_title_bar(widget, dark: bool) -> None:
    """แถบหัวหน้าต่างสีเข้ม/สว่างตามธีม (เฉพาะ Windows)"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attribute in _DARK_ATTRIBUTES:
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value),
                                                          ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


class _ChromeFilter(QObject):
    """ทุกหน้าต่างระดับบนที่เปิด (หน้าหลัก, wizard, popup) ได้ไอคอน + หัวหน้าต่างตามธีม"""

    def __init__(self, app, settings):
        super().__init__(app)
        self._settings = settings
        self._icon = app_icon()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show and getattr(obj, "isWindow", None) and obj.isWindow():
            if obj.windowIcon().isNull() or obj.windowIcon().cacheKey() != self._icon.cacheKey():
                obj.setWindowIcon(self._icon)
            theme = getattr(getattr(self._settings, "ui", None), "theme", "dark")
            set_dark_title_bar(obj, theme != "light")
        return False


_filter: _ChromeFilter | None = None


def install(app, settings) -> None:
    global _filter
    set_app_identity()
    app.setWindowIcon(app_icon())
    if _filter is None:
        _filter = _ChromeFilter(app, settings)
        app.installEventFilter(_filter)
