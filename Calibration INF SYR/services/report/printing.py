"""พิมพ์ PDF ของใบรายงานใน thread แยก (ไม่ค้างจอ แม้กำลังรันการทดสอบอยู่)

อ่าน PDF ด้วย QPdfDocument แล้ววาดทีละหน้าลง QPrinter (Qt อนุญาตให้วาดลง QPrinter นอก GUI thread)
ภาพต่อหน้าเรนเดอร์ที่ไม่เกิน 300 dpi (A4 300 dpi ≈ 35 MB ต่อหน้า) แล้วย่อ/ขยายให้เต็มกระดาษ
เลือกเครื่องพิมพ์: printer_for(parent, ask) — ask=True เปิดหน้าต่างพิมพ์ของ Windows, False ใช้เครื่องพิมพ์หลัก
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, QThread, Signal
from PySide6.QtGui import QPageLayout, QPageSize, QPainter

log = logging.getLogger(__name__)
MAX_DPI = 300


def new_printer():
    from PySide6.QtPrintSupport import QPrinter
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(True)                 # เอกสารมีขอบในตัวแล้ว — วางเต็มกระดาษ
    return printer


def printer_for(parent, ask: bool, pages: int = 0, title: str = ""):
    """QPrinter ที่พร้อมพิมพ์ หรือ None (ผู้ใช้กดยกเลิก / ไม่มีเครื่องพิมพ์)"""
    from PySide6.QtPrintSupport import QPrintDialog, QPrinterInfo
    printer = new_printer()
    if title:
        printer.setDocName(title)
    if ask:
        dialog = QPrintDialog(printer, parent)
        if pages:
            dialog.setMinMax(1, pages)
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintToFile, False)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return None
        return printer
    default = QPrinterInfo.defaultPrinter()
    if default.isNull():
        return None
    printer.setPrinterName(default.printerName())
    return printer


class PrintJob(QThread):
    """พิมพ์ PDF (bytes) ลงเครื่องพิมพ์ — finished_ok(จำนวนหน้า) / failed(ข้อความ)"""
    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(self, data: bytes, printer, parent=None):
        super().__init__(parent)
        self._data, self._printer = data, printer

    def run(self) -> None:
        from PySide6.QtPdf import QPdfDocument
        try:
            buffer = QBuffer()
            buffer.setData(QByteArray(self._data))
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            doc = QPdfDocument()
            doc.load(buffer)
            count = doc.pageCount()
            if count <= 0:
                self.failed.emit("the PDF has no pages")
                return
            first, last = 1, count
            if self._printer.fromPage() > 0:          # ผู้ใช้เลือกช่วงหน้าในหน้าต่างพิมพ์
                first, last = max(1, self._printer.fromPage()), min(count, self._printer.toPage() or count)
            dpi = min(MAX_DPI, max(150, self._printer.resolution()))
            painter = QPainter()
            if not painter.begin(self._printer):
                self.failed.emit("the printer could not be started")
                return
            try:
                for number in range(first, last + 1):
                    if number > first:
                        self._printer.newPage()
                    points = doc.pagePointSize(number - 1)
                    size = QSize(round(points.width() * dpi / 72), round(points.height() * dpi / 72))
                    image = doc.render(number - 1, size)
                    target = QRectF(painter.viewport())
                    painter.drawImage(target, image)
            finally:
                painter.end()
            self.finished_ok.emit(last - first + 1)
        except Exception as exc:          # ไดรเวอร์เครื่องพิมพ์ผิดพลาด — แจ้งผู้ใช้ ไม่ให้โปรแกรมล้ม
            log.exception("printing failed")
            self.failed.emit(str(exc))
