# ดึงข้อมูลงานจาก Google Sheet (ออกแบบไว้ — ยังไม่ทำ)

ผู้ใช้ 2026-11-13: ในอนาคตจะดึงข้อมูลจาก Google Sheet เข้าโปรแกรม — ดึงอัตโนมัติตอนเปิดโปรแกรม + ปุ่มดึงเอง + ช่องกรอกลิงก์
"ยังไม่ต้องทำตอนนี้" — เอกสารนี้เตรียมการออกแบบไว้ให้ต่อแบบ Lego โดยไม่ต้องรื้อของเดิม

## 1. หลักการ

- **เลขงาน (Job no.) คือกุญแจเชื่อม** — แถวใน Sheet = 1 งาน (MCI… = Infusion, MCS… = Syringe) · ตรงกับ `JobInfo.job_no`
  และคอลัมน์ `sessions.job_no` (มีแล้วตั้งแต่ schema v5)
- ข้อมูลที่ดึงมา **ไม่เขียนทับ** ผลทดสอบ — เก็บแยกตาราง แล้ว wizard ใช้ "เสนอ" (ตัวจาง รอ Tab/Enter) เหมือนช่องอัจฉริยะเดิม
- ดึงไม่ได้ (ไม่มีเน็ต/ลิงก์ผิด) ต้องไม่ทำให้โปรแกรมเปิดไม่ได้ — ทำใน thread แยก, แจ้งสถานะในแผง log
- อ่านอย่างเดียว (ไม่เขียนกลับ Sheet) ในรุ่นแรก

## 2. ฐานข้อมูล (เพิ่มเมื่อลงมือ — schema v6)

```sql
-- แหล่งข้อมูล (ลิงก์ที่ผู้ใช้กรอก)
CREATE TABLE sync_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, url TEXT, sheet TEXT,             -- ลิงก์ + ชื่อแท็บ
    enabled INTEGER DEFAULT 1, auto_on_start INTEGER DEFAULT 1,
    column_map_json TEXT,                        -- หัวคอลัมน์ใน Sheet -> ชื่อ field ของ JobInfo
    last_sync_at TEXT, last_status TEXT, last_rows INTEGER
);
-- งานที่ดึงมา (1 แถวต่อเลขงาน — ดึงซ้ำ = อัปเดตเฉพาะแถวที่เปลี่ยน ดูจาก row_hash)
CREATE TABLE external_jobs (
    job_no TEXT PRIMARY KEY, source_id INTEGER,
    pump_type TEXT, site TEXT, province TEXT, brand TEXT, model TEXT, serial_no TEXT, asset_id TEXT,
    department TEXT, accessory TEXT, accessory_brand TEXT, due_date TEXT, notes TEXT,
    raw_json TEXT, row_hash TEXT, synced_at TEXT
);
```

## 3. ส่วนที่ต้องเพิ่ม (แบบ Lego)

| ส่วน | ไฟล์ |
|---|---|
| ตัวดึง: ลิงก์แบบ "เผยแพร่เป็น CSV" อ่านด้วย `urllib` (ไม่ต้องมี API key) · ถ้า Sheet เป็นส่วนตัวค่อยใช้ Google API + บัญชีบริการ (key เก็บใน Windows Credential Manager) | `services/sheet_sync.py` (ลงทะเบียน `SYNC_SOURCES`) |
| เก็บ/อ่านตารางข้างบน | `Repository.save_external_jobs / external_job(job_no) / sync_sources` |
| ค่าตั้ง: ลิงก์, ดึงตอนเปิด, ปุ่มดึงเอง + สถานะครั้งล่าสุด | `config/settings.py` (`SyncSettings`) + 1 กลุ่มใน `GROUPS` ของหน้าตั้งค่า |
| ดึงตอนเปิด | `main.py` / `MainWindow` หลังสร้างหน้าต่าง → thread แยก |
| wizard: กรอกเลขงานที่มีใน Sheet → เสนอ โรงพยาบาล จังหวัด รุ่น S/N ฯลฯ เป็นตัวจาง | `JobSuggester` รับ `external_jobs` เพิ่ม (ลำดับ: เครื่องเดิม > Sheet > ประวัติ) |

## 4. คำถามที่ต้องถามผู้ใช้ก่อนลงมือ

1. Sheet เผยแพร่แบบสาธารณะ (CSV) ได้ไหม หรือเป็นส่วนตัว (ต้องใช้บัญชี Google)
2. หัวคอลัมน์จริงของ Sheet (จะทำตารางจับคู่คอลัมน์ให้แก้ได้ในหน้าตั้งค่า)
3. แถวที่ถูกลบออกจาก Sheet — ลบจากโปรแกรมด้วย หรือเก็บไว้
