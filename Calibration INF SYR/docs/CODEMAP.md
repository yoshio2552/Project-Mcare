# DeltaM — แผนที่โค้ด (อ่านแทนการเปิดโค้ดทั้งหมด)

อัปเดต 2026-11-20 (รอบ 6.21: ความปลอดภัยบีกเกอร์ หน้าผล/เล่นซ้ำ Google Sheet — ต่อจาก 6.20 เติมข้อมูลทันที/การระเหย) · ~19,000 บรรทัด Python (รวม tests) · ใช้ไฟล์นี้หาว่า "ต้องเปิดไฟล์ไหน" แล้วเปิดเฉพาะไฟล์นั้น
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
| settings.py (400) | ค่าตั้งทั้งหมดเป็น dataclass → `data/settings.json` (list ของ dict ได้ — ผู้ลงนาม/ช่องลายเซ็น) · `jobs` (คำนำหน้าเลขงาน) · `evaporation` (ภาชนะ วิธี trap) · `balance.cal_date/due_date` · `report.default_occl_inf_*/syr_*`, `default_battery_min`, `upgrade()` (ค่าเก่า → แยกชนิด), `language` th/en/mix · `report.*` ปรับแต่งใบ: footer_*, cal_pages, cal_u_column, *_show_u, *_show_flow_2sd, cal_show_occl_2sd, supply_ref, people, sign_* | `AppSettings` (serial, simulator, replay, engine, prerun, selfcheck, catalog, balance, warranty, ui — `ui.graph_range/graph_auto_cycles/graph_zoom_s`) · `EngineSettings` (ค่าคำนวณต่อการทดสอบ — คัดลอกตอนเริ่ม) · `PrerunCriteria`/`prerun_group()` |
| i18n.py (41) | `tr("English", **ค่า)` → แปลจากตาราง · `missing()` = ข้อความที่ยังไม่แปล | `tr`, `set_language`, `missing` |
| provinces.py (15) | 77 จังหวัด สำหรับช่องจังหวัด | `PROVINCES` |
| lang_th.py (1040) | ตารางคำแปลไทย `TRANSLATIONS` (เพิ่มคำใหม่ท้ายไฟล์ ไม่ต้องอ่านทั้งไฟล์ — ใช้ grep) | |

## core/ (ไม่มี Qt)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| models.py (370) ★ | dataclass กลางทุกชั้น | `JobInfo` (+ job_no, site, province, accessory_brand, accessory_usage, parts_warranty, `evaporation_trap`), `JOB_PREFIXES`, `split_job_no`/`join_job_no`/`pump_from_prefix` (คำนำหน้าแยกช่อง), `format_duration` ("10 min 54.28 s"), `StepConfig`, `TestPlan` → `session_config(i)` → `SessionConfig`, `EngineResult`, `Interval`, `IntervalStats`, `SessionSummary`, enum `PumpType/RunMode/EndMode/StartMode/Stage/SessionState/Verdict(PASS/FAIL/N/A/INVALID)` |
| engine.py (347) ★ | `FlowEngine`: pre-run → warm-up → slope → strategy → สถิติ → `summary()` | `process()`, `_apply_tuning()` (ตั้งหน้าต่างจากคาบหลัง pre-run), `capture_check()`, `verdict()`, `_SlopeWindow`, `_Span` |
| stats.py (122) | สถิติล้วน | `regression_slope`, `RunningStats` (Welford), `t_score`, `percent_error`, `flow_ml_per_h` |
| corrections.py (260) | g→ml (ISO 4787 Z: ρw Tanaka, ρa OIML) + self-check (การระเหย) + เลือกค่าการระเหย (`evaporation=`) | `gravimetric_correction()` → `GravimetricCorrection` (`evaporation_*`), `analyse_baseline()`, `BaselineEngine` |
| **evaporation.py (190)** | การระเหยระหว่างวัด (calc 18): แพร่ในภาชนะ + พาแบบธรรมชาติ Sh(Ra), psv CIPM-2007 · ระดับน้ำสูงขึ้นตามปริมาตร · trap = ไม่แก้ | `estimate()`, `decide()` → `EvaporationDecision`, `headspace_mm`, `sherwood` |
| cycle_analyzer.py (115) | ตัวจับแบบหน้าต่าง `2·n̄+1` (รอยืนยัน + เกณฑ์แอมพลิจูด) — ตอนนี้ใช้หาคาบหยาบตอนไม่รู้คาบ · `Extremum/Cycle/CycleEvent` ใช้ร่วม | `CycleAnalyzer.update()`, `MIN_SWING_FRACTION` |
| **phase_lock.py (330)** | **ตัวจับรอบที่ใช้จริง (2026-11-19)**: ล็อกคาบ + ปรับคาบด้วยสหสัมพันธ์ของ slope + คะแนนยอดตามระยะจาก 1 คาบ + ตรวจยอดสลับ (ไม่รู้คาบ) — ทนปั๊มหลายชั้นทุก rate | `PhaseLockedAnalyzer(n_bar, period_s, trusted)`, `_refine`, `_blind_scan`, `_pick_next`, `_verify_alternation`, `_lag_correlation` |
| prerun.py (260) | ช่วงก่อนวัด: หาคาบ (autocorrelation, เกณฑ์การแกว่ง `AMPLITUDE_RESOLUTIONS` = 1.5) + ตรวจ flow นิ่ง | `PeriodEstimator`, `flow_stability()`, `block_length()`, `PreRun` |
| windows.py (100) | **สูตรเดียว** คาบ × สัดส่วน → จำนวนจุด, ขั้นต่ำ 5/3, ระดับจุดต่อรอบ, ช่วงที่ใช้ได้ | `cycle_windows()` → `CycleWindows(level ok/low/too_low)`, `fraction_problems()`, `fractions_from_points()`, `time_window_for()` |
| **uncertainty.py (190)** | งบความไม่แน่นอน GUM ของ Q (ตราชั่ง เวลา อุณหภูมิ/อากาศ→Z การระเหย ความซ้ำ 2SD จากตาราง อื่นๆ) + Welch–Satterthwaite · ค่าตั้ง `config.settings.UncertaintySettings` | `budget(summary, settings, repeat)`, `k_factor`, `warn_beyond_tolerance` |
| repeatability.py (70) | ความซ้ำ 2SD: กรอกเอง (% / ml/h) หรือจากผลวัดซ้ำ · ค่าที่ใช้ = ค่าเฉลี่ยของชุด | `Study`, `from_input`, `from_runs`, `combined` |
| capture_check.py (130) | ตรวจผลจับรอบหลังจบ → INVALID (รอบไม่ตรงคาบ/ไม่พอ/**รอบเดี่ยวผิด `irregular`**) · `consistent` = ไม่มีคาบอ้างอิงแต่สม่ำเสมอ + ตรวจย้อนผลเก่า | `check_cycle_capture(..., durations)`, `check_summary()`, `effective_verdict()`, `CYCLE_RANGE` |
| **beaker.py (130)** | ความปลอดภัยบีกเกอร์ (calc 20): น้ำ = (w − บีกเกอร์เปล่า)/0.998, ระดับ ok/warn/alarm, คาดการณ์ก่อนเริ่ม rate, เวลาก่อนเต็ม, ปั๊มยังเดินไหม | `Beaker`, `level`, `predict`, `minutes_to`, `PumpRunningDetector` |
| warranty.py (125) | ประกันอะไหล่: สถานะ active/late/expired, วันเริ่มประกัน (เคลมไม่นับใหม่), สรุปต่อชนิดอะไหล่ | `status()`, `start_for()`, `summarize()`, `PartRecord`, `PartWarranty` |
| profiles.py (76) | กุญแจ ยี่ห้อ+รุ่น+ชนิด+ชุดสาย, โปรไฟล์ปริมาตรต่อรอบ | `pump_key()`, `PumpProfile` |
| tuning.py (200) | ปรับ (r, h) ราย rate โดยเล่น raw ที่เก็บไว้ผ่าน `FlowEngine` แล้วให้คะแนน | `tune()`, `evaluate()`, `TuningResult.recommended()`, `reference_period()` |
| registry.py (47) | Registry "ตัวต่อ Lego" | `Registry.register/create/get/choices` |
| strategies/ | วิธีแบ่งช่วงวัด ลงทะเบียน `STRATEGIES` · `origin_t` = เวลา 0 (peak แรก/จุดเริ่ม) | `pump_cycle.py` (110, ใช้ `PhaseLockedAnalyzer`, `set_period(period, trusted)`, สายผูกกับชนิดจุด, `Interval.t` นับจาก peak แรกของสาย A) · `time_based.py` (53, `time_interval`, `time_total`) · `base.py` (`FlowStrategy`) |

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
| job_suggestions.py (170) | คำแนะนำของช่องกรอก (ตัวจาง/รายการ) + เติมจากรุ่น · "-" = ไม่มีข้อมูล | `JobSuggester.suggest`, `infer_device(model)`, `infer_accessory_brand`, `latest`, `known_device` |
| **autofill.py (110)** | เติมข้อมูลงานทันที (2026-11-20): โรงพยาบาล→จังหวัด, รุ่น→ยี่ห้อ+ชนิด, ชุดสาย→ยี่ห้อ, S/N/รหัส→เครื่อง (ตาราง `autofill_memory` + ประวัติผล) | `Autofill.province/model_info/accessory_brand/site_accessory/device/remember` |
| **report/** | **ใบรายงาน PDF / พิมพ์ / ดูตัวอย่าง ตามแบบ Main Fable-1** (ไม่มี Qt ยกเว้น render/printing) | ดูตารางย่อยด้านล่าง |
| logging_setup.py (50) | log → ไฟล์ `data/logs` + แผง log บนจอ | `setup_logging`, `LogBridge` |
| audit.py (190) | ตรวจย้อนผลจาก raw.csv ทุกตัวเลข (ไม่มี Qt) — ปุ่มในหน้ารายละเอียด | `audit_folder(folder, summary) -> Audit` |
| sounds.py (230) | เสียงจาก `ui/assets/sounds/*.wav` · คลิกเล่นตอน "กด" ผ่าน QAudioSink ที่เปิดค้าง (`_FastOutput`, ปิดได้ `ui.sound_low_latency`) อย่างอื่น QSoundEffect · โหลดล่วงหน้า · สัญญาณเตือน remind/warn/alarm ดัง ≥ 70 % · เงียบเมื่อ offscreen | `play(name)`, `install_click_sounds(app, settings)`, `NAMES`, `ALARMS` |
| **beaker_guard.py (330)** | ระบบความปลอดภัยบีกเกอร์: รับน้ำหนัก (live_reading/results_ready) → เตือนใกล้เต็ม/จะล้น/rate ถัดไปจะล้น/หยุดปั๊ม/ยกบีกเกอร์ออก + จังหวะเสียง | `BeakerGuard` (`setup_requested`, `alert_changed`, `status_changed`, `set_beaker`, `start_check`, `acknowledge`), `Alert`, `BeakerStatus` |
| **replay_session.py (230)** | เล่นซ้ำผลจากไฟล์ของผล (raw + intervals + summary) → รายการ `EngineResult` เรียงเวลา ป้อนกราฟเดิมได้ (calc 21) | `build(detail) -> ReplayData`, `frame_values`, `rolling_slope`, `read_intervals` |
| **replay_export.py (230)** | HTML เล่นซ้ำไฟล์เดียว (canvas เอง เล่น/หยุด/ความเร็ว/เลื่อน ธีมตามเครื่อง) | `build_html(data, meta, labels)`, `payload` |
| **sheets.py (420)** | Google Sheet: แหล่ง CSV (อ่าน) / Apps Script (อ่าน+เขียน) · จับคู่คอลัมน์ (`guess_columns`) · สำเนา `data/sheets_cache.json` · ค้นแถวด้วยเลขงาน/S/N/ครุภัณฑ์ · โค้ด `APPS_SCRIPT` | `SheetSource`, `fetch`, `write_row`, `SheetStore` (`rows_for`, `lookup`, `update_cached`), `store()/set_store()`, `sync_all`, `sync_in_background` |

### services/report/ (ใบรายงาน — แบบ `template/Main Fable-1`)

| ไฟล์ | หน้าที่ | สัญลักษณ์หลัก |
|---|---|---|
| **signatures.py (200)** | ผู้ลงนาม (`Person`: ชื่อไทย/อังกฤษ/ชื่ออื่น + ภาพ) + ช่องลายเซ็น (`SignSlot`: บทบาท ตำแหน่ง who = operator/person:id/blank) · ค่าเริ่มต้น · `resolve` (จับคู่ผู้ทดสอบต้องตรงทั้งชื่อ) · `migrate` ค่าเก่า reviewer/approver/signers · `image_file` (สัมพัทธ์ = ใต้ data/) | `DEFAULT_SLOTS`, `people_from`, `slots_from`, `resolve`, `migrate` |
| model.py (420) | รวม session หลาย rate ของงานเดียว (job_id) เป็นใบ · เลือกผลล่าสุดที่ completed + ไม่ INVALID ราย rate + คำเตือน · n = รอบสาย A · ±1 SD ของเวลา/ปริมาตรต่อช่วง · ผลรวมของใบ · ข้อมูลที่ยังไม่กรอก | `group_jobs`, `collect`, `job_key`, `ReportJob`, `RateResult`, `ReportInfo` (merged JobInfo + job_reports), `ReportOptions`, `estimate_u` (คืน None จนกว่าจะมีงบความไม่แน่นอน) |
| checklist.py (140) | รายการตรวจ infusion / syringe ตามแบบ (key `กลุ่ม.รหัส` → pass/fail/na) · **เก็บเฉพาะข้อยกเว้น + รุ่น** (ไม่อยู่ = ผ่าน, รุ่น 0 = ไม่เคยบันทึก) | `ITEMS`, `compress`, `expand`, `describe`, `CHECKLIST_VERSION`, `ADDED_IN` |
| text.py (230) | ข้อความไทย/อังกฤษของเอกสาร (ไม่ผ่าน tr — ภาษาเอกสารแยกจากโปรแกรม) · วันที่ พ.ศ. · โหมด `mix` = ไทย + ศัพท์เทคนิคอังกฤษ (`TERMS`) | `Words` (`term`, `pick`, `term_lang`, `code`) |
| charts.py (250) | SVG: `flow_chart` (เวลาจริง แกน Y ขยายเองเมื่อค่าเกิน), `gauge`/`vgauge`/`gauge_limit`, `error_chart` (log ตามช่วงจริง) | `num`, `PUMP` (สีฟ้า/ชมพู) |
| layout.py (690) | หน้า HTML 4 ชนิด (Inspection/Calibration × Infusion/Syringe) · rate > 3 = หน้าเทคนิคเพิ่ม (หน้าละ 4) · Inspection หลาย rate = หน้า 2 ซ้ำ · ค่าตั้งของใบ: `u_of` (± U แยกใบ), `flow_2sd`, `u_cell` (U ml/h/%), `signs(slots)`, `cal_parts` (ชุดหน้า) | `Doc`, `pages`, `html_document`, `page_count`, `cal_parts` |
| (services) history_search.py (230) | ค้นเร็วช่องเดียว (`quick_match`: คำทั่วไป + inf/syr + ผ่าน/ไม่ผ่าน + วันที่ พ.ศ. + `ช่อง:ค่า`) · `AdvancedFilter` · `record`, `distinct`, `years` — ไม่มี Qt |
| style.py (420) | CSS: โครงแบบ Main Fable-1 (`TEMPLATE_CSS`) + `ATH` = ลายเส้น/สี/น้ำหนักตัวอักษรตามใบตัวอย่างของผู้ใช้ (2026-11-19 แบบ A-TH: เลขหัวข้อ 01 สีตามชนิดเครื่อง ป้ายอังกฤษตัวพิมพ์ใหญ่ ตัวเลข mono) + `EXTRA` (ไม่ผ่าน, ระดับย่อ fit1–3) · ฟอนต์ IBM Plex Sans Thai + Mono ฝัง data URI | `stylesheet`, `font_face`, `FONT_FILES` |
| render.py (230) | HTML → PDF ด้วย QtWebEngine (คิว, async, ผ่านไฟล์ชั่วคราว) → ย่อหน้าที่ล้น (`_FIT_JS`) → ตรวจล้น (`_CHECK_JS`) · บันทึกแบบแทนที่ + `FileLockedError` | `PdfRenderer`, `shared_renderer`, `render_pdf_sync`, `check_layout_sync`, `save_pdf`, `unique_path` |
| printing.py (100) | พิมพ์ PDF ใน QThread (≤ 300 dpi) · เลือกเครื่องพิมพ์ | `PrintJob`, `printer_for`, `new_printer` |
| service.py (125) | AppSettings → `ReportOptions` (+ ย้ายค่าลายเซ็นเก่า, ภาพเป็น path เต็ม) · Repository → ใบ (ติ๊ก rate เดียว = ทั้งงาน) · บันทึกข้อมูลใบ | `jobs_for`, `job_for_plan`, `save_info`, `language`, `default_folder` |
| demo.py (125) | ข้อมูลตัวอย่างชุดเดียวกับแบบ + ข้อมูลยาวสุด (เทสต์/เทียบภาพ) | `jobs(long=…)` |

## ui/

| ไฟล์ | หน้าที่ |
|---|---|
| main_window.py (190) | แถบนำทาง (ตั้งค่าอยู่ล่างสุด) + หน้า (ทดสอบ / ประวัติ / ตั้งค่า) · `BeakerGuard` + `AlertOverlay` + `open_beaker_setup` · ดึง Google Sheet ตอนเปิด · `main.py` สร้างผ่าน `Application.build_window()` |
| window_chrome.py (100) | ไอคอน `ui/assets/deltam.svg` ทุกหน้าต่าง + AppUserModelID (แถบงาน) + หัวหน้าต่างสีเข้มตามธีม (DWM) · `install(app, settings)` ใน main.py |
| theme.py (365) | สี (`Color`, `TONES`, `Color.INFUSION/SYRINGE`), ธีมมืด/สว่าง (`PALETTES`, `use_palette`, `resolve`, `tint`), ฟอนต์, stylesheet กลาง — อ่าน `Color.X` ตอนใช้ อย่าเก็บค่าระดับโมดูล |
| pages/test_page.py (480) ★ | หน้าทดสอบ: แผงแผน + การ์ด + กราฟ 4 ช่อง (`PLOT_GRID`) + แถบติดตาม · เปิด wizard, ถามเก็บผล · `_on_range_changed` (เต็ม/อัตโนมัติ/ซูม) |
| pages/history.py (700) | คอลัมน์ใหม่ (เลขงาน โรงพยาบาล ชุดสาย อะไหล่/ประกัน หมายเหตุ — ต่อท้าย `COLUMNS`, ลำดับบนจอ `VISUAL_ORDER`, แสดงตาม `DEFAULT_VISIBLE`/`ui.history_columns`, ปุ่มคอลัมน์) · แผงขวา `HistoryInspector` · ดับเบิลคลิก = `ResultWorkspace` (`_open_detail(row, force=True)`) · ข้อมูล Sheet ค้นได้ (`_attach_sheet_text`) · แก้ใน Sheet (`_edit_sheet_row`) · **Calibration = 1 แถวต่องาน** (▸ กางดูราย rate, `_rows`/`_build_rows`/`_job_texts`, ลบแถวงาน = ลบทุก rate) · ตารางผล แท็บตามโหมด, ค้นหา/กรอง (รวม INVALID), ลบ, ส่งออก, ปุ่มปรับหน้าต่าง · `COLUMNS` · คอลัมน์ 0 ช่องติ๊ก (ติ๊ก rate = ทั้งงาน, คงอยู่ข้ามตัวกรอง) + ปุ่มบันทึก PDF / พิมพ์ (`_make_report`) |
| pages/settings.py (640) | **แท็บด้านบน** `TABS` (+ แท็บย่อยใบรายงาน `REPORT_TABS`) จัดการ์ดจากตาราง `GROUPS` (`Field`: เปิด/ปิด = ช่องติ๊ก · kind folder/image/file = `PathEdit` · note) + หน้าย่อยลายเซ็น + ค้นหาตราชั่ง + ปุ่มข้อมูลสอบเทียบรอบปั๊ม/ความซ้ำ |
| dialogs/test_wizard.py (1500) ★ | wizard **6 ขั้น** · ขั้น 1 เติมทันที `_autofill_from/_fill/_unfill/_show_autofill`, คำนำหน้าเลขงาน `_job_prefix/_on_prefix_edited`, `_check_site_province/_ask_province_change`, `_remember_autofill`, `_balance_text` (วันครบกำหนด) · ขั้น 5 evaporation trap `_trap_yes`, `_apply_value_defaults` (อุดตันตามชนิด) · (งาน → ตรวจเครื่อง → โหมด → **ผลตรวจ + ประเภทงาน** (`_service_boxes`, `_apply_auto_service`) → **ค่าที่วัด** `PAGE_VALUES` (การอุดตันเฉพาะ Calibration) → ตั้งค่า) → `TestPlan` · `PAGE_*`, `STEP_COUNT` · `_on_next`, `JOB_FIELDS` · ขั้น 1: `_on_job_no_edited`, `_on_model_changed/_confirm_device` (เติมจากรุ่น), `_refresh_standard/_check_accessory_standard/_ask_accessory_change` · ขั้น 2: `_offer_warranty_claims/_show_part_history/_confirm_empty_lists` · ขั้น 4: `_check_calibration`, `_prompt_calibration`, `_refresh_windows`, `WINDOW_SOURCES` |
| dialogs/part_history.py (130) | popup ประวัติอะไหล่ + สถานะประกัน ติ๊กเคลม → `claims` |
| dialogs/accessory_change.py (45) | popup ชุดสายต่างจากมาตรฐานโรงพยาบาล: temporary / new_standard / None |
| dialogs/calibration_prompt.py (192) | popup เตือนสอบเทียบก่อนสร้างการทดสอบจับรอบปั๊ม (สอบเทียบ / ข้าม+แก้+บันทึก / จับตามเวลา) |
| dialogs/repeatability.py (330) | ตั้งค่า → ความไม่แน่นอน → ความซ้ำ (2SD): ตารางรุ่น/ชนิด/ชุดสาย/rate (มีค่า/ยังไม่มี) · ชุดของรายการ · กรอกเอง · สอบเทียบ N ครั้ง (ส่งแผนไปหน้าทดสอบ) · ลบชุด | `RepeatabilityDialog`, `EntryDialog`, `StudyDialog` |
| dialogs/calibration_data.py (205) | ตั้งค่า → ข้อมูลสอบเทียบรอบปั๊ม: ดู/แก้/เพิ่ม/ลบ regression, n̄ ราย rate ต่อรุ่น |
| dialogs/report_preview.py (420) | ใบรายงาน: `ReportActions.output/save/print` (ไฟล์ซ้ำ → เขียนทับ/เก็บทั้งคู่, ไฟล์เปิดค้าง → ลองใหม่/ชื่ออื่น) · `ReportPreviewDialog` (QPdfView ของ PDF จริง ซูม/ภาษา/กระโดดงาน/แก้ข้อมูล) · `offer_after_test` (บันทึก PDF · พิมพ์ · ข้อมูลใบ · ข้าม) |
| dialogs/report_info.py (230) | **แท็บ** งานและเครื่อง (+หมายเหตุ) / บริการและผู้ติดต่อ / ผลตรวจรายข้อ / ค่าที่วัด · ติ๊ก "แสดงช่องขั้นสูง" (ยี่ห้อชุดสาย ตราชั่ง อุปกรณ์) · ข้อมูลใบรายงาน: ประเภทงาน (ติ๊กแก้ได้ → `service_kinds`) ผู้ติดต่อ รายการตรวจ การอุดตัน 3 ครั้ง ไฟฟ้า ติ๊กขั้นสุดท้าย ตุ้มน้ำหนัก → `job_reports` |
| dialogs/result_review.py (105) | ถาม "เก็บผลนี้ไหม" (ไม่เก็บ = ลบจริง) + แถบเตือน INVALID |
| **dialogs/result_workspace.py (700)** | หน้าผลย้อนหลัง (ดับเบิลคลิกในประวัติ): หัว + สลับ rate + แท็บ ภาพรวม / กราฟ·เล่นซ้ำ (`ReplayView`) / เอกสาร (PDF ซูม 67 %) / งานและเครื่อง (ประกัน ณ วันนี้, Google Sheet) / ข้อมูลการวัด / คุณภาพและสอบย้อน · ส่งออก `export_html` / `export_video` | `ResultWorkspace`, `TABS` |
| dialogs/session_detail.py (125) | ข้อความสอบย้อน `correction_rows`, `uncertainty_rows`, `integrity_text`, `USAGE_TEXT` + ทางเข้าเดิม `SessionDetailDialog(parent, detail)` → `ResultWorkspace` |
| dialogs/beaker_setup.py (300) | หน้าต่างตั้งบีกเกอร์ 2 ขั้น (RE-ZERO รอ 0 g นิ่ง → วางบีกเกอร์ ความจุ/บีกเกอร์เปล่า) น้ำหนักสดจาก `live_reading` · ไม่บล็อก |
| dialogs/sheet_row.py (210) | แก้/เพิ่มข้อมูลของงานใน Google Sheet (Apps Script) + คอลัมน์ใหม่ + เติมจาก DeltaM |
| dialogs/recalibrate.py (77), profile_deviation.py (94), prerun_criteria.py (108) | Calibration รอบปั๊มใหม่ · รอบปั๊มต่างจากเดิม · เกณฑ์ flow นิ่งเฉพาะรุ่น |
| widgets/inspection_checks.py (190) | ผลตรวจรายข้อ ผ่าน/ไม่ผ่าน/ไม่มี (wizard ขั้น 2 + ข้อมูลใบรายงาน) |
| widgets/history_filters.py (300) | แผงคัดกรองขั้นสูงของหน้าประวัติ (สถานที่ ชนิด ยี่ห้อ รุ่น ชุดสาย ผู้ทดสอบ ปี พ.ศ. ช่วงวันที่ — `BuddhistDateEdit` แสดง/รับ พ.ศ.) + ป้ายตัวกรอง (`FilterChips`) |
| **widgets/signature_settings.py (390)** | ตั้งค่า → ใบรายงาน → ลายเซ็น: รายชื่อผู้ลงนาม + `PersonDialog` (เลือก PNG, `prepare_signature` พื้นขาว→ใส ตัดขอบ ย่อ, คัดลอกเข้า `signature_dir()`) + ช่องลายเซ็น 2 ใบ (`_SlotRows`) · `load/store(report)` |
| widgets/replay_view.py (300) | เล่นซ้ำ: กราฟ 4 ช่อง + การ์ด 6 ใบ + แถบควบคุม (เล่น ความเร็ว เลื่อน มุมมอง) · `seek`, `advance_to`, `export_video` (MP4 ด้วย QMediaRecorder + QVideoFrameInput) |
| widgets/history_inspector.py (190) | แผงรายละเอียดขวาของหน้าประวัติ (ผล ราย rate งาน เครื่อง ชุดสาย อะไหล่/ประกัน หมายเหตุ Sheet + ปุ่ม) |
| widgets/alert_overlay.py (190) · beaker_meter.py (90) | popup เตือนใหญ่แบบทันสมัย (ขอบสีตามความรุนแรง แดงกะพริบ) · ภาพบีกเกอร์ระดับน้ำ (การ์ดตราชั่ง/popup/หน้าต่างตั้ง) |
| widgets/sheet_settings.py (330) | ตั้งค่า → Google Sheet: ตารางแหล่ง + `SourceDialog` (ชนิด ลิงก์ แท็บ token คอลัมน์กุญแจ จับคู่คอลัมน์ ทดสอบ คัดลอกโค้ด Apps Script) |
| widgets/path_edit.py (65) | ช่อง path + ปุ่ม "เลือก…" (โฟลเดอร์/รูป/ไฟล์) ใช้ในหน้าตั้งค่า |
| widgets/date_field.py (55) | ช่องวันที่ของหน้าตั้งค่า (ปฏิทิน · พ.ศ. บนจอไทย · ว่างได้ → ISO) — `Field(kind="date")` |
| widgets/report_extras.py (220) | `defaults_from(report, pump)` (อุดตันแยกชนิด) · `apply_defaults` · `OCCL_UNITS` (+ kgf/cm²) · แบตเตอรี่ = นาทีอย่างเดียว · `set_occlusion_visible` · ค่า 0 = ยังไม่วัด · ช่องตัวเลขไม่รับล้อจนคลิก (`_Spin`) · ค่าที่วัดด้วยมือ: การอุดตัน 3 ครั้ง (เฉลี่ย ± 2SD สด) · ไฟฟ้า · ติ๊กขั้นสุดท้าย — wizard ขั้น 2 (→ `JobInfo.report` → report_json ตอนเก็บผลแรก) + ข้อมูลใบรายงาน |
| widgets/window_table.py (155) | ตารางหน้าต่างราย rate (แก้เป็นจุดได้) — ใช้ใน 2 dialog ข้างบน |
| widgets/plan_panel.py (300) | แผงแผนทดสอบ (+ ปุ่ม `GRAPH_RANGES` เต็ม/อัตโนมัติ/ซูม) + การ์ดตราชั่ง (น้ำหนัก 3 ตำแหน่ง, self-check) |
| widgets/checklist.py (450) | ขั้นตรวจเครื่อง: `Checklist(title, "received"|"replaced")` ช่องค้น Tab/Enter ติ๊ก, ชิป, ปุ่มประกันบนชิป, `FlowLayout` |
| widgets/process_tracker.py (305), stat_card.py (115 — ค่ารองย้ายลงล่างเมื่อแคบ), smart_edit.py (180, Tab รับคำแนะนำแม้รายการเปิด — ดักที่ popup ด้วย), pump_type.py (204), common.py (175, `WrapLabel` ป้ายหลายบรรทัดที่สูงพอเสมอ · `ElidedLabel` บรรทัดเดียวตัดท้าย … + tooltip), log_panel.py (39) | แถบติดตาม · การ์ดตัวเลข · ช่องกรอกอัจฉริยะ · ตัวเลือก Infusion/Syringe · `label/number_box/int_box/fmt/Card` · log |
| plots/base.py (345) | `SeriesStore` (recent เต็มความละเอียด + history คัดจุด — รันหลายชั่วโมง), `PlotModule` แม่แบบกราฟ (มุมมอง `current_range_mode/view_width_s/_roll_x/_fit_y_visible`, `period_s` จากช่วงวัดล่าสุด, `follows_origin`/`move_origin` เลื่อนแกนให้เวลา 0 = peak แรก — weight, slope), `RingBuffer`/`DecimatingBuffer` (หน่วยความจำคงที่) · กราฟ: weight, slope, intervals, cumulative · `cell.py` หัวกราฟ |

## template/ (แบบเอกสารรายงาน — ยังไม่ผูกกับโค้ด)

แบบร่าง 16 แบบ A–P ของใบ Calibration / Inspection / Quick Test (PNG รายหน้า + PDF + HTML + source ของ canvas) ไว้ให้ผู้ใช้เลือก
ก่อนทำตัวส่งออก PDF (`EXPORTERS`) · ดู `template/README.md` (ตาราง + ค่าที่โปรแกรมยังไม่มี) · ข้อมูลในแบบเป็นค่าสมมติทั้งหมด
· ชุดใหม่ FableA–E (ไทย/อังกฤษ, Inspection แยก Infusion/Syringe + Calibration 3 หน้า): `tools/report_templates/fable/build.py`
· เครื่องมือ `tools/report_templates/` (`pack.py` แพ็ก PNG/PDF/HTML ด้วย Edge headless, `dc2html.py`, `charts.py`) · แชทใหม่: `docs/TEMPLATE_CHAT_PROMPT.md`

## tools/ และ tests/

- `tools/make_sounds.py` สังเคราะห์ `ui/assets/sounds/*.wav` · `tools/make_icon.py` svg → `deltam.ico/.png`
- `tools/build_nuitka.py` พิมพ์/รันคำสั่งสร้าง exe ด้วย Nuitka (docs/build-nuitka.md) · `tools/capture_raw.py` เก็บบรรทัดดิบ + เวลาส่ง/รับ (ไม่ใช้ Qt, `--reparse`) · `tools/check_balance.py` ตรวจการอ่านตราชั่งจริง
- tests 274 ข้อ (~125 s) · บีกเกอร์/เล่นซ้ำ/HTML/Sheet/หน้าผล/คอลัมน์ประวัติ/ข้อมูลใบแท็บ (`test_safety_replay_sheets`) · เติมทันที/การระเหย/ไทยกึ่งอังกฤษ/เลขงาน (`test_autofill_evaporation`) · ปรับแต่งใบ/ลายเซ็น/หน้าตั้งค่าแท็บ (`test_report_options`) · ตัวจับล็อกคาบ (`test_phase_lock` เมทริกซ์จำลองหลายชั้น) · เสียง (`test_sounds`): `python -m unittest discover -s tests -v` · ไฟล์ตามหัวข้อ: core/engine (`test_core`), ตราชั่ง (`test_serial_timing`, `test_extensions`),
  g→ml (`test_corrections`), เรียนรู้/ปรับหน้าต่าง (`test_learning`, `test_recalibration`), เกณฑ์+ฟอร์ม (`test_criteria_smart`),
  หน้าต่างราย rate + INVALID + รันนาน (`test_windows`), UI offscreen (`test_ui_dialogs`),
  เลขงาน/ประกัน/v5/ชุดสายมาตรฐาน/wizard ขั้น 1–2/มุมมองกราฟ (`test_job_warranty`)
- `tests/fixtures/gf300_inf10_excerpt.csv` = ไบต์จริงจาก GF-300

## ฐานข้อมูล `data/deltam.db` (SCHEMA_VERSION 9 — migration อัตโนมัติ + สำรองไฟล์ `deltam.vN-backup.db`)

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
| **repeat_studies (v8)** | ความซ้ำ 2SD: 1 แถว = 1 ชุด (กรอกเอง/สอบเทียบ) · กุญแจ pump_key + rate · ผลแต่ละครั้ง (runs_json มีเลขผล) · ลบ = `deleted_at` (สอบย้อน) · `Repository.add_repeat_study/repeat_studies/repeat_value/repeat_overview/delete_repeat_study` |
| **autofill_memory (v9)** | ความจำเติมข้อมูลทันที: kind (site/model/accessory/device) + key → ค่าล่าสุด (`data_json`, `uses`) · `Repository.memory/remember` |
| (ไฟล์) data/sheets_cache.json | สำเนาข้อมูล Google Sheet ที่ดึงล่าสุด ต่อแหล่ง (หัวคอลัมน์ แถว สถานะ) — ไม่ใช่ตาราง DB |
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
| สร้าง exe | `docs/build-nuitka.md` |
| Google Sheet | `services/sheets.py` + `ui/widgets/sheet_settings.py` + `ui/dialogs/sheet_row.py` · wizard `_sheet_fill` · `docs/google-sheet-sync.md` |
| ความปลอดภัยบีกเกอร์ | `core/beaker.py` (สูตร) → `services/beaker_guard.py` (ตัดสิน/เสียง) → `ui/widgets/alert_overlay.py`, `ui/dialogs/beaker_setup.py` · ค่าตั้ง `settings.safety` |
| หน้าผลย้อนหลัง / เล่นซ้ำ | `ui/dialogs/result_workspace.py` + `ui/widgets/replay_view.py` + `services/replay_session.py` / `replay_export.py` |
| ค่าตั้งใหม่ | `config/settings.py` + 1 บรรทัดใน `GROUPS` ของ `ui/pages/settings.py` |
| ค่าตั้งของใบรายงานใหม่ | `config/settings.py` ReportSettings → `services/report/service.options_from_settings` → `ReportOptions` → `layout.Doc` + 1 บรรทัดใน `GROUPS` (+ ใส่กลุ่มใน `REPORT_TABS`) |
| ตาราง/คอลัมน์ฐานข้อมูล | `_SCHEMA` + `_migrate*` + `SCHEMA_VERSION` ใน `services/session_store.py` |
| ส่งออก/รายงาน | `services/exporters.py` (`@EXPORTERS.register`) · ใบรายงาน PDF: `services/report/` (ดูตารางย่อย) + `ui/dialogs/report_preview.py` |
| ตราชั่งรุ่นใหม่ | `hardware/` (`@SOURCES.register`) / `parsers.py` (`LINE_FORMATS`) |
| ตารางต่อยอดเต็ม (Lego) | README.md หัวข้อ "วิธีต่อยอด" |
