"""ProcessTracker: แถบติดตามความคืบหน้า + ข้อความสถานะ — "อยู่ขั้นไหนของแผน ช่วงไหนของขั้นนั้น และต้องทำอะไรต่อ"

    ┌────────┬───────────────────────────────────────────────────────────────────────┐
    │ ขั้น    │ ● ช่วง 4/6 · รอรอบปั๊มรอบแรกให้ครบ               [เริ่มวัดเดี๋ยวนี้]   42 % │
    │ 1/3    │ ✓ เชื่อมต่อ ── ✓ ก่อนวัด ── ✓ เตรียม ── ④ รอบแรก ── ⑤ วัดจริง ── ⑥ สรุปผล   │
    │ 10 ml/h│ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬░░░░░░░░░░░░░░░░░░░░░░░░░░░ (progress)            │
    └────────┴───────────────────────────────────────────────────────────────────────┘

- ชื่อช่วงอยู่ข้างวงกลม (ไม่ใช่ใต้วง) แถบจึงเตี้ย เหลือที่ให้กราฟ
- ข้อความบรรทัดบน = ข้อความของช่วงปัจจุบัน หรือข้อความสถานะ/ปุ่มลัดที่หน้าทดสอบส่งมา (show_message)
  แทนแถบข้อความ (PhaseBanner) เดิมที่กินพื้นที่อีก 1 แถว
- ช่วงที่ข้ามไป (เช่น ไม่มี pre-run, วิธีจับตามเวลาไม่ต้องรอรอบแรก) เป็นวงประ "–"
- ช่วงปัจจุบันมีวงแสงเต้นเบาๆ ให้เห็นว่าระบบยังทำงาน
เปลี่ยนรายชื่อช่วงได้ด้วย start(phases) (เช่น self-check ใช้ชุดสั้นกว่า)
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QPushButton, QVBoxLayout, QWidget

from config.i18n import tr
from ui.theme import TONES, Color
from ui.widgets.common import label

PENDING, CURRENT, DONE, SKIPPED = range(4)


def _color(hex_color: str, alpha: int = 255) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


class PhaseStepper(QWidget):
    """วงกลมของแต่ละช่วง + ชื่อข้างวง เชื่อมด้วยเส้น (บรรทัดเดียว)"""
    RADIUS = 10

    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.phases: list[str] = []
        self.states: list[int] = []
        self.tone = Color.ACCENT
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def set_states(self, phases: list[str], states: list[int], tone: str, animate: bool) -> None:
        self.phases, self.states, self.tone = phases, states, tone
        if animate and not self._timer.isActive():
            self._timer.start()
        elif not animate:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.04) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        n = len(self.phases)
        if not n:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r, cy = self.RADIUS, self.height() / 2
        number_font = QFont(self.font())
        number_font.setPixelSize(11)
        number_font.setBold(True)
        name_font = QFont(self.font())
        name_font.setPixelSize(12)
        slot = (self.width() - 2 * r - 6) / n

        # ตำแหน่งวง + ความยาวชื่อ (ชื่อของช่วงปัจจุบันเป็นตัวหนา)
        nodes = []
        for i, (name, state) in enumerate(zip(self.phases, self.states)):
            name_font.setBold(state == CURRENT)
            width = QFontMetrics(name_font).horizontalAdvance(name)
            nodes.append((r + 4 + i * slot, width))

        # เส้นเชื่อม: จากท้ายชื่อของช่วงนี้ ถึงวงของช่วงถัดไป
        for i in range(n - 1):
            x0 = nodes[i][0] + r + 6 + nodes[i][1] + 8
            x1 = nodes[i + 1][0] - r - 6
            if x1 <= x0:
                continue
            passed = self.states[i + 1] in (DONE, CURRENT, SKIPPED)
            pen = QPen(_color(self.tone if passed else Color.BORDER), 2)
            if self.states[i + 1] == SKIPPED:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(x0, cy), QPointF(x1, cy))

        for i, ((x, width), name, state) in enumerate(zip(nodes, self.phases, self.states)):
            center = QPointF(x, cy)
            box = QRectF(x - r, cy - r, 2 * r, 2 * r)
            if state == CURRENT:
                glow = 0.5 - 0.5 * math.cos(self._pulse * 2 * math.pi)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(_color(self.tone, int(35 + 55 * glow)))
                p.drawEllipse(center, r + 3 + 3 * glow, r + 3 + 3 * glow)
                p.setBrush(_color(self.tone))
                p.drawEllipse(center, r, r)
                p.setPen(_color(Color.ON_ACCENT))
                p.setFont(number_font)
                p.drawText(box, Qt.AlignmentFlag.AlignCenter, str(i + 1))
            elif state == DONE:
                p.setPen(QPen(_color(self.tone), 1.6))
                p.setBrush(_color(self.tone, 40))
                p.drawEllipse(center, r, r)
                pen = QPen(_color(self.tone), 2.0)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.drawPolyline([QPointF(x - 4.5, cy + 0.5), QPointF(x - 1.2, cy + 3.8), QPointF(x + 4.5, cy - 3.2)])
            else:
                skipped = state == SKIPPED
                pen = QPen(_color(Color.TEXT_FAINT if skipped else Color.BORDER), 1.6)
                if skipped:
                    pen.setStyle(Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.setBrush(_color(Color.SURFACE_ALT))
                p.drawEllipse(center, r, r)
                p.setPen(_color(Color.TEXT_FAINT))
                p.setFont(number_font)
                p.drawText(box, Qt.AlignmentFlag.AlignCenter, "–" if skipped else str(i + 1))

            name_font.setBold(state == CURRENT)
            p.setFont(name_font)
            p.setPen(_color(self.tone if state == CURRENT else Color.TEXT if state == DONE else Color.TEXT_FAINT))
            p.drawText(QRectF(x + r + 6, 0, width + 4, self.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        p.end()


class ProcessTracker(QWidget):
    """การ์ดติดตาม: ขั้นของแผน (ซ้าย) + ข้อความ/ปุ่ม + ช่วงของขั้น + แถบความคืบหน้า (ขวา)

    มี show_message / clear_message / action_clicked แบบเดียวกับแถบข้อความเดิม
    """
    action_clicked = Signal()

    TEST_PHASES = ["Connect", "Pre-run", "Prepare", "First cycle", "Measure", "Review"]
    PHASE_DETAILS = {
        "Connect": "Connecting to the balance",
        "Pre-run": "Pre-run — not counted in the result",
        "Prepare": "Filling the calculation window",
        "First cycle": "Waiting for the first complete pump cycle",
        "Measure": "Measuring",
        "Review": "Choose whether to keep the result",
        "Self-check": "Self-check — pump stopped, do not touch the beaker",
        "Result": "Self-check result",
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("tracker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(14)

        # ---- ซ้าย: ขั้นของแผน
        left = QVBoxLayout()
        left.setSpacing(0)
        left.addWidget(label(tr("STEP"), "sectionTitle"))
        self._step = label("—", "trackerStep")
        self._step_info = label("", "hint")
        left.addWidget(self._step)
        left.addWidget(self._step_info)
        left.addStretch()
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(96)
        row.addWidget(left_widget)

        divider = QWidget()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background: {Color.BORDER};")
        row.addWidget(divider)

        # ---- ขวา
        right = QVBoxLayout()
        right.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(10)
        self._text = label("", "trackerPhase")
        self._text.setWordWrap(True)
        self._button = QPushButton()
        self._button.setProperty("variant", "chip")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self.action_clicked)
        self._button.hide()
        self._percent = label("", "trackerPercent")
        head.addWidget(self._text, 1)
        head.addWidget(self._button)
        head.addWidget(self._percent)
        right.addLayout(head)
        self.stepper = PhaseStepper()
        right.addWidget(self.stepper)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.valueChanged.connect(self._on_progress)
        right.addWidget(self.progress)
        row.addLayout(right, 1)

        self._phases: list[str] = []
        self._states: list[int] = []
        self._visited: set[int] = set()
        self._current = -1
        self._tone = Color.ACCENT
        self._message: tuple[str, str] | None = None     # (ข้อความ, tone) ที่หน้าทดสอบส่งมา
        self._status = ""                                 # ข้อความของช่วง/ผลจบขั้น
        self._animate = False
        self.set_plan_step(None, None)
        self.start(self.TEST_PHASES, running=False)

    # ------------------------------------------------------------ ขั้นของแผน
    def set_plan_step(self, index: int | None, count: int | None, info: str = "") -> None:
        """index เริ่มที่ 0 — None = ยังไม่มีแผน"""
        if index is None or not count:
            self._step.setText("—")
            self._step_info.setText(tr("No test plan yet"))
            return
        self._step.setText(f'{min(index + 1, count)}<span style="color:{Color.TEXT_FAINT}; font-size:15px">/{count}</span>')
        self._step_info.setText(info)

    def set_caption(self, big: str, info: str = "") -> None:
        """ข้อความแทนเลขขั้น (เช่น ระหว่าง self-check)"""
        self._step.setText(f'<span style="font-size:15px">{big}</span>')
        self._step_info.setText(info)

    # ------------------------------------------------------------ ข้อความ / ปุ่มลัด
    def show_message(self, text: str, tone: str = "info", button: str | None = None) -> None:
        self._message = (text, tone)
        self._button.setVisible(button is not None)
        if button is not None:
            self._button.setText(button)
        self._render()

    def clear_message(self) -> None:
        self._message = None
        self._button.hide()
        self._render()

    # ------------------------------------------------------------ ช่วงของขั้น
    def start(self, phases: list[str], running: bool = True) -> None:
        self._phases = list(phases)
        self._states = [PENDING] * len(phases)
        self._visited = set()
        self._current = -1
        self._tone = Color.ACCENT
        self.progress.setValue(0)
        if running:
            self.set_phase(phases[0])
        else:
            self._status, self._animate = tr("Ready — press Start"), False
            self._render()

    def set_phase(self, name: str) -> None:
        """เข้าช่วง name: ช่วงก่อนหน้าที่เคยผ่าน = เสร็จ, ที่ไม่เคยผ่าน = ข้าม"""
        if name not in self._phases:
            return
        index = self._phases.index(name)
        if index == self._current:
            return
        self._current = index
        self._visited.add(index)
        for i in range(len(self._phases)):
            if i < index:
                self._states[i] = DONE if i in self._visited else SKIPPED
            else:
                self._states[i] = CURRENT if i == index else PENDING
        self._status = tr("Phase {i}/{n}", i=index + 1, n=len(self._phases)) + "  ·  " + \
            tr(self.PHASE_DETAILS.get(name, name))
        self._animate = True
        self._render()

    def finish(self, text: str, tone: str = "success") -> None:
        """จบขั้น: ช่วงที่ผ่านแล้ว = เสร็จ ที่เหลือ = ข้าม แสดงข้อความสรุปด้วยสีตามผล"""
        self._states = [DONE if i in self._visited else SKIPPED for i in range(len(self._phases))]
        self._current = len(self._phases)
        self._tone = TONES.get(tone, Color.ACCENT)
        self._status, self._animate = text, False
        self._render()

    def _render(self) -> None:
        if self._message is not None:
            text, tone = self._message
            color = TONES.get(tone, Color.TEXT) if tone not in ("info", "neutral") else Color.TEXT
        else:
            text = self._status
            color = self._tone if (self._animate or self._current >= len(self._phases)) else Color.TEXT
        self._text.setText(text)
        self._text.setStyleSheet(f"color: {color};")
        self.stepper.set_states([tr(p) for p in self._phases], self._states, self._tone, self._animate)

    def _on_progress(self, value: int) -> None:
        self._percent.setText(f"{value / 10:.0f} %" if value > 0 else "")
