# DeltaM — Handoff สำหรับเริ่มแชทใหม่

อัปเดต: 2026-11-13 · เวอร์ชัน 0.3.0 · branch `deltam/per-rate-windows` (commit b15400e, ยังไม่ merge เข้า main, ยังไม่ push)
ไฟล์นี้ตั้งใจให้ **สั้นพอจะอ่านจบในครั้งเดียว** — ทำให้แชทใหม่รู้บริบทและโครงสร้างโดยไม่ต้องเปิดโค้ดทั้งหมด

| อยากรู้ | อ่าน |
|---|---|
| ไฟล์ไหนทำอะไร / งานนี้ต้องเปิดไฟล์ไหน | [CODEMAP.md](CODEMAP.md) (แทนการเปิดโค้ด) |
| สูตร อัลกอริทึม เกณฑ์ตัวเลข | [calculation-methods.md](calculation-methods.md) — เปิดเฉพาะหัวข้อที่เกี่ยว |
| ทำไมถึงเป็นแบบนี้ / ผลจากข้อมูลจริง / ประวัติแต่ละรอบงาน | [HISTORY.md](HISTORY.md) — เปิดเฉพาะหัวข้อ (ตารางท้ายไฟล์นี้) |
| วิธีใช้ + ตารางจุดต่อยอด (Lego) | [README.md](../README.md) |

---

## 1. โปรเจ็กคืออะไร

โปรแกรม desktop (Python 3.14, PySide6, pyqtgraph, numpy, scipy, pyserial, openpyxl, sqlite3) สอบเทียบ/ตรวจสอบ flow rate ของ
**Infusion pump และ Syringe pump** ด้วยวิธีชั่งน้ำหนัก: อ่านน้ำหนักจากตราชั่ง → flow, % error → PASS/FAIL
ตราชั่งของผู้ใช้ **A&D GF-300** ผ่าน RS-232 (COM3, 2400 7E1, โหมด poll — ได้จริง ~5 Hz) · ผู้ใช้: วิศวกรเครื่องมือแพทย์ (ไทย)
โปรแกรมเดิมของผู้ใช้คือ ARGOS (VB6) — DeltaM คือตัวใหม่ที่แทน

```bash
python main.py --simulate
```
```bash
python -m unittest discover -s tests -v
```
(119 ข้อ ผ่าน ~90 s · UI test ต้อง `QT_QPA_PLATFORM=offscreen`)

## 2. กติกาการทำงานกับผู้ใช้คนนี้ (สำคัญ)

- **ตอบเป็นภาษาไทย** ชื่อตัวแปร/โค้ดเป็นอังกฤษ **คอมเมนต์ในโค้ดเป็นไทย**
- ทุกข้อความบนจอ/log ผ่าน `tr("English")` + คำแปลใน `config/lang_th.py` (ตรวจด้วย `config.i18n.missing()` หลังเปิดจอภาษาไทย)
- **"Lego style"**: ต่อยอดโดยเพิ่มไฟล์/ลงทะเบียน (`STRATEGIES`, `SOURCES`, `EXPORTERS`) แทนการแก้ของเดิม
- ผู้ใช้มักให้ **เสนอก่อนแล้วรอยืนยัน** — "อย่าเพิ่งทำ" = วิเคราะห์/เสนออย่างเดียว · "ทำเลย" จึงลงมือ
  · "ก:ค" = อนุมัติข้อ ก ถึง ค · ชอบ UI ทันสมัย สีแยกชัด (Infusion ฟ้า #38BDF8 / Syringe ชมพู #F472B6)
- แก้อัลกอริทึม → อัปเดต `docs/calculation-methods.md` + บันทึกรอบงานใน `docs/HISTORY.md` + สถานะใน HANDOFF นี้
- **`data/` = ข้อมูลจริงของผู้ใช้ ห้ามแก้/ลบ** (settings.json, deltam.db, sessions/, captures/) — ทดสอบด้วยฐานข้อมูลชั่วคราว
  `services.session_store.set_repository(Repository(tmp_db, tmp_dir))` หรือสำเนาใน scratchpad · อ่าน raw ใน data/ ได้
- รายงานตรงๆ: ทุกอย่างทดสอบกับ **ตราชั่งจำลอง/ข้อมูลที่บันทึกไว้** — ต้องบอกเสมอว่ายังไม่ได้ยืนยันกับปั๊ม/ตราชั่งจริง
- **"ไม่เก็บ" = ลบจริง** ไม่มีถังพัก · exe ไฟล์เดียวทำตอนท้ายสุด
- git: repo root คือ `D:\Claude` (โฟลเดอร์นี้เป็นโฟลเดอร์ย่อย) — **อย่า commit/push เองถ้าไม่ได้สั่ง** · มีการลบ `../Project Mcare`
  ค้างใน working tree ที่ไม่เกี่ยวกับงานนี้ — อย่าใส่ใน commit
- shell ของเครื่องเป็น cp874: พิมพ์ไทยออก console ต้อง `PYTHONIOENCODING=utf-8` (และ `python -I` ไม่อ่านตัวแปรนี้) · ไฟล์ใช้ utf-8 เสมอ
- ห้ามเปิดหน้าต่างจริงบนจอผู้ใช้ระหว่างตรวจ — ใช้ offscreen (สูตรในหัวข้อ 6)

## 3. การตัดสินใจของผู้ใช้ที่ต้องคงไว้

1. ไม่เก็บ = ลบจริง · SQLite ไฟล์เดียว เครื่องเดียว (`Repository` สลับชนิดได้ที่ `get_repository()`)
2. สิ่งที่เรียนรู้ทั้งหมดผูกกับ **ยี่ห้อ + รุ่น + ชนิดเครื่อง + ชุดสาย (Set IV)** (`core.profiles.pump_key`)
3. Infusion ค่าเริ่มต้น = จับรอบปั๊ม (peak) · Syringe = จับตามเวลาแบ่งช่วง
4. หน้าหลักชื่อ "ทดสอบ" — ชื่อ "Dashboard" สงวนไว้ให้หน้าสถิติในอนาคต
5. โหมด "กดเอง" ใช้แถบบนหน้าทดสอบ ไม่ใช่ popup (popup บังกราฟ)
6. รายการตรวจเครื่องแยกตามรุ่น ยิ่งใช้ยิ่งครบ · เอา CI 95 % ออกจากจอ/Excel เหลือ 2SD
7. **regression / n̄ ต้องแยกทุก rate และทุกรุ่น/ชุดสาย ห้ามใช้ค่าเดียว** (ผู้ใช้: "ผิดพลาดร้ายแรงอย่างมาก")
8. ผล INVALID (จับรอบไม่ตรงคาบ/ไม่พอ) เก็บได้เพื่อสอบย้อนหลัง แต่ขั้นไม่เลื่อน ไม่เรียนรู้
9. ค่าหน้าต่างที่แก้เอง/ค่าเริ่มต้นที่บันทึก ยังถือว่า "ยังไม่ได้สอบเทียบ" (ยังเตือน) · กรอกเป็นจำนวนจุด เก็บเป็นสัดส่วนของคาบ
10. ไม่เตือนเรื่องสอบเทียบรอบปั๊มเมื่อวิธีวัดไม่ได้ใช้รอบปั๊ม (จับตามเวลา / syringe)

## 4. ฟีเจอร์ที่มีแล้ว (สรุป)

- **Workflow**: wizard 4 ขั้น (งาน → ตรวจเครื่อง → โหมด Calibration/Inspection/Quick Test → ตั้งค่า) · หลาย rate ต่อเนื่อง · ถามเก็บ/ไม่เก็บทุกขั้น
- **วิธีจับ**: `pump_cycle` (peak-to-peak, จับรอบคู่/เดี่ยว, จบตามเวลา/จำนวนรอบ), `time_interval`, `time_total`
- **เริ่มวัด**: ทันที / ปล่อยรันก่อน / อัตโนมัติเมื่อ flow นิ่ง (เกณฑ์ 3 กลุ่ม + เฉพาะรุ่น) / กดเอง
- **ตราชั่ง**: stream/poll/auto, thread อ่านแยก, ตัวอ่าน A&D เข้มงวด, ค้นหาพอร์ตอัตโนมัติ, ตราชั่งจำลอง, Replay ไฟล์ดิบ
- **ค่าแก้**: g→ml ตาม ISO 4787 (Z) + self-check การระเหย · เก็บผลสุทธิ + ก่อนแก้คู่กัน (audit) · raw บีบอัด + SHA-256
- **เรียนรู้รอบปั๊ม**: โปรไฟล์ปริมาตรต่อรอบ, ปรับหน้าต่าง r/h ราย rate อัตโนมัติจากข้อมูลจริง, popup ค่าต่างจากเดิม, ปุ่ม Calibration ใหม่
- **หน้าต่างราย rate (ล่าสุด)**: ทุกจอแสดงค่าของแต่ละ rate · popup เตือนสอบเทียบ (ข้าม+แก้+บันทึกได้) · ตั้งค่า → ข้อมูลสอบเทียบรอบปั๊ม
  · เตือนจุดต่อรอบน้อย (< 12) / ห้าม (< 8) · ตรวจผลหลังจบ → INVALID
- **รันนานหลายชั่วโมง**: engine ไม่เก็บ raw ใน RAM, สถิติสะสม O(1), กราฟหน่วยความจำคงที่ (ทดสอบจำลอง 4 ชม. แล้ว)
- **หน้าประวัติ**: แท็บตามโหมด, ค้นหา, กรอง PASS/FAIL/INVALID, ดูกราฟย้อนหลัง, ลบ, ส่งออก Excel · สองภาษา ไทย/อังกฤษ

## 5. สถานะและข้อจำกัดที่รู้ (ณ 2026-11-13)

- **ยังไม่เคยรันทั้งระบบกับ GF-300 + ปั๊มจริง** — ใช้ capture จริง (TE-171 10/50/200 ml/h, TE-112 session id 11) เล่นซ้ำแทน
- ผู้ใช้ **ยังไม่ได้ดูหน้าจอจริง** ของงานรอบล่าสุด (popup สอบเทียบ, ข้อมูลสอบเทียบ, คอลัมน์หน้าต่างใน wizard, INVALID)
- ผล session id 11 แสดงเป็น INVALID (ตรวจย้อนหลัง, ฐานข้อมูลไม่ถูกแก้) — รอผู้ใช้ตัดสินใจลบ/ทำซ้ำ
- ฐานข้อมูลจริงยังเป็น v3 — จะย้ายเป็น v4 (+ สำรอง `deltam.v3-backup.db`) เมื่อผู้ใช้เปิดโปรแกรมรุ่นนี้ครั้งแรก
- ตราชั่ง 5 Hz ที่ rate สูง + ชุดสายรอบสั้น ได้ ~10 จุดต่อรอบ: จับรอบถูกแต่ผลรายรอบแกว่ง ±2SD ~8 % (จับตามเวลาแม่นกว่า)
- หาคาบที่ 10 ml/h ผิด (357 s แทน 71 s) — ถ้ารู้คาบจากโปรไฟล์ การตรวจหลังจบจับได้
- คำถาม "ARGOS ได้ ~0 % แต่ DeltaM ได้ −5 %" ยังไม่ปิด (HISTORY 6.3)
- เกณฑ์หลายตัวเป็นข้อเสนอของ AI ที่อิงข้อมูลไม่กี่ชุด: ขั้นต่ำ 5/3 จุด, จุดต่อรอบ 8/12, อัตราส่วน 0.7–1.4, 0.3–0.5 × คาบ,
  เกณฑ์ self-check, เกณฑ์ flow นิ่ง 3 กลุ่ม
- ยังไม่ได้ทำ: หยุดถามผู้ใช้กลางการทดสอบเมื่อหาคาบไม่ได้ (ตอนนี้ใช้คาบโปรไฟล์/เดาจากปริมาตรต่อรอบ + หมายเหตุ)
- สัญลักษณ์ ⚠/⛔ เป็นกล่องในภาพ offscreen (ไม่มีฟอนต์สัญลักษณ์) — บนจอจริงยังไม่ได้ดู

## 6. งานถัดไป

**ถามผู้ใช้ก่อนว่าจะทำอะไร** — ผู้ใช้มักมาพร้อมงาน/ไอเดียใหม่ รายการนี้คืองานค้างที่เคยคุยไว้:

1. ให้ผู้ใช้ลองบนจอจริง (งานรอบล่าสุด + ช่องกรอกอัจฉริยะ, เกณฑ์ 3 กลุ่ม, popup ค่าต่างจากเดิม) · merge branch เข้า main เมื่อผู้ใช้สั่ง
2. **Dashboard สถิติ (แท็บใหม่)** — ผู้ใช้จะทำ "ทีหลัง": error, รอบปั๊ม, เวลา, ปริมาตร ข้ามการทดสอบ ต่อรุ่น/ชุดสาย/rate
   ข้อมูลพร้อม: ตาราง `intervals`, `profile_observations`, `window_tuning`, `sessions.summary_json` · ใช้ skill dataviz ก่อนเขียนกราฟ
3. ยืนยันกับปั๊มจริง: rate สูงที่ 5 Hz (จับ peak vs จับตามเวลา, หรือเพิ่ม baud เป็น 9600), baseline ≥ 10 นาที, syringe pump
4. ปิดคำถาม −5 % เทียบ ARGOS (ตุ้มน้ำหนักมาตรฐาน หรือจดเวลา/น้ำหนักจริงจาก ARGOS)
5. ของที่ผู้ใช้เลื่อนไว้ (ต่อแบบ Lego): ใบรายงาน PDF (`EXPORTERS`), งบความไม่แน่นอน, Trumpet curve (IEC 60601-2-24 — เปิดมาตรฐานยืนยัน),
   ผู้ช่วย AI (อ่านผ่าน `Repository` อย่างเดียว, API key ใน Windows Credential Manager), บัญชีผู้ใช้/audit trail, หน้าประวัติรายเครื่อง,
   เรียนรู้ "เวลาที่นิ่ง" ต่อรุ่น + rate, รวมชื่อที่สะกดต่างกันในประวัติ
6. ท้ายสุด: exe ไฟล์เดียว (PyInstaller) — ระวัง path ของ `data/` และ `ui/assets/chevron-down.svg`

## 7. วิธีตรวจงานแบบอัตโนมัติ (ใช้ซ้ำได้)

```python
os.environ["QT_QPA_PLATFORM"] = "offscreen"          # ห้ามเปิดหน้าต่างจริงบนจอผู้ใช้ (ผู้ใช้กดโดนได้)
os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"     # ให้ widget.grab().save(png) มีตัวอักษร
from services import session_store
session_store.set_repository(session_store.Repository(tmp / "t.db", tmp / "sessions"))   # ก่อน import main
import services.logging_setup as ls; ls.LOG_DIR = tmp / "logs"    # ไม่เขียน log จริง
AppSettings.save = lambda self, path=None: None       # ตัวเลือกข้างกราฟบันทึก settings ทันที — ห้ามทับไฟล์จริง
from main import Application
app = QApplication([])                                 # ต้องมีก่อนสร้างหน้าต่าง ไม่งั้น crash 0xC0000409
from ui.theme import apply_theme; apply_theme(app)    # ไม่งั้นภาพได้สีพื้นเทา
s = AppSettings(); s.source = "simulator"; s.simulator.speed = 150
w = Application(s).build_window(); c = w.controller; page = w.test_page
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
result_review.ResultReviewDialog.exec = lambda self: QDialog.DialogCode.Accepted      # เก็บผลเสมอ
# popup เตือนสอบเทียบ: คืน obj ที่มี action = "calibrate" | "use" | "time" (+ values, save, stroke_ml, reorder, time_windows)
TestWizard._prompt_calibration = lambda self, job, items, known, stroke, recompute=None: None   # None = กลับไปแก้
c.ask_profile_decision = lambda check: "skip"         # ไม่งั้น popup ค่าต่างจากเดิมจะค้างสคริปต์
c.set_plan(TestPlan(...)); c.start_step()            # ฟัง c.session_finished(summary, kept)
w.close(); w.deleteLater(); app.processEvents(); del w; app.quit()   # ปิดตามลำดับ ไม่งั้น crash ตอนออก
```

ตรวจกับข้อมูลจริงโดยไม่แตะ data/: คัดลอก `data/deltam.db` ไป scratchpad แล้วเปิดด้วย `Repository(สำเนา, ...)` ·
อ่าน raw ด้วย `Repository.read_samples(folder)` / `hardware.replay.load_samples(path)` แล้วป้อน `FlowEngine.process(Sample(t, w))`

## 8. HISTORY.md มีอะไรบ้าง (เปิดเฉพาะที่เกี่ยว)

| หัวข้อ | เรื่อง |
|---|---|
| 6.1–6.3 | ตราชั่งจริงครั้งแรก (5 Hz, หน่วง 192 ms), capture TE-171, บั๊กบรรทัดขาด, เทียบ ARGOS (−5 %) |
| 6.4 | หน้าทดสอบ: PlotCell, แถบติดตาม, การ์ด, บั๊กปุ่มไม่เก็บ |
| 6.5–6.6 | self-check เกณฑ์สถิติ · g→ml ISO 4787 + เก็บค่าก่อนแก้ |
| 6.7–6.9 | โปรไฟล์/ปรับหน้าต่าง/บีบอัด+SHA-256 · กุญแจรุ่น+ชนิด+ชุดสาย, เกณฑ์ 3 กลุ่ม, ช่องกรอกอัจฉริยะ · Calibration รอบปั๊ม, schema v3 |
| 6.10–6.11 | ปัญหา 250/250 (session id 11) และการแก้ทั้งหมดรอบล่าสุด (หน้าต่างราย rate, INVALID, ข้อมูลสอบเทียบ, schema v4, RAM) |
