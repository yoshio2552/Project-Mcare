"""การระเหยของน้ำจากภาชนะรองรับระหว่างวัด (ผู้ใช้ 2026-11-20) — คำนวณล้วน ไม่มี Qt

ใช้ตอนไม่ได้ใช้ evaporation trap: ประมาณอัตราที่น้ำหายจากภาชนะด้วยฟิสิกส์ของการถ่ายเทมวล แล้วชดเชยในผล
(ค่าที่หักในสูตร flow b = −ė เหมือนค่าจาก self-check — ดู core/corrections.py) · ใช้ evaporation trap = ไม่แก้ค่า

แบบจำลอง: ไอน้ำแพร่จากผิวน้ำผ่าน "ช่องอากาศนิ่งในภาชนะ" ไปถึงปากภาชนะ แล้วถูกพาออกด้วยการพาแบบธรรมชาติ
(ความต้านทาน 2 ชั้นต่ออนุกรม)

    ė = Δρv · A / (h / D_AB + 1 / h_m)                                         [kg/s]

    A      = π d² / 4             พื้นที่ผิวน้ำ (d = เส้นผ่านศูนย์กลางภายในของภาชนะ)
    h      = ระยะผิวน้ำถึงปากภาชนะ = ความลึกภาชนะ − ระดับน้ำ (ระดับน้ำสูงขึ้นตามปริมาตรที่ปั๊มจ่าย -> ใช้ค่าเฉลี่ยต้น/ปลาย)
             ชั้นนี้คือการแพร่ของ Fick ในท่อ (Stefan tube) — แบบเส้นตรง ต่างจากสูตร log ของ Stefan < 2 % ที่ไอน้ำ ≤ 3 %
    Δρv    = ρv,sat(Tw) − RH · ρv,sat(Ta)   ไอน้ำอิ่มตัวที่ผิวน้ำ − ไอน้ำในอากาศรอบ (ρv = pv·Mv / (R·T))
             pv,sat ตามสูตร CIPM-2007 (Picard et al. 2008, Metrologia 45:149 — สูตรเดียวกับความหนาแน่นอากาศ)
    D_AB   = 1.87×10⁻¹⁰ · T^2.072 / p[atm]  m²/s     การแพร่ของไอน้ำในอากาศ (Marrero & Mason 1972, 280–450 K)
    h_m    = Sh · D_AB / L ,  L = A / P = d / 4       การพาแบบธรรมชาติเหนือผิวราบหงาย (ความยาวลักษณะ A/P)
             Sh = 0.96 Ra^(1/6)        1 ≤ Ra < 200       Goldstein, Sparrow & Jones (1973) IJHMT 16:1025
             Sh = 0.59 Ra^(1/4)      200 ≤ Ra < 2.2×10⁴   (ชุดเดียวกัน)
             Sh = 0.54 Ra^(1/4)  2.2×10⁴ ≤ Ra < 8×10⁶     Lloyd & Moran (1974) J. Heat Transfer 96:443
             Sh = 0.15 Ra^(1/3)     Ra ≥ 8×10⁶            (ชุดเดียวกัน)
             Ra = g · (Δρ / ρ̄) · L³ / (ν · D_AB) — Δρ = ความหนาแน่นอากาศชื้นรอบ − ที่ผิวน้ำ (อากาศอิ่มตัวเบากว่า)
             ν จากความหนืด Sutherland ÷ ความหนาแน่น ที่อุณหภูมิเฉลี่ยของชั้นฟิล์ม (Tw + Ta) / 2

ข้อจำกัด (บันทึกไว้ในผล + รวมในงบความไม่แน่นอน ± model_u_pct แบบสี่เหลี่ยม):
- ถือว่าอากาศรอบภาชนะนิ่ง (ตู้กันลมของตราชั่งปิด) และความชื้นในตู้เท่ากับที่วัดในห้อง (ประเมินการระเหยสูงไว้ก่อน)
- ไม่คิดการควบแน่น (ė < 0 -> 0) · ท่อปลายเข็มที่จุ่มในน้ำไม่เปลี่ยนพื้นที่ผิวอย่างมีนัย
ค่าที่วัดจริงด้วย self-check (ปั๊มหยุด) แม่นกว่าแบบจำลอง — โหมด auto ใช้ self-check ของวันนี้ก่อนถ้ามี
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

R = 8.314462618          # J/(mol·K)
M_AIR = 0.02896546       # kg/mol (CIPM-2007, อากาศแห้ง CO2 400 ppm)
M_WATER = 0.01801528     # kg/mol
G = 9.80665              # m/s²
P_ATM = 101325.0         # Pa
REFERENCE = ("Fick diffusion through the vessel headspace + natural convection Sh(Ra) "
             "(Goldstein, Sparrow & Jones 1973; Lloyd & Moran 1974) · psv CIPM-2007 · D_AB Marrero & Mason 1972")
METHODS = ("auto", "model", "self_check", "off")


def saturation_pressure(t_c: float) -> float:
    """ความดันไอน้ำอิ่มตัว (Pa) — CIPM-2007 (Picard et al. 2008, A.1.1)"""
    t = t_c + 273.15
    a, b, c, d = 1.2378847e-5, -1.9121316e-2, 33.93711047, -6.3431645e3
    return math.exp(a * t * t + b * t + c + d / t)


def vapour_density(pv_pa: float, t_c: float) -> float:
    """ความหนาแน่นไอน้ำ (kg/m³) จากความดันย่อย"""
    return pv_pa * M_WATER / (R * (t_c + 273.15))


def moist_air_density(p_pa: float, t_c: float, pv_pa: float) -> float:
    """ความหนาแน่นอากาศชื้น (kg/m³) แบบก๊าซอุดมคติ — ใช้หาแรงลอยตัวของชั้นอากาศเหนือผิวน้ำ"""
    xv = pv_pa / p_pa
    return p_pa / (R * (t_c + 273.15)) * (M_AIR - (M_AIR - M_WATER) * xv)


def diffusion_coefficient(t_c: float, p_pa: float) -> float:
    """สัมประสิทธิ์การแพร่ของไอน้ำในอากาศ (m²/s) — Marrero & Mason (1972)"""
    return 1.87e-10 * (t_c + 273.15) ** 2.072 / (p_pa / P_ATM)


def air_viscosity(t_c: float) -> float:
    """ความหนืดพลวัตของอากาศ (Pa·s) — Sutherland"""
    t = t_c + 273.15
    return 1.716e-5 * (t / 273.15) ** 1.5 * (273.15 + 110.4) / (t + 110.4)


def sherwood(ra: float) -> float:
    """Sh ของผิวราบหงายที่ปล่อยมวลขึ้น (การพาแบบธรรมชาติ) ตามช่วงของ Ra"""
    ra = max(ra, 1.0)
    if ra < 200.0:
        return 0.96 * ra ** (1.0 / 6.0)
    if ra < 2.2e4:
        return 0.59 * ra ** 0.25
    if ra < 8e6:
        return 0.54 * ra ** 0.25
    return 0.15 * ra ** (1.0 / 3.0)


@dataclass
class EvaporationEstimate:
    """ผลของแบบจำลอง 1 สภาวะ — เก็บทุกค่ากลางไว้สอบย้อน"""
    rate_g_per_h: float = 0.0           # น้ำที่หาย (บวก)
    area_mm2: float = 0.0
    headspace_mm: float = 0.0
    delta_rho_v: float = 0.0            # kg/m³
    d_ab: float = 0.0                   # m²/s
    rayleigh: float = 0.0
    sherwood: float = 0.0
    h_m: float = 0.0                    # m/s
    resistance_headspace: float = 0.0   # s/m (h / D_AB)
    resistance_convection: float = 0.0  # s/m (1 / h_m)


def estimate(diameter_mm: float, headspace_mm: float, water_t: float, air_t: float, rh_pct: float,
             pressure_hpa: float) -> EvaporationEstimate:
    """อัตราการระเหย (g/h) จากภาชนะเส้นผ่านศูนย์กลาง d ที่ผิวน้ำต่ำกว่าปากภาชนะ headspace_mm"""
    out = EvaporationEstimate()
    if diameter_mm <= 0:
        return out
    d = diameter_mm / 1000.0
    area = math.pi * d * d / 4.0
    h = max(0.0, headspace_mm) / 1000.0
    p = pressure_hpa * 100.0
    rh = min(max(rh_pct, 0.0), 100.0) / 100.0
    pv_s, pv_a = saturation_pressure(water_t), rh * saturation_pressure(air_t)
    delta_rho_v = vapour_density(pv_s, water_t) - vapour_density(pv_a, air_t)
    film = (water_t + air_t) / 2.0
    d_ab = diffusion_coefficient(film, p)
    rho_surface, rho_ambient = moist_air_density(p, water_t, pv_s), moist_air_density(p, air_t, pv_a)
    rho_mean = (rho_surface + rho_ambient) / 2.0
    nu = air_viscosity(film) / rho_mean
    length = d / 4.0                                    # A / P ของวงกลม
    ra = G * max(rho_ambient - rho_surface, 0.0) / rho_mean * length ** 3 / (nu * d_ab)
    sh = sherwood(ra)
    h_m = sh * d_ab / length
    r_head, r_conv = h / d_ab, 1.0 / h_m
    rate = max(delta_rho_v, 0.0) * area / (r_head + r_conv) * 1000.0 * 3600.0     # kg/s -> g/h
    out.rate_g_per_h, out.area_mm2, out.headspace_mm = rate, area * 1e6, h * 1000.0
    out.delta_rho_v, out.d_ab, out.rayleigh, out.sherwood, out.h_m = delta_rho_v, d_ab, ra, sh, h_m
    out.resistance_headspace, out.resistance_convection = r_head, r_conv
    return out


def headspace_mm(depth_mm: float, diameter_mm: float, volume_ml: float) -> float:
    """ระยะผิวน้ำถึงปากภาชนะ เมื่อมีน้ำ volume_ml (ภาชนะทรงกระบอก) — ไม่ติดลบ"""
    if diameter_mm <= 0:
        return 0.0
    area_mm2 = math.pi * diameter_mm * diameter_mm / 4.0
    return max(0.0, depth_mm - volume_ml * 1000.0 / area_mm2)


@dataclass
class EvaporationDecision:
    """ค่าการระเหยที่ใช้กับการทดสอบ 1 rate — บันทึกลง GravimetricCorrection (สอบย้อนได้ทุกค่า)"""
    method: str = "off"                 # self_check | model | trap | off
    trap: bool = False                  # ใช้ evaporation trap (ไม่แก้ค่า)
    baseline_g_per_h: float = 0.0       # ค่าที่หักในสูตร flow (ระเหย = ลบ)
    model_g_per_h: float = 0.0          # ค่าจากแบบจำลอง (แสดงในใบแม้ไม่ได้ใช้ — เช่นขีดฆ่าเมื่อใช้ trap)
    model_u_rel: float = 0.0            # ครึ่งความกว้างของความไม่แน่นอนแบบจำลอง (สัดส่วน, สี่เหลี่ยม)
    detail: dict = field(default_factory=dict)


def decide(evap_settings, trap: bool, self_check_rate_g_h: float | None, water_t: float, air_t: float,
           rh_pct: float, pressure_hpa: float, rate_ml_h: float = 0.0, duration_s: float = 0.0) -> EvaporationDecision:
    """เลือกค่าการระเหยของการทดสอบ

    trap = True                  -> ไม่แก้ค่า (method "trap") · ยังคิดค่าแบบจำลองไว้แสดง
    method auto (ค่าเริ่มต้น)      -> self-check ที่ผ่านของวันนี้ก่อน ไม่มี -> แบบจำลอง
    method model / self_check    -> ใช้อย่างเดียว (self_check ไม่มีผลของวันนี้ = ไม่แก้)
    method off                   -> ไม่แก้ (เหมือนก่อน 2026-11-20 เมื่อไม่มี self-check)
    ระดับน้ำ: เริ่มที่ start_volume_ml แล้วเพิ่มตามปริมาตรที่ปั๊มจ่ายตลอดเวลาที่ตั้ง -> ใช้ค่าเฉลี่ยของอัตราต้น/ปลาย
    """
    s = evap_settings
    method = str(getattr(s, "method", "auto") or "auto")
    method = method if method in METHODS else "auto"
    d, depth, v0 = float(s.vessel_diameter_mm), float(s.vessel_depth_mm), float(s.start_volume_ml)
    delivered = max(0.0, rate_ml_h) * max(0.0, duration_s) / 3600.0
    h_start = headspace_mm(depth, d, v0)
    h_end = headspace_mm(depth, d, v0 + delivered)
    first = estimate(d, h_start, water_t, air_t, rh_pct, pressure_hpa)
    last = estimate(d, h_end, water_t, air_t, rh_pct, pressure_hpa) if delivered > 0 else first
    model = (first.rate_g_per_h + last.rate_g_per_h) / 2.0
    detail = dict(reference=REFERENCE, diameter_mm=d, depth_mm=depth, start_volume_ml=v0,
                  delivered_ml=round(delivered, 3), headspace_start_mm=round(h_start, 2), headspace_end_mm=round(h_end, 2),
                  water_t=water_t, air_t=air_t, rh_pct=rh_pct, pressure_hpa=pressure_hpa,
                  start=asdict(first), end=asdict(last))
    if depth > 0 and d > 0 and v0 + delivered > math.pi * d * d / 4.0 * depth / 1000.0:
        detail["warning"] = "The vessel would overflow during the test"
    out = EvaporationDecision(model_g_per_h=model, model_u_rel=float(s.model_u_pct) / 100.0, detail=detail, trap=trap)
    if trap:
        out.method = "trap"
        return out
    if method in ("auto", "self_check") and self_check_rate_g_h is not None:
        out.method, out.baseline_g_per_h = "self_check", float(self_check_rate_g_h)
        return out
    if method in ("auto", "model"):
        out.method, out.baseline_g_per_h = "model", -model
        return out
    out.method = "off"
    return out
