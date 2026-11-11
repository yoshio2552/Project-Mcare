"""ฟังก์ชันคณิตศาสตร์/สถิติล้วนๆ (pure function ไม่มี state) ทดสอบแยกได้ง่าย"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np
from scipy import stats as _scipy_stats


@lru_cache(maxsize=None)
def t_score(n: int, confidence: float = 0.95) -> float:
    """ค่า t แบบสองหางสำหรับ n ตัวอย่าง (cache ไว้ คำนวณครั้งเดียวต่อค่า n)"""
    if n < 2:
        return 0.0
    return float(_scipy_stats.t.ppf((1.0 + confidence) / 2.0, n - 1))


def mean(values: Sequence[float]) -> float:
    return float(np.mean(values)) if len(values) else 0.0


def expanded_std(values: Sequence[float], k: float = 2.0) -> float:
    """k x SD (sample SD, ddof=1) — ค่าเริ่มต้น k=2 (~95%)"""
    if len(values) < 2:
        return 0.0
    return k * float(np.std(values, ddof=1))


def confidence_interval(values: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    """คืน (mean, margin) โดยช่วงเชื่อมั่นคือ mean ± margin"""
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    m = float(np.mean(values))
    if n < 2:
        return m, 0.0
    standard_error = float(np.std(values, ddof=1)) / math.sqrt(n)
    return m, t_score(n, confidence) * standard_error


def percent_error(measured: float, target: float) -> float:
    """(measured - target) / target x 100"""
    if target == 0:
        return 0.0
    return (measured - target) / target * 100.0


def regression_slope(points: Iterable[tuple[float, float]]) -> float:
    """ความชันของเส้นตรง least-squares ผ่านจุด (t, w) -> หน่วย w ต่อ t"""
    points = list(points)
    n = len(points)
    if n < 3:
        return 0.0
    t0 = points[0][0]
    sum_t = sum_w = sum_t2 = sum_tw = 0.0
    for t, w in points:
        dt = t - t0
        sum_t += dt
        sum_w += w
        sum_t2 += dt * dt
        sum_tw += dt * w
    denominator = n * sum_t2 - sum_t * sum_t
    if abs(denominator) < 1e-6:
        return 0.0
    return (n * sum_tw - sum_t * sum_w) / denominator


def flow_ml_per_h(delta_weight_g: float, delta_time_s: float, density_g_per_ml: float = 1.0,
                  baseline_g_per_h: float = 0.0) -> float:
    """แปลงน้ำหนักที่เพิ่ม (g) ในช่วงเวลา (s) เป็น flow (ml/h) ไม่ติดลบ

    baseline_g_per_h = อัตราน้ำหนักที่เปลี่ยนเองตอนปั๊มหยุด (จาก self-check) จะถูกหักออกก่อน
    """
    if delta_time_s <= 0 or density_g_per_ml <= 0:
        return 0.0
    grams_per_h = delta_weight_g / delta_time_s * 3600.0 - baseline_g_per_h
    return max(0.0, grams_per_h / density_g_per_ml)
