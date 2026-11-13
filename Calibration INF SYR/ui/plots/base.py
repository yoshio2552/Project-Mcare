"""แม่แบบของโมดูลกราฟ + buffer ข้อมูล

เพิ่มกราฟใหม่:
    1) สร้างไฟล์ใน ui/plots/ สืบทอด PlotModule แล้วเขียน setup / consume / redraw / reset
    2) เพิ่มคลาสลงใน PLOT_GRID ของ ui/pages/test_page.py
    (ถ้าต้องการปุ่ม/ตัวเลือกข้างกราฟ เขียน controls() คืน QWidget — หน้าทดสอบจะวางไว้ข้างกราฟให้)
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt

from config.i18n import tr
from config.settings import UiSettings
from core.models import EngineResult, SessionConfig
from ui.theme import Color


class RingBuffer:
    """ตารางตัวเลขขนาดคงที่ (จองหน่วยความจำครั้งเดียว) เต็มแล้วทิ้งค่าเก่าสุด

    จองที่ไว้ 2 เท่าของความจุ แล้วเลื่อนหน้าต่างไปเรื่อยๆ — ย้ายข้อมูลกลับต้นตารางครั้งเดียวต่อทุก "ความจุ" จุด
    (เดิมเลื่อนทั้งตารางทุกจุดเมื่อเต็ม: 40,000 จุด x 4 คอลัมน์ต่อ 1 จุดใหม่ — รันนานหลายชั่วโมงเปลือง CPU)
    หน่วยความจำคงที่ตลอดการทดสอบ ไม่ว่าจะรันนานแค่ไหน
    """

    def __init__(self, columns: int, capacity: int):
        self._capacity = max(1, capacity)
        self._data = np.full((columns, 2 * self._capacity), np.nan)
        self._start = 0
        self._size = 0

    def append(self, *values: float | None) -> None:
        end = self._start + self._size
        if end == self._data.shape[1]:          # ถึงปลายที่จองไว้: ย้ายข้อมูลที่ยังใช้กลับต้นตาราง
            self._data[:, :self._size] = self._data[:, self._start:end]
            self._start, end = 0, self._size
        self._data[:, end] = [np.nan if v is None else v for v in values]
        if self._size < self._capacity:
            self._size += 1
        else:
            self._start += 1

    def column(self, index: int) -> np.ndarray:
        return self._data[index, self._start:self._start + self._size]

    def clear(self) -> None:
        self._start = self._size = 0

    def __len__(self) -> int:
        return self._size


class DecimatingBuffer(RingBuffer):
    """เก็บได้ตลอดการทดสอบ: เมื่อเต็มจะคัดเหลือจุดเว้นจุด แล้วรับจุดใหม่ถี่น้อยลงครึ่งหนึ่ง
    (รูปร่างของทั้งการทดสอบยังอยู่ครบ ไม่ทิ้งช่วงต้น)"""

    def __init__(self, columns: int, capacity: int):
        super().__init__(columns, capacity - capacity % 2)
        self._stride = 1
        self._seen = 0

    def append(self, *values: float | None) -> None:
        self._seen += 1
        if (self._seen - 1) % self._stride:
            return
        capacity = self._capacity
        if self._size == capacity:
            self._data[:, :capacity // 2] = self._data[:, :capacity:2]
            self._size = capacity // 2
            self._stride *= 2
        self._data[:, self._size] = [np.nan if v is None else v for v in values]
        self._size += 1

    def clear(self) -> None:
        super().clear()
        self._stride, self._seen = 1, 0


class PlotModule:
    title = ""
    y_label = ""
    x_label = "Time (s)"
    # ((สี, ชื่อ) หรือ (สี, ชื่อ, สัญลักษณ์) หรือ (สี, ชื่อ, สัญลักษณ์, key), ...)
    # มี key = กดที่ชื่อบนหัวกราฟเพื่อซ่อน/แสดงเส้นนั้นได้ (ดู series_visible / set_series_visible)
    legend: tuple = ()
    # รูปแบบการวาดที่สลับได้บนหัวกราฟ ((key, ชื่อ), ...) — ว่าง = ไม่มีตัวเลือก
    styles: tuple = ()

    def __init__(self, plot: pg.PlotItem, ui: UiSettings):
        self.plot = plot
        self.ui = ui
        self.window_s = ui.rolling_window_s
        # มุมมองแกนเวลา: None = ตามค่าที่เลือกบนหน้าทดสอบ (ui.graph_range) · หน้าประวัติตั้งเป็น "full"
        self.range_mode: str | None = None
        self.period_s: float | None = None      # คาบรอบปั๊ม/ความยาวช่วงล่าสุด (ใช้กับโหมด Auto)
        self._dirty = False
        self.chains = 2                 # จำนวนสายของวิธีจับรอบปั๊ม (1 = จับรอบเดียว) — ตั้งก่อน begin_session
        self.on_option_changed = None   # callback เมื่อผู้ใช้เปลี่ยนตัวเลือกบนหัวกราฟ (หน้าทดสอบใช้บันทึกค่า)
        self.header = None              # PlotHeader (Qt) ถ้ามี — ไม่มี = ใช้ชื่อกราฟของ pyqtgraph
        self.hidden: set[str] = set()   # key ของเส้นที่ผู้ใช้ซ่อน
        self._title, self._legend = "", ()

        self.set_header(self.title, self.legend)
        plot.setLabel("left", tr(self.y_label))
        plot.setLabel("bottom", tr(self.x_label))
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setClipToView(True)
        plot.setDownsampling(auto=True, mode="peak")
        for axis in ("left", "bottom"):
            plot.getAxis(axis).setPen(pg.mkPen(Color.BORDER))
            plot.getAxis(axis).setTextPen(pg.mkPen(Color.TEXT_MUTED))
        self.setup()

    def set_header(self, title: str, legend: tuple = ()) -> None:
        """ชื่อกราฟ + คำอธิบายเส้น (เปลี่ยนได้ตามวิธีจับของการทดสอบ)"""
        self._title, self._legend = title, tuple(legend)
        if self.header is not None:
            self.header.render(self)
            return
        entries = "".join(
            f'&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:{color}">{(symbol or ["●"])[0]}</span>'
            f'&nbsp;<span style="color:{Color.TEXT_MUTED}; font-size:9pt">{tr(name)}</span>'
            for color, name, *symbol in ((e[0], e[1], *e[2:3]) for e in legend)
        )
        self.plot.setTitle(f'<span style="color:{Color.TEXT}; font-size:10pt; font-weight:600">{tr(title)}</span>{entries}')

    # ------------------------------------------------ ส่วนที่คลาสลูกเขียน
    def setup(self) -> None:
        """สร้างเส้น/จุดของกราฟ (เรียกครั้งเดียว)"""

    def consume(self, result: EngineResult) -> bool:
        """เก็บข้อมูลจากผลลัพธ์ 1 ตัว — คืน True ถ้ามีข้อมูลใหม่ที่ต้องวาด"""
        return False

    def redraw(self) -> None:
        """วาดข้อมูลล่าสุดลงกราฟ"""

    def reset(self) -> None:
        """ล้างข้อมูลทั้งหมด"""

    # ------------------------------------------------ หัวกราฟแบบ Qt (PlotHeader)
    def attach_header(self, header) -> None:
        """ใช้หัวกราฟแบบ Qt แทนชื่อกราฟของ pyqtgraph (ได้พื้นที่กราฟมากขึ้น + กดซ่อนเส้นได้)"""
        self.header = header
        self.plot.setTitle(None)
        header.render(self)

    def series_visible(self, key: str) -> bool:
        return key not in self.hidden

    def set_series_visible(self, key: str, visible: bool) -> None:
        """ผู้ใช้กดชื่อเส้นบนหัวกราฟ — คลาสลูก override ถ้าต้องจำค่าไว้ใน settings"""
        (self.hidden.discard if visible else self.hidden.add)(key)
        self._option_changed()

    def current_style(self) -> str:
        return ""

    def set_style(self, key: str) -> None:
        """ผู้ใช้เลือกรูปแบบการวาดบนหัวกราฟ"""

    def _option_changed(self) -> None:
        self.set_header(self._title, self._legend)
        self.redraw()
        if self.on_option_changed:
            self.on_option_changed()

    # ------------------------------------------------------- ส่วนกลาง
    def set_chains(self, chains: int) -> None:
        self.chains = 1 if chains == 1 else 2

    def begin_session(self, config: SessionConfig) -> None:
        self.period_s = None
        self.reset()
        self.plot.enableAutoRange()             # เริ่มรอบใหม่: ล้างมุมมองที่ค้างจากรอบก่อน
        self.redraw()

    def feed(self, results: list[EngineResult]) -> None:
        for result in results:
            self._track_period(result)
            if self.consume(result):
                self._dirty = True
        if self._dirty:
            self._dirty = False
            self.redraw()

    def set_window(self, seconds: int) -> None:
        self.window_s = seconds
        self.redraw()

    def set_range_mode(self, mode: str | None) -> None:
        """เปลี่ยนมุมมองแกนเวลา (full / auto / zoom) แล้ววาดใหม่ทันที"""
        self.range_mode = mode
        self.redraw()

    def _track_period(self, result: EngineResult) -> None:
        """จำคาบล่าสุดไว้ใช้กับโหมด Auto: คาบจากช่วงก่อนวัด หรือความยาวของช่วงวัดล่าสุด (1 รอบปั๊ม / 1 ช่วงเวลา)"""
        if result.interval is not None and result.interval.duration_s > 0:
            self.period_s = result.interval.duration_s
        elif result.prerun is not None and result.prerun.period_s:
            self.period_s = result.prerun.period_s

    # ------------------------------------------------ ตัวช่วยสำหรับคลาสลูก
    def _line(self, color: str, name: str | None = None, width: float = 2.0, **kwargs):
        return self.plot.plot(pen=pg.mkPen(color, width=width), name=name, **kwargs)

    def current_range_mode(self) -> str:
        mode = self.range_mode or getattr(self.ui, "graph_range", "auto")
        return mode if mode in ("full", "auto", "zoom") else "auto"

    def view_width_s(self) -> float | None:
        """ความกว้างแกนเวลาตามโหมด (None = full: ตั้งแต่ 0 ถึงจุดล่าสุด)

        auto  = N รอบปั๊ม (ui.graph_auto_cycles) — ไม่รู้คาบ ใช้ rolling_window_s
        zoom  = ui.graph_zoom_s วินาที (ไม่กว้างกว่า auto)
        """
        mode = self.current_range_mode()
        if mode == "full":
            return None
        auto = float(self.window_s)
        if self.period_s:
            auto = max(30.0, getattr(self.ui, "graph_auto_cycles", 6) * self.period_s)
        if mode == "zoom":
            return max(10.0, min(float(getattr(self.ui, "graph_zoom_s", 60)), auto))
        return auto

    def _visible_x(self, last_t: float) -> tuple[float, float]:
        width = self.view_width_s()
        if width is None:
            return 0.0, max(last_t, 10.0)
        return max(0.0, last_t - width), max(width, last_t)

    def _roll_x(self, last_t: float) -> tuple[float, float]:
        """ตั้งแกนเวลาตามโหมดที่เลือก คืนช่วง (ซ้าย, ขวา) ที่แสดง"""
        left, right = self._visible_x(last_t)
        self.plot.setXRange(left, right, padding=0)
        return left, right

    def _fit_y_visible(self, x: np.ndarray, y: np.ndarray, left: float, right: float, min_span: float) -> None:
        """แกน Y ตามข้อมูล "ในช่วงที่เห็น" เท่านั้น — รูปแบบรอบปั๊มไม่ถูกบีบจนแบนเพราะค่าช่วงอื่น
        min_span กันไม่ให้ขยาย noise ระดับความละเอียดตราชั่งจนดูเหมือนแกว่งแรง"""
        if not len(x):
            return
        mask = (x >= left) & (x <= right) & np.isfinite(y)
        if not mask.any():
            return
        low, high = float(np.min(y[mask])), float(np.max(y[mask]))
        if high - low < min_span:
            middle = (high + low) / 2.0
            low, high = middle - min_span / 2.0, middle + min_span / 2.0
        self.plot.setYRange(low, high, padding=0.08)

    def _add_target_band(self) -> None:
        """เส้น target + แถบเกณฑ์ยอมรับ (เรียกใน setup แล้วใช้ _set_target ตอนเริ่ม session)"""
        band_color = pg.mkColor(Color.SUCCESS)
        band_color.setAlpha(22)
        self._band = pg.LinearRegionItem(orientation="horizontal", movable=False,
                                         brush=band_color, pen=pg.mkPen(None))
        self._band.setZValue(-10)
        self._target_line = pg.InfiniteLine(angle=0, pen=pg.mkPen(Color.TEXT_FAINT, width=1, style=Qt.PenStyle.DashLine))
        self._target_line.setZValue(-5)
        self.plot.addItem(self._band)
        self.plot.addItem(self._target_line)
        self._band.hide()
        self._target_line.hide()

    def _set_target(self, config: SessionConfig) -> None:
        if config.target_flow <= 0:
            self._band.hide()
            self._target_line.hide()
            return
        delta = config.target_flow * config.tolerance_pct / 100.0
        self._band.setRegion((config.target_flow - delta, config.target_flow + delta))
        self._target_line.setValue(config.target_flow)
        self._band.show()
        self._target_line.show()
        self._y_base = (config.target_flow - 1.6 * delta, config.target_flow + 1.6 * delta)
        self._fit_y(())

    def _fit_y(self, values) -> None:
        """ตั้งแกน Y ให้เห็นแถบเกณฑ์เสมอ และขยายออกถ้าค่าที่ส่งมาหลุดนอกแถบ"""
        low, high = getattr(self, "_y_base", (0.0, 1.0))
        finite = [float(v) for v in values if v is not None and np.isfinite(v)]
        if finite:
            low, high = min(low, min(finite)), max(high, max(finite))
        self.plot.setYRange(low, high, padding=0.05)
