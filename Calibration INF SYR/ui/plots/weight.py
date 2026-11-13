"""กราฟน้ำหนักดิบจากตราชั่ง (ดูความต่อเนื่องของสัญญาณตลอด session)

แกนเวลาตามโหมดมุมมอง (Full / Auto / Zoom) และแกน Y ปรับตามข้อมูลในช่วงที่เห็นเท่านั้น
— น้ำหนักทั้งรอบเพิ่มเป็นสิบกรัม ถ้าปรับตามทั้งรอบ รอยกระเพื่อมของรอบปั๊ม (ไม่กี่ mg) จะแบนจนมองไม่เห็น
"""
from ui.plots.base import DecimatingBuffer, PlotModule
from ui.theme import Color

MIN_SPAN_G = 0.005      # แกน Y แคบสุด 5 mg (ตราชั่งละเอียด 1 mg — ไม่ขยาย noise จนดูเหมือนแกว่ง)


class WeightPlot(PlotModule):
    title = "Balance weight"
    y_label = "Weight (g)"

    def setup(self):
        self._buffer = DecimatingBuffer(2, min(self.ui.max_points, 20000))
        self._curve = self._line(Color.SERIES_WEIGHT)

    def consume(self, result):
        self._buffer.append(result.t, result.weight)
        return True

    def redraw(self):
        x, y = self._buffer.column(0), self._buffer.column(1)
        self._curve.setData(x, y)
        if not len(x):
            return
        left, right = self._roll_x(float(x[-1]))
        self._fit_y_visible(x, y, left, right, MIN_SPAN_G)

    def reset(self):
        self._buffer.clear()
