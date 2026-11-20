"""หน้า Settings: แก้ค่าตั้งของระบบ — แท็บด้านบนแยกหมวด (ผู้ใช้ 2026-11-20: แบบโปรแกรมสากล หาง่าย)

ฟอร์มสร้างจากตาราง GROUPS — เพิ่มค่าตั้งใหม่ = เพิ่ม field ใน config/settings.py
แล้วเพิ่ม 1 บรรทัดในตารางนี้ ไม่ต้องเขียน widget เอง · กลุ่มอยู่แท็บไหน = ตาราง TABS / REPORT_TABS
ค่าที่บันทึกมีผลกับการทดสอบ "ครั้งถัดไป" (การทดสอบที่กำลังเดินใช้สำเนาค่าตอนเริ่ม)
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from config.i18n import LANGUAGES, tr
from config.settings import AppSettings
from hardware import SOURCES
from hardware.parsers import format_choices
from hardware.serial_balance import Detection, detect_settings, list_ports
from ui.icons import Glyph, glyph_icon
from ui.theme import THEMES, Color
from ui.widgets.common import Card, PageHeader, label
from ui.widgets.date_field import DateField
from ui.widgets.path_edit import PathEdit
from ui.widgets.report_extras import OCCL_UNITS


@dataclass
class Field:
    section: str            # ชื่อ attribute ของ AppSettings ("" = ระดับบนสุด)
    name: str               # ชื่อ field
    text: str               # ป้ายบนจอ
    minimum: float = 0
    maximum: float = 1e6
    decimals: int = 0       # ใช้กับ float
    suffix: str = ""
    choices: object = None  # list ของ (ค่า, ข้อความ) หรือ callable ที่คืน list -> combo box (_ON_OFF = ช่องติ๊ก)
    editable: bool = False
    hint: str = ""
    translate: bool = True  # แปลข้อความของตัวเลือกใน combo ไหม
    # "" = ตามชนิดของค่า, "text" = ข้อความ, "lines" = รายการ (บรรทัดละ 1 รายการ)
    # "folder" / "image" / "file" = ช่อง path + ปุ่มเลือก (ไม่ต้องพิมพ์ path เอง) · "note" = ข้อความอธิบายอย่างเดียว
    # "date" = เลือกวันที่จากปฏิทิน (เก็บ YYYY-MM-DD, ว่างได้)
    kind: str = ""


_ON_OFF = [(True, "On"), (False, "Off")]
DATA_SOURCE = "Data source"

GROUPS: list[tuple[str, list[Field]]] = [
    ("Interface", [
        Field("ui", "language", "Language", choices=lambda: list(LANGUAGES.items()), translate=False),
        Field("ui", "theme", "Theme", choices=lambda: list(THEMES.items())),
        Field("ui", "sounds", "Sounds", choices=_ON_OFF, hint="All sounds of the program"),
        Field("ui", "sound_clicks", "Click sounds", choices=_ON_OFF, hint="Soft tick when a button is pressed"),
        Field("ui", "sound_volume", "Sound volume", 0, 100, suffix=" %"),
        Field("ui", "sound_low_latency", "Instant click sound", choices=_ON_OFF,
              hint="Clicks play through an always-open audio channel so they sound the moment you press. "
                   "Turn off if a sound device misbehaves"),
        Field("ui", "sound_on_finish", "Sound when a test finishes", choices=_ON_OFF),
        Field("ui", "attention_every_s", "Remind while a result waits for an answer", 0, 600, suffix=" s",
              hint="Soft beep + flashing taskbar every few seconds until someone answers 'Keep this result?'. 0 = off"),
        Field("ui", "confirm_stop", "Confirm before stopping", choices=_ON_OFF),
        Field("ui", "smooth_scroll", "Smooth scrolling graphs", choices=_ON_OFF,
              hint="The time axis glides between balance readings (Auto / Zoom view) instead of jumping 5–10 times a second"),
        Field("ui", "smooth_fps", "Smooth scrolling: target frame rate", 10, 120, suffix=" fps",
              hint="Lowered automatically when the computer is busy, so the program never lags"),
        Field("ui", "smooth_budget_pct", "Smooth scrolling: screen time at most", 10, 80, suffix=" %",
              hint="Share of the screen thread the scrolling may use"),
        Field("ui", "graph_range", "Graph view", choices=[
            ("full", "Full — whole test, start fixed"), ("auto", "Auto — several pump cycles"),
            ("zoom", "Zoom — latest data, close up")],
            hint="Also switchable on the Test page; applies to all four graphs"),
        Field("ui", "graph_auto_cycles", "Auto view width", 2, 50, suffix=" cycles",
              hint="Pump cycles (or time-based intervals) shown in Auto view — the cycle is detected while testing"),
        Field("ui", "rolling_window_s", "Auto view width before the cycle is known", 30, 3600, suffix=" s"),
        Field("ui", "graph_zoom_s", "Zoom view width", 10, 3600, suffix=" s"),
        Field("ui", "graph_full_min_s", "Full view: shortest time axis", 0, 86400, suffix=" s",
              hint="Full view shows 0 to at least this long. Tests that end by time use the test's own duration instead"),
        Field("ui", "graph_flow_y_pct", "Flow graphs: fixed Y range", 0, 100, 0, " %",
              hint="Cumulative and interval flow graphs stay at the set rate ± this much; 0 = follow the data. "
                   "The range widens only when the mean itself is outside it"),
    ]),
    ("Reference balance", [
        Field("balance", "model", "Balance model", kind="text"),
        Field("balance", "serial_no", "Balance serial no.", kind="text",
              hint="Saved with every result for traceability (replaces the Balance ID field in the test form)"),
        Field("balance", "capacity", "Balance capacity", kind="text", hint="Shown on the calibration certificate"),
        Field("balance", "readability", "Balance readability", kind="text"),
        Field("balance", "cal_date", "Balance calibrated on", kind="date",
              hint="Date on the balance's calibration certificate — shown on the Calibration report"),
        Field("balance", "due_date", "Balance calibration due", kind="date",
              hint="Next calibration due — shown on the Calibration report; the test wizard warns once it has passed"),
    ]),
    ("Uncertainty", [
        Field("uncertainty", "simulated", "Values are simulated", choices=_ON_OFF,
              hint="Set to Off after entering the real certificate values"),
        Field("uncertainty", "balance_cert", "Balance certificate no.", kind="text"),
        Field("uncertainty", "balance_u_g", "Balance calibration U", 0, 1, 5, " g", hint="At the working load"),
        Field("uncertainty", "balance_k", "Balance coverage factor k", 1, 10, 2),
        Field("uncertainty", "balance_resolution_g", "Balance resolution d", 0, 1, 5, " g"),
        Field("uncertainty", "balance_repeat_g", "Balance repeatability s", 0, 1, 5, " g"),
        Field("uncertainty", "thermo_cert", "Thermometer certificate no.", kind="text"),
        Field("uncertainty", "thermo_u_c", "Thermometer U", 0, 10, 3, " °C"),
        Field("uncertainty", "thermo_k", "Thermometer coverage factor k", 1, 10, 2),
        Field("uncertainty", "no_temp_c", "Water temperature not entered: ±", 0, 20, 1, " °C"),
        Field("uncertainty", "hygro_u_pct", "Hygrometer U", 0, 50, 2, " %RH"),
        Field("uncertainty", "hygro_k", "Hygrometer coverage factor k", 1, 10, 2),
        Field("uncertainty", "baro_u_hpa", "Barometer U", 0, 50, 2, " hPa"),
        Field("uncertainty", "baro_k", "Barometer coverage factor k", 1, 10, 2),
        Field("uncertainty", "no_air_c", "Air temperature not measured: ±", 0, 20, 1, " °C",
              hint="Humidity not measured ±10 %RH · pressure not measured ±15 hPa"),
        Field("uncertainty", "clock_ppm", "Computer clock rate ±", 0, 1000, 1, " ppm"),
        Field("uncertainty", "timestamp_u_s", "Timestamp uncertainty per point", 0, 1, 4, " s"),
        Field("uncertainty", "water_density_rel", "Water density (formula/purity), relative", 0, 0.01, 7),
        Field("uncertainty", "evaporation_u_g_h", "Evaporation / self-check u", 0, 1, 4, " g/h"),
        Field("uncertainty", "repeat_default_pct", "2SD when none is entered for the model / IV set / rate", 0, 50, 4, " %",
              hint="0 = not included until a value is entered or measured"),
        Field("uncertainty", "repeat_runs", "Runs in a repeatability study", 2, 10),
        Field("uncertainty", "extra", "Other components", kind="lines",
              hint="One per line: name | value % | normal or rect"),
    ]),
    # ---- ใบรายงาน (แท็บ "ใบรายงาน" มีแท็บย่อย REPORT_TABS) · ผู้ลงนาม/ลายเซ็น = ui/widgets/signature_settings.py
    ("Saving and printing", [
        Field("report", "language", "Report language",
              choices=[("", "Same as the program"), ("th", "Thai"), ("en", "English"),
                       ("mix", "Thai with English technical terms")],
              hint="Thai with English technical terms: item names, headings, units and result words stay in English; "
                   "explanations stay in Thai"),
        Field("report", "preview_after_test", "Preview after a test", choices=_ON_OFF,
              hint="Off = save the PDF or print straight away"),
        Field("report", "preview_from_history", "Preview from History", choices=_ON_OFF),
        Field("report", "preview_zoom_pct", "Preview zoom", 0, 400, suffix=" %", hint="0 = fit to the window width"),
        Field("report", "ask_printer", "Choose the printer each time", choices=_ON_OFF,
              hint="Off = print to the Windows default printer"),
        Field("report", "folder", "PDF folder", kind="folder", hint="Blank = DeltaM Reports in Documents"),
        Field("report", "merge_files", "Several jobs from History",
              choices=[(False, "One PDF per job"), (True, "One combined PDF")]),
    ]),
    ("Company and header", [
        Field("report", "company_mark", "Company short name", kind="text"),
        Field("report", "company_name", "Company name", kind="text"),
        Field("report", "address_th", "Company address (Thai)", kind="text"),
        Field("report", "address_en", "Company address (English)", kind="text"),
        Field("report", "logo", "Logo file", kind="image", hint="PNG or JPG — blank = the short name in bold"),
    ]),
    ("Page footer", [
        Field("report", "footer_version", "Program name and version", choices=_ON_OFF,
              hint="Middle of the footer, e.g. DeltaM 0.3.0"),
        Field("report", "footer_trace", "Result numbers for tracing", choices=_ON_OFF,
              hint="Small line under the footer: result no. · SHA-256 of the raw data (open the result and press "
                   "Audit to check every number)"),
    ]),
    ("Graphs and values (both reports)", [
        Field("report", "graph_style", "Report graph style",
              choices=[("step", "Steps"), ("points", "Points joined by a line")],
              hint="Flow of each interval on the report — can also be changed in the preview"),
        Field("report", "graph_intervals", "Report graph: flow of each interval", choices=_ON_OFF,
              hint="Each line can be switched on or off on its own — also in the report preview (Graph menu)"),
        Field("report", "graph_mean", "Report graph: mean line", choices=_ON_OFF),
        Field("report", "graph_moving_avg", "Report graph: running mean line", choices=_ON_OFF),
        Field("report", "leak_limit_ua", "Leakage current limit", 1, 10000, 0, " µA"),
        Field("report", "supply_ref", "Supply voltage reference", kind="text",
              hint="Shown under the supply voltage on page 1, e.g. AC Supply 200-230VAC — blank = not shown"),
    ]),
    ("Inspection report", [
        Field("report", "insp_show_u", "Show ± U on the gauge and graph", choices=_ON_OFF,
              hint="The shaded uncertainty band and ± value around Error%"),
        Field("report", "insp_show_flow_2sd", "Show the flow-rate spread ±2SD", choices=_ON_OFF),
        Field("", "", "Occlusion", kind="note",
              hint="The Inspection report shows only that the occlusion alarm works — the measured pressure and "
                   "its 2SD are on the Calibration report"),
    ]),
    ("Calibration report", [
        Field("report", "cal_pages", "Pages", choices=[
            ("all", "All pages (with the uncertainty page)"), ("no_uncertainty", "Without the uncertainty page"),
            ("certificate", "First two pages only (inspection + certificate)")],
            hint="Pages left out are not deleted — choose All again to print them"),
        Field("report", "cal_u_column", "U in the results table", choices=[
            ("ml_h", "ml/h, 4 decimals (0.0000)"), ("pct", "Percent, 3 decimals (0.000 %)"), ("hide", "Do not show")]),
        Field("report", "cal_show_u", "Show ± U on gauges and graphs", choices=_ON_OFF,
              hint="Technical pages: shaded band, error bars and Error% ± U"),
        Field("report", "cal_show_flow_2sd", "Show the flow-rate spread ±2SD", choices=_ON_OFF,
              hint="±2SD column of the results table and the spread line of each rate"),
        Field("report", "cal_show_occl_2sd", "Show occlusion mean ± 2SD", choices=_ON_OFF,
              hint="Off = the mean only (page 1 and the occlusion table)"),
    ]),
    ("Defaults for measured values (step 5 of a new test)", [
        Field("report", "default_supply_v", "Supply voltage", 0, 1000, 0, " V", hint="0 = blank"),
        Field("report", "default_final_ticks", "Whole unit checked / label attached", choices=_ON_OFF,
              hint="Ticked at the start"),
        Field("report", "default_battery_min", "Runs on battery for more than", 0, 10000, 0, " min",
              hint="Not a test — the report states the unit runs on battery longer than this. 0 = blank"),
        Field("evaporation", "default_trap", "Evaporation trap used", choices=_ON_OFF,
              hint="Starting choice in step 5 — the evaporation settings are under Calculation"),
    ]),
    # การอุดตันแยกชนิดเครื่อง (ผู้ใช้ 2026-11-20) — wizard ใช้ชุดตามชนิดที่เลือกในขั้น 1 · เกณฑ์ที่บันทึกของรุ่นเดียวกันมาก่อน
    ("Occlusion defaults · Infusion pump", [
        Field("report", "default_occl_inf_level", "Occlusion level set", kind="text", hint="e.g. M — blank = none"),
        Field("report", "default_occl_inf_unit", "Occlusion pressure unit", choices=[(u, u) for u in OCCL_UNITS],
              translate=False),
        Field("report", "default_occl_inf_low", "Manufacturer's limit: low", 0, 10000, 2,
              hint="0 = blank · the limit saved for the same model is used first"),
        Field("report", "default_occl_inf_high", "Manufacturer's limit: high", 0, 10000, 2, hint="0 = blank"),
    ]),
    ("Occlusion defaults · Syringe pump", [
        Field("report", "default_occl_syr_level", "Occlusion level set", kind="text", hint="e.g. M — blank = none"),
        Field("report", "default_occl_syr_unit", "Occlusion pressure unit", choices=[(u, u) for u in OCCL_UNITS],
              translate=False),
        Field("report", "default_occl_syr_low", "Manufacturer's limit: low", 0, 10000, 2,
              hint="0 = blank · the limit saved for the same model is used first"),
        Field("report", "default_occl_syr_high", "Manufacturer's limit: high", 0, 10000, 2, hint="0 = blank"),
    ]),
    ("Job number", [
        Field("jobs", "prefix_infusion", "Prefix · Infusion pump", kind="text",
              hint="Filled in front of the job number when Infusion is chosen (can still be changed per job)"),
        Field("jobs", "prefix_syringe", "Prefix · Syringe pump", kind="text"),
    ]),
    (DATA_SOURCE, [
        Field("", "source", "Source", choices=lambda: SOURCES.choices(),
              hint="Simulator lets you try the program without a balance connected"),
        Field("serial", "port", "Port", choices=lambda: [(p, p) for p in list_ports()], editable=True, translate=False),
        Field("serial", "baudrate", "Baud rate", translate=False,
              choices=[(b, str(b)) for b in (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200)]),
        Field("serial", "bytesize", "Data bits", choices=[(7, "7"), (8, "8")], translate=False),
        Field("serial", "parity", "Parity", choices=[("N", "None"), ("E", "Even"), ("O", "Odd")]),
        Field("serial", "stopbits", "Stop bits", choices=[(1, "1"), (2, "2")], translate=False),
        Field("serial", "mode", "Balance output", choices=[
            ("auto", "Auto detect"), ("stream", "Stream (balance sends by itself)"), ("poll", "Ask for each value"),
        ], hint="Auto listens first; if the balance is silent it asks for values instead"),
        Field("serial", "poll_interval_s", "Ask every", 0.02, 5, 2, " s"),
        Field("serial", "response_timeout_s", "Wait for a full answer up to", 0.1, 10, 2, " s",
              hint="Lines that are still incomplete after this are discarded (GF-300 answers in about 0.2 s)"),
        Field("serial", "line_format", "Line format", choices=format_choices,
              hint="Strict A&D only accepts complete lines; the looser formats can misread a cut-off line"),
        Field("replay", "path", "Replay file", kind="file", hint="A raw.csv or capture file recorded earlier (time, weight)"),
        Field("replay", "speed", "Replay speed", 0.1, 500, 1, " x"),
    ]),
    ("Calculation", [
        Field("engine", "density_g_per_ml", "Liquid density", 0.5, 2.0, 4, " g/ml",
              hint="Used only when no liquid temperature is entered in the test form"),
        Field("engine", "air_buoyancy", "Air buoyancy correction (ISO 4787)", choices=_ON_OFF,
              hint="g → ml with the Z factor: water density from liquid temperature, air density from "
                   "air temperature, humidity and pressure (about +0.1 %)"),
        Field("engine", "default_humidity_pct", "Humidity if not entered", 0, 100, 0, " %RH"),
        Field("engine", "default_pressure_hpa", "Air pressure if not entered", 500, 1200, 2, " hPa"),
        Field("engine", "reference_density_g_per_ml", "Density of the balance's reference weights", 1, 25, 2, " g/ml",
              hint="Stainless steel calibration weights = 8.0 g/ml (OIML R111)"),
        Field("engine", "warmup_s", "Warm-up", 0, 600, 1, " s"),
        # หน้าต่างจับรอบปั๊มไม่ใช้ค่าเดียวทุก rate อีกแล้ว (ดูปุ่ม "ข้อมูลสอบเทียบรอบปั๊ม" ด้านล่าง)
        Field("engine", "regression_window", "Slope graph window (time-based capture)", 3, 5000, suffix=" pts",
              hint="Only smooths the live slope graph of time-based tests. Pump-cycle capture uses each rate's own "
                   "windows (Pump-cycle calibration data below)"),
        Field("engine", "auto_window_fraction", "Window / pump cycle", 0.1, 0.49, 2,
              hint="Regression window as a fraction of the pump cycle — starting value for rates not tuned yet"),
        Field("engine", "auto_half_fraction", "n̄ / pump cycle", 0, 0.75, 2,
              hint="0 = same as the regression window. Each model, IV set and rate gets its own values once tuned"),
        Field("engine", "cycle_chains", "Pump-cycle capture", choices=[
            (2, "Paired cycles (peak→peak and valley→valley)"), (1, "Single cycle (one reference point)"),
        ], hint="Paired runs two chains of intervals side by side; single keeps only chain A"),
        Field("engine", "auto_tune_timeout_s", "Stop looking for the cycle after", 30, 3600, 0, " s"),
        Field("engine", "default_stroke_volume_ml", "Default volume per cycle (new models)", 0.01, 5, 3, " ml",
              hint="Used to estimate the pump cycle of a model that has not been measured, and when the cycle "
                   "cannot be found before measuring. Your pumps so far: 0.12–0.21 ml"),
    ]),
    # การระเหยระหว่างวัด (core/evaporation.py — ผู้ใช้ 2026-11-20)
    ("Evaporation during the measurement", [
        Field("evaporation", "method", "Evaporation correction", choices=[
            ("auto", "Today's self-check, otherwise calculated"), ("model", "Calculated from the vessel and air"),
            ("self_check", "Today's self-check only"), ("off", "No correction")],
            hint="Used only when no evaporation trap is used. A measured self-check is more accurate than the calculation"),
        Field("evaporation", "vessel_diameter_mm", "Vessel inside diameter (water surface)", 5, 500, 1, " mm",
              hint="100 ml beaker ≈ 50 mm"),
        Field("evaporation", "vessel_depth_mm", "Vessel inside depth", 5, 500, 1, " mm"),
        Field("evaporation", "start_volume_ml", "Water in the vessel at the start", 0, 5000, 1, " ml",
              hint="The water level rises with the delivered volume; the calculation uses the start and end levels"),
        Field("evaporation", "model_u_pct", "Uncertainty of the calculation ±", 0, 200, 0, " %",
              hint="Added to the uncertainty budget (rectangular)"),
        Field("", "", "How it is calculated", kind="note",
              hint="Water vapour diffuses from the water surface up to the rim, then natural convection carries it "
                   "away (Goldstein 1973, Lloyd & Moran 1974). Uses the water and air temperature, humidity and "
                   "pressure of the test — every value is saved with the result"),
    ]),
    # เกณฑ์ "flow นิ่ง" ของโหมดเริ่มวัดอัตโนมัติ แยก 3 กลุ่ม ชนิดเครื่อง x วิธีจับ (config.settings.PrerunSettings)
    ("Automatic start · Infusion, pump-cycle capture", [
        Field("prerun.infusion_cycle", "stability_pct", "Allowed flow variation", 0.1, 50, 1, " %"),
        Field("prerun.infusion_cycle", "block_mode", "Block length unit", choices=[
            ("cycle", "Pump cycles (needs the pump cycle)"), ("time", "Seconds")]),
        Field("prerun.infusion_cycle", "block_cycles", "Cycles per block", 1, 20),
        Field("prerun.infusion_cycle", "block_s", "Block length", 2, 3600, 0, " s"),
        Field("prerun.infusion_cycle", "min_block_mg", "Lengthen each block to at least", 0, 5000, 0, " mg"),
        Field("prerun.infusion_cycle", "align_to_cycle", "Round up to whole pump cycles", choices=_ON_OFF),
        Field("prerun.infusion_cycle", "blocks", "Blocks compared", 2, 20),
        Field("prerun.infusion_cycle", "max_wait_min", "Start anyway after", 0, 240, 0, " min",
              hint="0 = wait until stable. Each model can have its own values (test wizard, step 6)"),
    ]),
    ("Automatic start · Infusion, time-based capture", [
        Field("prerun.infusion_time", "stability_pct", "Allowed flow variation", 0.1, 50, 1, " %"),
        Field("prerun.infusion_time", "block_mode", "Block length unit", choices=[
            ("cycle", "Pump cycles (needs the pump cycle)"), ("time", "Seconds")]),
        Field("prerun.infusion_time", "block_cycles", "Cycles per block", 1, 20),
        Field("prerun.infusion_time", "block_s", "Block length", 2, 3600, 0, " s"),
        Field("prerun.infusion_time", "min_block_mg", "Lengthen each block to at least", 0, 5000, 0, " mg"),
        Field("prerun.infusion_time", "align_to_cycle", "Round up to whole pump cycles", choices=_ON_OFF),
        Field("prerun.infusion_time", "blocks", "Blocks compared", 2, 20),
        Field("prerun.infusion_time", "max_wait_min", "Start anyway after", 0, 240, 0, " min",
              hint="0 = wait until stable. Each model can have its own values (test wizard, step 6)"),
    ]),
    ("Automatic start · Syringe, time-based capture", [
        Field("prerun.syringe_time", "stability_pct", "Allowed flow variation", 0.1, 50, 1, " %"),
        Field("prerun.syringe_time", "block_mode", "Block length unit", choices=[
            ("cycle", "Pump cycles (needs the pump cycle)"), ("time", "Seconds")]),
        Field("prerun.syringe_time", "block_cycles", "Cycles per block", 1, 20),
        Field("prerun.syringe_time", "block_s", "Block length", 2, 3600, 0, " s"),
        Field("prerun.syringe_time", "min_block_mg", "Lengthen each block to at least", 0, 5000, 0, " mg"),
        Field("prerun.syringe_time", "align_to_cycle", "Round up to whole pump cycles", choices=_ON_OFF),
        Field("prerun.syringe_time", "blocks", "Blocks compared", 2, 20),
        Field("prerun.syringe_time", "max_wait_min", "Start anyway after", 0, 240, 0, " min",
              hint="0 = wait until stable. Each model can have its own values (test wizard, step 6)"),
    ]),
    ("Self-check", [
        Field("selfcheck", "duration_min", "Duration", 1, 240, 0, " min"),
        Field("selfcheck", "max_halves_z", "Change must exceed balance noise by", 1, 10, 1, " ×",
              hint="Not settled = the two halves differ by more than this many times their uncertainty (from 10 blocks)"),
        Field("selfcheck", "max_halves_diff_mg_h", "Always accept a change between halves up to", 1, 1000, 0, " mg/h",
              hint="Smaller differences than this never count as unsettled — they are too small to matter"),
        Field("selfcheck", "max_abs_rate_mg_h", "Largest believable rate", 10, 10000, 0, " mg/h"),
    ]),
    ("Device check lists", [
        Field("catalog", "accessories", "Accessories", kind="lines", hint="One item per line"),
        Field("catalog", "parts", "Replaceable parts", kind="lines"),
        Field("warranty", "months", "Part warranty", 1, 120, suffix=" months",
              hint="Counted from the first time a part is recorded for a device — a warranty claim never restarts it"),
        Field("warranty", "grace_months", "Late claims considered for", 0, 24, suffix=" months"),
    ]),
    # ความปลอดภัยของบีกเกอร์ (ผู้ใช้ 2026-11-20 — core/beaker.py, services/beaker_guard.py)
    ("Beaker overflow protection", [
        Field("safety", "enabled", "Overflow protection", choices=_ON_OFF,
              hint="Warns with sound and a large pop-up before the beaker overflows"),
        Field("safety", "ask_on_start", "Set the beaker when the balance connects", choices=_ON_OFF,
              hint="On start-up: take the beaker off, RE-ZERO, put the beaker back — DeltaM then knows the water level"),
        Field("safety", "beaker_capacity_ml", "Beaker capacity", 5, 5000, 0, " ml"),
        Field("safety", "beaker_mass_g", "Empty beaker weight", 0, 5000, 1, " g",
              hint="Starting value — the setup window can weigh the empty beaker"),
        Field("safety", "warn_pct", "Warn when the beaker is", 10, 100, 0, " % full",
              hint="Warning sound + pop-up. The test keeps running"),
        Field("safety", "alarm_pct", "Alarm when the beaker is", 10, 100, 0, " % full",
              hint="Loud repeating alarm + large pop-up until someone presses Silence. The test keeps running"),
        Field("safety", "check_before_start", "Check before starting each rate", choices=_ON_OFF,
              hint="Calculates whether the rate would overflow the beaker and asks first"),
        Field("safety", "allowance_min", "Extra time in the calculation", 0, 120, 1, " min",
              hint="Pre-run plus the time until someone stops the pump"),
        Field("safety", "remind_after_test", "Remind to stop the pump after a rate", choices=_ON_OFF,
              hint="Soft beeps while water still flows into the beaker after the test has finished"),
        Field("safety", "remind_every_s", "Soft reminder every", 5, 600, 0, " s"),
        Field("safety", "idle_flow_min", "Remind when water flows with no test running for", 0, 120, 1, " min",
              hint="The pump runs but no test was started (or it was stopped long ago). 0 = off"),
        Field("safety", "alarm_every_s", "Alarm repeats every", 1, 60, 0, " s"),
    ]),
    ("Google Sheet options", [
        Field("sheets", "sync_on_start", "Read the sheets when DeltaM starts", choices=_ON_OFF,
              hint="In the background — DeltaM opens normally without internet and uses the last copy"),
        Field("sheets", "use_in_wizard", "Fill the new-test form from the sheet", choices=_ON_OFF,
              hint="Typing a Job no., serial no. or asset ID found in a sheet fills the empty fields"),
        Field("sheets", "use_in_history", "Search the sheet data in History", choices=_ON_OFF),
        Field("sheets", "timeout_s", "Give up reading after", 3, 120, 0, " s"),
    ]),
    ("Simulator", [
        Field("simulator", "speed", "Time speed-up", 0.1, 500, 1, " x"),
        Field("simulator", "error_pct", "Pump error", -50, 50, 2, " %"),
        Field("simulator", "ripple_pct", "Flow ripple", 0, 95, 1, " %"),
        Field("simulator", "cycle_period_s", "Cycle period", 1, 3600, 1, " s"),
        Field("simulator", "evaporation_mg_h", "Evaporation", 0, 5000, 0, " mg/h"),
    ]),
]


# แท็บด้านบน: (ชื่อแท็บ, [[กลุ่มคอลัมน์ซ้าย], [กลุ่มคอลัมน์ขวา]]) — ชื่อกลุ่มตาม GROUPS (2026-11-20 แทน LEFT_COLUMN)
SIGNATURES = "Signatures"
GOOGLE_SHEET = "Google Sheet"
REPORT = "Report"
TABS: list[tuple[str, list[list[str]]]] = [
    ("General", [["Interface"], []]),
    ("Balance and data", [[DATA_SOURCE], ["Reference balance", "Simulator"]]),
    ("Calculation", [["Calculation"], ["Evaporation during the measurement", "Self-check"]]),
    ("Automatic start", [["Automatic start · Infusion, pump-cycle capture", "Automatic start · Syringe, time-based capture"],
                         ["Automatic start · Infusion, time-based capture"]]),
    ("Uncertainty", [["Uncertainty"], []]),
    ("Safety", [["Beaker overflow protection"], []]),
    (GOOGLE_SHEET, [[], ["Google Sheet options"]]),  # ซ้าย = รายการแหล่ง (ui/widgets/sheet_settings.py) · ขวา = ตัวเลือก
    ("New test defaults", [["Job number", "Defaults for measured values (step 5 of a new test)", "Device check lists"],
                           ["Occlusion defaults · Infusion pump", "Occlusion defaults · Syringe pump"]]),
    (REPORT, []),           # แท็บย่อย REPORT_TABS
]
REPORT_TABS: list[tuple[str, list[list[str]]]] = [
    ("Saving and printing", [["Saving and printing"], []]),
    ("Header and footer", [["Company and header"], ["Page footer"]]),
    (SIGNATURES, []),
    ("Report content", [["Inspection report", "Graphs and values (both reports)"], ["Calibration report"]]),
]


class _DetectWorker(QObject):
    progress = Signal(str)
    done = Signal(object)       # Detection | None | Exception

    def __init__(self, serial_settings):
        super().__init__()
        self._settings = serial_settings
        self.cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            self.done.emit(detect_settings(self._settings, progress=self.progress.emit,
                                           should_stop=lambda: self.cancelled))
        except Exception as exc:
            self.done.emit(exc)


class SettingsPage(QWidget):
    saved = Signal()
    repeat_study_requested = Signal(object)     # TestPlan ของการสอบเทียบความซ้ำ -> หน้าต่างหลักส่งไปหน้าทดสอบ

    def __init__(self, settings: AppSettings, pause_balance=None, resume_balance=None, sample_period=None):
        """pause_balance / resume_balance: ฟังก์ชันปล่อย/คืนพอร์ตตราชั่งระหว่างค้นหาอัตโนมัติ
        sample_period: ฟังก์ชันคืนช่วงเวลาต่อจุดของตราชั่งที่วัดได้ (ใช้แปลงสัดส่วนของคาบเป็นจำนวนจุด)"""
        super().__init__()
        self.setObjectName("page")
        self._settings = settings
        self._pause_balance, self._resume_balance = pause_balance, resume_balance
        self._sample_period = sample_period or (lambda: None)
        self._editors: list[tuple[Field, QWidget]] = []
        self._cards: dict[str, Card] = {}
        self._detect_thread: QThread | None = None
        self._detect_worker: _DetectWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        header = PageHeader(tr("Settings"), tr("Saved values apply from the next test"))
        self.status = label("", "hint")
        reset = QPushButton(tr("Reset to defaults"))
        save = QPushButton("  " + tr("Save"))
        save.setProperty("variant", "primary")
        save.setIcon(glyph_icon(Glyph.SAVE, Color.ON_ACCENT, size=14))
        save.setStyleSheet("padding: 7px 18px; font-size: 13px;")
        for widget in (self.status, reset, save):
            header.actions.addWidget(widget)
        layout.addWidget(header)

        groups = dict(GROUPS)
        self.tabs = QTabWidget()
        self.tabs.setProperty("tabsStyle", "settings")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        for title, columns in TABS:
            if title == REPORT:
                self.report_tabs = QTabWidget()
                self.report_tabs.setProperty("tabsStyle", "sub")
                self.report_tabs.setDocumentMode(True)
                self.report_tabs.tabBar().setDrawBase(False)
                for sub_title, sub_columns in REPORT_TABS:
                    if sub_title == SIGNATURES:
                        from ui.widgets.signature_settings import SignatureSettings
                        self.signatures = SignatureSettings()
                        self.report_tabs.addTab(self._scroll(self.signatures), tr(sub_title))
                    else:
                        self.report_tabs.addTab(self._tab_page(sub_columns, groups), tr(sub_title))
                self.tabs.addTab(self.report_tabs, tr(title))
            elif title == GOOGLE_SHEET:
                from ui.widgets.sheet_settings import SheetSettings
                self.sheet_settings = SheetSettings()
                holder = QWidget()
                holder_box = QHBoxLayout(holder)
                holder_box.setContentsMargins(0, 0, 0, 0)
                holder_box.setSpacing(14)
                holder_box.addWidget(self.sheet_settings, 3)
                side = QVBoxLayout()
                for group_title in columns[1]:
                    side.addWidget(self._build_group(group_title, groups[group_title]))
                side.addStretch(1)
                holder_box.addLayout(side, 2)
                self.tabs.addTab(self._scroll(holder), tr(title))
            else:
                self.tabs.addTab(self._tab_page(columns, groups), tr(title))
        self._add_detect_row()
        self._add_calibration_row()
        self._add_repeatability_row()
        layout.addWidget(self.tabs, 1)

        save.clicked.connect(self._save)
        reset.clicked.connect(self._reset)
        self.load()

    # ------------------------------------------------------------ สร้าง UI
    @staticmethod
    def _scroll(widget: QWidget) -> QScrollArea:
        holder = QWidget()
        box = QVBoxLayout(holder)
        box.setContentsMargins(0, 14, 8, 8)
        box.addWidget(widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(holder)
        return scroll

    def _tab_page(self, columns: list[list[str]], groups: dict) -> QScrollArea:
        """หน้าแท็บ: การ์ดของกลุ่ม 2 คอลัมน์ (คอลัมน์ขวาว่าง = การ์ดกว้างครึ่งหน้า อ่านง่ายกว่าเต็มจอ)"""
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        for titles in (columns + [[], []])[:2]:
            column = QVBoxLayout()
            column.setSpacing(14)
            for title in titles:
                column.addWidget(self._build_group(title, groups[title]))
            column.addStretch()
            row.addLayout(column, 1)
        return self._scroll(content)

    def _build_group(self, title: str, group_fields: list[Field]) -> Card:
        card = Card(tr(title))
        self._cards[title] = card
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for f in group_fields:
            if f.kind == "note":                         # ข้อความอธิบายอย่างเดียว (ไม่มีค่าตั้ง)
                note = label(tr(f.hint), "hint")
                note.setWordWrap(True)
                form.addRow(label(tr(f.text), "fieldLabel"), note)
                continue
            editor = self._build_editor(f)
            self._editors.append((f, editor))
            row = editor
            if f.editable and callable(f.choices):      # combo ที่รายการเปลี่ยนได้ -> มีปุ่ม refresh
                row = QWidget()
                box = QHBoxLayout(row)
                box.setContentsMargins(0, 0, 0, 0)
                box.setSpacing(6)
                refresh = QPushButton()
                refresh.setIcon(glyph_icon(Glyph.REFRESH, Color.TEXT, size=14))
                refresh.setToolTip(tr("Scan for ports"))
                refresh.clicked.connect(lambda _=False, fd=f, ed=editor: self._fill_combo(fd, ed, ed.currentText()))
                box.addWidget(editor, 1)
                box.addWidget(refresh)
            if isinstance(editor, QCheckBox):            # เปิด/ปิด: ช่องติ๊ก + ข้อความในตัว (ไม่ต้องอ่านป้ายซ้าย)
                editor.setText(tr(f.text))
                form.addRow("", row)
            else:
                form.addRow(label(tr(f.text), "fieldLabel"), row)
            if f.hint:
                hint = label(tr(f.hint), "hint")
                hint.setWordWrap(True)
                form.addRow("", hint)
        card.body.addLayout(form)
        card.body.addStretch()
        return card

    def _build_editor(self, f: Field) -> QWidget:
        if f.choices is _ON_OFF:                    # เปิด/ปิด = ช่องติ๊ก (2026-11-20 — เดิม combo On/Off)
            return QCheckBox()
        if f.kind in ("folder", "image", "file"):
            return PathEdit(f.kind)
        if f.kind == "date":
            return DateField()
        if f.choices is not None:
            combo = QComboBox()
            combo.setEditable(f.editable)
            return combo
        if f.kind == "text":
            return QLineEdit()
        if f.kind == "lines":
            editor = QPlainTextEdit()
            editor.setFixedHeight(128)
            return editor
        current = getattr(self._target(f), f.name)
        box = QDoubleSpinBox() if isinstance(current, float) else QSpinBox()
        if isinstance(box, QDoubleSpinBox):
            box.setDecimals(f.decimals)
            box.setRange(f.minimum, f.maximum)
        else:
            box.setRange(int(f.minimum), int(f.maximum))
        box.setSuffix(f.suffix)
        box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return box

    def _fill_combo(self, f: Field, combo: QComboBox, value) -> None:
        choices = f.choices() if callable(f.choices) else f.choices
        combo.clear()
        for data, text in choices:
            combo.addItem(tr(text) if f.translate else text, data)
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif f.editable:
            combo.setEditText(str(value))

    def _target(self, f: Field):
        target = self._settings
        for part in f.section.split(".") if f.section else ():      # รองรับกลุ่มซ้อน เช่น "prerun.syringe_time"
            target = getattr(target, part)
        return target

    # ---------------------------------------------------------- load / save
    def _set_editor(self, f: Field, editor: QWidget, value) -> None:
        if isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))
        elif isinstance(editor, (PathEdit, DateField)):
            editor.setText(str(value or ""))
        elif isinstance(editor, QComboBox):
            self._fill_combo(f, editor, value)
        elif isinstance(editor, QLineEdit):
            editor.setText(str(value))
        elif isinstance(editor, QPlainTextEdit):
            editor.setPlainText("\n".join(value))
        else:
            editor.setValue(value)

    def _read_editor(self, f: Field, editor: QWidget):
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, (PathEdit, DateField)):
            return editor.text()
        if isinstance(editor, QComboBox):
            return editor.currentText().strip() if f.editable else editor.currentData()
        if isinstance(editor, QLineEdit):
            return editor.text().strip()
        if isinstance(editor, QPlainTextEdit):
            return [line.strip() for line in editor.toPlainText().splitlines() if line.strip()]
        return editor.value()

    def load(self) -> None:
        for f, editor in self._editors:
            self._set_editor(f, editor, getattr(self._target(f), f.name))
        self.signatures.load(self._settings.report)      # ผู้ลงนาม + ช่องลายเซ็น
        self.sheet_settings.load(self._settings)          # แหล่ง Google Sheet

    def _save(self) -> None:
        for f, editor in self._editors:
            setattr(self._target(f), f.name, self._read_editor(f, editor))
        self.signatures.store(self._settings.report)
        self.sheet_settings.store(self._settings)
        try:
            self._settings.save()
            self.status.setText(tr("Saved ✓"))
        except OSError as exc:
            self.status.setText(tr("Could not save: {error}", error=exc))
        self.saved.emit()

    def _reset(self) -> None:
        self._settings.reset()
        self.load()
        self.status.setText(tr("Defaults restored (not saved yet)"))

    # ------------------------------------------------------ ค้นหาตราชั่งอัตโนมัติ
    def _add_detect_row(self) -> None:
        card = self._cards[DATA_SOURCE]
        row = QHBoxLayout()
        self.btn_detect = QPushButton(tr("Find the balance automatically"))
        self.btn_detect.setToolTip(tr("Tries the ports and the usual port settings until the balance answers"))
        self.detect_status = label("", "hint")
        self.detect_status.setWordWrap(True)
        row.addWidget(self.btn_detect)
        row.addWidget(self.detect_status, 1)
        card.body.insertLayout(card.body.count() - 1, row)
        self.btn_detect.clicked.connect(self._toggle_detect)

    # ------------------------------------------------------ ข้อมูลสอบเทียบรอบปั๊ม
    def _add_calibration_row(self) -> None:
        card = self._cards["Calculation"]
        row = QHBoxLayout()
        button = QPushButton(tr("Pump-cycle calibration data…"))
        button.setToolTip(tr("See and edit the regression and n̄ windows of every rate, per model and IV set"))
        hint = label(tr("Regression / n̄ of every rate, per brand + model + pump type + IV set"), "hint")
        hint.setWordWrap(True)
        row.addWidget(button)
        row.addWidget(hint, 1)
        card.body.insertLayout(card.body.count() - 1, row)
        button.clicked.connect(self._open_calibration_data)

    def _add_repeatability_row(self) -> None:
        """ตารางความซ้ำ 2SD ต่อ รุ่น/ชนิด/ชุดสาย/rate (กรอกเอง หรือสอบเทียบ N ครั้ง) — ใช้ในงบความไม่แน่นอน"""
        card = self._cards["Uncertainty"]
        row = QHBoxLayout()
        button = QPushButton(tr("Measurement repeatability (2SD)…"))
        button.setProperty("variant", "primary")
        hint = label(tr("2SD per brand + model + pump type + IV set + rate — enter it or measure it (repeated runs)"), "hint")
        hint.setWordWrap(True)
        row.addWidget(button)
        row.addWidget(hint, 1)
        card.body.insertLayout(1, row)
        button.clicked.connect(self._open_repeatability)

    def _open_repeatability(self) -> None:
        from services.session_store import get_repository
        from ui.dialogs.repeatability import RepeatabilityDialog
        dialog = RepeatabilityDialog(self, get_repository(), self._settings)
        dialog.start_requested.connect(self.repeat_study_requested)
        dialog.exec()

    def _open_calibration_data(self) -> None:
        from services.session_store import get_repository
        from services.window_plan import sample_period_estimate
        from ui.dialogs.calibration_data import CalibrationDataDialog
        repository = get_repository()
        dt, _ = sample_period_estimate(self._settings, self._sample_period(), repository)
        CalibrationDataDialog(self, repository, self._settings.engine, dt).exec()

    def _editor(self, section: str, name: str) -> tuple[Field, QWidget]:
        return next((f, e) for f, e in self._editors if f.section == section and f.name == name)

    def _toggle_detect(self) -> None:
        if self._detect_worker is not None:             # กดอีกครั้ง = ยกเลิก
            self._detect_worker.cancelled = True
            return
        current = dataclasses.replace(self._settings.serial)
        for name in ("port", "baudrate", "bytesize", "parity", "stopbits"):   # เริ่มจากค่าที่เห็นบนจอ
            setattr(current, name, self._read_editor(*self._editor("serial", name)))
        if self._pause_balance:
            self._pause_balance()
        self.btn_detect.setText(tr("Cancel"))
        self._detect_worker = _DetectWorker(current)
        self._detect_thread = QThread(self)
        self._detect_worker.moveToThread(self._detect_thread)
        self._detect_thread.started.connect(self._detect_worker.run)
        self._detect_worker.progress.connect(lambda text: self.detect_status.setText(tr("Trying {what}…", what=text)))
        self._detect_worker.done.connect(self._on_detect_done)
        self._detect_thread.start()

    @Slot(object)
    def _on_detect_done(self, result) -> None:
        self._detect_thread.quit()
        self._detect_thread.wait(3000)
        self._detect_thread = self._detect_worker = None
        self.btn_detect.setText(tr("Find the balance automatically"))
        if isinstance(result, Detection):
            for name in ("port", "baudrate", "bytesize", "parity", "stopbits", "mode"):
                self._set_editor(*self._editor("serial", name), getattr(result, name))
            self._set_editor(*self._editor("", "source"), "serial")
            self.detect_status.setText(tr(
                "Found: {port} · {baud} {bits}{parity}{stop} · {mode} · about {rate:.0f} values/s — "
                "press Save to use it.   Sample: {line}",
                port=result.port, baud=result.baudrate, bits=result.bytesize, parity=result.parity,
                stop=result.stopbits, mode=result.mode, rate=result.rate_hz, line=result.sample_line))
        elif isinstance(result, Exception):
            self.detect_status.setText(tr("Search failed: {error}", error=result))
        else:
            self.detect_status.setText(tr("No balance answered. Check the cable, power and the balance's output setting."))
        if self._resume_balance:
            self._resume_balance()
