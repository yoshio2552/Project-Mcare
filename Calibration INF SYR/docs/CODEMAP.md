# DeltaM — แผนที่โค้ด (อ่านแทนการเปิดโค้ดทั้งหมด)

อัปเดต 2026-11-13 · ~14,000 บรรทัด Python (รวม tests) · ใช้ไฟล์นี้หาว่า "ต้องเปิดไฟล์ไหน" แล้วเปิดเฉพาะไฟล์นั้น
(ตัวเลขในวงเล็บ = จำนวนบรรทัด · ★ = ไฟล์ใหญ่/สำคัญ อ่านเฉพาะส่วนที่ต้องแก้)

## ชั้นของระบบ (ชั้นล่างไม่ import ชั้นบน)

```
config/   ค่าตั้ง + ภาษา                          ← ทุกชั้นใช้ได้
core/     คำนวณล้วน ไม่มี Qt ไม่มี hardware        ← ทดสอบได้โดยไม่ต้องมีจอ
hardware/ แหล่งน้ำหนัก (ตราชั่งจริง/จำลอง/replay)
services/ เชื่อม core + hardware + ฐานข้อมูล เข้ากับ Qt (thread, signal)
ui/       หน้าจอ PySide6 + pyqtgraph — คุยกับ SessionController / Repository เท่านั้น
```

เส้นทางข้อมูลระหว่างทดสอบ:
`BalanceSource.read()` → `AcquisitionWorker` (thread) → `FlowEngine.process()` → `EngineResult` → `SessionController` (รวมชุด ~30 FPS) → การ์ด/กราฟ
ข้อมูลดิบเขียนลงดิสก์ระหว่างรันโดย `RawRecorder` (ไม่เก็บใน RAM)

## config/

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| constants.py (40) | ชื่อ/เวอร์ชัน (0.3.0), path ของ `data/`, preset rate/tolerance/วิธีจับ/ค่าโหมด | `RATE_PRESETS`, `DEFAULT_STRATEGY`, `MODE_DEFAULTS`, `WINDOW_CHOICES_S` |
| settings.py (230) | ค่าตั้งทั้งหมดเป็น dataclass → `data/settings.json` | `AppSettings` (serial, simulator, replay, engine, prerun, selfcheck, catalog, ui) · `EngineSettings` (ค่าคำนวณต่อการทดสอบ — คัดลอกตอนเริ่ม) · `PrerunCriteria`/`prerun_group()` |
| i18n.py (41) | `tr("English", **ค่า)` → แปลจากตาราง · `missing()` = ข้อความที่ยังไม่แปล | `tr`, `set_language`, `missing` |
| lang_th.py (950) | ตารางคำแปลไทย `TRANSLATIONS` (เพิ่มคำใหม่ท้ายไฟล์ ไม่ต้องอ่านทั้งไฟล์ — ใช้ grep) | |

## core/ (ไม่มี Qt)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| models.py (285) ★ | dataclass กลางทุกชั้น | `JobInfo`, `StepConfig`, `TestPlan` → `session_config(i)` → `SessionConfig`, `EngineResult`, `Interval`, `IntervalStats`, `SessionSummary`, enum `PumpType/RunMode/EndMode/StartMode/Stage/SessionState/Verdict(PASS/FAIL/N/A/INVALID)` |
| engine.py (347) ★ | `FlowEngine`: pre-run → warm-up → slope → strategy → สถิติ → `summary()` | `process()`, `_apply_tuning()` (ตั้งหน้าต่างจากคาบหลัง pre-run), `capture_check()`, `verdict()`, `_SlopeWindow`, `_Span` |
| stats.py (122) | สถิติล้วน | `regression_slope`, `RunningStats` (Welford), `t_score`, `percent_error`, `flow_ml_per_h` |
| corrections.py (239) | g→ml (ISO 4787 Z: ρw Tanaka, ρa OIML) + self-check (การระเหย) | `gravimetric_correction()` → `GravimetricCorrection`, `analyse_baseline()`, `BaselineEngine` |
| cycle_analyzer.py (90) | จับ peak/valley ของ slope ด้วยหน้าต่าง `2·n̄+1` → รอบ TOP→TOP / DOWN→DOWN | `CycleAnalyzer.update()` |
| prerun.py (258) | ช่วงก่อนวัด: หาคาบ (autocorrelation) + ตรวจ flow นิ่ง | `PeriodEstimator`, `flow_stability()`, `block_length()`, `PreRun` |
| windows.py (100) | **สูตรเดียว** คาบ × สัดส่วน → จำนวนจุด, ขั้นต่ำ 5/3, ระดับจุดต่อรอบ, ช่วงที่ใช้ได้ | `cycle_windows()` → `CycleWindows(level ok/low/too_low)`, `fraction_problems()`, `fractions_from_points()`, `time_window_for()` |
| capture_check.py (101) | ตรวจผลจับรอบหลังจบ → INVALID (รอบไม่ตรงคาบ/ไม่พอ) + ตรวจย้อนผลเก่า | `check_cycle_capture()`, `check_summary()`, `effective_verdict()` |
| profiles.py (76) | กุญแจ ยี่ห้อ+รุ่น+ชนิด+ชุดสาย, โปรไฟล์ปริมาตรต่อรอบ | `pump_key()`, `PumpProfile` |
| tuning.py (200) | ปรับ (r, h) ราย rate โดยเล่น raw ที่เก็บไว้ผ่าน `FlowEngine` แล้วให้คะแนน | `tune()`, `evaluate()`, `TuningResult.recommended()`, `reference_period()` |
| registry.py (47) | Registry "ตัวต่อ Lego" | `Registry.register/create/get/choices` |
| strategies/ | วิธีแบ่งช่วงวัด ลงทะเบียน `STRATEGIES` | `pump_cycle.py` (84, `uses_cycles=True`, จับรอบคู่/เดี่ยว) · `time_based.py` (53, `time_interval`, `time_total`) · `base.py` (`FlowStrategy`) |

## hardware/

| ไฟล์ | หน้าที่ |
|---|---|
| base.py (33) | สัญญา `BalanceSource` (open/read/close) — ลงทะเบียน `SOURCES` |
| serial_balance.py (317) | RS-232 stream/poll/auto, thread อ่านแยก + คิว + เวลาประทับ, `detect_settings()` ค้นหาพอร์ต, `Diagnostics` |
| parsers.py (81) | อ่านบรรทัด A&D แบบเข้มงวด/auto/generic (`LINE_FORMATS`) |
| simulator.py (60) | ตราชั่งจำลอง (flow แกว่งตามรอบ, noise, การระเหย) — `weight_at(t)` |
| replay.py (69) | เล่นซ้ำ raw.csv / capture เหมือนตราชั่ง · `load_samples()` |

## services/ (Qt glue)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| session_controller.py (583) ★ | **หัวใจ**: แผนหลายขั้น, start/stop, เก็บ/ไม่เก็บ, self-check, monitor, เรียนรู้โปรไฟล์, ปรับหน้าต่าง | `set_plan`, `start_step`, `keep_result`, `discard_result`, `_prepare_settings` (ประกอบค่าคำนวณ 1 ขั้น), `_prepare_windows`, `_learn_profile`, `_tune_windows`, `rate_windows`, signals `review_requested/session_finished/results_ready` |
| session_store.py (888) ★ | `Repository` SQLite `data/deltam.db` (SCHEMA_VERSION 4) + โฟลเดอร์ผล | ผล: `save/list/load/delete/verify/read_samples` · โปรไฟล์: `get_profile/expected_period_info/check_observation/add_observation/recalibrate/set_model_default` · หน้าต่าง: `window_fractions/save_tuning/save_window/delete_window/tuned_windows/calibration_models/tuning_datasets` · `get_repository()/set_repository()` |
| window_plan.py (113) | หน้าต่าง **ราย rate** (คาบ + ที่มา + สัดส่วน + จุด) ใช้ร่วมทุกจอ | `rate_window()`, `plan_windows()`, `RateWindow`, `sample_period_estimate()`, `FIT_TEXT` |
| acquisition.py (89) | thread: อ่าน → engine → recorder → signal | `AcquisitionWorker` |
| recorder.py (42) | เขียน raw.csv / prerun.csv ระหว่างรัน (flush ทุก 1 s) | `RawRecorder` |
| monitor.py (88) | น้ำหนักสดตอนว่าง + วัดช่วงเวลาต่อจุดของตราชั่ง | `BalanceMonitor` |
| tuner.py (71) | รัน `core.tuning` ใน thread หลังเก็บผล | `WindowTuner` |
| exporters.py (104) | ส่งออก Excel — จุดต่อ PDF (`EXPORTERS`) | `XlsxExporter` |
| job_suggestions.py (112) | smart autofill ของฟอร์มงาน | `JobSuggester` |
| logging_setup.py (50) | log → ไฟล์ `data/logs` + แผง log บนจอ | `setup_logging`, `LogBridge` |

## ui/

| ไฟล์ | หน้าที่ |
|---|---|
| main_window.py (120) | แถบนำทาง + หน้า (ทดสอบ / ประวัติ / ตั้งค่า) · `main.py` สร้างผ่าน `Application.build_window()` |
| theme.py (265) | สี (`Color`, `TONES`, `Color.INFUSION/SYRINGE`), ฟอนต์, stylesheet กลาง |
| pages/test_page.py (470) ★ | หน้าทดสอบ: แผงแผน + การ์ด + กราฟ 4 ช่อง (`PLOT_GRID`) + แถบติดตาม · เปิด wizard, ถามเก็บผล |
| pages/history.py (291) | ตารางผล แท็บตามโหมด, ค้นหา/กรอง (รวม INVALID), ลบ, ส่งออก, ปุ่มปรับหน้าต่าง · `COLUMNS` |
| pages/settings.py (420) | ฟอร์มสร้างจากตาราง `GROUPS` (`Field`) + ค้นหาตราชั่ง + ปุ่มข้อมูลสอบเทียบรอบปั๊ม |
| dialogs/test_wizard.py (982) ★ | wizard 4 ขั้น (งาน → ตรวจเครื่อง → โหมด → ตั้งค่า) → `TestPlan` · `_on_next`, `_check_calibration`, `_prompt_calibration`, `_refresh_windows`, `JOB_FIELDS`, `WINDOW_SOURCES` |
| dialogs/calibration_prompt.py (192) | popup เตือนสอบเทียบก่อนสร้างการทดสอบจับรอบปั๊ม (สอบเทียบ / ข้าม+แก้+บันทึก / จับตามเวลา) |
| dialogs/calibration_data.py (205) | ตั้งค่า → ข้อมูลสอบเทียบรอบปั๊ม: ดู/แก้/เพิ่ม/ลบ regression, n̄ ราย rate ต่อรุ่น |
| dialogs/result_review.py (105) | ถาม "เก็บผลนี้ไหม" (ไม่เก็บ = ลบจริง) + แถบเตือน INVALID |
| dialogs/session_detail.py (263) | ดูผลย้อนหลัง: ข้อมูล + การจับรอบ + ค่าแก้ (audit) + กราฟ |
| dialogs/recalibrate.py (77), profile_deviation.py (94), prerun_criteria.py (108) | Calibration รอบปั๊มใหม่ · รอบปั๊มต่างจากเดิม · เกณฑ์ flow นิ่งเฉพาะรุ่น |
| widgets/window_table.py (155) | ตารางหน้าต่างราย rate (แก้เป็นจุดได้) — ใช้ใน 2 dialog ข้างบน |
| widgets/plan_panel.py (280) | แผงแผนทดสอบ + การ์ดตราชั่ง (self-check) |
| widgets/process_tracker.py (305), stat_card.py (79), smart_edit.py (149), pump_type.py (204), common.py (106), log_panel.py (39) | แถบติดตาม · การ์ดตัวเลข · ช่องกรอกอัจฉริยะ · ตัวเลือก Infusion/Syringe · `label/number_box/int_box/fmt/Card` · log |
| plots/base.py (230) | `PlotModule` แม่แบบกราฟ, `RingBuffer`/`DecimatingBuffer` (หน่วยความจำคงที่) · กราฟ: weight, slope, intervals, cumulative · `cell.py` หัวกราฟ |

## tools/ และ tests/

- `tools/capture_raw.py` เก็บบรรทัดดิบ + เวลาส่ง/รับ (ไม่ใช้ Qt, `--reparse`) · `tools/check_balance.py` ตรวจการอ่านตราชั่งจริง
- tests 119 ข้อ (~90 s): `python -m unittest discover -s tests -v` · ไฟล์ตามหัวข้อ: core/engine (`test_core`), ตราชั่ง (`test_serial_timing`, `test_extensions`),
  g→ml (`test_corrections`), เรียนรู้/ปรับหน้าต่าง (`test_learning`, `test_recalibration`), เกณฑ์+ฟอร์ม (`test_criteria_smart`),
  หน้าต่างราย rate + INVALID + รันนาน (`test_windows`), UI offscreen (`test_ui_dialogs`)
- `tests/fixtures/gf300_inf10_excerpt.csv` = ไบต์จริงจาก GF-300

## ฐานข้อมูล `data/deltam.db` (SCHEMA_VERSION 4 — migration อัตโนมัติ + สำรองไฟล์ `deltam.vN-backup.db`)

| ตาราง | เก็บอะไร |
|---|---|
| sessions | ผลทุกขั้น (คอลัมน์ค้นหา + `summary_json` เต็ม, `verdict`, `mode`, `folder`) |
| intervals | ทุกช่วงวัดของทุกผล (Dashboard ในอนาคต) |
| profiles / profile_observations | ปริมาตรต่อรอบต่อรุ่น / คาบที่วัดได้รายครั้ง (+ decision, `calibrated_at`) |
| window_tuning | r, h ราย rate + `source` (tuned / manual / uncalibrated) |
| prerun_criteria | เกณฑ์ flow นิ่งเฉพาะรุ่น |
| self_checks, model_items, session_files | self-check · รายการตรวจเครื่องต่อรุ่น · SHA-256 ไฟล์ผล |

โฟลเดอร์ผล `data/sessions/<วันเวลา>_<ชนิด>_<rate>mlh/`: `raw.csv.gz`, `prerun.csv.gz`, `intervals.csv`, `summary.json`

## งานแบบไหน เปิดไฟล์ไหน

| งาน | เปิด |
|---|---|
| สูตร/อัลกอริทึม | `docs/calculation-methods.md` หัวข้อที่เกี่ยว → `core/` ไฟล์นั้น (+ อัปเดตเอกสาร) |
| ค่าที่ใช้คำนวณ 1 ขั้น | `SessionController._prepare_settings` / `_prepare_windows` |
| หน้าจอใหม่ / หน้า Dashboard | `ui/pages/` + `ui/main_window.py` (`_add_page`) + อ่านข้อมูลผ่าน `Repository` |
| ฟอร์มสร้างการทดสอบ | `ui/dialogs/test_wizard.py` (ใหญ่ — grep ชื่อเมธอดก่อน) |
| ค่าตั้งใหม่ | `config/settings.py` + 1 บรรทัดใน `GROUPS` ของ `ui/pages/settings.py` |
| ตาราง/คอลัมน์ฐานข้อมูล | `_SCHEMA` + `_migrate*` + `SCHEMA_VERSION` ใน `services/session_store.py` |
| ส่งออก/รายงาน | `services/exporters.py` (`@EXPORTERS.register`) |
| ตราชั่งรุ่นใหม่ | `hardware/` (`@SOURCES.register`) / `parsers.py` (`LINE_FORMATS`) |
| ตารางต่อยอดเต็ม (Lego) | README.md หัวข้อ "วิธีต่อยอด" |
