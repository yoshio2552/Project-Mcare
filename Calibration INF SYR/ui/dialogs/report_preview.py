"""ใบรายงาน PDF: หน้าต่างดูตัวอย่าง + การบันทึก/พิมพ์ (ใช้ร่วมกันทั้งหลังทดสอบเสร็จ และหน้าประวัติ)

ReportActions(parent, settings, repository)
    .output(jobs, action, preview)   action = "save" | "print" — preview=True เปิดหน้าต่างตัวอย่าง ไม่งั้นทำทันที
    .save(jobs, lang, ask_location)  บันทึก PDF (ใบเดียว / หลายใบแยกไฟล์ / รวมไฟล์เดียว ตามค่าตั้ง)
    .print(jobs, lang)               พิมพ์ใน thread แยก (หน้าต่างเลือกเครื่องพิมพ์ของ Windows ถ้าตั้งให้ถาม)
ReportPreviewDialog: แสดง PDF จริงทุกหน้า (เหมือนกระดาษ) เลื่อน/ซูมได้ สลับภาษาได้ แก้ข้อมูลใบได้
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QActionGroup, QDesktopServices
from PySide6.QtWidgets import (QComboBox, QDialog, QMenu, QToolButton, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                               QProgressDialog, QPushButton, QVBoxLayout, QWidget)

from config.i18n import tr
from services.report import layout, service
from services.report.model import ReportJob

log = logging.getLogger(__name__)
LANGS = [("th", "ไทย"), ("mix", "ไทย + English terms"), ("en", "English")]   # mix = ศัพท์เทคนิคอังกฤษ (2026-11-20)


def fit_to_screen(widget: QWidget) -> None:
    """หน้าต่างไม่สูง/กว้างเกินพื้นที่จอ (เหนือแถบงาน) — จอเล็กปุ่มล่างยังกดได้"""
    from PySide6.QtGui import QGuiApplication
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    widget.setMaximumSize(area.width(), area.height() - 40)
    widget.resize(min(widget.width(), area.width()), min(widget.height(), area.height() - 40))
ZOOM_STEPS = (0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0)


def warning_lines(jobs: list[ReportJob]) -> list[str]:
    """คำเตือนก่อนออกใบ: rate ที่ใช้ไม่ได้/ไม่ครบ + ข้อมูลของใบที่ยังไม่ได้กรอก (แปลแล้ว)"""
    lines = []
    for job in jobs:
        prefix = (job.job_no or job.kind.capitalize()) + ": "
        if not job.rates:
            lines.append(prefix + tr("no usable flow result — this report cannot be made"))
        for text, values in job.warnings:
            lines.append(prefix + tr(text, **values))
        missing = [tr(text, **values) for text, values in job.missing()]
        if missing:
            lines.append(prefix + tr("not filled in: {items}", items=", ".join(missing)))
    return lines


class ReportActions:
    def __init__(self, parent: QWidget, settings, repository):
        self.parent, self.settings, self.repository = parent, settings, repository
        self._print_jobs: list = []
        self.last_saved: list[Path] = []        # ไฟล์ที่บันทึกล่าสุด (ใช้ในเทสต์/ข้อความ)

    # ------------------------------------------------------------ ทางเข้า
    def output(self, jobs: list[ReportJob], action: str, preview: bool) -> bool:
        jobs = [job for job in jobs if job.rates]
        if not jobs:
            QMessageBox.warning(self.parent, tr("Report"), tr("None of the selected jobs has a usable flow result."))
            return False
        lang = service.language(self.settings)
        if preview:
            dialog = ReportPreviewDialog(self.parent, jobs, lang, self)
            dialog.exec()
            return True
        if not self.confirm_warnings(jobs):
            return False
        return self.save(jobs, lang, ask_location=False) if action == "save" else self.print(jobs, lang)

    def confirm_warnings(self, jobs: list[ReportJob]) -> bool:
        lines = warning_lines(jobs)
        if not lines:
            return True
        box = QMessageBox(QMessageBox.Icon.Warning, tr("Report"),
                          tr("Check before making the report:") + "\n\n• " + "\n• ".join(lines[:12]),
                          QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel, self.parent)
        box.button(QMessageBox.StandardButton.Ok).setText(tr("Make the report anyway"))
        return box.exec() == QMessageBox.StandardButton.Ok

    # ------------------------------------------------------------ สร้าง PDF
    def render(self, jobs_sets: list[list[ReportJob]], lang: str) -> list[bytes] | None:
        """PDF ของแต่ละชุดใบ (รอผลโดยวน event loop — จอ/การทดสอบยังทำงาน) · ผิดพลาด -> None"""
        from services.report import render as rendering
        progress = QProgressDialog(tr("Building the report…"), "", 0, len(jobs_sets), self.parent)
        progress.setCancelButton(None)
        progress.setMinimumDuration(400)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        out = []
        try:
            for index, jobs in enumerate(jobs_sets):
                progress.setValue(index)
                out.append(rendering.render_pdf_sync(layout.html_document(jobs, lang)))
            progress.setValue(len(jobs_sets))
        except Exception as exc:
            log.exception("report rendering failed")
            QMessageBox.critical(self.parent, tr("Report"), tr("Could not build the PDF: {error}", error=exc))
            return None
        finally:
            progress.close()
        return out

    # ------------------------------------------------------------ บันทึก
    def save(self, jobs: list[ReportJob], lang: str, ask_location: bool, data: bytes | None = None) -> bool:
        """data = PDF ที่สร้างไว้แล้วของทุกใบรวมกัน (จากหน้าตัวอย่าง) — ใช้เมื่อบันทึกเป็นไฟล์เดียว"""
        folder = service.default_folder(self.settings)
        merged = len(jobs) > 1 and self.settings.report.merge_files
        if len(jobs) == 1 or merged:
            name = jobs[0].file_name(lang) if len(jobs) == 1 else \
                f"DeltaM_Reports_{jobs[0].date_iso[:10] or 'jobs'}_{'EN' if lang == 'en' else 'TH'}.pdf"
            if ask_location:
                path, _ = QFileDialog.getSaveFileName(self.parent, tr("Save PDF"), str(folder / name), "PDF (*.pdf)")
                if not path:
                    return False
                targets = [Path(path)]
            else:
                targets = self._resolve_existing([folder / name])
                if targets is None:
                    return False
            pdfs = [data] if data is not None else self.render([jobs], lang)
        else:
            if ask_location:
                chosen = QFileDialog.getExistingDirectory(self.parent, tr("Folder for the PDF files"), str(folder))
                if not chosen:
                    return False
                folder = Path(chosen)
            targets = self._resolve_existing([folder / job.file_name(lang) for job in jobs])
            if targets is None:
                return False
            pdfs = self.render([[job] for job in jobs], lang)
        if pdfs is None:
            return False
        saved = []
        for target, pdf in zip(targets, pdfs):
            path = self._write(pdf, target)
            if path is None:
                break
            saved.append(path)
        self.last_saved = saved
        if saved:
            self._report_saved(saved)
        return len(saved) == len(targets)

    def _resolve_existing(self, targets: list[Path]) -> list[Path] | None:
        """มีไฟล์ชื่อเดิมอยู่แล้ว: ถามครั้งเดียว — เขียนทับ / เก็บทั้งคู่ (เติม (2)) / ยกเลิก"""
        from services.report.render import unique_path
        existing = [t for t in targets if t.exists()]
        if not existing:
            return targets
        box = QMessageBox(QMessageBox.Icon.Question, tr("Save PDF"),
                          tr("{n} file(s) already exist, e.g. {name}", n=len(existing), name=existing[0].name),
                          QMessageBox.StandardButton.NoButton, self.parent)
        replace = box.addButton(tr("Replace"), QMessageBox.ButtonRole.AcceptRole)
        keep = box.addButton(tr("Keep both"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is replace:
            return targets
        if box.clickedButton() is keep:
            return [unique_path(t) for t in targets]
        return None

    def _write(self, data: bytes, target: Path) -> Path | None:
        """บันทึก — ไฟล์เปิดค้างในโปรแกรมอื่น: ถาม ลองใหม่ / บันทึกเป็นชื่ออื่น / ยกเลิก"""
        from services.report.render import FileLockedError, save_pdf
        while True:
            try:
                return save_pdf(data, target)
            except FileLockedError:
                box = QMessageBox(QMessageBox.Icon.Warning, tr("Save PDF"),
                                  tr("{name} is open in another program (for example a PDF viewer), so it cannot be "
                                     "replaced. Close it and try again, or save under another name.", name=target.name),
                                  QMessageBox.StandardButton.NoButton, self.parent)
                retry = box.addButton(tr("Try again"), QMessageBox.ButtonRole.AcceptRole)
                other = box.addButton(tr("Save as…"), QMessageBox.ButtonRole.ActionRole)
                box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() is retry:
                    continue
                if box.clickedButton() is other:
                    path, _ = QFileDialog.getSaveFileName(self.parent, tr("Save PDF"), str(target), "PDF (*.pdf)")
                    if not path:
                        return None
                    target = Path(path)
                    continue
                return None
            except OSError as exc:
                QMessageBox.critical(self.parent, tr("Save PDF"), tr("Could not save {name}: {error}", name=target.name, error=exc))
                return None

    def _report_saved(self, saved: list[Path]) -> None:
        log.info(tr("Report saved: {path}", path=", ".join(str(p) for p in saved)))
        box = QMessageBox(QMessageBox.Icon.Information, tr("Save PDF"),
                          tr("Saved {n} PDF file(s) to {folder}", n=len(saved), folder=saved[0].parent),
                          QMessageBox.StandardButton.Ok, self.parent)
        open_file = box.addButton(tr("Open PDF"), QMessageBox.ButtonRole.ActionRole) if len(saved) == 1 else None
        open_folder = box.addButton(tr("Open folder"), QMessageBox.ButtonRole.ActionRole)
        box.exec()
        if open_file is not None and box.clickedButton() is open_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(saved[0])))
        elif box.clickedButton() is open_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(saved[0].parent)))

    # ------------------------------------------------------------ พิมพ์
    def print(self, jobs: list[ReportJob], lang: str, data: bytes | None = None) -> bool:
        from services.report.printing import PrintJob, printer_for
        pages = sum(layout.page_count(job) for job in jobs)
        title = " · ".join(job.job_no or job.kind for job in jobs[:3])
        printer = printer_for(self.parent, self.settings.report.ask_printer, pages, f"DeltaM {title}")
        if printer is None:
            if not self.settings.report.ask_printer:
                QMessageBox.warning(self.parent, tr("Print"), tr("No default printer is set in Windows."))
            return False
        if data is None:
            pdfs = self.render([jobs], lang)
            if pdfs is None:
                return False
            data = pdfs[0]
        job = PrintJob(data, printer, self.parent)
        self._print_jobs.append((job, printer))
        job.finished_ok.connect(lambda n: log.info(tr("Report sent to the printer ({n} pages)", n=n)))
        job.failed.connect(lambda error: QMessageBox.critical(self.parent, tr("Print"),
                                                              tr("Printing failed: {error}", error=error)))
        job.finished.connect(lambda j=job: self._forget(j))
        job.start()
        return True

    def _forget(self, job) -> None:
        self._print_jobs = [(j, p) for j, p in self._print_jobs if j is not job]
        job.deleteLater()

    def wait_printing(self, timeout_ms: int = 60000) -> None:
        for job, _ in list(self._print_jobs):
            job.wait(timeout_ms)


class ReportPreviewDialog(QDialog):
    """ตัวอย่างใบรายงาน = PDF ที่จะบันทึก/พิมพ์จริง (ไม่ใช่ HTML) เลื่อน/ซูมได้ สลับภาษาได้"""

    def __init__(self, parent: QWidget | None, jobs: list[ReportJob], lang: str, actions: ReportActions):
        super().__init__(parent)
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        self.jobs, self.lang, self.actions = list(jobs), lang, actions
        self.data: bytes | None = None
        self.checks: list = []
        self._buffer: QBuffer | None = None
        self.setWindowTitle(tr("Report preview"))
        self.setModal(True)
        self.resize(980, 980)
        fit_to_screen(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        bar = QHBoxLayout()
        self.lang_box = QComboBox()
        for value, text in LANGS:
            self.lang_box.addItem(text, value)
        self.lang_box.setCurrentIndex(max(0, self.lang_box.findData(lang)))
        bar.addWidget(QLabel(tr("Report language")))
        bar.addWidget(self.lang_box)
        self.job_box = QComboBox()
        for job in self.jobs:
            self.job_box.addItem(job.label)
        self.job_box.setVisible(len(self.jobs) > 1)
        bar.addWidget(self.job_box, 1)
        if len(self.jobs) == 1:
            bar.addStretch(1)
        self.btn_out = QPushButton("−")
        self.btn_in = QPushButton("+")
        self.btn_fit = QPushButton(tr("Fit width"))
        for button in (self.btn_out, self.btn_in):
            button.setFixedWidth(34)
        self.zoom_label = QLabel("")
        bar.addWidget(self.btn_out)
        bar.addWidget(self.zoom_label)
        bar.addWidget(self.btn_in)
        bar.addWidget(self.btn_fit)
        # รูปแบบกราฟ flow รายช่วง (ค่าเริ่มต้นจากหน้าตั้งค่า -> ใบรายงาน) — เปลี่ยนที่นี่มีผลกับใบนี้เท่านั้น
        self.btn_graph = QToolButton()
        self.btn_graph.setText(tr("Graph"))
        self.btn_graph.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.btn_graph)
        styles = QActionGroup(menu)
        options = self.jobs[0].options
        # ทุกเส้นติ๊กเปิด/ปิดอิสระ (ผู้ใช้ 2026-11-20) — เส้น flow รายช่วงเลือกรูปแบบขั้นบันได/จุด ได้เมื่อเปิดอยู่
        self.act_intervals = menu.addAction(tr("Flow of each interval"))
        self.act_intervals.setCheckable(True)
        self.act_intervals.setChecked(getattr(options, "chart_intervals", True))
        self.act_step = menu.addAction("    " + tr("Steps"))
        self.act_points = menu.addAction("    " + tr("Points joined by a line"))
        for action, value in ((self.act_step, "step"), (self.act_points, "points")):
            action.setCheckable(True)
            action.setChecked(options.chart_style == value)
            styles.addAction(action)
        menu.addSeparator()
        self.act_mean = menu.addAction(tr("Mean line"))
        self.act_moving = menu.addAction(tr("Running mean line"))
        self.act_mean.setCheckable(True)
        self.act_mean.setChecked(options.chart_mean)
        self.act_moving.setCheckable(True)
        self.act_moving.setChecked(options.chart_moving)
        for action in (self.act_intervals, self.act_step, self.act_points, self.act_mean, self.act_moving):
            action.triggered.connect(self._on_graph_options)
        menu.aboutToShow.connect(self._sync_graph_menu)
        self.btn_graph.setMenu(menu)
        bar.addWidget(self.btn_graph)
        self.btn_info = QPushButton(tr("Report data…"))
        bar.addWidget(self.btn_info)
        root.addLayout(bar)

        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("background: #FEF3C7; color: #78350F; padding: 6px 10px; border-radius: 4px;")
        root.addWidget(self.notice)

        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        # ซูมเริ่มต้นจากหน้าตั้งค่า (ผู้ใช้ 2026-11-20: 67 % — เดิมพอดีความกว้าง ใกล้เกินไป) · 0 = พอดีความกว้าง
        zoom = int(getattr(getattr(actions.settings, "report", None), "preview_zoom_pct", 67) or 0)
        if zoom > 0:
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.view.setZoomFactor(max(0.25, min(4.0, zoom / 100.0)))
        else:
            self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.view.setPageSpacing(14)
        root.addWidget(self.view, 1)
        self.status = QLabel("")
        self.status.setStyleSheet("color: #6B7280;")

        buttons = QHBoxLayout()
        buttons.addWidget(self.status, 1)
        self.btn_close = QPushButton(tr("Close"))
        self.btn_print = QPushButton(tr("Print"))
        self.btn_save = QPushButton(tr("Save PDF"))
        self.btn_save.setProperty("variant", "primary")
        for button in (self.btn_close, self.btn_print, self.btn_save):
            buttons.addWidget(button)
        root.addLayout(buttons)

        self.lang_box.currentIndexChanged.connect(self._on_lang)
        self.job_box.currentIndexChanged.connect(self._jump_to_job)
        self.btn_out.clicked.connect(lambda: self._zoom(-1))
        self.btn_in.clicked.connect(lambda: self._zoom(1))
        self.btn_fit.clicked.connect(self._fit)
        self.btn_info.clicked.connect(self._edit_info)
        self.btn_close.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)
        self.btn_print.clicked.connect(self._print)
        self._show_warnings()
        self._update_zoom_label()
        QTimer.singleShot(0, self.refresh)

    # ------------------------------------------------------------ สร้าง/แสดง
    def refresh(self) -> None:
        from services.report.render import shared_renderer
        self._set_busy(True)
        shared_renderer().render(layout.html_document(self.jobs, self.lang), self._on_rendered)

    def _on_rendered(self, data, error, checks) -> None:
        from services.report.render import layout_problems
        self._set_busy(False)
        if data is None:
            self.status.setText(tr("Could not build the PDF: {error}", error=error))
            return
        self.data, self.checks = data, checks
        self._buffer = QBuffer(self)
        self._buffer.setData(QByteArray(data))
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.document.load(self._buffer)
        problems = layout_problems(checks)
        shrunk = sum(1 for item in checks if item.get("fit"))
        text = tr("{pages} pages", pages=self.document.pageCount())
        if shrunk:
            text += " · " + tr("{n} page(s) set tighter to fit long data", n=shrunk)
        if problems:
            text += " · " + tr("some content does not fit on the page — shorten the long entries")
            log.warning("report layout: %s", problems)
        self.status.setText(text)

    def _set_busy(self, busy: bool) -> None:
        for button in (self.btn_save, self.btn_print, self.btn_info, self.lang_box, self.btn_graph):
            button.setEnabled(not busy)
        if busy:
            self.status.setText(tr("Building the report…"))

    def _show_warnings(self) -> None:
        lines = warning_lines(self.jobs)
        self.notice.setText("\n".join("• " + line for line in lines[:8]))
        self.notice.setVisible(bool(lines))

    def _sync_graph_menu(self) -> None:
        on = self.act_intervals.isChecked()
        self.act_step.setEnabled(on)
        self.act_points.setEnabled(on)

    def _on_graph_options(self) -> None:
        self._sync_graph_menu()
        for job in self.jobs:
            job.options.chart_intervals = self.act_intervals.isChecked()
            job.options.chart_style = "points" if self.act_points.isChecked() else "step"
            job.options.chart_mean = self.act_mean.isChecked()
            job.options.chart_moving = self.act_moving.isChecked()
        self.refresh()

    def _on_lang(self) -> None:
        self.lang = self.lang_box.currentData()
        self.refresh()

    def _jump_to_job(self, index: int) -> None:
        page = sum(layout.page_count(job) for job in self.jobs[:max(0, index)])
        self.view.pageNavigator().jump(page, QPointF(), self.view.zoomFactor())

    def _zoom(self, direction: int) -> None:
        from PySide6.QtPdfWidgets import QPdfView
        current = self.view.zoomFactor()
        steps = [z for z in ZOOM_STEPS if (z > current + 1e-3 if direction > 0 else z < current - 1e-3)]
        if not steps:
            return
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(steps[0] if direction > 0 else steps[-1])
        self._update_zoom_label()

    def _fit(self) -> None:
        from PySide6.QtPdfWidgets import QPdfView
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._update_zoom_label()

    def _update_zoom_label(self) -> None:
        from PySide6.QtPdfWidgets import QPdfView
        fit = self.view.zoomMode() == QPdfView.ZoomMode.FitToWidth
        self.zoom_label.setText(tr("Fit") if fit else f"{self.view.zoomFactor() * 100:.0f} %")

    def _current_job_index(self) -> int:
        return max(0, self.job_box.currentIndex()) if len(self.jobs) > 1 else 0

    def _edit_info(self) -> None:
        from ui.dialogs.report_info import ReportInfoDialog
        index = self._current_job_index()
        dialog = ReportInfoDialog(self, self.jobs[index])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        service.save_info(self.actions.repository, self.jobs[index], dialog.result_info(), dialog.device_values())
        self._show_warnings()
        self.refresh()

    # ------------------------------------------------------------ บันทึก/พิมพ์
    def _save(self) -> None:
        merged = len(self.jobs) == 1 or self.actions.settings.report.merge_files
        self.actions.save(self.jobs, self.lang, ask_location=True, data=self.data if merged else None)

    def _print(self) -> None:
        if self.actions.print(self.jobs, self.lang, data=self.data):
            self.status.setText(tr("Sent to the printer — printing continues in the background"))



def offer_after_test(parent: QWidget, settings, repository, job_id: str) -> str:
    """หลังเก็บผลขั้นสุดท้ายของแผน: ถาม บันทึก PDF · พิมพ์ · ข้อมูลใบรายงาน · ข้าม — คืน "save" | "print" | "skip" | "none"

    ตั้งค่า "แสดงตัวอย่างหลังทดสอบ" เปิด = เปิดหน้าต่างตัวอย่าง (ปุ่มที่กดเป็นสิ่งที่ทำต่อจากตัวอย่าง)
    """
    from ui.dialogs.report_info import ReportInfoDialog
    job = service.job_for_plan(repository, job_id, settings)
    if job is None or not job.rates:
        return "none"
    while True:
        lines = warning_lines([job])
        text = tr("All steps are saved. Make the {kind} report for {job}?",
                  kind=tr(job.kind.capitalize()), job=job.job_no or job.label)
        if lines:
            text += "\n\n• " + "\n• ".join(lines[:8])
        box = QMessageBox(QMessageBox.Icon.Question, tr("Report"), text, QMessageBox.StandardButton.NoButton, parent)
        save = box.addButton(tr("Save PDF"), QMessageBox.ButtonRole.AcceptRole)
        printing = box.addButton(tr("Print"), QMessageBox.ButtonRole.AcceptRole)
        info = box.addButton(tr("Report data…"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr("Skip"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is info:
            dialog = ReportInfoDialog(parent, job)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                service.save_info(repository, job, dialog.result_info(), dialog.device_values())
            continue
        if clicked in (save, printing):
            action = "save" if clicked is save else "print"
            actions = ReportActions(parent, settings, repository)
            parent._report_actions = actions            # ให้มีชีวิตอยู่ระหว่างพิมพ์เบื้องหลัง
            actions.output([job], action, preview=settings.report.preview_after_test)
            return action
        return "skip"
