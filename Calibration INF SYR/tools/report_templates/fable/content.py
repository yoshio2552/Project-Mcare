"""เนื้อหาร่วมของแบบ FableA–E: ข้อความ ไทย/อังกฤษ + ข้อมูลสมมติ + รายการตรวจแยก Infusion / Syringe

กติกาของชุดนี้ (ผู้ใช้กำหนด 2026-11-17):
  - ไม่มีเลขที่รายงาน ไม่มีหัวข้อบันทึกข้อมูลดิบ · ไม่ใช้วงเล็บ/วงเล็บเหลี่ยมในเอกสาร
  - คำอธิบายการคำนวณใช้ภาษาคนอ่านเข้าใจ (ไม่มี "ก่อนแก้ / หลังแก้ / การแก้ค่าที่ใช้")
  - Inspection แยก Infusion / Syringe · 2 หน้า (รายการตรวจ + ผลวัด rate เดียว) · ลายเซ็น 2 ช่อง
  - Calibration 3 หน้า (รายการตรวจที่ไม่มี rate · สรุปผล ลายเซ็น 3 ช่อง · รายงานทางเทคนิค)
  - Occlusion วัด 3 ครั้ง · ความปลอดภัยทางไฟฟ้าเหลือแรงดันไฟ + กระแสรั่ว (ไม่มี Ground)
ตัวเลข ชื่อโรงพยาบาล เป็นข้อมูลสมมติทั้งหมด (ค่า Calibration ชุดเดียวกับแบบ Q–Z / A1–A5)
"""

COMPANY = "M.Care Engineering Co., Ltd."
ADDRESS = {
    "th": "56-56/1 หมู่ 7 ต.เสาธงหิน อ.บางใหญ่ จ.นนทบุรี 11140",
    "en": "56-56/1 Moo 7, Saothonghin, Bangyai, Nonthaburi 11140",
}

# ---------------------------------------------------------------- ข้อความ
TEXT = {
    "th": dict(
        page="หน้า", made="จัดทำด้วย DeltaM 0.3.0",
        insp_title="รายงานการตรวจสภาพเครื่อง", insp_kind="INSPECTION REPORT",
        meas_title="ผลวัดอัตราการไหล", meas_kind="FLOW RATE MEASUREMENT",
        cal_title="ใบรับรองผลการสอบเทียบ", cal_kind="CALIBRATION CERTIFICATE",
        tech_title="รายงานทางเทคนิค", tech_kind="TECHNICAL REPORT",
        infusion="เครื่องให้สารละลาย", syringe="เครื่องให้ยาด้วยกระบอกฉีด",
        infusion_en="Infusion pump", syringe_en="Syringe pump",
        job="เลขงาน", date="วันที่", service="ประเภทงาน", device_kind="ชนิดเครื่อง",
        pm="บำรุงรักษา", repair="ซ่อม", calib="สอบเทียบ",
        customer="ผู้รับบริการ", device="เครื่องที่ตรวจ", device_cal="เครื่องที่สอบเทียบ",
        hospital="โรงพยาบาล", dept="หน่วยงาน", province="จังหวัด", contact="ผู้ติดต่อ", tel="โทรศัพท์",
        brand="ยี่ห้อ รุ่น", serial="หมายเลขเครื่อง", asset="รหัสครุภัณฑ์", ivset="ชุดให้สารละลาย", syr="กระบอกฉีดที่ใช้",
        visual="ตรวจสภาพภายนอก", function="ตรวจการทำงาน", performance="ตรวจสมรรถนะ",
        safety="ความปลอดภัยทางไฟฟ้า", final="ตรวจขั้นสุดท้าย",
        item="รายการ", ok="ผ่าน", fail="ไม่ผ่าน", na="ไม่มี",
        supply="แรงดันไฟที่จ่าย", leak="กระแสรั่วของเครื่อง", limit="เกณฑ์", not_over="ไม่เกิน",
        final_visual="ตรวจความเรียบร้อยทั้งเครื่อง", final_label="ติดป้ายตรวจสภาพแล้ว",
        received="อุปกรณ์ที่รับมากับเครื่อง", parts="อะไหล่ที่เปลี่ยน", parts_n="เปลี่ยน {n} รายการ", claim_n="เคลมประกัน {n} รายการ",
        claim="เคลมประกัน", no_parts="ไม่มีการเปลี่ยนอะไหล่",
        remarks="หมายเหตุ", result="ผลการตรวจ", result_cal="ผลการสอบเทียบ",
        insp_statement="ตรวจสภาพและบำรุงรักษาเรียบร้อย เครื่องพร้อมใช้งานตามปกติ",
        cal_statement="เครื่องจ่ายได้ตรงตามเกณฑ์ทุกอัตราที่สอบเทียบ สัญญาณเตือนการอุดตันทำงานในช่วงที่กำหนด",
        inspected_by="ผู้ตรวจ", received_by="ผู้รับเครื่อง", hospital_side="เจ้าหน้าที่โรงพยาบาล", engineer="วิศวกรบริการ",
        calibrated_by="ผู้สอบเทียบ", reviewed_by="ผู้ทวนสอบ", approved_by="ผู้อนุมัติ", sign_date="วันที่",
        see_p2="ดูหน้า 2", see_cal="ดูผลสอบเทียบหน้า 2",
        set_rate="ค่าที่ตั้ง", measured="ค่าที่วัดได้", error="คลาดเคลื่อน", tolerance="เกณฑ์ยอมรับ", verdict="ผล",
        spread="การกระจาย ±2SD", unc="ความไม่แน่นอน U", duration="เวลาที่วัด", count="จำนวนรอบปั๊ม", count_time="จำนวนช่วงวัด",
        cycle_time="เวลาต่อรอบ", interval_time="ความยาวช่วงวัด", minute="นาที", second="วินาที",
        how="วิธีวัด", how_sec="วิธีวัดและรายละเอียด", detail="รายละเอียดการวัด", tools="เครื่องมือมาตรฐานและสภาวะขณะวัด",
        supervisor="หัวหน้าฝ่ายบริการ", manager="ผู้จัดการฝ่ายเทคนิค",
        how_text="วัดด้วยวิธีชั่งน้ำหนัก ชั่งน้ำที่เครื่องจ่ายออกมาอย่างต่อเนื่อง แล้วคิดเป็นปริมาตรต่อชั่วโมง"
                 "จากความหนาแน่นของน้ำที่อุณหภูมิขณะวัด",
        how_cycle="แบ่งช่วงวัดตามรอบการทำงานของปั๊ม จากยอดถึงยอด", how_time="แบ่งช่วงวัดตามเวลา ช่วงละ 30 วินาที",
        standard="เครื่องมือมาตรฐาน", balance="เครื่องชั่ง", capacity="พิกัด", readability="อ่านละเอียด",
        balance_check="ตรวจด้วยตุ้มน้ำหนัก 50 g ก่อนใช้งาน อ่านได้ 50.000 g",
        conditions="สภาวะขณะวัด", liquid="ของเหลว", water="น้ำกลั่น", water_t="อุณหภูมิน้ำ", air_t="อุณหภูมิอากาศ",
        rh="ความชื้นสัมพัทธ์", pressure="ความดันอากาศ",
        chart_flow="อัตราการไหลของแต่ละรอบปั๊ม", chart_flow_time="อัตราการไหลของแต่ละช่วงวัด",
        chart_x="เวลา นาที", chart_band="ช่วงเกณฑ์ยอมรับ", chart_mean="ค่าเฉลี่ย",
        occl="สัญญาณเตือนการอุดตัน", occl_sub="วัดความดันขณะเครื่องเตือน 3 ครั้ง", occl_level="ระดับที่ตั้ง",
        occl_row="ความดันขณะเตือน", time_no="ครั้งที่", mean="เฉลี่ย", occl_limit="เกณฑ์ของผู้ผลิต",
        results="ผลการสอบเทียบอัตราการไหล",
        unc_note="U คือความไม่แน่นอนของการวัด ที่ระดับความเชื่อมั่นประมาณ 95 % ตัวคูณครอบคลุม k = 2",
        err_note="คลาดเคลื่อน คิดจากค่าที่วัดได้ลบค่าที่ตั้ง หารด้วยค่าที่ตั้ง",
        trace="ผลการวัดสอบกลับได้ถึงหน่วย SI ผ่านเครื่องชั่งมาตรฐานที่ระบุ",
        chart_err="ความคลาดเคลื่อนเทียบเกณฑ์ยอมรับ", chart_err_y="คลาดเคลื่อน %", rate_axis="ค่าที่ตั้ง ml/h",
        per_rate="อัตราการไหลของแต่ละรอบปั๊ม แยกตามค่าที่ตั้ง", stats="สถิติของแต่ละค่าที่ตั้ง",
        lowest="ต่ำสุด", highest="สูงสุด", average="ค่าเฉลี่ย",
        volume="การคิดปริมาตรจากน้ำหนัก", density="ความหนาแน่นของน้ำ", per_gram="น้ำ 1 กรัม คิดเป็น",
        evap="น้ำที่ระเหยระหว่างวัด", evap_v="0.012 กรัมต่อชั่วโมง นำมาชดเชยแล้ว",
        volume_note="ตัวเลขทุกค่าในรายงานนี้เป็นปริมาตรที่คิดตามตารางนี้แล้ว",
        method_ref="อ้างอิง IEC 60601-2-24 และ ISO 4787",
        validity="ผลนี้ใช้กับเครื่องที่ระบุและสภาพ ณ วันที่ตรวจเท่านั้น",
    ),
    "en": dict(
        page="Page", made="Produced with DeltaM 0.3.0",
        insp_title="Inspection Report", insp_kind="SERVICE REPORT",
        meas_title="Flow Rate Measurement", meas_kind="SERVICE REPORT",
        cal_title="Calibration Certificate", cal_kind="CALIBRATION",
        tech_title="Technical Report", tech_kind="CALIBRATION",
        infusion="Infusion pump", syringe="Syringe pump", infusion_en="", syringe_en="",
        job="Job no.", date="Date", service="Service type", device_kind="Device type",
        pm="Preventive maintenance", repair="Repair", calib="Calibration",
        customer="Customer", device="Device inspected", device_cal="Device calibrated",
        hospital="Hospital", dept="Department", province="Province", contact="Contact", tel="Telephone",
        brand="Make and model", serial="Serial no.", asset="Asset code", ivset="Infusion set", syr="Syringe used",
        visual="Visual inspection", function="Function inspection", performance="Performance inspection",
        safety="Electrical safety", final="Final inspection",
        item="Item", ok="Pass", fail="Fail", na="N/A",
        supply="Supply voltage", leak="Equipment leakage current", limit="Limit", not_over="not over",
        final_visual="Whole unit checked", final_label="Inspection label attached",
        received="Accessories received", parts="Parts replaced", parts_n="{n} parts replaced", claim_n="{n} under warranty",
        claim="warranty", no_parts="No parts replaced",
        remarks="Remarks", result="Inspection result", result_cal="Calibration result",
        insp_statement="Inspection and preventive maintenance completed. The unit is ready for normal use.",
        cal_statement="The pump delivers within tolerance at every calibrated rate. The occlusion alarm operates "
                      "within the specified range.",
        inspected_by="Inspected by", received_by="Received by", hospital_side="Hospital staff", engineer="Service engineer",
        calibrated_by="Calibrated by", reviewed_by="Reviewed by", approved_by="Approved by", sign_date="Date",
        see_p2="see page 2", see_cal="see page 2",
        set_rate="Set rate", measured="Measured", error="Error", tolerance="Tolerance", verdict="Result",
        spread="Spread ±2SD", unc="Uncertainty U", duration="Measuring time", count="Pump cycles", count_time="Intervals",
        cycle_time="Time per cycle", interval_time="Interval length", minute="min", second="s",
        how="Method", how_sec="Method and details", detail="Measurement details", tools="Reference standard and conditions",
        supervisor="Service supervisor", manager="Technical manager",
        how_text="Gravimetric method. The water delivered by the pump is weighed continuously and converted to "
                 "volume per hour using the density of water at the measured temperature.",
        how_cycle="Intervals follow the pump's own cycle, peak to peak", how_time="Intervals are 30 seconds each",
        standard="Reference standard", balance="Balance", capacity="Capacity", readability="Readability",
        balance_check="Checked with a 50 g weight before use, reading 50.000 g",
        conditions="Conditions during measurement", liquid="Liquid", water="Distilled water", water_t="Water temperature",
        air_t="Air temperature", rh="Relative humidity", pressure="Air pressure",
        chart_flow="Flow rate of each pump cycle", chart_flow_time="Flow rate of each interval",
        chart_x="Time, minutes", chart_band="Tolerance range", chart_mean="Mean",
        occl="Occlusion alarm", occl_sub="Pressure at alarm, measured three times", occl_level="Level set",
        occl_row="Pressure at alarm", time_no="Run", mean="Mean", occl_limit="Manufacturer's limit",
        results="Flow rate calibration results",
        unc_note="U is the measurement uncertainty at about 95 % confidence, coverage factor k = 2",
        err_note="Error is the measured value minus the set value, divided by the set value",
        trace="Results are traceable to SI units through the reference balance listed",
        chart_err="Error against tolerance", chart_err_y="Error %", rate_axis="Set rate ml/h",
        per_rate="Flow rate of each pump cycle, by set rate", stats="Statistics at each set rate",
        lowest="Lowest", highest="Highest", average="Mean",
        volume="From weight to volume", density="Density of water", per_gram="1 g of water counts as",
        evap="Water lost to evaporation", evap_v="0.012 g per hour, allowed for",
        volume_note="Every figure in this report is a volume worked out with this table",
        method_ref="With reference to IEC 60601-2-24 and ISO 4787",
        validity="These results apply to the unit named, in its condition on the inspection date.",
    ),
}

# ---------------------------------------------------------------- รายการตรวจ (ไทย, อังกฤษ[, รายละเอียด ไทย, อังกฤษ])
CHECKS = {
    "infusion": {
        "visual": [("ตัวยึดเสา", "Pole clamp"), ("ตัวหนีบสาย", "Tubing clamp"), ("ยางรองฐาน", "Rubber foot"),
                   ("ช่องเสียบสายไฟ", "AC inlet plug"), ("แผงหน้าเครื่อง", "Front panel"), ("ตัวเครื่องและฝาครอบ", "Chassis and housing"),
                   ("ตัวล็อกประตู", "Door lock knob"), ("สวิตช์เปิดปิด", "Power switch")],
        "function": [("ชุดนิ้วบีบสาย", "Peristaltic finger"),
                     ("ปุ่มกด", "Key function"),
                     ("เสียงเตือน", "Buzzer"),
                     ("ไฟ AC และการชาร์จ", "AC line and charging"),
                     ("จอแสดงผล", "Display segment")],
        "performance": [("ตรวจจับฟองอากาศ", "Air in line", "เตือนเมื่อมีฟองอากาศในสาย", "alarms on air in the line"),
                        ("ตรวจจับการอุดตัน", "Occlusion detection", "วัด 3 ครั้ง เฉลี่ย 69 kPa", "three runs, mean 69 kPa"),
                        ("แบตเตอรี่", "Battery", "ทำงานต่อเนื่อง 120 นาที ที่ 25 ml/h", "runs 120 minutes at 25 ml/h"),
                        ("อัตราการไหล", "Flow rate", "", "")],
    },
    "syringe": {
        "visual": [("ตัวยึดเสา", "Pole clamp"), ("คลัตช์", "Clutch"), ("ยางรองฐาน", "Rubber foot"),
                   ("ตัวเลื่อนและยางหุ้ม", "Slider and boot"), ("แผงหน้าเครื่อง", "Front panel"), ("ช่องเสียบสายไฟ", "AC inlet plug"),
                   ("ตัวยึดกระบอกฉีด", "Syringe clamp"), ("ตัวเครื่อง", "Pump casing")],
        "function": [("จอแสดงผล", "Display segment"),
                     ("เสียงเตือน", "Buzzer"),
                     ("ปุ่มกด", "Key function"),
                     ("การไล่อากาศ", "Purge"),
                     ("แบตเตอรี่", "Battery"),
                     ("ไฟ AC และการชาร์จ", "AC line and charging")],
        "performance": [("ตรวจจับขนาดกระบอกฉีด", "Syringe size detection", "อ่านขนาดได้ถูกต้อง", "size read correctly"),
                        ("ตรวจจับการอุดตัน", "Occlusion detection", "วัด 3 ครั้ง เฉลี่ย 60 kPa", "three runs, mean 60 kPa"),
                        ("เตือนยาใกล้หมด", "Nearly empty detection", "ไฟเตือนกะพริบเมื่อถึงระยะ", "lamp blinks at the mark"),
                        ("อัตราการไหล", "Flow rate", "", "")],
    },
}

DATE = {"th": "17 พ.ย. 2569", "en": "17 Nov 2026"}

JOBS = {
    "infusion": dict(
        job="MCI-0142", dept=("ICU 2", "ICU 2"), brand="Terumo TE-171", serial="17110582", asset="ICU-IP-031",
        consumable=("Terumo 20 หยดต่อ ml", "Terumo 20 drops per ml"), tol=5.0,
        rate=50.0, measured=50.42, error=0.8, spread=2.4, minutes=14.7, count=58, unit_time=15.2, by_cycle=True,
        occl=(68, 71, 69), occl_level="M", occl_limit=(40, 100), supply=224, leak=38,
        parts=[(("ชุดนิ้วบีบสาย", "Peristaltic finger unit"), True), (("แบตเตอรี่", "Battery"), False),
               (("ตัวล็อกประตู", "Door lock knob"), False), (("เซนเซอร์ฟองอากาศ", "Air-in-line sensor"), True),
               (("ยางรองฐาน 4 ชิ้น", "Rubber foot, 4 pcs"), False), (("ฟิวส์", "Fuse"), False),
               (("แผ่นปุ่มกด", "Keypad membrane"), False)],
        received=[("สายไฟ", "Power cord"), ("ตัวยึดเสา", "Pole clamp"), ("คู่มือการใช้งาน", "User manual")],
    ),
    "syringe": dict(
        job="MCS-0388", dept=("NICU", "NICU"), brand="Terumo TE-331", serial="33104417", asset="NICU-SP-012",
        consumable=("Terumo 50 ml", "Terumo 50 ml"), tol=3.0,
        rate=5.0, measured=4.91, error=-1.8, spread=1.9, minutes=30.0, count=60, unit_time=30.0, by_cycle=False,
        occl=(58, 61, 60), occl_level="M", occl_limit=(40, 80), supply=223, leak=31,
        parts=[(("ตัวยึดกระบอกฉีด", "Syringe clamp"), True), (("แบตเตอรี่", "Battery"), False)],
        received=[("สายไฟ", "Power cord"), ("ตัวยึดเสา", "Pole clamp")],
    ),
}
CUSTOMER = dict(hospital=("โรงพยาบาลตัวอย่าง", "Sample Hospital"), province=("ขอนแก่น", "Khon Kaen"),
                contact=("คุณสมหญิง ใจดี", "Ms Somying Jaidee"), tel="043 000 000")

# Calibration (Infusion MCI-0142): ค่าที่ตั้ง, นาที, จำนวนรอบ, ค่าที่วัดได้, คลาดเคลื่อน %, ±2SD %, U %, เวลาต่อรอบ s
CAL_ROWS = [
    (10.0, 14.3, 12, 9.87, -1.3, 3.1, 0.9, 71.4),
    (50.0, 14.7, 58, 50.42, 0.8, 2.4, 0.6, 15.2),
    (200.0, 15.0, 231, 196.10, -2.0, 7.8, 0.7, 3.9),
]
ENV = dict(water_t="23.4 °C", air_t="24.1 °C", rh="56 %", pressure="1008 hPa", density="0.9975 g/ml", per_gram="1.0036 ml")
BALANCE = dict(model="A&D GF-300", serial="14654769", capacity="310 g", readability="0.001 g")


def series(mean: float, spread_pct: float, n: int, seed: int) -> list[float]:
    """flow รายช่วงสมมติ (กำหนดได้ ไม่สุ่มใหม่) — ค่าเฉลี่ยตรงกับตาราง, ±2SD ใกล้ค่าที่ระบุ"""
    state, out = seed, []
    for _ in range(n):
        total = 0.0
        for _ in range(3):
            state = (state * 16807) % 2147483647
            total += state / 2147483647 - 0.5
        out.append(total * 2.0)                      # sd ≈ 1
    centre = sum(out) / n
    sd = (sum((v - centre) ** 2 for v in out) / (n - 1)) ** 0.5
    scale = mean * spread_pct / 200.0 / sd
    return [mean + (v - centre) * scale for v in out]
