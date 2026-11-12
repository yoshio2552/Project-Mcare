"""WindowTuner: ปรับสัดส่วนหน้าต่าง/คาบ จากข้อมูลย้อนหลัง ใน thread แยก (ไม่ให้หน้าจอค้าง)

เรียกอัตโนมัติหลัง "เก็บผล" การทดสอบแบบจับรอบปั๊ม (เฉพาะรุ่น + ชุดสาย + rate นั้น)
และจากปุ่มในหน้าประวัติ (ทุก rate ของรุ่นนั้น)
ถ้าเริ่มการทดสอบใหม่ระหว่างคำนวณ จะถูกยกเลิกทันที (ไม่แย่งเวลาประมวลผลกับการอ่านตราชั่ง)
งานอ่านฐานข้อมูลทำใน thread หลัก — thread แยกทำแค่การคำนวณ (core.tuning ไม่มี Qt)
"""
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal

from core.tuning import tune

log = logging.getLogger("deltam.tuning")


class WindowTuner(QObject):
    finished = Signal(object, object)       # (brand, model, iv_set, pump_type), list[TuningResult]
    progress = Signal(float)                # 0..1

    def __init__(self, repository, parent: QObject | None = None):
        super().__init__(parent)
        self._repository = repository
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, brand: str, model: str, iv_set: str, rate: float | None = None,
              chains: int = 2, current_fraction: tuple[float, float] | float = (0.4, 0.4),
              pump_type: str = "infusion") -> bool:
        """เริ่มปรับ (คืน False ถ้าไม่มีข้อมูลพอ หรือกำลังทำงานอยู่)"""
        if self.busy:
            return False
        datasets = self._repository.tuning_datasets(brand, model, iv_set, rate, pump_type=pump_type)
        if not datasets:
            return False
        self._stop.clear()
        key = (brand, model, iv_set, pump_type)
        self._thread = threading.Thread(target=self._run, args=(key, datasets, chains, current_fraction),
                                        name="window-tuner", daemon=True)
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._stop.set()

    def wait(self, seconds: float = 5.0) -> None:
        if self._thread is not None:
            self._thread.join(seconds)

    def _run(self, key, datasets, chains, current_fraction) -> None:
        results = []
        total, done = len(datasets), 0
        try:
            for rate, data in sorted(datasets.items()):
                results.append(tune(data, rate, current_fraction, chains, should_stop=self._stop.is_set,
                                    progress=lambda f, d=done: self.progress.emit((d + f) / total)))
                done += 1
        except InterruptedError:
            log.info("Window tuning cancelled")
            return
        except Exception:
            log.exception("Window tuning failed")
            return
        self.finished.emit(key, results)
