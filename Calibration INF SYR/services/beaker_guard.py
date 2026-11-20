"""BeakerGuard: ระบบความปลอดภัยของบีกเกอร์รับน้ำ (ผู้ใช้ 2026-11-20) — ตัวกลางระหว่างน้ำหนักสดกับเสียง/popup

ข้อมูลเข้า (จาก SessionController):
    live_reading      น้ำหนักตอนว่าง (BalanceMonitor ~4 ครั้ง/วินาที) — รวมช่วงรอเก็บผล/หลังจบ
    results_ready     น้ำหนักระหว่างทดสอบ (EngineResult.weight)
    balance_status    เชื่อมตราชั่งได้ครั้งแรก -> ขอให้ตั้งบีกเกอร์ (RE-ZERO + วางบีกเกอร์) ถ้ายังไม่ได้ตั้ง
    session_started / session_finished / state_changed

สิ่งที่ส่งออก (หน้าจอรับไปแสดง — ไม่มี widget ในไฟล์นี้):
    setup_requested(str)          เปิดหน้าต่างตั้งบีกเกอร์ ("start" | "removed" | "manual")
    alert_changed(object)         Alert ปัจจุบัน (None = ไม่มี) -> popup ใหญ่ (ui/widgets/alert_overlay.py)
    status_changed(object)        BeakerStatus -> แถบระดับน้ำบนการ์ดตราชั่ง

ลำดับความสำคัญของการเตือน (แสดงทีละอัน อันสำคัญสุด):
    overflow  ≥ alarm_pct ระหว่าง/หลังทดสอบ — เสียง "alarm" ซ้ำทุก alarm_every_s จนกว่าจะกดรับทราบ หรือเอาน้ำออก
    next      rate ถัดไปคำนวณแล้วจะล้น — เสียง "alarm" ซ้ำจนกว่าจะกดรับทราบ/เอาน้ำออก
    warn      ≥ warn_pct ใกล้เต็ม — เสียง "warn" ทุก WARN_EVERY_S จนกว่าจะกดรับทราบ (ทดสอบเดินต่อ)
    remind    rate จบแล้วแต่ปั๊มยังเดิน — เสียง "remind" นุ่มๆ ทุก remind_every_s จนกว่าปั๊มหยุด/กดรับทราบ
    zero      ยกบีกเกอร์ออกแล้ว — บอกให้กด RE-ZERO แล้ววางกลับ (ไม่มีเสียงซ้ำ)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

from config.i18n import tr
from core.beaker import EMPTY_PAN_G, Beaker, PumpRunningDetector, level, minutes_to, predict
from services import sounds

log = logging.getLogger("deltam.safety")

WARN_EVERY_S = 12.0
CHECK_EVERY_S = 0.25        # ตรวจระดับไม่ถี่กว่านี้ (ข้อมูลระหว่างทดสอบมา 5–10 ครั้ง/วินาที)
ZERO_STABLE_S = 1.5
PRIORITY = ("overflow", "next", "warn", "remind", "zero")


@dataclass
class Alert:
    kind: str               # overflow | next | warn | remind | zero
    severity: str           # danger | warning | info
    title: str
    message: str
    fill_pct: float | None = None
    water_ml: float | None = None
    capacity_ml: float | None = None
    warn_pct: float = 85.0
    alarm_pct: float = 95.0
    ack_text: str = ""      # ข้อความปุ่มรับทราบ


@dataclass
class BeakerStatus:
    known: bool
    weight_g: float | None
    water_ml: float | None
    capacity_ml: float
    fill_pct: float | None
    level: str              # ok | warn | alarm | removed | unknown
    minutes_left: float | None = None   # ระหว่างทดสอบ: เวลาก่อนถึงเกณฑ์จะล้น ที่ rate ปัจจุบัน


class BeakerGuard(QObject):
    setup_requested = Signal(str)
    alert_changed = Signal(object)
    status_changed = Signal(object)

    def __init__(self, settings, controller=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.controller = controller
        s = settings.safety
        self.beaker = Beaker(capacity_ml=s.beaker_capacity_ml, empty_g=s.beaker_mass_g, known=False)
        self.weight: float | None = None
        self._last_check = 0.0
        self._active: dict[str, Alert] = {}         # kind -> Alert ที่ยังไม่ได้กดรับทราบ
        self._acked: set[str] = set()               # kind ที่ผู้ใช้กดรับทราบแล้ว (เงียบจนกว่าสถานการณ์เปลี่ยน)
        self._shown: Alert | None = None
        self._shown_text = ""
        self._running = False
        self._rate = 0.0                            # rate ของการทดสอบที่กำลังเดิน/เพิ่งจบ (ml/h)
        self._finished_at: float | None = None      # เวลาที่ rate ล่าสุดจบ (เตือนหยุดปั๊ม)
        self._removed = False
        self._zero_since: float | None = None
        self._setup_asked = False
        self.detector = PumpRunningDetector()
        self._sound_timer = QTimer(self)
        self._sound_timer.timeout.connect(self._repeat_sound)
        if controller is not None:
            controller.live_reading.connect(lambda w, _stable=None: self.on_weight(w))
            controller.results_ready.connect(self._on_results)
            controller.balance_status.connect(self._on_balance_status)
            controller.session_started.connect(self._on_session_started)
            controller.session_finished.connect(self._on_session_finished)
            controller.state_changed.connect(self._on_state)

    # ------------------------------------------------------------ ค่าตั้ง
    @property
    def enabled(self) -> bool:
        return bool(self.settings.safety.enabled)

    def set_beaker(self, capacity_ml: float, empty_g: float) -> None:
        """จากหน้าต่างตั้งบีกเกอร์ (RE-ZERO แล้ว + วางบีกเกอร์แล้ว)"""
        self.beaker = Beaker(capacity_ml=max(1.0, capacity_ml), empty_g=max(0.0, empty_g), known=True)
        self._removed = False
        self._acked.clear()
        self._active.pop("zero", None)
        log.info(tr("Beaker set: {cap:g} ml, empty {mass:.1f} g — water now {water:.1f} ml",
                    cap=self.beaker.capacity_ml, mass=self.beaker.empty_g,
                    water=self.beaker.water_ml(self.weight) if self.weight is not None else 0.0))
        self._evaluate(force=True)

    def forget_beaker(self) -> None:
        self.beaker.known = False
        self._active.clear()
        self._publish()

    # ------------------------------------------------------------ ข้อมูลเข้า
    def _on_balance_status(self, connected: bool, _text: str) -> None:
        if connected and not self._setup_asked and self.enabled and self.settings.safety.ask_on_start \
                and not self.beaker.known:
            self._setup_asked = True
            self.setup_requested.emit("start")

    def _on_results(self, results: list) -> None:
        if results:
            self.on_weight(results[-1].weight)

    def _on_session_started(self, config) -> None:
        self._running = True
        self._rate = float(getattr(config, "target_flow", 0.0) or 0.0)
        self._finished_at = None
        for kind in ("remind", "next"):
            self._active.pop(kind, None)
            self._acked.discard(kind)
        self._publish()

    def _on_state(self, state) -> None:
        running = getattr(self.controller, "is_running", False)
        if self._running and not running:
            # rate จบ (ครบเวลา/กดหยุด) — ปั๊มของจริงยังเดินจนกว่าคนจะมาหยุด
            self._running = False
            self._finished_at = time.monotonic()
            self.detector.reset()
            self._acked.discard("remind")
        self._running = running

    def _on_session_finished(self, _summary, _kept: bool) -> None:
        self._check_next_rate()

    def on_weight(self, weight: float) -> None:
        """น้ำหนักล่าสุด (g) จากตราชั่ง — ตอนว่างหรือระหว่างทดสอบ"""
        now = time.monotonic()
        self.weight = float(weight)
        self.detector.add(now, self.weight)
        if now - self._last_check < CHECK_EVERY_S:
            return
        self._last_check = now
        self._evaluate()

    # ------------------------------------------------------------ ตัดสิน
    def _evaluate(self, force: bool = False) -> None:
        if not self.enabled or self.weight is None:
            self._publish()
            return
        s, w, beaker = self.settings.safety, self.weight, self.beaker
        if not beaker.known:
            self._publish()
            return
        if beaker.removed(w):
            # ยกบีกเกอร์ออก = เอาน้ำออก: เงียบทุกเสียงเตือนระดับน้ำ แล้วรอ RE-ZERO + วางกลับ
            if not self._removed:
                self._removed = True
                self._zero_since = None
                for kind in ("overflow", "warn", "next"):
                    self._active.pop(kind, None)
                    self._acked.discard(kind)
                self._active["zero"] = Alert(
                    "zero", "info", tr("Beaker removed"),
                    tr("Press RE-ZERO on the balance with the pan empty, then put the beaker back."),
                    ack_text=tr("Got it"))
            if abs(w) <= EMPTY_PAN_G * 0.4:
                self._zero_since = self._zero_since or time.monotonic()
                if time.monotonic() - self._zero_since >= ZERO_STABLE_S and "zero" in self._active:
                    self._active["zero"].message = tr("Zero OK — now put the beaker back on the pan.")
            self._publish()
            return
        if self._removed:                       # วางบีกเกอร์กลับแล้ว
            self._removed = False
            self._active.pop("zero", None)
            log.info(tr("Beaker back on the balance — water {ml:.1f} ml", ml=beaker.water_ml(w)))
            self._check_next_rate()

        fill = beaker.fill_pct(w)
        lvl = level(fill, s.warn_pct, s.alarm_pct)
        water, cap = beaker.water_ml(w), beaker.capacity_ml
        if lvl == "alarm":
            self._raise(Alert("overflow", "danger", tr("The beaker is about to overflow"),
                              tr("Water {ml:.0f} of {cap:g} ml ({pct:.0f} %). Stop the pump and empty the beaker. "
                                 "The test keeps running.", ml=water, cap=cap, pct=fill),
                              fill, water, cap, s.warn_pct, s.alarm_pct, tr("Silence")))
            self._active.pop("warn", None)
        else:
            self._clear("overflow")
            if lvl == "warn":
                left = minutes_to(beaker, w, self._current_rate(), s.alarm_pct)
                extra = tr(" About {min:.0f} min left at this rate.", min=left) if left is not None else ""
                self._raise(Alert("warn", "warning", tr("The beaker is nearly full"),
                                  tr("Water {ml:.0f} of {cap:g} ml ({pct:.0f} %).", ml=water, cap=cap, pct=fill)
                                  + extra + " " + tr("The test keeps running."),
                                  fill, water, cap, s.warn_pct, s.alarm_pct, tr("Got it")))
            else:
                self._clear("warn")
        self._check_remind()
        self._publish()

    def _current_rate(self) -> float:
        measured = self.detector.rate_ml_h()
        if measured is not None and measured > 0:
            return measured
        return self._rate

    def _check_remind(self) -> None:
        s = self.settings.safety
        if not s.remind_after_test or self._running or self._finished_at is None:
            self._clear("remind")
            return
        running = self.detector.running()
        if running is False:                    # ปั๊มหยุดแล้ว
            self._finished_at = None
            self._clear("remind")
            return
        if running and "remind" not in self._acked and "remind" not in self._active:
            self._raise(Alert("remind", "info", tr("The test has finished — stop the pump"),
                              tr("The pump is still delivering water into the beaker. Stop the pump "
                                 "(or start the next rate) to avoid an overflow."),
                              self.beaker.fill_pct(self.weight), self.beaker.water_ml(self.weight),
                              self.beaker.capacity_ml, s.warn_pct, s.alarm_pct, tr("Pump stopped")))

    def _check_next_rate(self) -> None:
        """หลังจบ rate / วางบีกเกอร์กลับ: rate ถัดไปของแผนจะล้นไหม"""
        prediction = self.next_prediction()
        if prediction is None or prediction.level != "alarm":
            self._clear("next")
            self._publish()
            return
        rate, minutes = self._next_step()
        self._raise(Alert("next", "danger", tr("The next rate will overflow the beaker"),
                          tr("{rate:g} ml/h for {min:g} min adds about {add:.0f} ml → {end:.0f} of {cap:g} ml "
                             "({pct:.0f} %). Empty the beaker and press RE-ZERO before starting.",
                             rate=rate, min=minutes, add=prediction.added_ml, end=prediction.end_ml,
                             cap=self.beaker.capacity_ml, pct=prediction.end_pct),
                          self.beaker.fill_pct(self.weight), prediction.now_ml, self.beaker.capacity_ml,
                          self.settings.safety.warn_pct, self.settings.safety.alarm_pct, tr("Silence")))
        self._publish()

    def _next_step(self) -> tuple[float, float]:
        controller = self.controller
        plan = getattr(controller, "plan", None)
        index = getattr(controller, "step_index", 0)
        if plan is None or index >= len(plan.steps):
            return 0.0, 0.0
        step = plan.steps[index]
        return float(step.target_flow), float(step.duration_min)

    def next_prediction(self, rate: float | None = None, minutes: float | None = None):
        if not self.enabled or not self.beaker.known or self.weight is None or self.beaker.removed(self.weight):
            return None
        if rate is None:
            rate, minutes = self._next_step()
        if not rate:
            return None
        s = self.settings.safety
        return predict(self.beaker, self.weight, rate, minutes or 0.0, s.allowance_min, s.warn_pct, s.alarm_pct)

    # ------------------------------------------------------------ ก่อนเริ่ม rate (หน้าทดสอบเรียก)
    def start_check(self, rate: float, minutes: float):
        """คืน Prediction ถ้าต้องถามผู้ใช้ก่อนเริ่ม (จะล้น) ไม่งั้น None"""
        if not self.settings.safety.check_before_start:
            return None
        prediction = self.next_prediction(rate, minutes)
        return prediction if prediction is not None and prediction.level == "alarm" else None

    # ------------------------------------------------------------ การเตือน
    def acknowledge(self, kind: str) -> None:
        """ผู้ใช้กดรับทราบ: เงียบเสียงของเรื่องนี้ (จนกว่าสถานการณ์เปลี่ยน เช่น เอาน้ำออกแล้วเต็มใหม่)"""
        self._acked.add(kind)
        self._active.pop(kind, None)
        if kind == "remind":
            self._finished_at = None
        self._publish()

    def _raise(self, alert: Alert) -> None:
        if alert.kind in self._acked:
            return
        fresh = alert.kind not in self._active
        self._active[alert.kind] = alert
        if fresh:
            log.warning(alert.title + " — " + alert.message)
            self._play(alert.kind)

    def _clear(self, kind: str) -> None:
        self._active.pop(kind, None)
        self._acked.discard(kind)

    def current(self) -> Alert | None:
        for kind in PRIORITY:
            if kind in self._active:
                return self._active[kind]
        return None

    def _publish(self) -> None:
        alert = self.current()
        kind = alert.kind if alert else None
        shown = self._shown.kind if self._shown else None
        if kind != shown:                       # เรื่องที่เตือนเปลี่ยน: เริ่มจังหวะเสียงใหม่
            self._restart_sound(alert)
        if alert is not self._shown or (alert is not None and self._shown_text != alert.message):
            self._shown = alert
            self._shown_text = alert.message if alert else ""
            self.alert_changed.emit(alert)
        self.status_changed.emit(self.status())

    def status(self) -> BeakerStatus:
        s, w, beaker = self.settings.safety, self.weight, self.beaker
        if not beaker.known or w is None:
            return BeakerStatus(False, w, None, beaker.capacity_ml, None, "unknown")
        if beaker.removed(w):
            return BeakerStatus(True, w, None, beaker.capacity_ml, None, "removed")
        fill = beaker.fill_pct(w)
        left = minutes_to(beaker, w, self._current_rate(), s.alarm_pct) if self._running else None
        return BeakerStatus(True, w, beaker.water_ml(w), beaker.capacity_ml, fill,
                            level(fill, s.warn_pct, s.alarm_pct), left)

    # ------------------------------------------------------------ เสียง
    def _interval_for(self, kind: str) -> float:
        s = self.settings.safety
        return {"overflow": s.alarm_every_s, "next": s.alarm_every_s, "warn": WARN_EVERY_S,
                "remind": s.remind_every_s}.get(kind, 0)

    def _restart_sound(self, alert: Alert | None) -> None:
        self._sound_timer.stop()
        if alert is None:
            return
        interval = self._interval_for(alert.kind)
        if interval > 0:
            self._sound_timer.start(int(max(1.0, interval) * 1000))

    def _repeat_sound(self) -> None:
        alert = self.current()
        if alert is None:
            self._sound_timer.stop()
            return
        self._play(alert.kind)

    @staticmethod
    def _play(kind: str) -> None:
        name = {"overflow": "alarm", "next": "alarm", "warn": "warn", "remind": "remind"}.get(kind)
        if name:
            sounds.play(name)
