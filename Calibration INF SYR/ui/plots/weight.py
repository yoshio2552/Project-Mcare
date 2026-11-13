"""กราฟน้ำหนักดิบจากตราชั่ง (ดูความต่อเนื่องของสัญญาณตลอด session)

แกนเวลาตามโหมดมุมมอง (Full / Auto / Zoom) และแกน Y ปรับตามข้อมูลในช่วงที่เห็นเท่านั้น
— น้ำหนักทั้งรอบเพิ่มเป็นสิบกรัม ถ้าปรับตามทั้งรอบ รอยกระเพื่อมของรอบปั๊ม (ไม่กี่ mg) จะแบนจนมองไม่เห็น
ข้อมูลเก็บแบบ SeriesStore: ซูมหลังรันหลายชั่วโมงยังเห็นทุกจุด · โหมดเต็มยังเห็นตั้งแต่จุดแรก
"""
from ui.plots.base import PlotModule, SeriesStore
from ui.theme import Color

MIN_SPAN_G = 0.005      # แกน Y แคบสุด 5 mg (ตราชั่งละเอียด 1 mg — ไม่ขยาย noise จนดูเหมือนแกว่ง)


class WeightPlot(PlotModule):
    title = "Balance weight"
    y_label = "Weight (g)"

    def setup(self):
        self._store = SeriesStore(2, self.ui.max_points)
        self._curve = self._line(Color.SERIES_WEIGHT)

    def consume(self, result):
        self._store.append(result.t, result.weight)
        return True

    def redraw(self):
        last = self._store.last(0)
        if last is None:
            self._curve.setData([], [])
            return
        x, y = self._store.view(self.visible_left(last))
        self._curve.setData(x, y)
        left, right = self._roll_x(last)
        self._fit_y_visible(x, y, left, right, MIN_SPAN_G)

    def reset(self):
        self._store.clear()
