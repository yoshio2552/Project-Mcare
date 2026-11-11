# cache_data.py
from scipy import stats

# สร้างตารางเปล่าๆ ไว้
T_SCORE_LOOKUP = [0.0] * 31

def _init_cache():
    """คำนวณ t-score เก็บไว้ในตาราง"""
    alpha = (1 + 0.95) / 2.
    for n in range(2, 31):
        T_SCORE_LOOKUP[n] = stats.t.ppf(alpha, n - 1)

# สั่งให้ทำงานทันทีที่ไฟล์ถูก Import (ครั้งเดียวตอนเริ่มโปรแกรม)
_init_cache()