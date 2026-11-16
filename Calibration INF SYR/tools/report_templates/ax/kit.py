"""ชุดเครื่องมือของแบบ A-TH และ A1–A5 (ปรับจากแบบ A) — ข้อความ EN/TH, ข้อมูลสมมติ, บล็อก HTML ที่ใช้ร่วม
แบบ A ต้นฉบับไม่ถูกแตะ: ที่นี่สร้างไฟล์ใหม่ทั้งหมดใน template/A-TH และ template/A1…A5
ข้อมูลเป็นค่าสมมติ — ค่าในกราฟคำนวณจากชุดเดียวกับตาราง
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qz"))
from common import (INFUSION, SYRINGE, SYR_INSP, INF_QT, SYR, INF, f, esc, series, mean, sd, Ax, T, R, PL,  # noqa: E402
                    PG, C, svg, fonts, dc)
from common import L as LN  # noqa: E402  (เส้น SVG — ชื่อ L ใช้เป็นภาษา)

INK, GREY, DIM, RULE, PAPER = "#15181C", "#5A626C", "#9AA2AC", "#D5D9DE", "#F3F5F7"

# ---------------------------------------------------------------- ข้อความ EN / TH
S = {
    "company": ("[Company Name] Co., Ltd.", "บริษัท [ชื่อบริษัท] จำกัด"),
    "lab": ("Medical Equipment Calibration Laboratory", "ห้องปฏิบัติการสอบเทียบเครื่องมือแพทย์"),
    "service": ("Medical Equipment Service", "ศูนย์บริการเครื่องมือแพทย์"),
    "addr": ("[Address] · [Province] [Postcode] · Tel [—]", "[ที่อยู่] · [จังหวัด] [รหัสไปรษณีย์] · โทร [—]"),
    "cal_title": ("Calibration Certificate", "ใบรับรองผลการสอบเทียบ"),
    "cal_tech": ("Technical record", "รายละเอียดทางเทคนิค"),
    "insp_title": ("Inspection Report", "รายงานการตรวจสภาพเครื่อง"),
    "qt_title": ("Quick Function Test", "รายงานทดสอบการทำงานเบื้องต้น"),
    "page": ("Page {a} of {b}", "หน้า {a} / {b}"),
    "cert_no": ("Certificate No.", "เลขที่ใบรับรอง"),
    "report_no": ("Report No.", "เลขที่รายงาน"),
    "job_no": ("Job No.", "เลขที่งาน"),
    "date_cal": ("Date of calibration", "วันที่สอบเทียบ"),
    "date_issue": ("Date of issue", "วันที่ออกใบรับรอง"),
    "date_insp": ("Date of inspection", "วันที่ตรวจ"),
    "next_due": ("Next due", "ครบกำหนดครั้งถัดไป"),
    "date": ("Date", "วันที่"),
    "customer": ("Customer", "ผู้รับบริการ"),
    "hospital": ("Hospital", "โรงพยาบาล"),
    "department": ("Department", "หน่วยงาน"),
    "province": ("Province", "จังหวัด"),
    "contact": ("Contact person", "ผู้ติดต่อ"),
    "tel": ("Telephone", "โทรศัพท์"),
    "cust_ref": ("Customer reference", "เลขอ้างอิงลูกค้า"),
    "received": ("Date received", "วันที่รับเครื่อง"),
    "item": ("Item calibrated", "เครื่องที่สอบเทียบ"),
    "equipment": ("Equipment", "เครื่องที่ตรวจ"),
    "description": ("Description", "ชนิดเครื่อง"),
    "inf_desc": ("Infusion pump, volumetric", "เครื่องให้สารละลาย (infusion pump)"),
    "syr_desc": ("Syringe pump", "เครื่องให้ยาแบบกระบอกฉีด (syringe pump)"),
    "mfr_model": ("Manufacturer / Model", "ยี่ห้อ / รุ่น"),
    "sn_asset": ("Serial No. / Asset ID", "หมายเลขเครื่อง / รหัสครุภัณฑ์"),
    "admin_set": ("Administration set", "ชุดให้สารละลาย"),
    "syringe_used": ("Syringe used", "กระบอกฉีดยาที่ใช้"),
    "balance": ("Reference balance", "ตราชั่งมาตรฐาน"),
    "bal_make": ("Make / model", "ยี่ห้อ / รุ่น"),
    "bal_sn": ("Serial No.", "หมายเลขเครื่อง"),
    "bal_cap": ("Capacity · readability", "พิกัด · ค่าละเอียด"),
    "bal_cert": ("Calibration certificate", "ใบรับรองการสอบเทียบ"),
    "bal_by": ("Calibrated by", "สอบเทียบโดย"),
    "bal_due": ("Calibrated · due", "สอบเทียบ · ครบกำหนด"),
    "bal_check": ("Check before use", "ตรวจก่อนใช้งาน"),
    "bal_check_v": ("50 g F1 → 50.000 g · 0 mg (±3 mg) OK", "ตุ้ม 50 g F1 → 50.000 g · 0 mg (±3 mg) ผ่าน"),
    "bal_lab": ("[accredited laboratory]", "[ห้องปฏิบัติการที่ได้รับการรับรอง]"),
    "thermo": ("Thermo-hygrometer", "เครื่องวัดอุณหภูมิ-ความชื้น"),
    "thermometer": ("Liquid thermometer", "เทอร์โมมิเตอร์วัดน้ำ"),
    "ref_std": ("Reference standard", "เครื่องมือมาตรฐาน"),
    "cert_due": ("Cert. No. / Due", "เลขใบรับรอง / ครบกำหนด"),
    "method_sec": ("Method and reference standards", "วิธีและเครื่องมือมาตรฐาน"),
    "method": ("Method", "วิธีการ"),
    "method_v": ("Gravimetric flow measurement, in-house procedure [WI-CAL-01], based on IEC 60601-2-24:2012",
                 "วัดอัตราไหลด้วยวิธีชั่งน้ำหนัก ตามวิธีปฏิบัติงาน [WI-CAL-01] อ้างอิง IEC 60601-2-24:2012"),
    "volume": ("Volume", "การแปลงปริมาตร"),
    "volume_v": ("Mass to volume by ISO 4787:2021 (Z factor)", "แปลงมวลเป็นปริมาตรตาม ISO 4787:2021 (ตัวประกอบ Z)"),
    "intervals": ("Intervals", "การแบ่งช่วงวัด"),
    "intervals_inf": ("Pump-cycle capture, peak to peak", "จับรอบปั๊ม จากยอดถึงยอด"),
    "intervals_syr": ("Time intervals of 60 s", "แบ่งตามเวลา ช่วงละ 60 วินาที"),
    "trace": ("Measurement results are traceable to the International System of Units (SI) through the reference standards listed, calibrated by [accredited calibration body].",
              "ผลการวัดสอบกลับได้ถึงหน่วย SI ผ่านเครื่องมือมาตรฐานที่ระบุ ซึ่งสอบเทียบโดย [หน่วยงานสอบเทียบที่ได้รับการรับรอง]"),
    "env": ("Environmental conditions", "สภาวะแวดล้อม"),
    "liquid": ("Test liquid", "ของเหลวที่ใช้"),
    "water": ("Distilled water", "น้ำกลั่น"),
    "liquid_t": ("Liquid temp.", "อุณหภูมิน้ำ"),
    "air_t": ("Air temp.", "อุณหภูมิอากาศ"),
    "rh": ("Relative humidity", "ความชื้นสัมพัทธ์"),
    "pressure": ("Air pressure", "ความดันอากาศ"),
    "results": ("Results", "ผลการสอบเทียบ"),
    "c_set": ("Set rate", "ค่าที่ตั้ง"),
    "c_dur": ("Duration", "เวลาวัด"),
    "c_n": ("Intervals", "จำนวนช่วง"),
    "c_meas": ("Measured", "ค่าที่วัดได้"),
    "c_err": ("Error", "คลาดเคลื่อน"),
    "c_u": ("U (k=2)", "U (k=2)"),
    "c_tol": ("Tolerance", "เกณฑ์"),
    "c_res": ("Result", "ผล"),
    "min": ("min", "นาที"),
    "pass": ("PASS", "ผ่าน"),
    "fail": ("FAIL", "ไม่ผ่าน"),
    "np": ("N/P", "ไม่ได้ทดสอบ"),
    "na": ("N/A", "ไม่มี"),
    "err_def": ("Error = (Q<sub>measured</sub> − Q<sub>set</sub>) / Q<sub>set</sub> × 100. Measured flow is the mean of all intervals, corrected to volume at 20 °C.",
                "ความคลาดเคลื่อน = (Q<sub>วัดได้</sub> − Q<sub>ตั้ง</sub>) / Q<sub>ตั้ง</sub> × 100 · ค่าที่วัดได้คือค่าเฉลี่ยของทุกช่วงวัด แปลงเป็นปริมาตรที่ 20 °C"),
    "u_def": ("U is the expanded uncertainty with coverage factor k = 2, approximately 95 % confidence (JCGM 100:2008).",
              "U คือความไม่แน่นอนขยาย ตัวประกอบครอบคลุม k = 2 ที่ระดับความเชื่อมั่นประมาณ 95 % (JCGM 100:2008)"),
    "conformity": ("Statement of conformity", "ข้อความแสดงความสอดคล้อง"),
    "conf_text": ("The item conforms to the stated tolerance at all tested rates. Decision rule: simple acceptance, guard band w = 0 (ILAC-G8:09/2019). The measurement uncertainty is reported but not applied to the decision.",
                  "เครื่องเป็นไปตามเกณฑ์ที่กำหนดทุกอัตราที่ทดสอบ · กฎการตัดสิน simple acceptance ไม่มี guard band (w = 0) ตาม ILAC-G8:09/2019 · รายงานค่าความไม่แน่นอนไว้ แต่ไม่นำมาใช้ตัดสิน"),
    "overall": ("Overall", "ผลรวม"),
    "calibrated_by": ("Calibrated by", "ผู้สอบเทียบ"),
    "checked_by": ("Checked by", "ผู้ทวนสอบ"),
    "approved_by": ("Approved by", "ผู้อนุมัติ"),
    "inspected_by": ("Inspected by", "ผู้ตรวจสภาพ"),
    "received_by": ("Received by (customer)", "ผู้รับเครื่อง (โรงพยาบาล)"),
    "tested_by": ("Tested by", "ผู้ทดสอบ"),
    "r_cal": ("Calibration engineer", "วิศวกรสอบเทียบ"),
    "r_chk": ("Technical reviewer", "ผู้ตรวจทานทางเทคนิค"),
    "r_app": ("Authorized signatory", "ผู้มีอำนาจลงนาม"),
    "r_tm": ("Technical manager", "ผู้จัดการวิชาการ"),
    "r_svc": ("Service engineer", "วิศวกรบริการ"),
    "r_pos": ("Position", "ตำแหน่ง"),
    "n_cal": ("[Operator name]", "[ชื่อผู้สอบเทียบ]"),
    "n_chk": ("[Reviewer name]", "[ชื่อผู้ทวนสอบ]"),
    "n_app": ("[Approver name]", "[ชื่อผู้อนุมัติ]"),
    "n_tech": ("[Technician name]", "[ชื่อผู้ตรวจ]"),
    "n_cust": ("[Name]", "[ชื่อ-นามสกุล]"),
    "sign": ("Signature", "ลงชื่อ"),
    "stamp": ("Laboratory stamp", "ตราประทับ"),
    "disclaimer": ("The results relate only to the item calibrated. This certificate shall not be reproduced except in full without written approval of the laboratory.",
                   "ผลการสอบเทียบนี้ใช้กับเครื่องที่ระบุเท่านั้น ห้ามคัดลอกใบรับรองบางส่วนโดยไม่ได้รับอนุญาตเป็นลายลักษณ์อักษรจากห้องปฏิบัติการ"),
    "generated": ("Generated by DeltaM 0.3.0", "จัดทำโดย DeltaM 0.3.0"),
    "end_cert": ("END OF CERTIFICATE", "สิ้นสุดใบรับรอง"),
    "per_interval": ("Results per interval", "ผลรายช่วงวัด"),
    "ri_n": ("Intervals (pump cycles)", "จำนวนช่วงวัด (รอบปั๊ม)"),
    "ri_period": ("Mean cycle period", "คาบรอบเฉลี่ย"),
    "ri_vol": ("Volume per cycle", "ปริมาตรต่อรอบ"),
    "ri_raw": ("Uncorrected flow (1 g = 1 ml)", "อัตราไหลก่อนแก้ (1 g = 1 ml)"),
    "ri_flow": ("Corrected flow", "อัตราไหลหลังแก้"),
    "ri_err": ("Error · ±2SD", "คลาดเคลื่อน · ±2SD"),
    "ri_pre": ("Pre-run (start mode)", "ช่วงก่อนวัด (โหมดเริ่ม)"),
    "interval": ("interval", "ช่วงวัดที่"),
    "legend": ("— error per interval   — mean   - - tolerance ±5 %", "— ค่าแต่ละช่วง   — ค่าเฉลี่ย   - - เกณฑ์ ±5 %"),
    "corrections": ("Corrections applied", "การแก้ค่าที่ใช้"),
    "co_rw": ("Water density at {t} °C", "ความหนาแน่นน้ำที่ {t} °C"),
    "co_ra": ("Air density", "ความหนาแน่นอากาศ"),
    "co_z": ("Z factor (ISO 4787)", "ตัวประกอบ Z (ISO 4787)"),
    "co_ev": ("Evaporation (self-check)", "การระเหย (ตรวจตัวเอง)"),
    "co_dt": ("Balance sampling interval", "ช่วงเวลาอ่านค่าตราชั่ง"),
    "record": ("Data record", "บันทึกข้อมูลดิบ"),
    "raw": ("Raw data {r} ml/h · SHA-256", "ข้อมูลดิบ {r} ml/h · SHA-256"),
    "retained": ("Retained at laboratory", "เก็บรักษาที่ห้องปฏิบัติการ"),
    "years": ("[n] years", "[n] ปี"),
    "budget": ("Uncertainty budget · 50 ml/h", "งบความไม่แน่นอน · 50 ml/h"),
    "b_src": ("Source", "แหล่งความไม่แน่นอน"),
    "b_type": ("Type", "ประเภท"),
    "b_u": ("u, %", "u, %"),
    "b_share": ("Share", "สัดส่วน"),
    "b_rep": ("Repeatability of cycle flow, s/√n", "ความซ้ำของอัตราไหลรายรอบ s/√n"),
    "b_ev": ("Evaporation from the vessel", "การระเหยจากภาชนะ"),
    "b_set": ("Set and tubing compliance", "ความยืดหยุ่นของสายและชุดให้"),
    "b_bal": ("Balance calibration and linearity", "การสอบเทียบและความเป็นเชิงเส้นของตราชั่ง"),
    "b_time": ("Sample timing", "การจับเวลา"),
    "b_rho": ("Water and air density", "ความหนาแน่นน้ำและอากาศ"),
    "b_uc": ("Combined u<sub>c</sub> · expanded U = 2·u<sub>c</sub>", "ความไม่แน่นอนรวม u<sub>c</sub> · ขยาย U = 2·u<sub>c</sub>"),
    "conf_chart": ("Error ± U against tolerance", "ความคลาดเคลื่อน ± U เทียบเกณฑ์"),
    "chart_key": ("● error   ── U (k = 2)   shaded = tolerance ±5 %", "● คลาดเคลื่อน   ── U (k = 2)   แถบ = เกณฑ์ ±5 %"),
    # Inspection
    "qual": ("Qualitative inspection", "ตรวจสภาพและการทำงาน"),
    "c_item": ("Item", "รายการ"),
    "c_pass": ("Pass", "ผ่าน"),
    "c_fail": ("Fail", "ไม่ผ่าน"),
    "c_na": ("N/A", "ไม่มี"),
    "quant": ("Quantitative tests", "ทดสอบสมรรถนะ"),
    "c_test": ("Test", "รายการทดสอบ"),
    "c_setting": ("Setting", "ค่าตั้ง"),
    "c_limit": ("Limit", "เกณฑ์"),
    "q_flow": ("Flow accuracy, gravimetric", "ความแม่นยำอัตราไหล (ชั่งน้ำหนัก)"),
    "q_occ": ("Occlusion alarm, time to alarm", "สัญญาณเตือนอุดตัน (เวลาจนเตือน)"),
    "q_es": ("Electrical safety, IEC 62353", "ความปลอดภัยทางไฟฟ้า IEC 62353"),
    "np_note": ("N/P = not performed", "ไม่ได้ทดสอบ = ไม่มีเครื่องวิเคราะห์ในวันตรวจ"),
    "accessories": ("Accessories received", "อุปกรณ์ที่รับมา"),
    "acc": (["Power cord", "Pole clamp", "User manual"], ["สายไฟ", "ตัวยึดเสา", "คู่มือการใช้งาน"]),
    "parts": ("Parts replaced", "อะไหล่ที่เปลี่ยน"),
    "c_part": ("Part", "อะไหล่"),
    "c_basis": ("Basis", "ประเภท"),
    "c_warr": ("Warranty", "การรับประกัน"),
    "p1": ("Plunger clamp", "ตัวยึดก้านดัน"),
    "p1b": ("Warranty claim", "เคลมประกัน"),
    "p1w": ("from 2026-03-02, not restarted", "นับจาก 2 มี.ค. 2569 ไม่เริ่มนับใหม่"),
    "p2": ("Battery pack", "แบตเตอรี่"),
    "p2b": ("Chargeable", "คิดค่าบริการ"),
    "p2w": ("until 2027-11-13", "ถึง 13 พ.ย. 2570"),
    "conclusion": ("Conclusion", "สรุปผล"),
    "concl_text": ("All performed checks are within limits. The equipment is fit for clinical use. Remarks: [—]",
                   "ผลการตรวจทุกรายการที่ทำอยู่ในเกณฑ์ เครื่องพร้อมใช้งานทางคลินิก · หมายเหตุ: [—]"),
    "fit": ("Fit for use", "พร้อมใช้งาน"),
    # Quick test
    "qt_rate": ("Set rate", "ค่าที่ตั้ง"),
    "qt_time": ("Test time", "เวลาทดสอบ"),
    "cycles": ("cycles", "รอบ"),
    "limit": ("limit", "เกณฑ์"),
    "qt_note": ("Screening check by gravimetric method with balance A&amp;D GF-300 (S/N 14654769). A quick function test confirms basic delivery at one rate only. It does not replace periodic calibration or inspection.",
                "ตรวจคัดกรองด้วยวิธีชั่งน้ำหนัก ตราชั่ง A&amp;D GF-300 (S/N 14654769) · ทดสอบเพียงอัตราเดียวเพื่อยืนยันการทำงานเบื้องต้น ไม่ใช้แทนการสอบเทียบหรือการตรวจสภาพตามรอบ"),
    "remarks": ("Remarks", "หมายเหตุ"),
    "labels_cut": ("Device labels · cut along the line", "ป้ายติดเครื่อง · ตัดตามเส้นประ"),
    "tested": ("TESTED", "ทดสอบแล้ว"),
    "dnu": ("DO NOT USE", "ห้ามใช้งาน"),
    "l_test": ("Test", "การทดสอบ"),
    "l_test_v": ("Quick function test", "ทดสอบการทำงานเบื้องต้น"),
    "l_reason": ("Reason", "สาเหตุ"),
    "l_reason_v": ("Flow error outside limit", "อัตราไหลคลาดเคลื่อนเกินเกณฑ์"),
    "l_contact": ("Contact", "ติดต่อ"),
    "l_contact_v": ("[Service phone]", "[เบอร์ศูนย์บริการ]"),
    "l_by": ("By", "ผู้ทดสอบ"),
    "l_by_v": ("[Initials]", "[ชื่อย่อ]"),
    "l_dnu_note": ("ห้ามใช้งาน — ส่งซ่อม", "Do not use — send for repair"),
    "labels_note": ("The program prints only the label that matches the result. Both are shown here for review.",
                    "โปรแกรมจะพิมพ์เฉพาะป้ายที่ตรงกับผล ที่แสดงทั้งสองแบบเพื่อให้พิจารณา"),
}

CHECK_ITEMS = [
    (("Housing and labels", "ตัวเครื่องและฉลาก"), "p"), (("Pole clamp", "ตัวยึดเสา"), "p"),
    (("Power cord and plug", "สายไฟและปลั๊ก"), "p"), (("Battery operation", "การทำงานด้วยแบตเตอรี่"), "p"),
    (("Keypad and controls", "ปุ่มกดและการควบคุม"), "p"), (("Display and indicators", "จอแสดงผลและไฟสถานะ"), "p"),
    (("Syringe clamp and plunger holder", "ตัวยึดกระบอกฉีดและก้านดัน"), "p"),
    (("Syringe size detection", "การตรวจจับขนาดกระบอกฉีด"), "p"),
    (("Audible and visual alarms", "สัญญาณเตือนเสียงและแสง"), "p"), (("Nurse call output", "สัญญาณเรียกพยาบาล"), "na"),
]

TH_MONTH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def t(key, L, **kw):
    s = S[key][0 if L == "en" else 1]
    return s.format(**kw) if kw and isinstance(s, str) else s


def other(key, L):
    """ข้อความภาษาอีกภาษา (ใช้เป็นหัวข้อรอง)"""
    return S[key][1 if L == "en" else 0]


def dt(iso, L):
    """วันที่: EN = ISO 2026-11-13 · TH = 13 พ.ย. 2569 (พ.ศ.)"""
    if L == "en":
        return iso
    parts = iso.split(" ")
    ymd = parts[0].split("-")
    tail = f" {parts[1]} น." if len(parts) > 1 else ""
    if len(ymd) == 2:
        return f"{TH_MONTH[int(ymd[1]) - 1]} {int(ymd[0]) + 543}"
    return f"{int(ymd[2])} {TH_MONTH[int(ymd[1]) - 1]} {int(ymd[0]) + 543}{tail}"


def num_cls(L):
    """ตัวเลข/วันที่: EN ใช้ mono, TH ใช้ sans (mono ไม่มีอักษรไทย)"""
    return "mono" if L == "en" else "tnum"


# ---------------------------------------------------------------- ข้อมูลสมมติ
def _rho_water(tc):
    a1, a2, a3, a4, a5 = -3.983035, 301.797, 522528.9, 69.34881, 999.974950
    return a5 * (1 - (tc + a1) ** 2 * (tc + a2) / (a3 * (tc + a4))) / 1000


def _rho_air(p, rh, tc):
    return (0.34848 * p - 0.009 * rh * math.exp(0.061 * tc)) / (273.15 + tc) / 1000


def _cal(periods, seeds):
    rates = []
    for r, period, raw, seed in zip(INFUSION["rates"], periods, (9.83, 50.20, 195.4), seeds):
        s1 = r["meas"] * r["sd2"] / 200
        flows = series(r["n"], r["meas"], s1, seed, ar=0.15)
        rates.append(dict(r, period=period, raw=raw, flows=flows, err=(r["meas"] - r["set"]) / r["set"] * 100,
                          vol=r["meas"] * period / 3600, dur=r["n"] * period / 60))
    rw, ra = _rho_water(23.4), _rho_air(1008, 56, 24.1)
    return dict(rates=rates, rw=rw, ra=ra, z=1 / (rw - ra) * (1 - ra / 8.0), water=23.4, air=24.1, rh=56, hpa=1008)


CAL = dict(job="MCI-0142", cert="DM-C-2611-0042", date="2026-11-13", issue="2026-11-14", received="2026-11-12",
           brand="Terumo", model="TE-171", serial="17110582", asset="ICU-IP-031", dept="ICU 2",
           **_cal((72.2, 15.2, 3.9), (101, 202, 304)))
# A-TH ใช้ค่าของแบบ A เดิม (คาบ 10 ml/h = 71.4 s)
CAL_A = dict(CAL, **_cal((71.4, 15.2, 3.9), (101, 202, 304)))

HOSP = dict(name=("โรงพยาบาลตัวอย่าง", "โรงพยาบาลตัวอย่าง"), province=("Khon Kaen", "ขอนแก่น"),
            contact=("[Contact name] · [position]", "[ชื่อผู้ติดต่อ] · [ตำแหน่ง]"), tel="[—]", ref="[PO no.]")

INSP = dict(job="MCS-0388", no="DM-I-2611-0107", date="2026-11-13", due="2027-05", brand="Terumo", model="TE-331",
            serial="33104417", asset="NICU-SP-007", dept="NICU", syringe=("Terumo 50 ml", "Terumo 50 ml"),
            set=SYR_INSP["set"], meas=SYR_INSP["meas"], minutes=SYR_INSP["minutes"], limit=SYRINGE["limit"],
            occ=("5 ml/h · level M", "2:40 min", "≤ 5 min [mfr]", "p"))
# A-TH: ค่าของแบบ A เดิม (50 ml/h, 49.12, occlusion ไม่ได้ทดสอบ)
INSP_A = dict(INSP, asset="NICU-SP-012", syringe=("[Brand] 50 ml", "[ยี่ห้อ] 50 ml"), set=50.0, meas=49.12,
              occ=("[level]", "—", "[—]", "np"))

QT = dict(job="MCI-0151", no="DM-Q-2611-0215", date="2026-11-13 14:22", serial="17110609", dept="ER",
          set=INF_QT["set"], meas=INF_QT["meas"], n=INF_QT["n"], period=INF_QT["period"])
QT["secs"] = round(QT["n"] * QT["period"])
# A-TH: แบบ A เดิมเขียน 2:00 · 31 cycles (คาบ 15.2 s ใน 2 นาที ได้ ~8 รอบ) → แก้เป็น 8 รอบ
QT_A = dict(QT, n=8, secs=120)

BUDGET = [("b_rep", "A", 0.16), ("b_ev", "B", 0.18), ("b_set", "B", 0.12), ("b_bal", "B", 0.08),
          ("b_time", "B", 0.02), ("b_rho", "B", 0.02)]


def mmss(s):
    return f"{s // 60}:{s % 60:02d}"


# ---------------------------------------------------------------- บล็อก HTML
def kv(rows, cls="kv", L="en"):
    out = []
    for lab, val, *opt in rows:
        mono = opt and opt[0]
        out.append(f'<span class="lbl">{lab}</span><span class="val{" " + num_cls(L) if mono else ""}">{val}</span>')
    return f'<div class="{cls}">{"".join(out)}</div>'


def sec(n, key, L, cls="sec", extra=""):
    num = f'<span class="sec-n">{n}</span>' if n else ""
    return (f'<h2 class="{cls}">{num}<span class="sec-t">{t(key, L)}</span>'
            f'<span class="sec-th">{other(key, L)}</span>{extra}</h2>')


def customer_rows(L, D=CAL, full=True):
    i = 0 if L == "en" else 1
    rows = [(t("hospital", L), HOSP["name"][i]), (t("department", L), D["dept"]), (t("province", L), HOSP["province"][i])]
    if full:
        rows += [(t("contact", L), HOSP["contact"][i]), (t("tel", L), HOSP["tel"], True),
                 (t("cust_ref", L), HOSP["ref"], True)]
    return rows


def item_rows(L, D=CAL, kind="inf"):
    rows = [(t("description", L), t("inf_desc" if kind == "inf" else "syr_desc", L)),
            (t("mfr_model", L), f'{D["brand"]} · {D["model"]}'),
            (t("sn_asset", L), f'{D["serial"]} · {D["asset"]}', True)]
    if kind == "inf":
        rows.append((t("admin_set", L), "[Set brand] [Set model]" if L == "en" else "[ยี่ห้อชุดสาย] [รุ่น]"))
    else:
        rows.append((t("syringe_used", L), D["syringe"][0 if L == "en" else 1]))
    return rows


def balance_rows(L, full=True):
    rows = [(t("bal_make", L), "A&amp;D GF-300"), (t("bal_sn", L), "14654769", True),
            (t("bal_cap", L), "310 g · 0.001 g", True)]
    if full:
        rows += [(t("bal_cert", L), "[cert. no.]" if L == "en" else "[เลขที่ใบรับรอง]"),
                 (t("bal_by", L), t("bal_lab", L)), (t("bal_due", L), "[—] · [—]")]
    rows.append((t("bal_check", L), t("bal_check_v", L)))
    return rows


def env_rows(L, D=CAL):
    return [(t("liquid", L), t("water", L)), (t("liquid_t", L), f'{D["water"]} °C', True),
            (t("air_t", L), f'{D["air"]} °C', True), (t("rh", L), f'{D["rh"]} %', True),
            (t("pressure", L), f'{D["hpa"]} hPa', True)]


def pass_word(L, cls="pass"):
    return f'<span class="{cls}">{t("pass", L)}</span>'


def results_table(L, D=CAL, cls="t", pass_cls="pass"):
    nc = num_cls(L)
    head = (f'<tr><th>{t("c_set", L)}<br>ml/h</th><th>{t("c_dur", L)}<br>{t("min", L)}</th><th>{t("c_n", L)}<br>n</th>'
            f'<th>{t("c_meas", L)}<br>ml/h</th><th>{t("c_err", L)}<br>%</th><th>±2SD<br>%</th><th>{t("c_u", L)}<br>%</th>'
            f'<th>{t("c_tol", L)}<br>%</th><th>{t("c_res", L)}</th></tr>')
    rows = "".join(
        f'<tr><td class="{nc}" style="font-weight: 500">{r["set"]:.1f}</td><td class="{nc}">{r["dur"]:.1f}</td>'
        f'<td class="{nc}">{r["n"]}</td><td class="{nc}">{r["meas"]:.2f}</td><td class="{nc}">{f(r["err"], 1, True)}</td>'
        f'<td class="{nc}">{r["sd2"]:.1f}</td><td class="{nc}">{r["U"]:.1f}</td><td class="{nc}">±{INFUSION["limit"]:.1f}</td>'
        f'<td>{pass_word(L, pass_cls)}</td></tr>' for r in D["rates"])
    return f'<table class="{cls}"><thead>{head}</thead><tbody>{rows}</tbody></table>'


def conformity_chart(L, D=CAL, w=698, row_h=30, accent=INF):
    """ความคลาดเคลื่อน ± U ราย rate เทียบแถบเกณฑ์ ±5 %"""
    ax = Ax(84, w - 40, 0, 0, -6.5, 6.5, 0, 1)
    out, y = [], 18
    for v in (-5, 0, 5):
        out.append(T(ax.sx(v), 12, f(v, 0, True) + " %" if v else "0", anchor="middle", fill=GREY))
    top = y
    for r in D["rates"]:
        out.append(R(ax.sx(-5), y, ax.sx(5) - ax.sx(-5), row_h - 6, accent["tint"]))
        out.append(L_(ax.sx(0), y, ax.sx(0), y + row_h - 6))
        e, u = r["err"], r["U"]
        cy = y + (row_h - 6) / 2
        out.append(LN(ax.sx(e - u), cy, ax.sx(e + u), cy, INK, 2.5))
        for v in (e - u, e + u):
            out.append(LN(ax.sx(v), cy - 5, ax.sx(v), cy + 5, INK, 1.5))
        out.append(C(ax.sx(e), cy, 4.5, INK))
        out.append(T(0, cy + 4, f'{r["set"]:g} ml/h', fill=INK, weight=600))
        out.append(T(w, cy + 4, f'{f(e, 1, True)} ± {u:.1f}', anchor="end", fill=INK))
        y += row_h
    for v in (-5, 5):
        out.append(LN(ax.sx(v), top - 2, ax.sx(v), y - 4, accent["ink"], 1.5, "4 3"))
    out.append(T(84, y + 12, t("chart_key", L), fill=GREY))
    return svg(w, y + 18, "Error with expanded uncertainty for each rate against the ±5 % tolerance", out)


def L_(x1, y1, x2, y2):
    return LN(x1, y1, x2, y2, DIM, 1)


def interval_chart(L, r, w=424, h=176, accent=INF, lim=5.0, legend=True):
    """error รายช่วง + ค่าเฉลี่ย + เกณฑ์ ±5 % (โครงเดียวกับแบบ A) — วาดที่ขนาดจริง ไม่ย่อด้วย viewBox (ตัวอักษรคง 12 px)"""
    errs = [(q - r["set"]) / r["set"] * 100 for q in r["flows"]]
    bottom = h - (42 if legend else 22)
    ax = Ax(40, w - 4, 6, bottom, 1, len(errs), -10, 10)
    out = [R(ax.x0, ax.sy(lim), ax.x1 - ax.x0, ax.sy(-lim) - ax.sy(lim), accent["tint"]),
           LN(ax.x0, ax.sy(lim), ax.x1, ax.sy(lim), accent["ink"], 1, "4 3"),
           LN(ax.x0, ax.sy(-lim), ax.x1, ax.sy(-lim), accent["ink"], 1, "4 3"),
           LN(ax.x0, ax.sy(0), ax.x1, ax.sy(0), DIM), LN(ax.x0, ax.y0, ax.x0, ax.y1, DIM), LN(ax.x0, ax.y1, ax.x1, ax.y1, DIM)]
    for v, lab in ((lim, "+5"), (0, "0"), (-lim, "−5")):
        out.append(T(ax.x0 - 6, ax.sy(v) + 4, lab, anchor="end", fill=GREY))
    out.append(T(ax.x0 - 6, 14, "%", anchor="end", fill=GREY))
    xs = list(range(1, len(errs) + 1))
    out.append(PL(ax.pts(xs, [max(-9.5, min(9.5, e)) for e in errs]), INK, 1.2))
    out.append(LN(ax.x0, ax.sy(r["err"]), ax.x1, ax.sy(r["err"]), "#E0731A", 1.5))
    ty = bottom + 16
    out.append(T(ax.x0, ty, "1", fill=GREY))
    out.append(T(ax.x1, ty, f'{len(errs)}', anchor="end", fill=GREY))
    out.append(T((ax.x0 + ax.x1) / 2, ty, t("interval", L), anchor="middle", fill=GREY))
    if legend:
        out.append(T(ax.x1, h - 6, t("legend", L), anchor="end", fill=GREY))
    return svg(w, h, f'Error per interval at {r["set"]:g} ml/h', out)


def interval_rows(L, r):
    pre = r["pre"] if L == "en" else r["pre"].replace("auto", "อัตโนมัติ").replace("delay", "หน่วงเวลา").replace(" s", " วินาที")
    return [(t("ri_n", L), str(r["n"])), (t("ri_period", L), f'{r["period"]} s'), (t("ri_vol", L), f'{r["vol"]:.3f} ml'),
            (t("ri_raw", L), f'{r["raw"]:.2f} ml/h' if r["raw"] < 100 else f'{r["raw"]:.1f} ml/h'), (t("ri_flow", L), f'{r["meas"]:.2f} ml/h'),
            (t("ri_err", L), f'{f(r["err"], 1, True)} % · {r["sd2"]} %'), (t("ri_pre", L), pre)]


def rows_html(rows, cls="row"):
    return "".join(f'<div class="{cls}"><span>{a}</span><span>{b}</span></div>' for a, b in rows)


def correction_rows(L, D=CAL):
    def sp(x, d):
        s = f"{x:.{d}f}"
        return s[:5] + " " + s[5:] if d > 3 else s
    return [(t("co_rw", L, t=D["water"]), f'{sp(D["rw"], 5)} g/ml'), (t("co_ra", L), f'{sp(D["ra"], 5)} g/ml'),
            (t("co_z", L), f'{sp(D["z"], 5)} ml/g'), (t("co_ev", L), "−0.012 g/h"), (t("co_dt", L), "0.20 s")]


def record_rows(L):
    return [(t("raw", L, r=10), "9f3c…a41e"), (t("raw", L, r=50), "27be…0c95"), (t("raw", L, r=200), "c71d…5b28"),
            (t("retained", L), t("years", L))]


def budget_table(L, cls="t"):
    uc = math.sqrt(sum(u * u for _, _, u in BUDGET))
    tot = uc * uc
    rows = "".join(f'<tr><td>{t(k, L)}</td><td>{typ}</td><td class="{num_cls(L)}">{u:.2f}</td>'
                   f'<td class="{num_cls(L)}">{u * u / tot * 100:.0f} %</td></tr>' for k, typ, u in BUDGET)
    rows += (f'<tr><td style="font-weight: 600">{t("b_uc", L)}</td><td></td><td class="{num_cls(L)}" style="font-weight: 600">{uc:.2f}</td>'
             f'<td class="{num_cls(L)}" style="font-weight: 600">U = {2 * uc:.1f} %</td></tr>')
    return (f'<table class="{cls}"><thead><tr><th>{t("b_src", L)}</th><th>{t("b_type", L)}</th><th>{t("b_u", L)}</th>'
            f'<th>{t("b_share", L)}</th></tr></thead><tbody>{rows}</tbody></table>')


def ref_table(L, cls="t"):
    nc = num_cls(L)
    return (f'<table class="{cls}"><thead><tr><th>{t("ref_std", L)}</th><th>{t("bal_sn", L)}</th><th>{t("cert_due", L)}</th></tr></thead><tbody>'
            f'<tr><td>A&amp;D GF-300</td><td class="{nc}">14654769</td><td class="{nc}">[—] / [—]</td></tr>'
            f'<tr><td>{t("thermometer", L)}</td><td class="{nc}">[—]</td><td class="{nc}">[—] / [—]</td></tr>'
            f'<tr><td>{t("thermo", L)}</td><td class="{nc}">[—]</td><td class="{nc}">[—] / [—]</td></tr></tbody></table>')


def sig_roles(L, kind):
    """ช่องลายเซ็น: cal = 3 ช่อง · insp = 2 ช่อง · (หัวช่อง, ชื่อ, ตำแหน่ง · วันที่)"""
    if kind == "cal":
        return [(t("calibrated_by", L), t("n_cal", L), f'{t("r_cal", L)} · {dt(CAL["date"], L)}'),
                (t("checked_by", L), t("n_chk", L), f'{t("r_chk", L)} · {dt(CAL["issue"], L)}'),
                (t("approved_by", L), t("n_app", L), f'{t("r_app", L)} · {dt(CAL["issue"], L)}')]
    return [(t("inspected_by", L), t("n_tech", L), f'{t("r_svc", L)} · {dt(INSP["date"], L)}'),
            (t("received_by", L), t("n_cust", L), f'{t("r_pos", L)} · {t("date", L)}')]


def checklist_tables(L, items=CHECK_ITEMS, cls="t chk"):
    i = 0 if L == "en" else 1
    half = (len(items) + 1) // 2

    def tab(part):
        rows = "".join(f'<tr><td>{n[i]}</td>' + "".join(
            f'<td><span class="box">{"✓" if m == k else ""}</span></td>' for k in ("p", "f", "na")) + "</tr>"
                       for n, m in part)
        return (f'<table class="{cls}"><thead><tr><th>{t("c_item", L)}</th><th>{t("c_pass", L)}</th>'
                f'<th>{t("c_fail", L)}</th><th>{t("c_na", L)}</th></tr></thead><tbody>{rows}</tbody></table>')
    return tab(items[:half]), tab(items[half:])


def quant_table(L, D=INSP, cls="t", pass_cls="pass"):
    nc = num_cls(L)
    e = (D["meas"] - D["set"]) / D["set"] * 100
    occ = D["occ"]
    res = lambda m: pass_word(L, pass_cls) if m == "p" else f'<span class="lbl">{t("np", L)}</span>'
    meas = f'{D["meas"]:.3f}' if D["set"] < 10 else f'{D["meas"]:.2f}'
    return (f'<table class="{cls}"><thead><tr><th>{t("c_test", L)}</th><th>{t("c_setting", L)}</th><th>{t("c_meas", L)}</th>'
            f'<th>{t("c_err", L)}</th><th>{t("c_limit", L)}</th><th>{t("c_res", L)}</th></tr></thead><tbody>'
            f'<tr><td>{t("q_flow", L)}</td><td class="{nc}">{D["set"]:g} ml/h · {D["minutes"]} {t("min", L)}</td>'
            f'<td class="{nc}">{meas} ml/h</td><td class="{nc}">{f(e, 1, True)} %</td><td class="{nc}">±{D["limit"]:.1f} %</td><td>{res("p")}</td></tr>'
            f'<tr><td>{t("q_occ", L)}</td><td class="{nc}">{occ[0]}</td><td class="{nc}">{occ[1]}</td><td class="{nc}">—</td>'
            f'<td class="{nc}">{occ[2]}</td><td>{res(occ[3])}</td></tr>'
            f'<tr><td>{t("q_es", L)}</td><td class="{nc}">Class I</td><td class="{nc}">—</td><td class="{nc}">—</td>'
            f'<td class="{nc}">[—]</td><td>{res("np")}</td></tr></tbody></table>')


def parts_table(L, cls="t"):
    nc = num_cls(L)
    return (f'<table class="{cls}"><thead><tr><th>{t("c_part", L)}</th><th>{t("c_basis", L)}</th><th>{t("c_warr", L)}</th></tr></thead><tbody>'
            f'<tr><td>{t("p1", L)}</td><td>{t("p1b", L)}</td><td class="{nc}">{t("p1w", L)}</td></tr>'
            f'<tr><td>{t("p2", L)}</td><td>{t("p2b", L)}</td><td class="{nc}">{t("p2w", L)}</td></tr></tbody></table>')


def thai_tweak(L):
    """CSS เพิ่มสำหรับฉบับไทย: บรรทัดสูงขึ้นเพื่อสระบน/ล่าง"""
    return "" if L == "en" else ".lbl,.val,td,th,p,span{line-height:1.45}"


BASE_CSS = """
.mono{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}
.tnum{font-variant-numeric:tabular-nums lining-nums}
.box{display:inline-flex;width:13px;height:13px;border:1px solid #5A626C;vertical-align:middle;align-items:center;justify-content:center;font-size:12px;line-height:11px;font-weight:700}
svg text{font-family:'IBM Plex Sans','IBM Plex Sans Thai',sans-serif}
sub{font-size:12px;line-height:0;vertical-align:-3px}
"""
