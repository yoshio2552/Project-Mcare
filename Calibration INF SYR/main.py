"""จุดเริ่มโปรแกรม DeltaM — Calibration & Inspection: Infusion / Syringe Pump

    python main.py              ใช้ค่าตั้งที่บันทึกไว้ (ค่าเริ่มต้น: ตราชั่งผ่าน serial)
    python main.py --simulate   ใช้ตราชั่งจำลอง (ไม่ต้องต่อเครื่องจริง)
"""
import argparse
import os
import sys

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config.constants import APP_NAME
from config.i18n import set_language
from config.settings import AppSettings
from services.logging_setup import setup_logging
from ui.main_window import MainWindow
from ui.theme import apply_theme


class Application:
    """ถือของที่อยู่ตลอดอายุโปรแกรม และสร้างหน้าต่างใหม่เมื่อเปลี่ยนภาษา"""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.log_bridge = setup_logging()
        self.window: MainWindow | None = None

    def build_window(self, page: int = 0) -> MainWindow:
        set_language(self.settings.ui.language)
        old = self.window
        geometry = old.geometry() if old else None
        if old is not None:
            old.close()
            old.deleteLater()
        self.window = MainWindow(self.settings, self.log_bridge)
        if old is not None:
            self.window.controller.adopt(old.controller)
        self.window.language_changed.connect(lambda: QTimer.singleShot(0, lambda: self.build_window(page=2)))
        if geometry is not None:
            self.window.setGeometry(geometry)
        self.window.show_page(page)
        self.window.show()
        return self.window


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--simulate", action="store_true", help="ใช้ตราชั่งจำลองแทนเครื่องจริง")
    args, qt_args = parser.parse_known_args()

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName(APP_NAME)
    apply_theme(app)

    settings = AppSettings.load()
    if args.simulate:
        settings.source = "simulator"
    application = Application(settings)
    application.build_window()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
