"""ReplayView: เล่นซ้ำผลที่บันทึกไว้เหมือนรันสด (ผู้ใช้ 2026-11-20) — กราฟ 4 ช่องชุดเดียวกับหน้าทดสอบ + การ์ดตัวเลข + แถบควบคุม

    ┌ เวลา ┬ flow ขณะนั้น ┬ ค่าเฉลี่ย ┬ คลาดเคลื่อน ┬ ช่วงวัด ┬ น้ำหนัก ┐
    │ Flow เฉลี่ยสะสม        │ Flow รายช่วง            │
    │ Flow ขณะนั้น + peak    │ น้ำหนักบนตราชั่ง          │
    └ ⏮ ▶  1× ▾  ━━━━━━━━━●━━━━━━━  05:12 / 14:00   เต็ม อัตโนมัติ ซูม ┘
ข้อมูลจาก services/replay_session.build() (ตรงกับผลที่บันทึกทุกช่วง) · เริ่มที่ "ท้ายสุด" = กราฟของผลทั้งหมด
export_video(path) = MP4 (H.264) ด้วย Qt เอง (QMediaRecorder + QVideoFrameInput) ไม่ต้องติดตั้งโปรแกรมเพิ่ม
"""
from __future__ import annotations

import time

from PySide6.QtCore import QEventLoop, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from config.i18n import tr
from config.settings import UiSettings
from core.models import EndMode, SessionConfig
from ui.icons import Glyph, glyph_icon
from ui.plots import CumulativePlot, IntervalPlot, SlopePlot, WeightPlot
from ui.plots.cell import PlotCell
from ui.theme import Color
from ui.widgets.common import fmt, label

SPEEDS = (1, 2, 5, 10, 30, 60, 120)
FRAME_MS = 40
RANGES = (("full", "Full"), ("auto", "Auto"), ("zoom", "Zoom"))


def clock(seconds: float) -> str:
    sign = "−" if seconds < 0 else ""
    seconds = abs(seconds)
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{h:d}:{m:02d}:{s:02d}" if h else f"{sign}{m:02d}:{s:02d}"


class _Tile(QFrame):
    def __init__(self, title: str, unit: str = ""):
        super().__init__()
        self.setProperty("card", True)
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 8, 12, 8)
        box.setSpacing(0)
        from ui.widgets.common import ElidedLabel
        box.addWidget(ElidedLabel(title.upper(), "sectionTitle"))     # ชื่อยาวตัดท้าย — การ์ด 6 ใบไม่ดันจอ
        self.setMinimumWidth(90)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.value = label("—", "heroCompact")
        row.addWidget(self.value)
        row.addWidget(label(unit, "heroUnit"), alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch()
        box.addLayout(row)

    def set(self, text: str, color: str | None = None) -> None:
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};" if color else "")


class ReplayView(QWidget):
    position_changed = Signal(float)

    def __init__(self, data, ui: UiSettings | None = None, parent=None, header: str = ""):
        super().__init__(parent)
        self.data = data
        base = ui or UiSettings()
        self.ui = UiSettings(max_points=max(8000, len(data.results) + 10))
        for name in ("interval_style", "interval_moving_avg", "interval_overall_mean", "interval_uncorrected",
                     "graph_auto_cycles", "graph_zoom_s", "graph_flow_y_pct", "rolling_window_s"):
            setattr(self.ui, name, getattr(base, name))
        self.ui.graph_range = "full"
        self._index = 0
        self._t = data.t_end
        self._speed = 10
        self._playing = False
        self._last_tick = 0.0
        summary = data.summary
        config = summary.get("config") or {}
        self._config = SessionConfig(target_flow=max(1e-6, data.target), tolerance_pct=data.tolerance,
                                     strategy=config.get("strategy") or "pump_cycle",
                                     end_mode=EndMode.TIME, duration_min=max(data.t_end, 1.0) / 60.0)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        if header:
            self.header = label(header, "pageTitle")
            root.addWidget(self.header)

        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        self.t_time = _Tile(tr("Time since the first peak"))
        self.t_flow = _Tile(tr("Flow now"), "ml/h")
        self.t_mean = _Tile(tr("Measured flow"), "ml/h")
        self.t_error = _Tile(tr("Flow error (net)"), "%")
        self.t_count = _Tile(tr("Intervals"))
        self.t_weight = _Tile(tr("Balance weight"), "g")
        for tile in (self.t_time, self.t_flow, self.t_mean, self.t_error, self.t_count, self.t_weight):
            tiles.addWidget(tile, 1)
        root.addLayout(tiles)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.cells = [PlotCell(CumulativePlot, self.ui), PlotCell(IntervalPlot, self.ui),
                      PlotCell(SlopePlot, self.ui), PlotCell(WeightPlot, self.ui)]
        for index, cell in enumerate(self.cells):
            grid.addWidget(cell, index // 2, index % 2)
        root.addLayout(grid, 1)
        self.plots = [cell.module for cell in self.cells]

        # ---- แถบควบคุม
        bar = QFrame()
        bar.setProperty("card", True)
        controls = QHBoxLayout(bar)
        controls.setContentsMargins(12, 6, 12, 6)
        controls.setSpacing(10)
        self.btn_restart = QPushButton()
        self.btn_restart.setIcon(glyph_icon(Glyph.REFRESH, Color.TEXT, size=16))
        self.btn_restart.setToolTip(tr("Back to the start"))
        self.btn_play = QPushButton("  " + tr("Play"))
        self.btn_play.setProperty("variant", "primary")
        self.btn_play.setIcon(glyph_icon(Glyph.PLAY, Color.ON_ACCENT, size=14))
        self.btn_play.setMinimumWidth(110)
        self.speed = QComboBox()
        for value in SPEEDS:
            self.speed.addItem(f"{value}×", value)
        self.speed.setCurrentIndex(SPEEDS.index(10))
        self.speed.setToolTip(tr("Replay speed"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.position = label("", "metricValue")
        self.position.setMinimumWidth(130)
        controls.addWidget(self.btn_restart)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.speed)
        controls.addWidget(self.slider, 1)
        controls.addWidget(self.position)
        self._range_buttons = {}
        for index, (key, text) in enumerate(RANGES):
            button = QPushButton(tr(text))
            button.setProperty("variant", "segmentSmall")
            button.setProperty("position", "first" if index == 0 else "last" if index == len(RANGES) - 1 else "mid")
            button.setCheckable(True)
            button.setChecked(key == "full")
            button.clicked.connect(lambda _=False, k=key: self.set_range(k))
            self._range_buttons[key] = button
            controls.addWidget(button)
        root.addWidget(bar)
        self._bar = bar

        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._seek_timer = QTimer(self)
        self._seek_timer.setSingleShot(True)
        self._seek_timer.setInterval(60)
        self._seek_timer.timeout.connect(self._seek_from_slider)
        self.btn_play.clicked.connect(self.toggle)
        self.btn_restart.clicked.connect(lambda: self.seek(self.data.t_start))
        self.speed.currentIndexChanged.connect(lambda _: setattr(self, "_speed", self.speed.currentData()))
        self.slider.valueChanged.connect(lambda _: self._seek_timer.start())
        self.seek(data.t_end)

    # ------------------------------------------------------------ ควบคุม
    def set_range(self, key: str) -> None:
        for name, button in self._range_buttons.items():
            button.setChecked(name == key)
        for plot in self.plots:
            plot.set_range_mode(key)

    def toggle(self) -> None:
        self.pause() if self._playing else self.play()

    def play(self) -> None:
        if self._t >= self.data.t_end - 1e-6:
            self.seek(self.data.t_start)
            if self._range_buttons["full"].isChecked():
                self.set_range("auto")      # เล่นแบบสด: ตามข้อมูลล่าสุดเหมือนหน้าทดสอบ
        self._playing = True
        self._last_tick = time.perf_counter()
        self.btn_play.setText("  " + tr("Pause"))
        self.btn_play.setIcon(glyph_icon(Glyph.PAUSE, Color.ON_ACCENT, size=14))
        self._timer.start()

    def pause(self) -> None:
        self._playing = False
        self._timer.stop()
        self.btn_play.setText("  " + tr("Play"))
        self.btn_play.setIcon(glyph_icon(Glyph.PLAY, Color.ON_ACCENT, size=14))

    def _tick(self) -> None:
        now = time.perf_counter()
        dt, self._last_tick = now - self._last_tick, now
        self.advance_to(self._t + dt * self._speed)
        if self._t >= self.data.t_end:
            self.pause()

    def _seek_from_slider(self) -> None:
        span = self.data.duration
        target = self.data.t_start + span * self.slider.value() / 1000.0
        if abs(target - self._t) > span / 2000.0:
            self.seek(target)

    # ------------------------------------------------------------ ตำแหน่ง
    def seek(self, t: float) -> None:
        """กระโดดไปเวลา t: ล้างกราฟแล้วป้อนทุกผลจนถึง t ครั้งเดียว (วาดครั้งเดียว)"""
        t = max(self.data.t_start, min(self.data.t_end, t))
        for plot in self.plots:
            plot.set_chains(self.data.chains)
            plot.begin_session(self._config)
            if plot.range_mode is None:
                plot.range_mode = "full"
            plot.full_min_s = 0.0
        self._index = 0
        self._t = self.data.t_start
        self.advance_to(t)

    def advance_to(self, t: float) -> None:
        t = max(self.data.t_start, min(self.data.t_end, t))
        end = self.data.index_at(t)
        if end > self._index:
            batch = self.data.results[self._index:end]
            for plot in self.plots:
                plot.feed(batch)
            self._index = end
        self._t = t
        self._update_readout()

    def _update_readout(self) -> None:
        from services.replay_session import frame_values
        values = frame_values(self.data, self._index)
        self.t_time.set(clock(self._t))
        self.t_flow.set(fmt(values["flow"], 3))
        self.t_mean.set(fmt(values["mean"], 3))
        error = values["error"]
        tone = None
        if error is not None:
            tone = Color.SUCCESS if abs(error) <= self.data.tolerance else Color.DANGER
        self.t_error.set(fmt(error, 2, signed=True), tone)
        self.t_count.set(str(values["count"]))
        self.t_weight.set(fmt(values["weight"], 3))
        self.position.setText(f"{clock(self._t)} / {clock(self.data.t_end)}")
        span = self.data.duration
        self.slider.blockSignals(True)
        self.slider.setValue(int((self._t - self.data.t_start) / span * 1000) if span > 0 else 1000)
        self.slider.blockSignals(False)
        self.position_changed.emit(self._t)

    @property
    def current_time(self) -> float:
        return self._t

    def stop(self) -> None:
        self.pause()

    # ------------------------------------------------------------ วิดีโอ MP4
    def export_video(self, path: str, speed: float = 10.0, fps: int = 30, size: QSize = QSize(1600, 900),
                     progress=None, should_stop=None) -> tuple[bool, str]:
        """บันทึกการเล่นซ้ำทั้งหมดเป็น MP4 (H.264) — ความยาววิดีโอ = เวลาทดสอบ ÷ speed
        progress(fraction) · should_stop() -> True = ยกเลิก · คืน (สำเร็จ, ข้อความ)"""
        from PySide6.QtMultimedia import (
            QMediaCaptureSession, QMediaFormat, QMediaRecorder, QVideoFrame, QVideoFrameInput,
        )
        self.pause()
        old_size, old_t, old_range = self.size(), self._t, self.plots[0].range_mode
        self.resize(size)
        self._bar.hide()                    # วิดีโอไม่ต้องมีปุ่มควบคุม
        self.set_range("auto")
        self.seek(self.data.t_start)
        self.ensurePolished()
        session = QMediaCaptureSession()
        frames = QVideoFrameInput()
        session.setVideoFrameInput(frames)
        recorder = QMediaRecorder()
        session.setRecorder(recorder)
        media = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
        media.setVideoCodec(QMediaFormat.VideoCodec.H264)
        recorder.setMediaFormat(media)
        recorder.setOutputLocation(QUrl.fromLocalFile(path))
        recorder.setVideoResolution(size)
        recorder.setVideoFrameRate(fps)
        recorder.setQuality(QMediaRecorder.Quality.HighQuality)
        errors: list[str] = []
        recorder.errorOccurred.connect(lambda _e, text: errors.append(text))
        step = max(0.001, speed / fps)
        total = max(1, int(self.data.duration / step) + int(fps * 1.5))        # ค้างภาพสุดท้าย 1.5 s
        state = {"n": 0, "cancelled": False}
        loop = QEventLoop()

        def send() -> None:
            while state["n"] < total:
                if should_stop is not None and should_stop():
                    state["cancelled"] = True
                    break
                self.advance_to(self.data.t_start + state["n"] * step)
                image = self.grab().toImage().scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                      Qt.TransformationMode.SmoothTransformation)
                frame = QVideoFrame(image)
                frame.setStartTime(int(state["n"] * 1_000_000 / fps))
                frame.setEndTime(int((state["n"] + 1) * 1_000_000 / fps))
                if not frames.sendVideoFrame(frame):
                    return                  # คิวเต็ม รอ readyToSendVideoFrame
                state["n"] += 1
                if progress is not None and state["n"] % 10 == 0:
                    progress(state["n"] / total)
            if recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState:
                recorder.stop()

        frames.readyToSendVideoFrame.connect(send)
        recorder.recorderStateChanged.connect(
            lambda st: loop.quit() if st == QMediaRecorder.RecorderState.StoppedState else None)
        recorder.errorOccurred.connect(lambda *_: loop.quit())
        recorder.record()
        QTimer.singleShot(0, send)
        loop.exec()
        frames.readyToSendVideoFrame.disconnect(send)
        self._bar.show()
        self.resize(old_size)
        self.set_range(old_range or "full")
        self.seek(old_t)
        if state["cancelled"]:
            return False, tr("Cancelled")
        if errors:
            return False, "; ".join(errors)
        return True, tr("{n} frames · {s:.0f} s video", n=state["n"], s=state["n"] / fps)
