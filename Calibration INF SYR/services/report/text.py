"""ข้อความของใบรายงาน ไทย / อังกฤษ (แบบ Main Fable-1)

ยกมาจาก tools/report_templates/fable/content.py (TEXT) + a.py (X) เฉพาะที่แบบนี้ใช้ + ข้อความกรณีจริง
(ไม่ผ่าน, ยังไม่ได้ประเมิน U, หลายอัตรา) — ข้อความในเอกสารไม่ผ่าน tr() เพราะภาษาของเอกสารเลือกแยกจากภาษาโปรแกรม
"""
from __future__ import annotations

# (ไทย, อังกฤษ)
_T = dict(
    page=("หน้า", "Page"),
    insp_title=("รายงานการตรวจสภาพเครื่อง", "Inspection Report"), insp_kind=("INSPECTION REPORT", "SERVICE REPORT"),
    meas_title=("ผลวัดอัตราการไหล", "Flow Rate Measurement"),
    cal_title=("ใบรับรองผลการสอบเทียบ", "Calibration Certificate"), cal_kind=("CALIBRATION CERTIFICATE", "CALIBRATION"),
    tech_title=("รายงานทางเทคนิค", "Technical Report"),
    device_name=dict(infusion=("Infusion Pump", "Infusion Pump"), syringe=("Syringe Pump", "Syringe Pump")),
    device_th=dict(infusion="เครื่องให้สารละลาย", syringe="เครื่องให้ยาด้วยกระบอกฉีด"),
    job=("เลขงาน", "Job no."), service=("ประเภทงาน", "Service type"), device_kind=("ชนิดเครื่อง", "Device type"),
    date_insp=("วันที่ตรวจ", "Inspection date"), date_cal=("วันที่สอบเทียบ", "Calibration date"),
    pm=("บำรุงรักษา", "Preventive maintenance"), repair=("ซ่อม", "Repair"), calib=("สอบเทียบ", "Calibration"),
    customer=("ผู้รับบริการ", "Customer"), device=("เครื่องที่ตรวจ", "Device inspected"),
    device_cal=("เครื่องที่สอบเทียบ", "Device calibrated"),
    hospital=("โรงพยาบาล", "Hospital"), dept=("หน่วยงาน", "Department"), province=("จังหวัด", "Province"),
    contact=("ผู้ติดต่อ", "Contact"),
    brand=("ยี่ห้อ รุ่น", "Make and model"), serial=("หมายเลขเครื่อง", "Serial no."), asset=("รหัสครุภัณฑ์", "Asset code"),
    ivset=("ชุดให้สารละลาย", "Infusion set"), syr=("กระบอกฉีดที่ใช้", "Syringe used"),
    visual=("ตรวจสภาพภายนอก", "Visual inspection"), function=("ตรวจการทำงาน", "Function inspection"),
    performance=("ตรวจสมรรถนะ", "Performance inspection"), safety=("ความปลอดภัยทางไฟฟ้า", "Electrical safety"),
    item=("รายการ", "Item"), ok=("ผ่าน", "Pass"), fail=("ไม่ผ่าน", "Fail"), na=("ไม่มี", "N/A"),
    parts=("อะไหล่ที่เปลี่ยน", "Parts replaced"), no_parts=("ไม่มีการเปลี่ยนอะไหล่", "No parts replaced"),
    result=("ผลการตรวจ", "Inspection result"), result_cal=("ผลการสอบเทียบ", "Calibration result"),
    insp_statement=("ตรวจสภาพและบำรุงรักษาเรียบร้อย เครื่องพร้อมใช้งานตามปกติ",
                    "Inspection and preventive maintenance completed. The unit is ready for normal use."),
    insp_statement_fail=("พบรายการที่ไม่ผ่าน เครื่องยังไม่พร้อมใช้งาน ต้องแก้ไขและตรวจซ้ำก่อนใช้งาน",
                         "One or more items failed. The unit is not ready for use until it is repaired and checked again."),
    cal_statement=("เครื่องจ่ายได้ตรงตามเกณฑ์ทุกอัตราที่สอบเทียบ", "The pump delivers within tolerance at every calibrated rate."),
    cal_statement_occl=("สัญญาณเตือนการอุดตันทำงานในช่วงที่กำหนด", "The occlusion alarm operates within the specified range."),
    cal_statement_fail=("ผลอย่างน้อยหนึ่งรายการอยู่นอกเกณฑ์ยอมรับ ดูรายละเอียดในตาราง ต้องแก้ไขและสอบเทียบซ้ำก่อนใช้งาน",
                        "At least one result is outside tolerance — see the tables. Repair and calibrate again before use."),
    inspected_by=("ผู้ตรวจ", "Inspected by"), received_by=("ผู้รับเครื่อง", "Received by"),
    hospital_side=("เจ้าหน้าที่โรงพยาบาล", "Hospital staff"), engineer=("วิศวกรบริการ", "Service engineer"),
    calibrated_by=("ผู้สอบเทียบ", "Calibrated by"), reviewed_by=("ผู้ทวนสอบ", "Reviewed by"), approved_by=("ผู้อนุมัติ", "Approved by"),
    supervisor=("หัวหน้าฝ่ายบริการ", "Service supervisor"), manager=("ผู้จัดการฝ่ายเทคนิค", "Technical manager"),
    set_rate=("ค่าที่ตั้ง", "Set rate"), measured=("ค่าที่วัดได้", "Measured"), error=("Error%", "Error%"),
    tolerance=("เกณฑ์ยอมรับ", "Tolerance"), verdict=("ผล", "Result"), duration=("เวลาที่วัด", "Measuring time"), mmss=("นาที:วินาที", "min:s"),
    minute=("นาที", "min"),
    how=("วิธีวัด", "Method"), how_sec=("วิธีวัดและรายละเอียด", "Method and details"),
    tools=("เครื่องมือมาตรฐานและสภาวะขณะวัด", "Reference standard and conditions"),
    how_text=("วัดด้วยวิธีชั่งน้ำหนัก ชั่งน้ำที่เครื่องจ่ายออกมาอย่างต่อเนื่อง แล้วคิดเป็นปริมาตรต่อชั่วโมง"
              "จากความหนาแน่นของน้ำที่อุณหภูมิขณะวัด",
              "Gravimetric method. The water delivered by the pump is weighed continuously and converted to "
              "volume per hour using the density of water at the measured temperature."),
    standard=("เครื่องมือมาตรฐาน", "Reference standard"), balance=("เครื่องชั่ง", "Balance"),
    capacity=("พิกัด", "Capacity"), readability=("อ่านละเอียด", "Readability"),
    balance_check=("ตรวจด้วยตุ้มน้ำหนัก {w} g ก่อนใช้งาน อ่านได้ {r} g", "Checked with a {w} g weight before use, reading {r} g"),
    conditions=("สภาวะขณะวัด", "Conditions during measurement"), liquid=("ของเหลว", "Liquid"),
    water=("น้ำกลั่น", "Distilled water"), water_t=("อุณหภูมิน้ำ", "Water temperature"),
    air_t=("อุณหภูมิอากาศ", "Air temperature"), rh=("ความชื้นสัมพัทธ์", "Relative humidity"),
    pressure=("ความดันอากาศ", "Air pressure"),
    chart_flow=("อัตราการไหลของแต่ละรอบปั๊ม", "Flow rate of each pump cycle"),
    chart_flow_time=("อัตราการไหลของแต่ละช่วงวัด", "Flow rate of each interval"),
    occl=("สัญญาณเตือนการอุดตัน", "Occlusion alarm"), occl_level=("ระดับที่ตั้ง", "Level set"),
    occl_row=("ความดันขณะเตือน", "Pressure at alarm"), mean=("เฉลี่ย", "Mean"), mean_2sd=("เฉลี่ย ± 2SD", "Mean ± 2SD"),
    occl_insp=("{m} ± {s} {u}", "{m} ± {s} {u}"),
    occl_limit=("เกณฑ์ของผู้ผลิต", "Manufacturer's limit"), occl_run=("ครั้งที่", "Run"),
    results=("ผลการสอบเทียบอัตราการไหล", "Flow rate calibration results"),
    unc_note=("U คือความไม่แน่นอนขยายของการวัด ที่ระดับความเชื่อมั่นประมาณ 95 % (k ≈ 2 จากองศาอิสระประสิทธิผล) ประเมินตาม GUM",
              "U is the expanded measurement uncertainty at about 95 % confidence (k ≈ 2 from the effective degrees of freedom), evaluated per the GUM"),
    unc_none=("ความไม่แน่นอน U ยังไม่ได้ประเมินในรายงานนี้", "The measurement uncertainty U is not evaluated in this report"),
    err_note=("Error% = (ค่าที่วัดได้ − ค่าที่ตั้ง) ÷ ค่าที่ตั้ง × 100",
              "Error% = (measured − set value) ÷ set value × 100"),
    trace=("ผลการวัดสอบกลับได้ถึงหน่วย SI ผ่านเครื่องชั่งมาตรฐานที่ระบุ",
           "Results are traceable to SI units through the reference balance listed"),
    chart_err=("Error% เทียบเกณฑ์ยอมรับ", "Error% against tolerance"),
    rate_sec=("ผลรายค่าที่ตั้ง", "Results per set rate"),
    volume=("การคิดปริมาตรจากน้ำหนัก", "From weight to volume"), density=("ความหนาแน่นของน้ำ", "Density of water"),
    per_gram=("น้ำ 1 กรัม คิดเป็น", "1 g of water counts as"), evap=("น้ำที่ระเหยระหว่างวัด", "Water lost to evaporation"),
    volume_note=("ตัวเลขทุกค่าในรายงานนี้เป็นปริมาตรที่คิดตามตารางนี้แล้ว",
                 "Every figure in this report is a volume worked out with this table"),
    method_ref=("อ้างอิง IEC 60601-2-24 และ ISO 4787", "With reference to IEC 60601-2-24 and ISO 4787"),
    validity=("ผลนี้ใช้กับเครื่องที่ระบุและสภาพ ณ วันที่ตรวจเท่านั้น",
              "These results apply to the unit named, in its condition on the inspection date."),
    # ---- จาก a.py (X)
    flow_strip=("อัตราการไหล · วัดที่อัตราเดียว", "Flow rate · measured at one rate"),
    flow_strip_n=("อัตราการไหล · วัด {n} อัตรา", "Flow rate · measured at {n} rates"),
    details_p2=("รายละเอียดและกราฟหน้า 2", "details and chart on page 2"),
    details_pn=("รายละเอียดและกราฟหน้า 2–{p}", "details and charts on pages 2–{p}"),
    unc=("ความไม่แน่นอน", "Uncertainty"), result_short=("ผล", "Result"),
    supply=("แรงดันไฟที่จ่าย", "Supply voltage"), leak=("กระแสรั่วของเครื่อง", "Equipment leakage current"),
    leak_lim=("เกณฑ์ ไม่เกิน {v} µA", "limit not over {v} µA"),
    claim=("เคลมประกัน", "warranty"), new=("เปลี่ยนใหม่", "new"),
    parts_n=("เปลี่ยน {n} รายการ · เคลมประกัน {c} รายการ", "{n} parts replaced · {c} under warranty"),
    received=("อุปกรณ์ที่รับมากับเครื่อง", "Accessories received"),
    fin1=("ตรวจความเรียบร้อยทั้งเครื่องแล้ว", "Whole unit checked"), fin2=("ติดป้ายตรวจสภาพแล้ว", "Inspection label attached"),
    overall=("ผลรวม", "Overall"), name=("ชื่อ-นามสกุล", "Full name"),
    esign=("ลายมือชื่ออิเล็กทรอนิกส์", "Electronic signature"),
    occl_cal=("วัด 3 ครั้ง ดูหน้า 2", "3 runs, see page 2"),
    flow_cal=("{n} อัตรา ดูหน้า 2", "{n} rates, see page 2"), flow_cal_1=("1 อัตรา ดูหน้า 2", "1 rate, see page 2"),
    flow_item=("อัตราการไหล", "Flow rate"),
    cyc=("จับรอบปั๊ม", "Pump cycle"), cyc_tech="Cycle-synchronous",
    tim=("แบ่งช่วงเวลา", "Time interval"), tim_tech="Fixed time interval",
    split=("การแบ่งช่วงวัด", "Interval method"),
    n_cyc=("จำนวนรอบปั๊ม", "Pump cycles"), n_tim=("จำนวนช่วงวัด", "Intervals"),
    t_cyc=("เวลาต่อรอบเฉลี่ย", "Mean time per cycle"), t_tim=("เวลาต่อช่วงเฉลี่ย", "Mean time per interval"),
    t_all=("เวลาที่วัด", "Measuring time"),
    trace_ref=("ข้อมูลดิบ", "Raw data"),
    # ---- หน้าความไม่แน่นอน (ใบ Calibration หน้าสุดท้าย — 2026-11-19)
    unc_title=("ความไม่แน่นอนของการวัด", "Measurement Uncertainty"),
    unc_sum=("สรุปความไม่แน่นอนขยาย", "Expanded uncertainty"),
    unc_budget=("งบความไม่แน่นอน (ความไม่แน่นอนมาตรฐานสัมพัทธ์ของค่าที่วัดได้ %)",
                "Uncertainty budget (relative standard uncertainty of the measured flow, %)"),
    unc_model=("แบบจำลองการวัดและที่มาของค่า", "Measurement model and sources"),
    unc_U_mlh=("U (k)", "U (k)"), unc_U_pct=("U", "U"), unc_k=("k", "k"), unc_conf=("ระดับความเชื่อมั่น", "Coverage"),
    unc_comp=("องค์ประกอบ", "Component"), unc_uc=("ความไม่แน่นอนรวม u_c", "Combined u_c"),
    unc_Upct_row=("ความไม่แน่นอนขยาย U (%)", "Expanded U (%)"), unc_Umlh_row=("ความไม่แน่นอนขยาย U (ml/h)", "Expanded U (ml/h)"),
    unc_eq=("Q = (Δm ÷ Δt × 3600 − b) × Z · Δm, Δt = น้ำหนักและเวลารวมจาก peak แรกถึงปลายรอบสุดท้าย · "
            "b = อัตราที่หักจาก self-check · Z = ค่าแก้ ml/g ตาม ISO 4787 (ความหนาแน่นน้ำ อากาศ ตุ้มน้ำหนัก)",
            "Q = (Δm ÷ Δt × 3600 − b) × Z · Δm, Δt = total mass and time from the first peak to the end of the last cycle · "
            "b = self-check rate · Z = ml/g factor per ISO 4787 (water, air and weight densities)"),
    unc_method=("ประเมินตาม GUM (JCGM 100:2008) · รวมแบบรากที่สองของผลรวมกำลังสอง · k จากองศาอิสระประสิทธิผล "
                "(Welch–Satterthwaite) ที่ระดับความเชื่อมั่นประมาณ 95 %",
                "Evaluated per the GUM (JCGM 100:2008) · root-sum-of-squares · k from the effective degrees of freedom "
                "(Welch–Satterthwaite) for about 95 % coverage"),
    unc_certs=("ใบรับรองเครื่องมือ: ตราชั่ง {b} · เทอร์โมมิเตอร์ {t}", "Instrument certificates: balance {b} · thermometer {t}"),
    unc_sim=("ค่าจากใบรับรองเครื่องมือในรายงานนี้เป็นค่าจำลอง ยังไม่ใช่ค่าจากใบรับรองจริง",
             "The instrument certificate values in this report are simulated, not taken from real certificates"),
    unc_rep=("ความซ้ำ (2SD) {r} ml/h: {s}", "Repeatability (2SD) {r} ml/h: {s}"),
    unc_rep_none=("ยังไม่มีค่า", "none entered"),
    set_min=("ตั้ง {m} นาที", "set {m} min"), set_cyc=("ตั้ง {n} รอบ", "set {n} cycles"),
    time_note=("ค่าที่วัดได้ = ปริมาตรรวม ÷ เวลารวม จาก peak แรกถึงปลายรอบสุดท้าย · นับเฉพาะรอบเต็ม เวลาที่วัดจึงเกินเวลาที่ตั้งได้ไม่เกิน 1 รอบ",
               "Measured = total volume ÷ total time from the first peak to the end of the last cycle · whole cycles only, "
               "so the measuring time may exceed the set time by up to one cycle"),
    v_cyc=("ปริมาตรต่อรอบ", "Volume per cycle"), v_tim=("ปริมาตรต่อช่วง", "Volume per interval"),
    v_all=("ปริมาตรรวม", "Total volume"),
    spread=("การกระจาย ±2SD", "Spread ±2SD"), err_u=("Error% ± U", "Error% ± U"),
    x_axis=("เวลา นาที", "time, min"), band=("ช่วงเกณฑ์ยอมรับ", "acceptance band"), mean_line=("ค่าเฉลี่ย", "mean"), each=("ค่าแต่ละช่วงวัด", "each interval"),
    moving_line=("ค่าเฉลี่ยสะสม", "running mean"),
    legend_pt=("ค่าที่วัดได้ ± U", "Measured ± U"), legend_pt_nou=("ค่าที่วัดได้", "Measured"),
    legend_fit=("แนวโน้ม linear regression", "Linear regression trend"),
    legend_tol=("เกณฑ์ ±{t:g} %", "Limit ±{t:g} %"),
    trend=("แนวโน้ม", "Trend"), trend_tag=("แนวโน้ม", "trend"),
    trend_v=("{s} % ต่อ 10 เท่าของอัตรา", "{s} % per decade of rate"),
    worst=("Error% มากสุด", "Largest Error%"), worst_v=("{e} % ที่ {r:g} ml/h", "{e} % at {r:g} ml/h"),
    margin=("เผื่อถึงขอบเกณฑ์", "Margin to limit"), margin_v=("{m} % รวม U แล้ว", "{m} % after U"),
    margin_v_nou=("{m} %", "{m} %"),
    rate_x=("ค่าที่ตั้ง ml/h · สเกล log", "Set rate ml/h · log scale"),
    split_note=("จับรอบปั๊ม = Cycle-synchronous ตามรอบการทำงานของปั๊ม · แบ่งช่วงเวลา = Fixed time interval ใช้กับอัตราต่ำ",
                "Pump cycle = cycle-synchronous · Time interval = fixed time interval, used at low rates"),
    invalid=("ใช้ไม่ได้", "Invalid"),
    # ---- แบบตัวอย่างของผู้ใช้ 2026-11-19
    final=("ตรวจขั้นสุดท้าย", "Final inspection"),
    see_p2=("ดูหน้า 2", "see page 2"), see_pn=("ดูหน้า 2–{p}", "see pages 2–{p}"),
    err_max=("Error% สูงสุด {e}", "largest Error% {e}"),
    occl_detail=("วัด 3 ครั้ง เฉลี่ย {m} ± {s} {u}", "3 runs, mean {m} ± {s} {u}"),
    occl_caption=("วัดความดันขณะเครื่องเตือน 3 ครั้ง", "Pressure at alarm, measured 3 times"),
    meas_detail=("รายละเอียดการวัด", "Measurement details"), split_by=("แบ่งช่วงวัด:", "Intervals:"),
    std_cond=("เครื่องมือมาตรฐานและสภาวะขณะวัด", "Reference standard and conditions"),
    check_w=("ตรวจด้วยตุ้ม {w} g ก่อนใช้", "{w} g check weight"),
    battery_detail=("ทำงานต่อเนื่อง {m} นาที ที่ {r} ml/h", "runs {m} min at {r} ml/h"),
    battery_rate=("ทดสอบที่ {r} ml/h", "tested at {r} ml/h"),
    made_by=("จัดทำโดย DeltaM {v}", "Produced with DeltaM {v}"),
    works_ok=("ทำงานปกติ", "Works normally"),
    occl_alarm_ok=("เตือนเมื่อมีการอุดตัน", "Alarms on occlusion"),
    verdict_overall=("สรุปผล", "Overall result"),
    in_tol=("อยู่ในเกณฑ์", "Within"), out_tol=("นอกเกณฑ์", "Outside"),
)

EN_LABELS = dict(
    customer="CUSTOMER", device="DEVICE INSPECTED", device_cal="DEVICE CALIBRATED", final="FINAL INSPECTION", visual="VISUAL INSPECTION", function="FUNCTION INSPECTION",
    performance="PERFORMANCE INSPECTION", safety="ELECTRICAL SAFETY", parts="PARTS REPLACED", flow="FLOW RATE MEASUREMENT",
    chart="FLOW RATE OF EACH INTERVAL", chart_cyc="FLOW RATE OF EACH PUMP CYCLE", std="REFERENCE STANDARD AND CONDITIONS", method="METHOD AND DETAILS", cond="CONDITIONS", results="RESULTS",
    occl="OCCLUSION ALARM", tools="METHOD AND REFERENCE STANDARD", err="ERROR% AGAINST TOLERANCE",
    rate="RESULTS PER SET RATE", volume="WEIGHT TO VOLUME",
    unc_sum="EXPANDED UNCERTAINTY", unc_budget="UNCERTAINTY BUDGET", unc_model="MODEL AND SOURCES",
)

# ชื่อองค์ประกอบของงบ (core/uncertainty.py) ในใบ — (ไทย, อังกฤษ)
UNC_NAMES = {
    "Balance calibration": ("ตราชั่ง — ใบรับรอง", "Balance — calibration"),
    "Balance resolution": ("ตราชั่ง — ความละเอียด", "Balance — resolution"),
    "Balance repeatability": ("ตราชั่ง — ความซ้ำ", "Balance — repeatability"),
    "Timestamps": ("เวลาประทับของข้อมูล", "Timestamps"),
    "Computer clock rate": ("อัตรานาฬิกาคอมพิวเตอร์", "Computer clock rate"),
    "Water temperature → density": ("อุณหภูมิน้ำ → ความหนาแน่น", "Water temperature → density"),
    "Water density formula / purity": ("ความหนาแน่นน้ำ — สูตร/ความบริสุทธิ์", "Water density — formula/purity"),
    "Air temperature → buoyancy": ("อุณหภูมิอากาศ → แรงลอยตัว", "Air temperature → buoyancy"),
    "Humidity → buoyancy": ("ความชื้น → แรงลอยตัว", "Humidity → buoyancy"),
    "Air pressure → buoyancy": ("ความดันอากาศ → แรงลอยตัว", "Air pressure → buoyancy"),
    "Evaporation / self-check": ("การระเหย / self-check", "Evaporation / self-check"),
    "Repeatability (2SD entered)": ("ความซ้ำของการวัด (2SD)", "Repeatability (2SD)"),
    # ผลที่คิดงบด้วยรุ่นก่อน 2026-11-19 เย็น (ความซ้ำจากผลก่อนหน้า) — ไม่แก้ผลเก่า แต่ชื่อต้องแสดงได้
    "Repeatability (earlier runs)": ("ความซ้ำของการวัด (ผลก่อนหน้า — วิธีเดิม)", "Repeatability (earlier results — old method)"),
}

_MONTHS = {
    "th": ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}


class Words:
    """ข้อความของ 1 ภาษา: w("key") / w("key", n=3) · w.device("infusion") · w.en("visual") = ป้ายอังกฤษด้านขวา (ฉบับไทยเท่านั้น)"""

    def __init__(self, lang: str):
        self.lang = "en" if lang == "en" else "th"
        self.i = 0 if self.lang == "th" else 1

    def __call__(self, key: str, **kw) -> str:
        value = _T[key]
        text = value if isinstance(value, str) else value[self.i]
        return text.format(**kw) if kw else text

    def device(self, pump: str, lower: bool = False) -> str:
        text = _T["device_name"].get(pump, _T["device_name"]["infusion"])[self.i]
        return text[:1] + text[1:].lower() if lower else text          # "Infusion pump" ตามแบบตัวอย่าง

    def device_th(self, pump: str) -> str:
        return _T["device_th"].get(pump, _T["device_th"]["infusion"])

    def en(self, key: str) -> str:
        return EN_LABELS.get(key, "") if self.lang == "th" else ""

    def pick(self, th: str, en: str) -> str:
        return th if self.lang == "th" else en

    def method(self, kind: str, tech: bool = True) -> str:
        name = self("cyc" if kind == "cycle" else "tim")
        tech_name = _T["cyc_tech" if kind == "cycle" else "tim_tech"]
        if tech and self.lang == "en":        # ฉบับอังกฤษ: ชื่อเทคนิคอย่างเดียว (ไม่ซ้ำคำ)
            return tech_name
        return f"{name} · {tech_name}" if tech else name

    def date(self, iso: str) -> str:
        """วันที่ในเอกสาร: ไทย = พ.ศ. ("17 พ.ย. 2569") · อังกฤษ = "17 Nov 2026" """
        from datetime import datetime
        try:
            when = datetime.fromisoformat(str(iso))
        except ValueError:
            return str(iso or "")
        year = when.year + 543 if self.lang == "th" else when.year
        return f"{when.day} {_MONTHS[self.lang][when.month - 1]} {year}"
