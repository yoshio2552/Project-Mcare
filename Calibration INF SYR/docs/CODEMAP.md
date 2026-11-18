# DeltaM — แผนที่โค้ด (อ่านแทนการเปิดโค้ดทั้งหมด)

อัปเดต 2026-11-18 (ใบรายงาน PDF) · ~15,000 บรรทัด Python (รวม tests) · ใช้ไฟล์นี้หาว่า "ต้องเปิดไฟล์ไหน" แล้วเปิดเฉพาะไฟล์นั้น
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
| constants.py (60) | ชื่อ/เวอร์ชัน (0.3.0), path ของ `data/` (`_app_dir()` = ข้าง exe เมื่อเป็น Nuitka/PyInstaller), preset rate/tolerance/วิธีจับ/ค่าโหมด | `RATE_PRESETS`, `DEFAULT_STRATEGY`, `MODE_DEFAULTS`, `WINDOW_CHOICES_S` |
| settings.py (255) | ค่าตั้งทั้งหมดเป็น dataclass → `data/settings.json` | `AppSettings` (serial, simulator, replay, engine, prerun, selfcheck, catalog, balance, warranty, ui — `ui.graph_range/graph_auto_cycles/graph_zoom_s`) · `EngineSettings` (ค่าคำนวณต่อการทดสอบ — คัดลอกตอนเริ่ม) · `PrerunCriteria`/`prerun_group()` |
| i18n.py (41) | `tr("English", **ค่า)` → แปลจากตาราง · `missing()` = ข้อความที่ยังไม่แปล | `tr`, `set_language`, `missing` |
| provinces.py (15) | 77 จังหวัด สำหรับช่องจังหวัด | `PROVINCES` |
| lang_th.py (1040) | ตารางคำแปลไทย `TRANSLATIONS` (เพิ่มคำใหม่ท้ายไฟล์ ไม่ต้องอ่านทั้งไฟล์ — ใช้ grep) | |

## core/ (ไม่มี Qt)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| models.py (320) ★ | dataclass กลางทุกชั้น | `JobInfo` (+ job_no, site, province, accessory_brand, accessory_usage, parts_warranty), `JOB_PREFIXES`/`pump_from_job_no`/`job_no_for_pump` (MCI/MCS), `StepConfig`, `TestPlan` → `session_config(i)` → `SessionConfig`, `EngineResult`, `Interval`, `IntervalStats`, `SessionSummary`, enum `PumpType/RunMode/EndMode/StartMode/Stage/SessionState/Verdict(PASS/FAIL/N/A/INVALID)` |
| engine.py (347) ★ | `FlowEngine`: pre-run → warm-up → slope → strategy → สถิติ → `summary()` | `process()`, `_apply_tuning()` (ตั้งหน้าต่างจากคาบหลัง pre-run), `capture_check()`, `verdict()`, `_SlopeWindow`, `_Span` |
| stats.py (122) | สถิติล้วน | `regression_slope`, `RunningStats` (Welford), `t_score`, `percent_error`, `flow_ml_per_h` |
| corrections.py (239) | g→ml (ISO 4787 Z: ρw Tanaka, ρa OIML) + self-check (การระเหย) | `gravimetric_correction()` → `GravimetricCorrection`, `analyse_baseline()`, `BaselineEngine` |
| cycle_analyzer.py (115) | จับ peak/valley ของ slope ด้วยหน้าต่าง `2·n̄+1` → รอบ TOP→TOP / DOWN→DOWN · รอยืนยัน + เกณฑ์แอมพลิจูด กันยอดรอง | `CycleAnalyzer.update()`, `MIN_SWING_FRACTION` |
| prerun.py (258) | ช่วงก่อนวัด: หาคาบ (autocorrelation) + ตรวจ flow นิ่ง | `PeriodEstimator`, `flow_stability()`, `block_length()`, `PreRun` |
| windows.py (100) | **สูตรเดียว** คาบ × สัดส่วน → จำนวนจุด, ขั้นต่ำ 5/3, ระดับจุดต่อรอบ, ช่วงที่ใช้ได้ | `cycle_windows()` → `CycleWindows(level ok/low/too_low)`, `fraction_problems()`, `fractions_from_points()`, `time_window_for()` |
| capture_check.py (101) | ตรวจผลจับรอบหลังจบ → INVALID (รอบไม่ตรงคาบ/ไม่พอ) + ตรวจย้อนผลเก่า | `check_cycle_capture()`, `check_summary()`, `effective_verdict()` |
| warranty.py (125) | ประกันอะไหล่: สถานะ active/late/expired, วันเริ่มประกัน (เคลมไม่นับใหม่), สรุปต่อชนิดอะไหล่ | `status()`, `start_for()`, `summarize()`, `PartRecord`, `PartWarranty` |
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
| session_store.py (1000) ★ | `Repository` SQLite `data/deltam.db` (SCHEMA_VERSION 5) + โฟลเดอร์ผล | ผล: `save/list/load/delete/verify/read_samples` · โปรไฟล์: `get_profile/expected_period_info/check_observation/add_observation/recalibrate/set_model_default` · หน้าต่าง: `window_fractions/save_tuning/save_window/delete_window/tuned_windows/calibration_models/tuning_datasets` · อะไหล่: `part_history/record_parts/delete_parts` · ชุดสายมาตรฐาน: `site_standard/set_site_standard` · `get_repository()/set_repository()` (**ห้ามเรียก get_repository ในเทสต์ก่อน set — เปิด data/ จริง**) |
| window_plan.py (113) | หน้าต่าง **ราย rate** (คาบ + ที่มา + สัดส่วน + จุด) ใช้ร่วมทุกจอ | `rate_window()`, `plan_windows()`, `RateWindow`, `sample_period_estimate()`, `FIT_TEXT` |
| acquisition.py (89) | thread: อ่าน → engine → recorder → signal | `AcquisitionWorker` |
| recorder.py (42) | เขียน raw.csv / prerun.csv ระหว่างรัน (flush ทุก 1 s) | `RawRecorder` |
| monitor.py (88) | น้ำหนักสดตอนว่าง + วัดช่วงเวลาต่อจุดของตราชั่ง | `BalanceMonitor` |
| tuner.py (71) | รัน `core.tuning` ใน thread หลังเก็บผล | `WindowTuner` |
| exporters.py (125) | ส่งออก Excel + ใบรายงาน PDF รวมไฟล์เดียว (`EXPORTERS`) | `XlsxExporter`, `PdfExporter` |
| job_suggestions.py (150) | smart autofill ของฟอร์มงาน + เติมจากรุ่น | `JobSuggester.suggest`, `infer_device(model)`, `infer_accessory_brand` |
| **report/** | **ใบรายงาน PDF / พิมพ์ / ดูตัวอย่าง ตามแบบ Main Fable-1** (ไม่มี Qt ยกเว้น render/printing) | ดูตารางย่อยด้านล่าง |
| logging_setup.py (50) | log → ไฟล์ `data/logs` + แผง log บนจอ | `setup_logging`, `LogBridge` |

### services/report/ (ใบรายงาน — แบบ `template/Main Fable-1`)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| model.py (330) | รวม session หลาย rate ของงานเดียว (job_id) เป็นใบ · เลือกผลล่าสุดที่ completed + ไม่ INVALID ราย rate + คำเตือน · n = รอบสาย A · ±1 SD ของเวลา/ปริมาตรต่อช่วง · ผลรวมของใบ · ข้อมูลที่ยังไม่กรอก | `group_jobs`, `collect`, `job_key`, `ReportJob`, `RateResult`, `ReportInfo` (merged JobInfo + job_reports), `ReportOptions`, `estimate_u` (คืน None จนกว่าจะมีงบความไม่แน่นอน) |
| checklist.py (140) | รายการตรวจ infusion / syringe ตามแบบ (key `กลุ่ม.รหัส` → pass/fail/na) · **เก็บเฉพาะข้อยกเว้น + รุ่น** (ไม่อยู่ = ผ่าน, รุ่น 0 = ไม่เคยบันทึก) | `ITEMS`, `compress`, `expand`, `describe`, `CHECKLIST_VERSION`, `ADDED_IN` |
| text.py (165) | ข้อความไทย/อังกฤษของเอกสาร (ไม่ผ่าน tr — ภาษาเอกสารแยกจากโปรแกรม) · วันที่ พ.ศ. | `Words` |
| charts.py (250) | SVG: `flow_chart` (เวลาจริง แกน Y ขยายเองเมื่อค่าเกิน), `gauge`/`vgauge`/`gauge_limit`, `error_chart` (log ตามช่วงจริง) | `num`, `PUMP` (สีฟ้า/ชมพู) |
| layout.py (420) | หน้า HTML 4 ชนิด (Inspection/Calibration × Infusion/Syringe) · rate > 3 = หน้าเทคนิคเพิ่ม (หน้าละ 4) · Inspection หลาย rate = หน้า 2 ซ้ำ | `Doc`, `pages`, `html_document`, `page_count` |
| style.py (270) | CSS ของแบบ (คัดลอกตรงจาก tools/report_templates/fable) + `EXTRA` (ไม่ผ่าน, ลายเซ็น, ระดับย่อ fit1–3) + ฟอนต์ Sarabun ฝัง data URI (ลองโฉม lab + IBM Plex 2026-11-18 แล้วผู้ใช้ขอกลับแบบเดิม) | `stylesheet`, `font_face` |
| render.py (230) | HTML → PDF ด้วย QtWebEngine (คิว, async, ผ่านไฟล์ชั่วคราว) → ย่อหน้าที่ล้น (`_FIT_JS`) → ตรวจล้น (`_CHECK_JS`) · บันทึกแบบแทนที่ + `FileLockedError` | `PdfRenderer`, `shared_renderer`, `render_pdf_sync`, `check_layout_sync`, `save_pdf`, `unique_path` |
| printing.py (100) | พิมพ์ PDF ใน QThread (≤ 300 dpi) · เลือกเครื่องพิมพ์ | `PrintJob`, `printer_for`, `new_printer` |
| service.py (95) | AppSettings → `ReportOptions` · Repository → ใบ (ติ๊ก rate เดียว = ทั้งงาน) · บันทึกข้อมูลใบ | `jobs_for`, `job_for_plan`, `save_info`, `language`, `default_folder` |
| demo.py (125) | ข้อมูลตัวอย่างชุดเดียวกับแบบ + ข้อมูลยาวสุด (เทสต์/เทียบภาพ) | `jobs(long=…)` |

## ui/

| ไฟล์ | หน้าที่ |
|---|---|
| main_window.py (120) | แถบนำทาง + หน้า (ทดสอบ / ประวัติ / ตั้งค่า) · `main.py` สร้างผ่าน `Application.build_window()` |
| theme.py (365) | สี (`Color`, `TONES`, `Color.INFUSION/SYRINGE`), ธีมมืด/สว่าง (`PALETTES`, `use_palette`, `resolve`, `tint`), ฟอนต์, stylesheet กลาง — อ่าน `Color.X` ตอนใช้ อย่าเก็บค่าระดับโมดูล |
| pages/test_page.py (480) ★ | หน้าทดสอบ: แผงแผน + การ์ด + กราฟ 4 ช่อง (`PLOT_GRID`) + แถบติดตาม · เปิด wizard, ถามเก็บผล · `_on_range_changed` (เต็ม/อัตโนมัติ/ซูม) |
| pages/history.py (500) | **Calibration = 1 แถวต่องาน** (▸ กางดูราย rate, `_rows`/`_build_rows`/`_job_texts`, ลบแถวงาน = ลบทุก rate) · ตารางผล แท็บตามโหมด, ค้นหา/กรอง (รวม INVALID), ลบ, ส่งออก, ปุ่มปรับหน้าต่าง · `COLUMNS` · คอลัมน์ 0 ช่องติ๊ก (ติ๊ก rate = ทั้งงาน, คงอยู่ข้ามตัวกรอง) + ปุ่มบันทึก PDF / พิมพ์ (`_make_report`) |
| pages/settings.py (420) | ฟอร์มสร้างจากตาราง `GROUPS` (`Field`) + ค้นหาตราชั่ง + ปุ่มข้อมูลสอบเทียบรอบปั๊ม |
| dialogs/test_wizard.py (1140) ★ | wizard 4 ขั้น (งาน → ตรวจเครื่อง → โหมด → ตั้งค่า) → `TestPlan` · `_on_next`, `JOB_FIELDS` · ขั้น 1: `_on_job_no_edited`, `_on_model_changed/_confirm_device` (เติมจากรุ่น), `_refresh_standard/_check_accessory_standard/_ask_accessory_change` · ขั้น 2: `_offer_warranty_claims/_show_part_history/_confirm_empty_lists` · ขั้น 4: `_check_calibration`, `_prompt_calibration`, `_refresh_windows`, `WINDOW_SOURCES` |
| dialogs/part_history.py (130) | popup ประวัติอะไหล่ + สถานะประกัน ติ๊กเคลม → `claims` |
| dialogs/accessory_change.py (45) | popup ชุดสายต่างจากมาตรฐานโรงพยาบาล: temporary / new_standard / None |
| dialogs/calibration_prompt.py (192) | popup เตือนสอบเทียบก่อนสร้างการทดสอบจับรอบปั๊ม (สอบเทียบ / ข้าม+แก้+บันทึก / จับตามเวลา) |
| dialogs/calibration_data.py (205) | ตั้งค่า → ข้อมูลสอบเทียบรอบปั๊ม: ดู/แก้/เพิ่ม/ลบ regression, n̄ ราย rate ต่อรุ่น |
| dialogs/report_preview.py (420) | ใบรายงาน: `ReportActions.output/save/print` (ไฟล์ซ้ำ → เขียนทับ/เก็บทั้งคู่, ไฟล์เปิดค้าง → ลองใหม่/ชื่ออื่น) · `ReportPreviewDialog` (QPdfView ของ PDF จริง ซูม/ภาษา/กระโดดงาน/แก้ข้อมูล) · `offer_after_test` (บันทึก PDF · พิมพ์ · ข้อมูลใบ · ข้าม) |
| dialogs/report_info.py (220) | ข้อมูลใบรายงาน: ประเภทงาน ผู้ติดต่อ รายการตรวจ การอุดตัน 3 ครั้ง ไฟฟ้า ติ๊กขั้นสุดท้าย ตุ้มน้ำหนัก → `job_reports` |
| dialogs/result_review.py (105) | ถาม "เก็บผลนี้ไหม" (ไม่เก็บ = ลบจริง) + แถบเตือน INVALID |
| dialogs/session_detail.py (263) | ดูผลย้อนหลัง: ข้อมูล + การจับรอบ + ค่าแก้ (audit) + กราฟ |
| dialogs/recalibrate.py (77), profile_deviation.py (94), prerun_criteria.py (108) | Calibration รอบปั๊มใหม่ · รอบปั๊มต่างจากเดิม · เกณฑ์ flow นิ่งเฉพาะรุ่น |
| widgets/inspection_checks.py (190) | ผลตรวจรายข้อ ผ่าน/ไม่ผ่าน/ไม่มี (wizard ขั้น 2 + ข้อมูลใบรายงาน) |
| widgets/report_extras.py (170) | ค่าที่วัดด้วยมือ: การอุดตัน 3 ครั้ง (เฉลี่ย ± 2SD สด) · ไฟฟ้า · ติ๊กขั้นสุดท้าย — wizard ขั้น 2 (→ `JobInfo.report` → report_json ตอนเก็บผลแรก) + ข้อมูลใบรายงาน |
| widgets/window_table.py (155) | ตารางหน้าต่างราย rate (แก้เป็นจุดได้) — ใช้ใน 2 dialog ข้างบน |
| widgets/plan_panel.py (300) | แผงแผนทดสอบ (+ ปุ่ม `GRAPH_RANGES` เต็ม/อัตโนมัติ/ซูม) + การ์ดตราชั่ง (น้ำหนัก 3 ตำแหน่ง, self-check) |
| widgets/checklist.py (450) | ขั้นตรวจเครื่อง: `Checklist(title, "received"|"replaced")` ช่องค้น Tab/Enter ติ๊ก, ชิป, ปุ่มประกันบนชิป, `FlowLayout` |
| widgets/process_tracker.py (305), stat_card.py (79), smart_edit.py (149), pump_type.py (204), common.py (106), log_panel.py (39) | แถบติดตาม · การ์ดตัวเลข · ช่องกรอกอัจฉริยะ · ตัวเลือก Infusion/Syringe · `label/number_box/int_box/fmt/Card` · log |
| plots/base.py (345) | `SeriesStore` (recent เต็มความละเอียด + history คัดจุด — รันหลายชั่วโมง), `PlotModule` แม่แบบกราฟ (มุมมอง `current_range_mode/view_width_s/_roll_x/_fit_y_visible`, `period_s` จากช่วงวัดล่าสุด), `RingBuffer`/`DecimatingBuffer` (หน่วยความจำคงที่) · กราฟ: weight, slope, intervals, cumulative · `cell.py` หัวกราฟ |

## template/ (แบบเอกสารรายงาน — ยังไม่ผูกกับโค้ด)

แบบร่าง 16 แบบ A–P ของใบ Calibration / Inspection / Quick Test (PNG รายหน้า + PDF + HTML + source ของ canvas) ไว้ให้ผู้ใช้เลือก
ก่อนทำตัวส่งออก PDF (`EXPORTERS`) · ดู `template/README.md` (ตาราง + ค่าที่โปรแกรมยังไม่มี) · ข้อมูลในแบบเป็นค่าสมมติทั้งหมด
· ชุดใหม่ FableA–E (ไทย/อังกฤษ, Inspection แยก Infusion/Syringe + Calibration 3 หน้า): `tools/report_templates/fable/build.py`
· เครื่องมือ `tools/report_templates/` (`pack.py` แพ็ก PNG/PDF/HTML ด้วย Edge headless, `dc2html.py`, `charts.py`) · แชทใหม่: `docs/TEMPLATE_CHAT_PROMPT.md`

## tools/ และ tests/

- `tools/build_nuitka.py` พิมพ์/รันคำสั่งสร้าง exe ด้วย Nuitka (docs/build-nuitka.md) · `tools/capture_raw.py` เก็บบรรทัดดิบ + เวลาส่ง/รับ (ไม่ใช้ Qt, `--reparse`) · `tools/check_balance.py` ตรวจการอ่านตราชั่งจริง
- tests 134 ข้อ (~90 s): `python -m unittest discover -s tests -v` · ไฟล์ตามหัวข้อ: core/engine (`test_core`), ตราชั่ง (`test_serial_timing`, `test_extensions`),
  g→ml (`test_corrections`), เรียนรู้/ปรับหน้าต่าง (`test_learning`, `test_recalibration`), เกณฑ์+ฟอร์ม (`test_criteria_smart`),
  หน้าต่างราย rate + INVALID + รันนาน (`test_windows`), UI offscreen (`test_ui_dialogs`),
  เลขงาน/ประกัน/v5/ชุดสายมาตรฐาน/wizard ขั้น 1–2/มุมมองกราฟ (`test_job_warranty`)
- `tests/fixtures/gf300_inf10_excerpt.csv` = ไบต์จริงจาก GF-300

## ฐานข้อมูล `data/deltam.db` (SCHEMA_VERSION 7 — migration อัตโนมัติ + สำรองไฟล์ `deltam.vN-backup.db`)

| ตาราง | เก็บอะไร |
|---|---|
| sessions | ผลทุกขั้น (คอลัมน์ค้นหา + `summary_json` เต็ม, `verdict`, `mode`, `folder`, v5: `job_no`, `site`, `province`, `iv_set_brand`, `iv_set_usage`) |
| intervals | ทุกช่วงวัดของทุกผล (Dashboard ในอนาคต) |
| profiles / profile_observations | ปริมาตรต่อรอบต่อรุ่น / คาบที่วัดได้รายครั้ง (+ decision, `calibrated_at`) |
| window_tuning | r, h ราย rate + `source` (tuned / manual / uncalibrated) |
| prerun_criteria | เกณฑ์ flow นิ่งเฉพาะรุ่น |
| self_checks, model_items, session_files | self-check · รายการตรวจเครื่องต่อรุ่น · SHA-256 ไฟล์ผล |
| part_replacements | อะไหล่ที่เปลี่ยนต่องาน: เครื่อง, วันที่, `claimed`, `warranty_start` (บันทึกตอนสร้างการทดสอบ) |
| site_accessory_standards | ชุดสายมาตรฐานของ โรงพยาบาล + ยี่ห้อ + รุ่น + ชนิด |
| **jobs (v7)** | **ข้อมูลงานชุดเดียวต่องาน** (`job_key` = job_id / `ref:<id>`): `job_json` = JobInfo (แก้ภายหลังที่นี่ — `list/load/job_sessions/job_history/search_devices` ใช้ค่านี้ทับสำเนาในผล, สำเนาตอนวัดอยู่ใน `job_snapshot`) · `report_json` = การอุดตัน ไฟฟ้า ติ๊กขั้นสุดท้าย ตุ้มน้ำหนัก · สร้างตอนเก็บผลแรกของงาน · แก้ข้อมูลเครื่อง → อัปเดตคอลัมน์ค้นหาของ sessions ด้วย |
| job_reports (v6) | เลิกใช้ — ย้ายเข้า jobs ตอนอัปเกรด v7 (คงไว้ ไม่ลบ) |

โฟลเดอร์ผล `data/sessions/<วันเวลา>_<ชนิด>_<rate>mlh/`: `raw.csv.gz`, `prerun.csv.gz`, `intervals.csv`, `summary.json`

## งานแบบไหน เปิดไฟล์ไหน

| งาน | เปิด |
|---|---|
| สูตร/อัลกอริทึม | `docs/calculation-methods.md` หัวข้อที่เกี่ยว → `core/` ไฟล์นั้น (+ อัปเดตเอกสาร) |
| ค่าที่ใช้คำนวณ 1 ขั้น | `SessionController._prepare_settings` / `_prepare_windows` |
| หน้าจอใหม่ / หน้า Dashboard | `ui/pages/` + `ui/main_window.py` (`_add_page`) + อ่านข้อมูลผ่าน `Repository` |
| ฟอร์มสร้างการทดสอบ | `ui/dialogs/test_wizard.py` (ใหญ่ — grep ชื่อเมธอดก่อน) · รายการตรวจเครื่อง `ui/widgets/checklist.py` |
| ประกันอะไหล่ | `core/warranty.py` + `Repository.part_history/record_parts` + `ui/dialogs/part_history.py` |
| สร้าง exe / ดึง Google Sheet (อนาคต) | `docs/build-nuitka.md` / `docs/google-sheet-sync.md` |
| ค่าตั้งใหม่ | `config/settings.py` + 1 บรรทัดใน `GROUPS` ของ `ui/pages/settings.py` |
| ตาราง/คอลัมน์ฐานข้อมูล | `_SCHEMA` + `_migrate*` + `SCHEMA_VERSION` ใน `services/session_store.py` |
| ส่งออก/รายงาน | `services/exporters.py` (`@EXPORTERS.register`) · ใบรายงาน PDF: `services/report/` (ดูตารางย่อย) + `ui/dialogs/report_preview.py` |
| ตราชั่งรุ่นใหม่ | `hardware/` (`@SOURCES.register`) / `parsers.py` (`LINE_FORMATS`) |
| ตารางต่อยอดเต็ม (Lego) | README.md หัวข้อ "วิธีต่อยอด" |
