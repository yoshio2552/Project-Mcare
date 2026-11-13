# สร้าง exe ด้วย Nuitka (เตรียมไว้ — ยังไม่ได้สร้างจริง)

ผู้ใช้ตัดสินใจ 2026-11-13: เปลี่ยนจาก PyInstaller เป็น **Nuitka** เพื่อความเร็วและความเสถียร — ทำตอนท้ายสุดเมื่องานอื่นเสร็จ
เอกสารนี้คือแนวทาง + สิ่งที่โค้ดเตรียมไว้แล้ว · **ทุกข้อที่ระบุว่า "ต้องยืนยัน" ยังไม่ได้ทดสอบบนเครื่องนี้**

## 1. สิ่งที่โค้ดเตรียมไว้แล้ว

| เรื่อง | ทำแล้ว |
|---|---|
| ที่เก็บ `data/` | `config/constants.py::_app_dir()` — รันเป็น exe แล้ว `data/` อยู่ **ข้าง exe** (Nuitka: `__compiled__.containing_dir`) ไม่ใช่ในโฟลเดอร์ชั่วคราวที่ onefile แตกไฟล์ (ถ้าอยู่ที่นั่น ผลทดสอบจะหายเมื่อปิดโปรแกรม) |
| ไฟล์ภาพ/ไอคอนของ UI | `ui/theme.py::ASSETS` อ่านจากโฟลเดอร์ของแพ็กเกจ — ต้องสั่ง `--include-data-dir=ui/assets=ui/assets` |
| สคริปต์สร้าง | `tools/build_nuitka.py` (พิมพ์คำสั่งก่อน, `--run` จึงสร้างจริง) |

## 2. ต้องเตรียมบนเครื่องที่จะสร้าง

1. `pip install nuitka ordered-set zstandard` (zstandard = บีบอัด onefile)
2. **C compiler** — Windows: Visual Studio Build Tools (MSVC, "Desktop development with C++")
   - ต้องยืนยัน: Python 3.14 กับ Nuitka รุ่นที่ใช้ — รุ่นใหม่ของ Python มักต้องใช้ MSVC และ Nuitka รุ่นล่าสุด
     ถ้า Nuitka ยังไม่รองรับ 3.14 ให้สร้าง venv ด้วย Python 3.12/3.13 สำหรับ build เท่านั้น (โค้ดไม่ได้ใช้ฟีเจอร์เฉพาะ 3.14 — ต้องรัน tests ยืนยัน)
3. ไอคอน `.ico` ของโปรแกรม (ยังไม่มี — ตอนนี้ไอคอนวาดด้วยโค้ด)

## 3. คำสั่ง (ร่าง)

```bash
python tools/build_nuitka.py
```
```bash
python tools/build_nuitka.py --run
```

ตัวเลือกหลักที่สคริปต์ใช้:

| ตัวเลือก | เหตุผล |
|---|---|
| `--standalone` (ค่าเริ่มต้น) | ได้โฟลเดอร์ `DeltaM.dist/` — **เปิดเร็วที่สุด** ไม่ต้องแตกไฟล์ทุกครั้งที่เปิด แนะนำสำหรับใช้งานจริง (แจกเป็น zip หรือตัวติดตั้ง) |
| `--onefile` (`--onefile` ของสคริปต์) | ไฟล์เดียวตามที่เคยคุย — แต่ทุกครั้งที่เปิดต้องแตกไฟล์ไปโฟลเดอร์ชั่วคราว (ช้ากว่า, antivirus บางตัวเตือนบ่อยกว่า) |
| `--enable-plugin=pyside6` | ให้ Nuitka รวม Qt plugins (platforms, styles, imageformats) ให้ครบ |
| `--include-package=pyqtgraph` | pyqtgraph import บางโมดูลแบบ dynamic (template ของ Qt แต่ละ binding) — รวมทั้งแพ็กเกจกันตกหล่น |
| `--include-data-dir=ui/assets=ui/assets` | ไฟล์ svg ของ UI (`chevron-down.svg`) |
| `--nofollow-import-to=tests,tools,_legacy,tkinter` | ไม่รวมของที่ไม่ใช้ (ไฟล์เล็กลง สร้างเร็วขึ้น) |
| `--windows-console-mode=disable` | ไม่มีหน้าต่าง console ดำ (log ไปที่ `data/logs` + แผง log บนจอ อยู่แล้ว) |

## 4. รายการตรวจหลังสร้าง (ต้องผ่าน 100 % ก่อนแจก)

- [ ] เปิด exe บนเครื่องที่ **ไม่มี Python** ได้
- [ ] `data/` ถูกสร้างข้าง exe · ฐานข้อมูลเดิมที่คัดลอกไปวางข้าง exe ถูกอ่าน/ย้ายเวอร์ชันได้ (+ ไฟล์สำรอง)
- [ ] ตราชั่งจริง GF-300 ผ่าน COM (pyserial) · ค้นหาพอร์ตอัตโนมัติ · ตราชั่งจำลอง · Replay
- [ ] ทุกหน้า: ทดสอบ (กราฟ 4 ช่องเดินลื่น ~30 FPS), ประวัติ, ตั้งค่า, wizard 4 ขั้น, popup ทุกตัว
- [ ] ส่งออก Excel (openpyxl) เปิดได้
- [ ] ภาษาไทย/อังกฤษ · ฟอนต์ไทยแสดงถูก · ไอคอน svg แสดง
- [ ] scipy/numpy ทำงาน (ปรับหน้าต่าง, self-check)
- [ ] รันนาน (≥ 1 ชม.) หน่วยความจำไม่เพิ่ม
- [ ] antivirus ของโรงพยาบาล/บริษัทไม่บล็อก (ถ้าบล็อก: standalone + ลงลายเซ็น หรือแจ้ง whitelist)

## 5. ความเสี่ยงที่รู้

- Nuitka แปลงเป็น C แล้วคอมไพล์ — สร้างครั้งแรกนาน (หลายสิบนาที, scipy ใหญ่)
- โค้ดที่ import แบบ dynamic (เช่น `importlib`) ต้องบอก Nuitka เอง — ตอนนี้โปรแกรมลงทะเบียน `STRATEGIES`/`SOURCES`/`EXPORTERS`
  ด้วยการ import ปกติ จึงไม่น่ามีปัญหา (ต้องยืนยันว่าทุกตัวขึ้นในรายการหลังสร้าง)
