"""AcquisitionWorker: วนอ่านตราชั่ง -> ป้อน engine -> ส่งผลให้ UI (ทำงานใน thread แยก)

เป็นจุดเดียวที่เชื่อม hardware กับ core เข้ากับ Qt
engine คืออะไรก็ได้ที่มี process(sample) -> EngineResult (FlowEngine หรือ BaselineEngine)
"""
from __future__ import annotations

import logging
import threading
import time

from PySide6.QtCore import QObject, Signal, Slot

from config.i18n import tr
from core.models import Stage
from hardware.base import BalanceSource
from services.recorder import RawRecorder

log = logging.getLogger("deltam.acquisition")

NO_DATA_WARNING_S = 3.0


class AcquisitionWorker(QObject):
    result = Signal(object)         # EngineResult
    finished = Signal(str)          # completed | stopped | error

    def __init__(self, source: BalanceSource, engine, recorder: RawRecorder | None = None):
        super().__init__()
        self._source = source
        self._engine = engine
        self._recorder = recorder
        self._stop = threading.Event()
        self.done = threading.Event()   # ตั้งเมื่อ loop จบและปิดพอร์ต/ไฟล์แล้ว

    def request_stop(self) -> None:
        """เรียกได้จากทุก thread"""
        self._stop.set()

    @Slot()
    def run(self) -> None:
        reason = "stopped"
        try:
            self._source.open()
            self._opened_at = time.perf_counter()
            log.info(tr("Connected to {source}", source=self._source.description))
            last_data = time.monotonic()
            warned = False
            while not self._stop.is_set():
                sample = self._source.read()
                if sample is None:
                    if not warned and time.monotonic() - last_data > NO_DATA_WARNING_S:
                        log.warning(tr("No data from the balance for {s:.0f} s — check the cable and continuous-output mode", s=NO_DATA_WARNING_S))
                        warned = True
                    continue
                if warned:
                    log.info(tr("Balance data resumed"))
                last_data, warned = time.monotonic(), False

                result = self._engine.process(sample)
                if self._recorder is not None:
                    self._recorder.write(result.stage is Stage.PRERUN, result.t, result.weight)
                self.result.emit(result)
                if result.finished:
                    reason = "completed"
                    break
        except Exception as exc:    # ขอบเขตของ thread: ต้องไม่ปล่อย exception หลุด
            reason = "error"
            log.error(tr("Reading failed: {error} — check the connection in Settings", error=exc))
        finally:
            try:
                self._source.close()
            except Exception as exc:
                log.warning(tr("Source did not close cleanly: {error}", error=exc))
            self._log_diagnostics()
            if self._recorder is not None:
                self._recorder.close()
            self.done.set()
            self.finished.emit(reason)

    def _log_diagnostics(self) -> None:
        """สรุปคุณภาพการอ่านของแหล่งข้อมูล (ถ้ามี) — บอกผู้ใช้ตรงๆ ว่ามีจุดที่ถูกทิ้ง/เวลาอาจคลาดไหม"""
        d = getattr(self._source, "diagnostics", None)
        if d is None:
            return
        text = tr("Balance reading: {ok} points, {partial} incomplete lines, {rejected} rejected lines, "
                  "{timeouts} no answer, {queued} late timestamps, longest queue {backlog}",
                  ok=d.samples, partial=d.partial, rejected=d.rejected, timeouts=d.timeouts,
                  queued=d.queued_lines, backlog=d.max_backlog)
        (log.warning if d.problems() else log.info)(text)
        samples = getattr(d, "rejected_samples", None)
        if samples:
            # ของจริงที่ตราชั่งส่งมา (ไบต์ดิบ) + ช่วงเวลาที่เกิด — ใช้แยกว่าเป็นท่อนบรรทัด/รหัสผิดพลาด/สัญญาณรบกวน
            times = getattr(d, "rejected_times", [])
            when = ""
            if times:
                start = getattr(self, "_opened_at", times[0])
                when = tr(" · from {a:.1f} s to {b:.1f} s after connecting", a=times[0] - start, b=times[-1] - start)
            log.warning(tr("Rejected balance lines, examples: {lines}", lines=" | ".join(samples)) + when)
        settings = getattr(self._source, "_settings", None)
        wait = getattr(settings, "response_timeout_s", None)
        if wait is not None and getattr(self._source, "mode", "") == "poll" and d.latency_max_s > wait:
            # ตราชั่งตอบช้ากว่าเวลารอที่ตั้ง (data/settings.json ของผู้ใช้ 2026-11-20 = 0.1 s แต่ GF-300 ตอบ ~0.19 s)
            log.warning(tr("The balance answered in up to {lat:.2f} s but Settings wait only {wait:.2f} s for a full "
                           "answer — set 'Wait for a full answer up to' to at least {need:.1f} s",
                           lat=d.latency_max_s, wait=wait, need=max(0.5, d.latency_max_s * 2)))
        if getattr(d, "stray_bytes", 0):
            log.info(tr("Bytes left in the port before asking (discarded): {n}", n=d.stray_bytes))
