# Prompt สำหรับเริ่มแชทใหม่ (คัดลอกทั้งกล่องด้านล่าง แล้วต่อท้ายด้วยงานใหม่)

```text
โปรเจ็ก DeltaM (โปรแกรมสอบเทียบ Infusion/Syringe pump ด้วยตราชั่ง A&D GF-300) อยู่ที่ D:\Claude\Calibration INF SYR
repo root คือ D:\Claude (โฟลเดอร์นี้เป็นโฟลเดอร์ย่อย) · branch หลัก main · เวอร์ชัน 0.3.0

ก่อนเริ่ม:
1. อ่าน docs/HANDOFF.md ให้จบ (สั้น — มีกติกา การตัดสินใจที่ต้องคงไว้ สถานะ งานค้าง สูตรตรวจแบบ offscreen)
2. อ่าน docs/CODEMAP.md แล้วใช้หาไฟล์ที่เกี่ยวกับงาน — ห้ามเปิดอ่านโค้ดทั้งหมด เปิดเฉพาะไฟล์/เมธอดที่ต้องแก้ (ไฟล์ใหญ่ให้ grep ก่อน)
3. ต้องรู้ที่มา/ผลจากข้อมูลจริง -> docs/HISTORY.md เฉพาะหัวข้อ · สูตร/เกณฑ์ -> docs/calculation-methods.md เฉพาะหัวข้อ
4. ดู git status / branch ปัจจุบันก่อนแก้

สถานะล่าสุด (2026-11-19, merge เข้า main แล้ว):
- ใบรายงาน PDF/พิมพ์/ดูตัวอย่าง (services/report/) หน้าตาตามใบตัวอย่างของผู้ใช้: ฟอนต์ IBM Plex Sans Thai + IBM Plex Mono
  (ฝังใน PDF จาก ui/assets/fonts) · หัวข้อเลข 01 สีตามชนิดเครื่อง · ป้ายอังกฤษตัวพิมพ์ใหญ่ · เส้น flow สีดำ พื้นเกณฑ์สีตามชนิดเครื่อง
  · ห้ามกลับไปใช้ IBM Plex Sans Thai *Looped* (ผู้ใช้ไม่เอา) · ตัวเลขในใบ: Error% 2 ตำแหน่ง ปริมาตร 3 ตำแหน่ง เวลา นาที:วินาที.xx
  · ใบ Inspection (ไม่ใช่ Calibration) ไม่ใส่ค่าการอุดตันที่วัด — เขียน "ทำงานปกติ" · ใบ Calibration หน้า 1 ข้ออัตราการไหล = rate + "ดูหน้า 2"
  · ทุกครั้งที่แก้หน้าตาใบ: python tools/report_templates/real_sample.py (และ --long) ต้อง "pages with problems: 0"
- ฐานข้อมูล v7: ตาราง jobs = ข้อมูลงานชุดเดียวต่องาน (job_json) + ข้อมูลใบ (report_json)
- wizard 5 ขั้น (ขั้น 3 = ผลตรวจรายข้อ + ค่าที่วัดด้วยมือ) · ค่าตั้งต้นขั้น 3 อยู่ในหน้าตั้งค่า (report.default_*) · วิธีจับแยกราย rate ได้
- หน้าประวัติ: ค้นเร็วช่องเดียว (services/history_search.py) + คัดกรองขั้นสูง (ui/widgets/history_filters.py) + ล้างที่เลือก
- ยังไม่ได้ลอง: เครื่องพิมพ์จริง · exe ด้วย Nuitka (docs/build-nuitka.md) · ค่าความไม่แน่นอน U ยังไม่ได้ประเมิน

กติกา (รายละเอียด HANDOFF หัวข้อ 2–3):
- ตอบภาษาไทย · โค้ด/ชื่อตัวแปรอังกฤษ · คอมเมนต์ในโค้ดภาษาไทย · ข้อความบนจอผ่าน tr("English") + คำแปลใน config/lang_th.py
  (ตรวจ config.i18n.missing() หลังเปิดจอภาษาไทย)
- ต่อยอดแบบ Lego: เพิ่มไฟล์/ลงทะเบียนแทนการรื้อของเดิม · UI ทันสมัย สีแยกชัด (Infusion ฟ้า / Syringe ชมพู)
- ห้ามแตะข้อมูลจริงใน data/ — ทดสอบด้วยฐานข้อมูลชั่วคราวหรือสำเนาใน scratchpad (set_repository ก่อน import main)
  ห้ามเรียก session_store.get_repository() ก่อน set_repository (จะเปิดและย้ายเวอร์ชัน data/deltam.db จริง) · ห้ามเปิดหน้าต่างจริงบนจอ ใช้ offscreen
- รายงานตรงๆ เสมอ: อะไรทดสอบแบบ offscreen / ตราชั่งจำลอง / ข้อมูลที่บันทึกไว้ และอะไรยังไม่ได้ลองกับของจริง
- แก้อัลกอริทึม/พฤติกรรม -> อัปเดต calculation-methods.md + บันทึกรอบงานใน HISTORY.md + สถานะใน HANDOFF.md + CODEMAP.md ถ้าไฟล์เปลี่ยน
- งานใหญ่: สรุปว่าจะทำอย่างไร แก้ไฟล์ไหน แล้วรอผมยืนยันก่อน · "ก:ค" = อนุมัติข้อ ก ถึง ค
- อย่า commit/push เองถ้าผมไม่ได้สั่ง · มีการลบ ../Project Mcare ค้างอยู่ใน working tree ห้ามใส่ใน commit
- tests: python -m unittest discover -s tests (ต้อง QT_QPA_PLATFORM=offscreen, 204 ข้อ ~105 s) ต้องผ่านทั้งหมดก่อนส่งงาน
- Edge headless ใน Git Bash ถูกบล็อก — งานที่ใช้ Edge (tools/report_templates/*/build.py) ให้รันจาก PowerShell

งานใหม่:
<พิมพ์งานที่นี่>
```
