"""งบความไม่แน่นอนของอัตราการไหล (GUM — JCGM 100:2008 · ค่าแก้ g→ml ตาม ISO 4787) — ไม่มี Qt

สมการของการวัด (วิธีชั่งน้ำหนัก ค่าที่ใช้ตัดสิน = ปริมาตรรวม ÷ เวลารวม):

    Q = (Δm / Δt × 3600 − b) × Z(ρw(T_w), ρa(T_a, RH, P), ρref)          [ml/h]

    Δm  น้ำหนักที่ชั่งได้ของสาย A (g)        Δt  เวลารวมของสาย A (s)
    b   อัตราน้ำหนักที่เปลี่ยนเองตอนปั๊มหยุด (self-check, g/h)     Z  ml/g (ISO 4787)

องค์ประกอบ (ทุกตัวเป็นความไม่แน่นอนมาตรฐานสัมพัทธ์ของ Q):
    ตราชั่ง — ใบรับรอง     U_cal/k ÷ Δm          (ค่าคลาดเคลื่อนของผลต่างน้ำหนักอยู่ในช่วง U ของจุดเดียว — ประมาณแบบระวัง)
    ตราชั่ง — ความละเอียด  √2 · d/√12 ÷ Δm       (อ่าน 2 ครั้ง ต้น/ปลาย, สี่เหลี่ยม)
    ตราชั่ง — ความซ้ำ     √2 · s_r ÷ Δm          (s_r จากใบรับรอง)
    เวลา — ประทับเวลา      √2 · u_ts ÷ Δt         (ความไม่สม่ำเสมอของเวลารับข้อมูลต่อจุด 2 จุด)
    เวลา — นาฬิกา          ppm/√3                 (อัตรานาฬิกาของเครื่อง, สี่เหลี่ยม)
    อุณหภูมิน้ำ            |∂Z/∂T_w|/Z · U_T/k     (ไม่ได้กรอกอุณหภูมิ: ใช้ ± no_temp_c สี่เหลี่ยม)
    อุณหภูมิอากาศ/ความชื้น/ความดัน  |∂Z/∂x|/Z · u_x  (คำนวณอนุพันธ์เชิงตัวเลขจากสูตรเดียวกับที่ใช้แก้)
    ความหนาแน่นน้ำ (สูตร/ความบริสุทธิ์)  u_ρ สัมพัทธ์
    การระเหย/self-check    u_b · Z ÷ Q
    ความซ้ำของการวัด          2SD ÷ 2 จากตารางความซ้ำ (core/repeatability.py: กรอกเอง หรือสอบเทียบ 3 ครั้ง) ของ
                              รุ่น+ชนิด+ชุดสาย+rate — ไม่มี: ค่าตั้งต้น (0) · ไม่ใช้ผลเก่า และไม่ใช้ 2SD ของช่วงวัดในผลนี้
                              (ผู้ใช้ 2026-11-19: ช่วงวัดต่อเนื่องในการรันเดียวไม่ใช่การวัดซ้ำ — ต้องเป็นการรันซ้ำ)
    อื่นๆ ที่ผู้ใช้เพิ่ม     ค่าในหน้าตั้งค่า (ปกติ = ค่ามาตรฐาน, สี่เหลี่ยม = ครึ่งความกว้าง ÷ √3)

u_c = √Σu_i² · ν_eff (Welch–Satterthwaite) · k = t(97.725 %, ν_eff) ≈ 2 · U = k · u_c (ระดับความเชื่อมั่นราว 95 %)
ทุกค่าที่ใช้ (รวมค่าจากหน้าตั้งค่า ณ ตอนนั้น) บันทึกในผล -> สอบย้อนได้ (summary.uncertainty)
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from config.settings import UncertaintySettings
from core.corrections import air_density, water_density, z_factor

METHOD = "GUM JCGM 100:2008 · ISO 4787 · Welch–Satterthwaite"
INFINITE = 1e9


@dataclass
class Component:
    name: str               # อังกฤษ (ผ่าน tr ที่ UI)
    source: str             # มาจากไหน (ค่าที่ใช้)
    u_rel_pct: float        # ความไม่แน่นอนมาตรฐานสัมพัทธ์ของ Q (%)
    distribution: str = "normal"
    nu: float = INFINITE


def _z(tw: float, ta: float, rh: float, p: float, ref: float, buoyancy: bool) -> float:
    return z_factor(water_density(tw), air_density(ta, rh, p) if buoyancy else 0.0, ref)


def _rel_sensitivity(fn, x: float, h: float) -> float:
    """|∂f/∂x| / f — ผลต่างกลาง"""
    f0 = fn(x)
    return abs(fn(x + h) - fn(x - h)) / (2 * h) / f0 if f0 else 0.0


def k_factor(nu_eff: float) -> float:
    """ตัวคูณครอบคลุมราว 95.45 % ตามองศาอิสระประสิทธิผล (t-distribution)"""
    if nu_eff >= 1e6:
        return 2.0
    try:
        from scipy.stats import t
        return float(t.ppf(0.977250, max(1.0, nu_eff)))
    except Exception:
        return 2.0


def budget(summary: dict, s: UncertaintySettings, repeat: dict | None = None) -> dict:
    """งบความไม่แน่นอนของผล 1 รายการ (summary เป็น dict แบบที่บันทึก) — {} = คิดไม่ได้ (ไม่มีน้ำหนัก/เวลารวม)"""
    mass, seconds = summary.get("total_mass_g"), summary.get("total_time_s")
    q = summary.get("mean_flow")
    if not mass or not seconds or not q or mass <= 0 or seconds <= 0:
        return {}
    corr = summary.get("correction") or {}
    buoyancy = bool(corr.get("air_buoyancy", True))
    ref = float(corr.get("reference_density_g_per_ml") or 8.0)
    tw = corr.get("liquid_temp_c")
    ta = float(corr.get("air_temp_c") or 20.0)
    rh = float(corr.get("humidity_pct") or 50.0)
    p = float(corr.get("pressure_hpa") or 1013.25)
    z = float(summary.get("ml_per_g") or 1.0)
    rate_g_h = mass / seconds * 3600.0
    comps: list[Component] = []
    add = lambda name, source, rel, dist="normal", nu=INFINITE: comps.append(      # noqa: E731
        Component(name, source, rel * 100.0, dist, nu))

    add("Balance calibration", f"U {s.balance_u_g:g} g (k={s.balance_k:g}) · {s.balance_cert} · Δm {mass:.4f} g",
        s.balance_u_g / s.balance_k / mass)
    add("Balance resolution", f"d {s.balance_resolution_g:g} g · 2 readings", math.sqrt(2) * s.balance_resolution_g / math.sqrt(12) / mass, "rect")
    add("Balance repeatability", f"s {s.balance_repeat_g:g} g · 2 readings", math.sqrt(2) * s.balance_repeat_g / mass)
    add("Timestamps", f"u {s.timestamp_u_s:g} s per point · Δt {seconds:.2f} s", math.sqrt(2) * s.timestamp_u_s / seconds)
    add("Computer clock rate", f"± {s.clock_ppm:g} ppm", s.clock_ppm * 1e-6 / math.sqrt(3), "rect")
    tw_used = float(tw) if tw is not None else None
    t_ref = tw_used if tw_used is not None else 20.0
    sens_tw = _rel_sensitivity(lambda x: _z(x, ta, rh, p, ref, buoyancy), t_ref, 0.05)
    if tw_used is not None and corr.get("water_density_source", "temperature") == "temperature":
        add("Water temperature → density", f"U {s.thermo_u_c:g} °C (k={s.thermo_k:g}) · {s.thermo_cert} · {tw_used:g} °C",
            sens_tw * s.thermo_u_c / s.thermo_k)
    else:
        add("Water temperature → density", f"not measured · ± {s.no_temp_c:g} °C", sens_tw * s.no_temp_c / math.sqrt(3), "rect")
    add("Water density formula / purity", f"{s.water_density_rel:g} relative", s.water_density_rel)
    if buoyancy:
        measured = lambda key: corr.get(key) == "form"      # noqa: E731
        sens_ta = _rel_sensitivity(lambda x: _z(t_ref, x, rh, p, ref, True), ta, 0.05)
        sens_rh = _rel_sensitivity(lambda x: _z(t_ref, ta, x, p, ref, True), rh, 0.5)
        sens_p = _rel_sensitivity(lambda x: _z(t_ref, ta, rh, x, ref, True), p, 0.5)
        add("Air temperature → buoyancy", f"{ta:g} °C",
            sens_ta * (s.thermo_u_c / s.thermo_k if measured("air_temp_source") or corr.get("air_temp_source") == "liquid"
                       else s.no_air_c / math.sqrt(3)))
        add("Humidity → buoyancy", f"{rh:g} %RH",
            sens_rh * (s.hygro_u_pct / s.hygro_k if measured("humidity_source") else 10.0 / math.sqrt(3)))
        add("Air pressure → buoyancy", f"{p:g} hPa",
            sens_p * (s.baro_u_hpa / s.baro_k if measured("pressure_source") else 15.0 / math.sqrt(3)))
    add("Evaporation / self-check", f"u {s.evaporation_u_g_h:g} g/h at {rate_g_h:.3f} g/h", s.evaporation_u_g_h / rate_g_h)
    # ความซ้ำ: 2SD ที่ผู้ใช้กรอก/สอบเทียบของ รุ่น+ชนิด+ชุดสาย+rate (Repository.repeat_value) -> u = 2SD ÷ 2 (Type B, ν = ∞)
    # ไม่มีค่า -> ค่าตั้งต้นในหน้าตั้งค่า (เริ่มต้น 0) · ไม่ใช้ผลเก่า/2SD ของช่วงวัดในผลนี้ (ผู้ใช้ 2026-11-19)
    if repeat:
        u_rep = float(repeat["sd2_ml_h"]) / 2.0 / q
        studies = repeat.get("studies") or []
        add("Repeatability (2SD entered)", f"2SD {repeat['sd2_pct']:.4f} % = ± {repeat['sd2_ml_h']:.4f} ml/h · "
            f"mean of {len(studies)} set(s) #{', #'.join(str(x['id']) for x in studies)}", u_rep)
    else:
        add("Repeatability (2SD entered)", f"none for this model / IV set / rate · default 2SD {s.repeat_default_pct:g} %",
            s.repeat_default_pct / 2.0 / 100.0)
    for line in s.extra or []:
        parts = [part.strip() for part in str(line).split("|")]
        try:
            value = float(parts[1])
        except (IndexError, ValueError):
            continue
        rect = len(parts) > 2 and parts[2].lower().startswith("rect")
        add(parts[0] or "Other", "Settings", value / 100.0 / (math.sqrt(3) if rect else 1.0), "rect" if rect else "normal")

    u_c = math.sqrt(sum(c.u_rel_pct ** 2 for c in comps))
    denominator = sum(c.u_rel_pct ** 4 / c.nu for c in comps if c.nu < INFINITE)
    nu_eff = (u_c ** 4 / denominator) if denominator > 0 else INFINITE
    k = k_factor(nu_eff)
    big = k * u_c
    return {
        "method": METHOD, "measured_ml_h": q, "z": z, "mass_g": mass, "time_s": seconds,
        "components": [asdict(c) for c in comps],
        "u_c_pct": u_c, "nu_eff": nu_eff if nu_eff < INFINITE else None, "k": k,
        "U_pct": big, "U_ml_h": big / 100.0 * q,           # ไม่ปัดตอนเก็บ — ปัดตอนแสดงเท่านั้น (ml/h 4 ตำแหน่ง, % 3 ตำแหน่ง)
        "repeatability": repeat or {},
        "settings": asdict(s), "simulated": s.simulated,
    }


def warn_beyond_tolerance(error_pct: float | None, u_pct: float | None, tolerance_pct: float) -> bool:
    """ผลอยู่ในเกณฑ์ แต่รวม U แล้วเกินเกณฑ์ (ILAC-G8: ยอมรับตรง แต่แจ้งให้ทราบ) — เตือนตอนทดสอบเสร็จเท่านั้น ไม่ใส่ในใบ"""
    if error_pct is None or not u_pct:
        return False
    return abs(error_pct) <= tolerance_pct < abs(error_pct) + u_pct
