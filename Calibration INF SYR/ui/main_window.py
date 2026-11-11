"""MainWindow: โครงหน้าต่างหลัก = แถบนำทางซ้าย + พื้นที่เพจ

เพิ่มหน้าใหม่: สร้าง widget ใน ui/pages/ แล้วเพิ่ม 1 บรรทัดใน self._add_page(...)
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from config.constants import APP_NAME, APP_SUBTITLE, APP_VERSION
from config.i18n import tr
from config.settings import AppSettings
from services.logging_setup import LogBridge
from services.session_controller import SessionController
from ui.icons import Glyph, glyph_icon
from ui.pages.test_page import TestPage
from ui.pages.history import HistoryPage
from ui.pages.settings import SettingsPage
from ui.theme import Color
from ui.widgets.common import label


class MainWindow(QMainWindow):
    language_changed = Signal()     # ผู้ใช้เปลี่ยนภาษา -> แอปสร้างหน้าต่างใหม่

    def __init__(self, settings: AppSettings, log_bridge: LogBridge):
        super().__init__()
        self._settings = settings
        self._language = settings.ui.language
        self.setWindowTitle(f"{APP_NAME} · {APP_SUBTITLE}  v{APP_VERSION}")
        self.resize(1480, 920)
        self.setMinimumSize(1180, 720)

        self.controller = SessionController(settings, self)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ------------------------------------------------ แถบนำทาง
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(84)
        self._rail = QVBoxLayout(rail)
        self._rail.setContentsMargins(8, 14, 8, 12)
        self._rail.setSpacing(6)
        logo = label("ΔM", "logo")
        logo.setToolTip(f"{APP_NAME} — {APP_SUBTITLE}")
        self._rail.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._rail.addSpacing(12)
        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)

        self.pages = QStackedWidget()
        root.addWidget(rail)
        root.addWidget(self.pages, 1)

        # ------------------------------------------------ เพจ
        self.test_page = TestPage(settings, self.controller, log_bridge)
        self.history = HistoryPage()
        self.settings_page = SettingsPage(settings, self.controller.stop_monitor, self.controller.start_monitor)
        self._add_page(tr("Test"), Glyph.DASHBOARD, self.test_page)
        self._add_page(tr("History"), Glyph.HISTORY, self.history)
        self._add_page(tr("Settings"), Glyph.SETTINGS, self.settings_page)
        self._rail.addStretch()
        self._rail.addWidget(label(f"v{APP_VERSION}", "hint"), alignment=Qt.AlignmentFlag.AlignHCenter)
        self._nav.button(0).setChecked(True)
        self.pages.currentChanged.connect(lambda i: self._nav.button(i).setChecked(True))
        self.test_page.plan_panel.btn_create.setFocus()

        self.controller.session_finished.connect(self.history.reload)
        self.settings_page.saved.connect(self.test_page._refresh_plan)
        self.settings_page.saved.connect(self._on_settings_saved)
        self.controller.start_monitor()

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _on_settings_saved(self) -> None:
        self.controller.restart_monitor()       # พอร์ต/แหล่งข้อมูลอาจเปลี่ยน
        if self._settings.ui.language != self._language:
            if self.controller.is_running:
                self.settings_page.status.setText(tr("The language will change once the test has finished"))
            else:
                self.language_changed.emit()

    def _add_page(self, text: str, glyph: str, page: QWidget) -> None:
        index = self.pages.addWidget(page)
        button = QToolButton()
        button.setProperty("nav", True)
        button.setText(text)
        button.setIcon(glyph_icon(glyph, Color.TEXT_MUTED, active_color=Color.ACCENT, size=22))
        button.setIconSize(QSize(22, 22))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setCheckable(True)
        button.setFixedSize(68, 60)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.pages.setCurrentIndex(index))
        self._nav.addButton(button, index)
        self._rail.addWidget(button)

    def closeEvent(self, event) -> None:
        if self.controller.is_running or self.controller.awaiting_review:
            answer = QMessageBox.question(
                self, tr("A test is running"),
                tr("The test is not finished. Stop it and close the program?") + "\n"
                + tr("The unfinished test will not be saved."),
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.controller.shutdown()
        event.accept()
