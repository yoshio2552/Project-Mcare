"""คำแปลภาษาไทย: ข้อความอังกฤษในโค้ด -> ข้อความไทยบนจอ

ข้อความที่ไม่มีในตารางนี้จะแสดงเป็นอังกฤษตามเดิม (ศัพท์เทคนิคบางคำจงใจคงไว้)
ตรวจว่ามีข้อความไหนยังไม่ได้แปล: ดู config.i18n.missing() หลังเปิดใช้งานหน้าจอ
"""

TRANSLATIONS = {
    # ---------------------------------------------------------------- ทั่วไป
    "Dashboard": "แดชบอร์ด",
    "History": "ประวัติ",
    "Settings": "ตั้งค่า",
    "Cancel": "ยกเลิก",
    "Back": "ย้อนกลับ",
    "Next": "ถัดไป",
    "Close": "ปิด",
    "Save": "บันทึก",
    "Refresh": "รีเฟรช",
    "Export": "ส่งออก",
    "Start": "เริ่ม",
    "Stop": "หยุด",
    "On": "เปิด",
    "Off": "ปิด",
    "Clear": "ล้าง",
    "Activity log": "บันทึกการทำงาน",
    "Open data folder": "เปิดโฟลเดอร์ข้อมูล",

    # ---------------------------------------------------------------- โหมด / วิธีวัด
    "Calibration": "Calibration (สอบเทียบ)",
    "Inspection": "Inspection (ตรวจสอบ)",
    "Quick Test": "Quick Test (ทดสอบเร็ว)",
    "Quick test": "Quick Test",
    "Infusion pump": "Infusion pump",
    "Syringe pump": "Syringe pump",
    "Pump cycle (peak-to-peak)": "จับรอบปั๊ม (peak-to-peak)",
    "Time, split into intervals": "จับตามเวลา แบ่งเป็นช่วง",
    "Time, single measurement": "จับตามเวลา วัดรวดเดียว",
    "Balance (serial port)": "ตราชั่ง (พอร์ตอนุกรม)",
    "Simulator (no hardware)": "ตัวจำลอง (ไม่ต้องต่อเครื่อง)",

    # ---------------------------------------------------------------- สถานะ
    "READY": "พร้อม",
    "RUNNING": "กำลังทดสอบ",
    "STOPPING…": "กำลังหยุด…",
    "COMPLETED": "เสร็จสิ้น",
    "STOPPED": "หยุดแล้ว",
    "ERROR": "ผิดพลาด",
    "Completed": "เสร็จสิ้น",
    "Stopped": "หยุดกลางคัน",
    "Error": "ผิดพลาด",
    "Running": "กำลังทดสอบ",
    "CONNECTING…": "กำลังเชื่อมต่อ…",
    "CONNECTED": "เชื่อมต่อแล้ว",
    "NOT CONNECTED": "ไม่ได้เชื่อมต่อ",
    "IN TEST": "กำลังทดสอบ",
    "IN TOLERANCE": "อยู่ในเกณฑ์",
    "OUT OF TOL.": "นอกเกณฑ์",
    "NO RESULT": "ไม่มีผล",
    "partial": "ไม่ครบ",

    # ---------------------------------------------------------------- ข้อมูลงาน
    "Pump type": "ชนิดเครื่อง",
    "Brand": "ยี่ห้อ",
    "Model": "รุ่น",
    "Serial no.": "Serial no.",
    "Asset ID": "รหัสครุภัณฑ์",
    "Department": "หน่วยงาน",
    "Syringe / set": "Syringe / ชุดสาย",
    "Operator": "ผู้ทดสอบ",
    "Balance ID": "รหัสตราชั่ง",
    "Temperature (°C)": "อุณหภูมิ (°C)",
    "Humidity (%RH)": "ความชื้น (%RH)",
    "Notes": "หมายเหตุ",
    "e.g. 50 ml syringe, IV set brand": "เช่น syringe 50 ml, ยี่ห้อชุดให้สารน้ำ",
    "Reference balance used": "ตราชั่งมาตรฐานที่ใช้",
    "Recall": "ดึงข้อมูล",
    "— Load a device tested before —": "— เลือกเครื่องที่เคยทดสอบ —",
    "All fields are optional, but they are saved with the result and used for traceability.":
        "ทุกช่องเว้นว่างได้ แต่ข้อมูลจะถูกบันทึกไปกับผลทดสอบเพื่อใช้สอบกลับ",

    # ---------------------------------------------------------------- wizard
    "New test": "สร้างการทดสอบ",
    "Create test": "สร้างการทดสอบ",
    "Step 1 of 3 · Device and job details": "ขั้น 1 จาก 3 · ข้อมูลเครื่องและงาน",
    "Who and what is being tested": "ทดสอบเครื่องอะไร โดยใคร",
    "Step 2 of 3 · Choose the test mode": "ขั้น 2 จาก 3 · เลือกโหมดการทดสอบ",
    "Click a mode to continue": "คลิกโหมดที่ต้องการเพื่อไปต่อ",
    "Step 3 of 3 · {mode} settings": "ขั้น 3 จาก 3 · ตั้งค่า {mode}",
    "Flow rates and how they are measured": "กำหนด rate ที่จะทดสอบ และวิธีวัด",
    "Several flow rates in sequence. A result is recorded for every rate.":
        "ทดสอบหลาย rate ต่อเนื่องกัน บันทึกผลแยกทุก rate",
    "One flow rate, full-length test against the tolerance.":
        "ทดสอบ rate เดียวเต็มเวลา เทียบกับเกณฑ์ยอมรับ",
    "A short check to see that the pump and balance behave as expected.":
        "ทดสอบสั้นๆ เพื่อดูว่าปั๊มและตราชั่งทำงานปกติ",
    "Measurement": "การวัด",
    "Method": "วิธีจับ",
    "End condition": "เงื่อนไขจบ",
    "Tolerance": "เกณฑ์ยอมรับ",
    "Start measuring": "เริ่มวัด",
    "Pre-run delay": "เวลาปล่อยรันก่อนวัด",
    "By time": "ตามเวลา",
    "By number of pump cycles": "ตามจำนวนรอบปั๊ม",
    "Immediately": "ทันที",
    "After a pre-run delay": "หลังปล่อยรันตามเวลาที่ตั้ง",
    "Automatically when flow is stable": "อัตโนมัติเมื่อ flow นิ่ง",
    "When I press the button": "เมื่อกดปุ่มเอง",
    "Measurement starts as soon as Start is pressed.": "เริ่มวัดทันทีที่กด Start",
    "The pump runs first for the set time (with countdown and live graphs), then measurement starts from zero.":
        "ปล่อยปั๊มรันก่อนตามเวลาที่ตั้ง (มีนับถอยหลังและกราฟจากข้อมูลจริง) แล้วเริ่มวัดโดยนับใหม่จากศูนย์",
    "Measurement starts by itself once the flow stops drifting. You can still start it by hand.":
        "ระบบเริ่มวัดเองเมื่อ flow นิ่งแล้ว และยังกดเริ่มเองได้ทุกเมื่อ",
    "Watch the live graphs and press Start measuring when the pump looks ready.":
        "ดูกราฟจากข้อมูลจริง แล้วกดเริ่มวัดเมื่อเห็นว่าปั๊มพร้อม",
    "Cycles are counted peak-to-peak and valley-to-valley; the test stops when both have reached the set number.":
        "นับรอบทั้งแบบ peak-ถึง-peak และ valley-ถึง-valley จบเมื่อทั้งสองแบบครบจำนวนที่ตั้ง",
    "When the time is up the test keeps going until the pump cycle in progress is complete.":
        "เมื่อครบเวลาแล้วจะยังไม่ตัด จนกว่ารอบปั๊มที่กำลังเดินอยู่จะจบจริง",
    "Flow rates": "Rate ที่ทดสอบ",
    "+ Add rate": "+ เพิ่ม rate",
    "Remove this rate": "ลบ rate นี้",
    "Target rate": "Rate ที่ตั้ง",
    "Duration": "ระยะเวลา",
    "Pump cycles": "จำนวนรอบปั๊ม",
    "Interval length": "ความยาวช่วง",
    "intervals": "ช่วง",
    "cycles": "รอบ",
    "Whole duration": "ทั้งช่วงเวลา",

    # ---------------------------------------------------------------- dashboard
    "Create a test on the left, then press Start": "สร้างการทดสอบทางซ้าย แล้วกดเริ่ม",
    "Test plan": "แผนการทดสอบ",
    "No test yet": "ยังไม่มีการทดสอบ",
    "Press New test to enter the device details and choose a mode.":
        "กด \"สร้างการทดสอบ\" เพื่อกรอกข้อมูลเครื่องและเลือกโหมด",
    "Graph window": "ช่วงเวลาบนกราฟ",
    "All steps done": "ครบทุกขั้นแล้ว",
    "Start {i}/{n} · {rate:g} ml/h": "เริ่มขั้น {i}/{n} · {rate:g} ml/h",
    "Step {i}/{n}": "ขั้น {i}/{n}",
    "Balance": "ตราชั่ง",
    "No data from the balance": "ไม่ได้รับข้อมูลจากตราชั่ง",
    "Flow error": "ค่าคลาดเคลื่อน",
    "Mean flow": "Flow เฉลี่ย",
    "Live average": "ค่าเฉลี่ยสะสม (สด)",
    "Chain A": "สาย A",
    "Chain B": "สาย B",
    "Last interval": "ช่วงล่าสุด",
    "Cycle timing": "เวลาต่อรอบปั๊ม",
    "Last cycle": "รอบล่าสุด",
    "Result": "ผลการทดสอบ",
    "Target": "Rate ที่ตั้ง",
    "Intervals": "จำนวนช่วง",
    "Stop the test?": "หยุดการทดสอบ?",
    "The test is not finished. Stop it now?\nData collected so far will be saved as an incomplete result.":
        "การทดสอบยังไม่เสร็จ ต้องการหยุดเดี๋ยวนี้หรือไม่?\nข้อมูลที่เก็บได้จะถูกบันทึกเป็นผลที่ไม่ครบ",
    "Test created. Set the pump to {rate:g} ml/h, start it, then press Start.":
        "สร้างการทดสอบแล้ว ตั้งปั๊มที่ {rate:g} ml/h เดินเครื่อง แล้วกดเริ่ม",
    "Connecting to the balance…": "กำลังเชื่อมต่อตราชั่ง…",
    "Start measuring now": "เริ่มวัดเดี๋ยวนี้",
    "Pre-run": "ช่วงก่อนวัด",
    "Pre-run — measurement starts in {time}": "ช่วงก่อนวัด — จะเริ่มวัดในอีก {time}",
    "Pre-run — waiting for stable flow (variation {v} / limit {limit:g} %)":
        "ช่วงก่อนวัด — รอให้ flow นิ่ง (ความแกว่ง {v} / เกณฑ์ {limit:g} %)",
    "Pre-run — watch the graphs, then press Start measuring when the pump is ready":
        "ช่วงก่อนวัด — ดูกราฟ แล้วกด \"เริ่มวัดเดี๋ยวนี้\" เมื่อปั๊มพร้อม",
    "measuring the pump cycle period…": "กำลังวัดคาบรอบปั๊ม…",
    "pump cycle {p:.1f} s": "รอบปั๊ม {p:.1f} วินาที",
    "Preparing — filling the calculation window (about {s:.0f} s left)":
        "กำลังเตรียม — รอข้อมูลเต็มหน้าต่างคำนวณ (อีกประมาณ {s:.0f} วินาที)",
    "Waiting for the first complete pump cycle…": "กำลังรอรอบปั๊มรอบแรกให้ครบ…",
    "Step {i}/{n} finished. Set the pump to {rate:g} ml/h, then press Start.":
        "ขั้น {i}/{n} เสร็จแล้ว ตั้งปั๊มที่ {rate:g} ml/h แล้วกดเริ่ม",
    "All steps are finished. Results are saved in History.": "ครบทุกขั้นแล้ว ผลถูกบันทึกไว้ในหน้าประวัติ",
    "Test stopped. Press Start to run this step again.": "หยุดการทดสอบแล้ว กดเริ่มเพื่อทดสอบขั้นนี้ใหม่",
    "The test ended with an error — see the activity log.": "การทดสอบจบด้วยข้อผิดพลาด — ดูรายละเอียดในบันทึกการทำงาน",
    "A test is running": "กำลังทดสอบอยู่",
    "The test is not finished. Stop it and close the program?": "การทดสอบยังไม่เสร็จ ต้องการหยุดและปิดโปรแกรมหรือไม่?",
    "Data collected so far will be saved.": "ข้อมูลที่เก็บได้จะถูกบันทึก",

    # ---------------------------------------------------------------- กราฟ
    "Cumulative average flow": "Flow เฉลี่ยสะสม",
    "Interval flow": "Flow รายช่วง",
    "Instantaneous flow & pump cycle": "Flow ขณะนั้น และรอบปั๊ม",
    "Balance weight": "น้ำหนักบนตราชั่ง",
    "Flow (ml/h)": "Flow (ml/h)",
    "Weight (g)": "น้ำหนัก (g)",
    "Time (s)": "เวลา (วินาที)",
    "Time since chain start (s)": "เวลาตั้งแต่เริ่มสาย (วินาที)",
    "Overall": "รวม",
    "Mean": "ค่าเฉลี่ย",
    "Peak": "Peak",
    "Valley": "Valley",

    # ---------------------------------------------------------------- history
    "Saved test results — double-click a row to open it": "ผลการทดสอบที่บันทึกไว้ — ดับเบิลคลิกเพื่อเปิดดู",
    "Search device, serial no., operator, date…": "ค้นหา เครื่อง, serial no., ผู้ทดสอบ, วันที่…",
    "All results": "ทุกผล",
    "All modes": "ทุกโหมด",
    "No results to show": "ไม่มีผลการทดสอบที่จะแสดง",
    "{shown} of {total}": "{shown} จาก {total}",
    "Date": "วันที่",
    "Mode": "โหมด",
    "Step": "ขั้น",
    "Device": "เครื่อง",
    "Target (ml/h)": "Rate ที่ตั้ง (ml/h)",
    "Mean flow (ml/h)": "Flow เฉลี่ย (ml/h)",
    "Error (%)": "คลาดเคลื่อน (%)",
    "CI 95% (±%)": "CI 95% (±%)",
    "Tolerance (±%)": "เกณฑ์ (±%)",
    "Status": "สถานะ",
    "Could not open this result: {error}": "เปิดผลนี้ไม่ได้: {error}",
    "Export failed: {error}": "ส่งออกไม่สำเร็จ: {error}",
    "Exported {n} results to\n{path}": "ส่งออก {n} รายการไปที่\n{path}",
    "Test result": "ผลการทดสอบ",
    "Test": "การทดสอบ",
    "Job ID": "รหัสงาน",

    # ---------------------------------------------------------------- settings
    "Saved values apply from the next test": "ค่าที่บันทึกจะมีผลกับการทดสอบครั้งถัดไป",
    "Reset to defaults": "คืนค่าเริ่มต้น",
    "Saved ✓": "บันทึกแล้ว ✓",
    "Could not save: {error}": "บันทึกไม่สำเร็จ: {error}",
    "Defaults restored (not saved yet)": "คืนค่าเริ่มต้นแล้ว (ยังไม่ได้บันทึก)",
    "The language will change once the test has finished": "ภาษาจะเปลี่ยนหลังการทดสอบเสร็จ",
    "Scan for ports": "ค้นหาพอร์ตใหม่",
    "Interface": "หน้าจอ",
    "Language": "ภาษา",
    "Sound when a test finishes": "เสียงเตือนเมื่อทดสอบเสร็จ",
    "Confirm before stopping": "ยืนยันก่อนหยุดการทดสอบ",
    "Data source": "แหล่งข้อมูล",
    "Source": "แหล่งข้อมูล",
    "Simulator lets you try the program without a balance connected": "ตัวจำลองใช้ทดลองโปรแกรมได้โดยไม่ต้องต่อตราชั่ง",
    "Port": "พอร์ต",
    "Baud rate": "Baud rate",
    "Data bits": "Data bits",
    "Parity": "Parity",
    "Stop bits": "Stop bits",
    "None": "ไม่มี",
    "Even": "คู่ (Even)",
    "Odd": "คี่ (Odd)",
    "Calculation": "การคำนวณ",
    "Liquid density": "ความหนาแน่นของเหลว",
    "Distilled water at 20°C = 0.9982. Enter 1.0000 to treat 1 g as 1 ml":
        "น้ำกลั่น 20°C = 0.9982 · ใส่ 1.0000 ถ้าต้องการให้ 1 g = 1 ml",
    "Warm-up": "ทิ้งข้อมูลช่วงแรก",
    "Window sizes": "ขนาดหน้าต่างคำนวณ",
    "Manual (values below)": "กำหนดเอง (ใช้ค่าด้านล่าง)",
    "Auto (measure the pump cycle first)": "อัตโนมัติ (วัดรอบปั๊มก่อน)",
    "Auto measures the pump cycle period before each test and sizes both windows to fit it. Used by the pump-cycle method only":
        "โหมดอัตโนมัติจะวัดคาบรอบปั๊มก่อนเริ่มทดสอบ แล้วตั้งขนาดหน้าต่างทั้งสองให้พอดี (ใช้กับวิธีจับรอบปั๊มเท่านั้น)",
    "Regression window": "หน้าต่าง regression",
    "Cycle half-window (n_bar)": "ครึ่งหน้าต่างจับรอบ (n_bar)",
    "Auto: window / pump cycle": "อัตโนมัติ: หน้าต่าง / คาบรอบปั๊ม",
    "Auto: give up after": "อัตโนมัติ: เลิกหาคาบเมื่อเกิน",
    "Automatic start (stable flow)": "เริ่มวัดอัตโนมัติ (flow นิ่ง)",
    "Allowed flow variation": "ความแกว่งของ flow ที่ยอมรับ",
    "Measurement starts when the flow of the last few blocks differs by less than this":
        "เริ่มวัดเมื่อ flow ของช่วงล่าสุดหลายช่วงต่างกันไม่เกินค่านี้",
    "Block length": "ความยาว 1 ช่วง",
    "Blocks compared": "จำนวนช่วงที่เทียบ",
    "Simulator": "ตัวจำลอง",
    "Time speed-up": "เร่งเวลา",
    "Pump error": "ความคลาดเคลื่อนของปั๊ม",
    "Flow ripple": "การแกว่งของ flow",
    "Cycle period": "คาบรอบปั๊ม",

    # ---------------------------------------------------------------- log
    "Connected to {source}": "เชื่อมต่อแหล่งข้อมูล: {source}",
    "No data from the balance for {s:.0f} s — check the cable and continuous-output mode":
        "ไม่ได้รับข้อมูลจากตราชั่งเกิน {s:.0f} วินาที — ตรวจสายและโหมดส่งข้อมูลต่อเนื่อง",
    "Balance data resumed": "ได้รับข้อมูลจากตราชั่งอีกครั้ง",
    "Reading failed: {error} — check the connection in Settings": "การอ่านข้อมูลล้มเหลว: {error} — ตรวจการเชื่อมต่อที่หน้าตั้งค่า",
    "Source did not close cleanly: {error}": "ปิดแหล่งข้อมูลไม่สมบูรณ์: {error}",
    "Cannot start the test: {error}": "เริ่มการทดสอบไม่ได้: {error}",
    "Step {i}/{n} started: target {rate:g} ml/h, tolerance ±{tol:g}%": "เริ่มขั้น {i}/{n}: rate {rate:g} ml/h เกณฑ์ ±{tol:g}%",
    "Result saved to {path}": "บันทึกผลที่ {path}",
    "Could not save the result: {error}": "บันทึกผลไม่สำเร็จ: {error}",
    "Step finished: {verdict} (error {error:+.2f}%)": "จบขั้นทดสอบ: {verdict} (คลาดเคลื่อน {error:+.2f}%)",
    "Test stopped by user": "ผู้ใช้หยุดการทดสอบ",

    # ---------------------------------------------------------------- เพิ่มในรอบ 0.3
    "Test": "ทดสอบ",
    "All": "ทั้งหมด",
    "Job": "งาน",
    "Serial": "Serial",
    "Code": "รหัส",
    "Recent": "ล่าสุด",
    "Add": "เพิ่ม",
    "Delete": "ลบ",
    "Discard": "ไม่เก็บ",
    "Keep result": "เก็บผล",
    "Keep?": "เก็บไหม?",
    "Keep this result?": "เก็บผลนี้ไหม?",
    "stable": "นิ่ง",
    "unstable": "ไม่นิ่ง",
    "passed": "ผ่าน",
    "did not pass": "ไม่ผ่าน",
    "Self-check": "Self-check",
    "Syringe / IV set": "Syringe / ชุดสาย",
    "Liquid temperature (°C)": "อุณหภูมิของเหลว (°C)",
    "Brand and type — part of the pump profile": "ยี่ห้อและชนิด — เป็นส่วนหนึ่งของโปรไฟล์ปั๊ม",
    "Used to convert g to ml": "ใช้แปลง g เป็น ml",
    "Type to search devices tested before…": "พิมพ์เพื่อค้นหาเครื่องที่เคยทดสอบ…",
    "Show the most recently tested devices": "แสดงเครื่องที่ทดสอบล่าสุด",
    "No matching device": "ไม่พบเครื่องที่ตรงกัน",
    "Add another item…": "เพิ่มรายการอื่น…",
    "Accessories": "อุปกรณ์ที่มากับเครื่อง",
    "Parts replaced": "อะไหล่ที่เปลี่ยน",
    "Accessories received with the device": "อุปกรณ์ที่มากับเครื่อง",
    "Step 1 of 4 · Device and job details": "ขั้น 1 จาก 4 · ข้อมูลเครื่องและงาน",
    "Step 2 of 4 · Device check": "ขั้น 2 จาก 4 · ตรวจเครื่อง",
    "Tick what came with the device and what was replaced": "ติ๊กอุปกรณ์ที่มากับเครื่อง และอะไหล่ที่เปลี่ยน",
    "Step 3 of 4 · Choose the test mode": "ขั้น 3 จาก 4 · เลือกโหมดการทดสอบ",
    "Step 4 of 4 · {mode} settings": "ขั้น 4 จาก 4 · ตั้งค่า {mode}",
    "From the pump profile": "จากโปรไฟล์ปั๊ม",
    "Measure the pump cycle before each rate": "วัดรอบปั๊มก่อนเริ่มทุก rate",
    "Manual (values in Settings)": "กำหนดเอง (ค่าในหน้าตั้งค่า)",
    "Pump profile found: {ml:.3f} ml per cycle from {n} earlier runs.": "พบโปรไฟล์ปั๊ม: {ml:.3f} ml ต่อรอบ จากการทดสอบ {n} ครั้ง",
    "No profile for this pump yet — the pump cycle will be measured before each rate and saved as its profile.":
        "ยังไม่มีโปรไฟล์ของปั๊มนี้ — โปรแกรมจะวัดรอบปั๊มก่อนเริ่มแต่ละ rate แล้วบันทึกเป็นโปรไฟล์",
    "New pump model": "ปั๊มรุ่นใหม่",
    "There is no pump profile for this brand, model and IV set yet.": "ยังไม่มีโปรไฟล์ของ ยี่ห้อ รุ่น และชุดสายนี้",
    "The program can measure the pump cycle before each rate (this adds a short wait of about three pump cycles) and remember it, so later tests of this pump start without that wait.":
        "โปรแกรมวัดรอบปั๊มก่อนเริ่มแต่ละ rate ได้ (ต้องรอเพิ่มประมาณ 3 รอบปั๊ม) แล้วจำไว้ ครั้งต่อไปที่ทดสอบปั๊มนี้จะเริ่มได้เลยโดยไม่ต้องรอ",
    "Brand and model are empty, so the result cannot be remembered for next time.": "ยังไม่ได้กรอกยี่ห้อและรุ่น จึงจำผลไว้ใช้ครั้งหน้าไม่ได้",
    "Measure and learn": "วัดและจำไว้",
    "Use manual sizes": "ใช้ค่ากำหนดเอง",
    "Enter the device details, choose a mode, then set up the measurement.": "กรอกข้อมูลเครื่อง เลือกโหมด แล้วตั้งค่าการวัด",
    "Window sizes: manual (Settings)": "ขนาดหน้าต่าง: กำหนดเอง (หน้าตั้งค่า)",
    "Pump profile: {ml:.3f} ml per cycle ({n} runs)": "โปรไฟล์ปั๊ม: {ml:.3f} ml ต่อรอบ ({n} ครั้ง)",
    "Pump cycle is measured before each rate": "จะวัดรอบปั๊มก่อนเริ่มแต่ละ rate",
    "Density from {temp:g} °C": "ความหนาแน่นจากอุณหภูมิ {temp:g} °C",
    "Self-check correction: {rate:+.1f} mg/h": "ค่าแก้จาก self-check: {rate:+.1f} mg/h",
    "Measure evaporation and balance drift with the pump stopped": "วัดการระเหยและการไหลของค่าตราชั่ง ขณะปั๊มหยุด",
    "No self-check today": "วันนี้ยังไม่ได้ทำ self-check",
    "Self-check today: {rate:+.1f} mg/h": "self-check วันนี้: {rate:+.1f} mg/h",
    "Self-check today did not pass": "self-check วันนี้ไม่ผ่าน",
    "The test is not finished. Stop it now?": "การทดสอบยังไม่เสร็จ ต้องการหยุดเดี๋ยวนี้หรือไม่?",
    "The unfinished test will not be saved.": "การทดสอบที่ยังไม่เสร็จจะไม่ถูกบันทึก",
    "Pre-run — waiting for stable flow (variation {v} / limit {limit} %)": "ช่วงก่อนวัด — รอให้ flow นิ่ง (ความแกว่ง {v} / เกณฑ์ {limit} %)",
    "Finished — choose whether to keep this result.": "จบแล้ว — เลือกว่าจะเก็บผลนี้หรือไม่",
    "Result not kept. Press Start to run this step again.": "ไม่เก็บผล กดเริ่มเพื่อทดสอบขั้นนี้ใหม่",
    "Incomplete result saved. Press Start to run this step again.": "บันทึกผลที่ไม่ครบแล้ว กดเริ่มเพื่อทดสอบขั้นนี้ใหม่",
    "Step {i}/{n} saved. Set the pump to {rate:g} ml/h, then press Start.": "บันทึกขั้น {i}/{n} แล้ว ตั้งปั๊มที่ {rate:g} ml/h แล้วกดเริ่ม",
    "Step {i}/{n} · {rate:g} ml/h": "ขั้น {i}/{n} · {rate:g} ml/h",
    "This test was stopped before it finished. If kept, it is saved as incomplete and the step still has to be run again.":
        "การทดสอบนี้ถูกหยุดก่อนครบ ถ้าเก็บ จะบันทึกเป็นผลที่ไม่ครบ และยังต้องทดสอบขั้นนี้ใหม่",
    "Discard deletes this data permanently. Pressing Start afterwards repeats this step.":
        "ไม่เก็บ = ลบข้อมูลนี้ถาวร แล้วกดเริ่มเพื่อทดสอบขั้นนี้ซ้ำ",
    "Self-check measures how much the weight changes by itself (evaporation and balance drift).\n\n1. Set up the beaker exactly as for a test, with liquid in it.\n2. Stop the pump.\n3. Do not touch the bench for {min:g} minutes.\n\nIf it passes, the measured rate is used to correct every test for the rest of today.\n\nStart now?":
        "Self-check วัดว่าน้ำหนักเปลี่ยนเองเท่าไร (การระเหย และการไหลของค่าตราชั่ง)\n\n1. จัดบีกเกอร์ให้เหมือนตอนทดสอบจริง มีของเหลวอยู่\n2. หยุดปั๊ม\n3. อย่าแตะโต๊ะ {min:g} นาที\n\nถ้าผ่าน ค่าที่วัดได้จะถูกใช้แก้ผลของทุกการทดสอบในวันนี้\n\nเริ่มเลยไหม?",
    "Self-check — pump stopped, do not touch the beaker · {time} left": "Self-check — หยุดปั๊ม อย่าแตะบีกเกอร์ · เหลือ {time}",
    "Self-check was cancelled.": "ยกเลิก self-check แล้ว",
    "Self-check passed — it will be applied to today's tests.": "Self-check ผ่าน — จะใช้แก้ผลการทดสอบของวันนี้",
    "Self-check did not pass and will not be used.": "Self-check ไม่ผ่าน จะไม่ถูกนำไปใช้",
    "Baseline {rate:+.1f} ± {se:.1f} mg/h · balance noise {sd:.2f} mg": "อัตราพื้นฐาน {rate:+.1f} ± {se:.1f} mg/h · noise ตราชั่ง {sd:.2f} mg",
    "Not enough data": "ข้อมูลไม่พอ",
    "Stopped before the set duration": "หยุดก่อนครบเวลาที่ตั้ง",
    "Rate changed between the first and second half (not settled)": "อัตราของครึ่งแรกกับครึ่งหลังต่างกัน (ยังไม่นิ่ง)",
    "Rate is too large to be evaporation or drift": "อัตรามากเกินกว่าจะเป็นการระเหยหรือการไหลของค่า",
    "Delete result": "ลบผลการทดสอบ",
    "Delete this result and its data permanently?\n{date} · {rate:g} ml/h": "ลบผลนี้และข้อมูลของมันถาวรหรือไม่?\n{date} · {rate:g} ml/h",
    "Replay recorded file": "เล่นซ้ำไฟล์ที่บันทึกไว้",
    "Balance output": "การส่งค่าของตราชั่ง",
    "Auto detect": "ตรวจอัตโนมัติ",
    "Stream (balance sends by itself)": "Stream (ตราชั่งส่งเอง)",
    "Ask for each value": "ถามค่าทีละครั้ง",
    "Auto listens first; if the balance is silent it asks for values instead": "โหมดอัตโนมัติจะฟังก่อน ถ้าตราชั่งเงียบจะเปลี่ยนเป็นถามค่าเอง",
    "Ask every": "ถามทุก",
    "Replay file": "ไฟล์สำหรับเล่นซ้ำ",
    "A raw.csv recorded earlier (time, weight)": "ไฟล์ raw.csv ที่บันทึกไว้ (เวลา, น้ำหนัก)",
    "Replay speed": "ความเร็วเล่นซ้ำ",
    "Used only when no liquid temperature is entered in the test form": "ใช้เฉพาะเมื่อไม่ได้กรอกอุณหภูมิของเหลวในฟอร์มทดสอบ",
    "Manual window sizes — used when a test is set to manual, or the pump cycle cannot be found":
        "ขนาดหน้าต่างแบบกำหนดเอง — ใช้เมื่อการทดสอบตั้งเป็นกำหนดเอง หรือหารอบปั๊มไม่ได้",
    "Window / pump cycle": "หน้าต่าง / คาบรอบปั๊ม",
    "Size of both windows as a fraction of the pump cycle (profile or measured)": "ขนาดหน้าต่างทั้งสองเป็นสัดส่วนของคาบรอบปั๊ม (จากโปรไฟล์หรือที่วัดได้)",
    "Stop looking for the cycle after": "เลิกหารอบปั๊มเมื่อเกิน",
    "An allowance for the balance resolution is added automatically at low rates": "ที่ rate ต่ำ โปรแกรมจะเผื่อเกณฑ์ตามความละเอียดของตราชั่งให้อัตโนมัติ",
    "Duration": "ระยะเวลา",
    "Max change between halves": "ความต่างสูงสุดระหว่างสองครึ่ง",
    "The rate of the first and second half must agree, otherwise the bench has not settled": "อัตราของครึ่งแรกและครึ่งหลังต้องใกล้กัน ไม่งั้นแปลว่าโต๊ะ/บีกเกอร์ยังไม่นิ่ง",
    "Largest believable rate": "อัตราสูงสุดที่ยอมรับได้",
    "Device check lists": "รายการตรวจเครื่อง",
    "One item per line": "บรรทัดละ 1 รายการ",
    "Replaceable parts": "อะไหล่",
    "Evaporation": "การระเหย",
    "Find the balance automatically": "ค้นหาตราชั่งอัตโนมัติ",
    "Tries the ports and the usual port settings until the balance answers": "ไล่ลองพอร์ตและค่าพอร์ตที่ใช้กันทั่วไป จนกว่าตราชั่งจะตอบ",
    "Trying {what}…": "กำลังลอง {what}…",
    "Found: {port} · {baud} {bits}{parity}{stop} · {mode} · about {rate:.0f} values/s — press Save to use it.   Sample: {line}":
        "พบ: {port} · {baud} {bits}{parity}{stop} · {mode} · ประมาณ {rate:.0f} ค่า/วินาที — กดบันทึกเพื่อใช้   ตัวอย่าง: {line}",
    "Search failed: {error}": "ค้นหาไม่สำเร็จ: {error}",
    "No balance answered. Check the cable, power and the balance's output setting.": "ไม่มีตราชั่งตอบ ตรวจสาย ไฟ และการตั้งค่าการส่งข้อมูลของตราชั่ง",
    "Instantaneous flow": "Flow ขณะนั้น",
    "Result saved": "บันทึกผลแล้ว",
    "Result discarded — press Start to run this step again": "ไม่เก็บผล — กดเริ่มเพื่อทดสอบขั้นนี้ใหม่",
    "Pump profile updated: {ml:.3f} ml per cycle ({n} runs)": "อัปเดตโปรไฟล์ปั๊ม: {ml:.3f} ml ต่อรอบ ({n} ครั้ง)",
    "Self-check started ({min:g} min) — pump stopped, do not touch the beaker": "เริ่ม self-check ({min:g} นาที) — หยุดปั๊ม อย่าแตะบีกเกอร์",
    "Density {rho:.4f} g/ml from {temp:g} °C": "ความหนาแน่น {rho:.4f} g/ml จากอุณหภูมิ {temp:g} °C",
    "Using today's self-check: baseline {rate:+.1f} mg/h": "ใช้ self-check ของวันนี้: อัตราพื้นฐาน {rate:+.1f} mg/h",
    "Window sizes from the pump profile: {n} points (cycle about {p:.1f} s)": "ขนาดหน้าต่างจากโปรไฟล์ปั๊ม: {n} จุด (รอบปั๊มประมาณ {p:.1f} วินาที)",
    "Self-check {verdict}: baseline {rate:+.1f} ± {se:.1f} mg/h, noise {sd:.2f} mg": "Self-check {verdict}: อัตราพื้นฐาน {rate:+.1f} ± {se:.1f} mg/h, noise {sd:.2f} mg",
    "Pump cycle at {rate:g} ml/h ({p:.1f} s) does not fit the profile's volume per cycle — remembered for this rate only":
        "รอบปั๊มที่ {rate:g} ml/h ({p:.1f} วินาที) ไม่ตรงกับปริมาตรต่อรอบของโปรไฟล์ — จำไว้ใช้เฉพาะ rate นี้",
    "Pump cycle ({p:.1f} s) differs from earlier runs at this rate and was not remembered":
        "รอบปั๊ม ({p:.1f} วินาที) ต่างจากที่เคยวัดที่ rate นี้ จึงไม่ได้จำไว้",
    "Select all": "เลือกทั้งหมด",
    "{n} of {total} ticked": "ติ๊ก {n} จาก {total}",
    "Add an item for {device}…": "เพิ่มรายการของ {device}…",
    "Enter brand and model in step 1 to keep a list for each model.": "กรอกยี่ห้อและรุ่นในขั้น 1 เพื่อให้โปรแกรมจำรายการแยกตามรุ่น",
    "★ = used with {device} before ({n} items). Right-click a ★ item to remove it from this model.":
        "★ = เคยใช้กับ {device} ({n} รายการ) คลิกขวาที่รายการ ★ เพื่อลบออกจากรุ่นนี้",
    "First time for {device} — what you tick or add is remembered for this model.":
        "ครั้งแรกของ {device} — สิ่งที่ติ๊กหรือเพิ่มจะถูกจำไว้กับรุ่นนี้",
    "Ticked {n} times for this model": "เคยติ๊ก {n} ครั้งกับรุ่นนี้",
    "Remove from this model": "ลบออกจากรุ่นนี้",

    # ---------------------------------------------------------------- tools/capture_raw.py
    "Record raw balance lines with send/receive times to CSV": "เก็บบรรทัดดิบจากตราชั่งพร้อมเวลาส่ง/รับ ลง CSV",
    "Short name added to the file name (e.g. inf50)": "ชื่อสั้นต่อท้ายชื่อไฟล์ (เช่น inf50)",
    "Stop after this many minutes (default: until Ctrl+C)": "หยุดเมื่อครบกี่นาที (ไม่ใส่ = จนกด Ctrl+C)",
    "Poll interval in seconds": "จังหวะถามค่า (วินาที)",
    "Poll command (CR LF is added)": "คำสั่งถามค่า (ต่อท้าย CR LF ให้เอง)",
    "Free text saved in the file header": "ข้อความบันทึกไว้ในหัวไฟล์",
    "Re-read an existing capture file with the current parser": "อ่านไฟล์ที่เก็บไว้ซ้ำด้วยตัวอ่านบรรทัดปัจจุบัน",
    "latency": "หน่วง",
    "rows": "แถว",
    "unreadable": "อ่านไม่ได้",
    "Saved: {path}": "บันทึกแล้ว: {path}",
    "Could not open {port}: {error}": "เปิด {port} ไม่ได้: {error}",
    "If another program (e.g. ARGOS) is using the port, close it first.":
        "ถ้ามีโปรแกรมอื่น (เช่น ARGOS) ใช้พอร์ตอยู่ ให้ปิดโปรแกรมนั้นก่อน",
    "Detected mode: {mode} · sample line: {line}": "ตรวจพบโหมด: {mode} · บรรทัดตัวอย่าง: {line}",
    "Recording to {path}": "กำลังบันทึกลง {path}",
    "Press Ctrl+C to stop.": "กด Ctrl+C เพื่อหยุด",
    "The balance did not send or answer anything readable": "ตราชั่งไม่ได้ส่งหรือตอบค่าที่อ่านได้เลย",
    "incomplete": "ไม่ครบ",
    "Wait for a full answer up to this many seconds": "รอคำตอบเต็มบรรทัดได้นานสุดกี่วินาที",
    "Line format": "รูปแบบบรรทัด",

    # ---------------------------------------------------------------- ความถูกต้องของการอ่านตราชั่ง
    "Wait for a full answer up to": "รอคำตอบเต็มบรรทัดได้นานสุด",
    "Lines that are still incomplete after this are discarded (GF-300 answers in about 0.2 s)":
        "บรรทัดที่ยังไม่ครบเมื่อพ้นเวลานี้จะถูกทิ้ง (GF-300 ตอบในราว 0.2 วินาที)",
    "Strict A&D only accepts complete lines; the looser formats can misread a cut-off line":
        "A&D แบบเข้มงวดรับเฉพาะบรรทัดที่ครบ แบบหลวมอาจอ่านบรรทัดที่ขาดเป็นน้ำหนักผิด",
    "A&D (strict, recommended)": "A&D (เข้มงวด แนะนำ)",
    "Auto (A&D, otherwise first number)": "อัตโนมัติ (A&D ไม่งั้นใช้ตัวเลขตัวแรก)",
    "First number in the line": "ตัวเลขตัวแรกในบรรทัด",
    "A raw.csv or capture file recorded earlier (time, weight)": "ไฟล์ raw.csv หรือไฟล์ capture ที่บันทึกไว้ (เวลา, น้ำหนัก)",
    "Balance reading: {ok} points, {partial} incomplete lines, {rejected} rejected lines, "
    "{timeouts} no answer, {queued} late timestamps, longest queue {backlog}":
        "การอ่านตราชั่ง: {ok} จุด, บรรทัดไม่ครบ {partial}, บรรทัดถูกปฏิเสธ {rejected}, "
        "ไม่ตอบ {timeouts}, เวลาอาจช้า {queued}, คิวค้างสูงสุด {backlog}",
    "Check balance reading accuracy through the same path as the main program":
        "ตรวจความถูกต้องของการอ่านตราชั่ง ผ่านเส้นทางเดียวกับโปรแกรมหลัก",
    "Simulate the program freezing this many seconds every 10 s": "จำลองโปรแกรมค้างกี่วินาที ทุก 10 วินาที",
    "Points: {n} · rate {hz:.2f} Hz · longest gap {gap:.2f} s · time going backwards: {back}":
        "จุด: {n} · อัตรา {hz:.2f} Hz · ช่องว่างยาวสุด {gap:.2f} s · เวลาถอยหลัง: {back}",
    "Answer time (poll): last {last:.0f} ms · longest {max:.0f} ms": "เวลาตอบ (poll): ล่าสุด {last:.0f} ms · นานสุด {max:.0f} ms",
    "Incomplete lines {partial} · rejected {rejected} · no answer {timeouts} · late timestamps {queued} · "
    "longest queue {backlog}":
        "บรรทัดไม่ครบ {partial} · ถูกปฏิเสธ {rejected} · ไม่ตอบ {timeouts} · เวลาอาจช้า {queued} · คิวค้างสูงสุด {backlog}",
    "Clock check: perf_counter {perf:.3f} s vs Windows clock {wall:.3f} s ({ppm:+.0f} ppm)":
        "ตรวจนาฬิกา: perf_counter {perf:.3f} s เทียบนาฬิกา Windows {wall:.3f} s ({ppm:+.0f} ppm)",
    "Weight {a:.3f} → {b:.3f} g · slope = {flow:.3f} ml/h · jumps > 50 mg: {jumps}":
        "น้ำหนัก {a:.3f} → {b:.3f} g · ความชัน = {flow:.3f} ml/h · กระโดดเกิน 50 mg: {jumps}",
    # ---------------------------------------------------------------- แถบติดตามขั้น/ช่วง
    "STEP": "ขั้น",
    "No test plan yet": "ยังไม่มีแผนทดสอบ",
    "Ready — press Start": "พร้อม — กดเริ่ม",
    "Phase {i}/{n}": "ช่วง {i}/{n}",
    "Connect": "เชื่อมต่อ",
    "Prepare": "เตรียม",
    "First cycle": "รอบแรก",
    "Measure": "วัดจริง",
    "Review": "สรุปผล",
    "Connecting to the balance": "กำลังเชื่อมต่อตราชั่ง",
    "Pre-run — not counted in the result": "ช่วงก่อนวัด — ไม่นำไปคิดผล",
    "Filling the calculation window": "กำลังเติมหน้าต่างคำนวณ",
    "Waiting for the first complete pump cycle": "รอรอบปั๊มรอบแรกให้ครบ",
    "Measuring": "กำลังวัด",
    "Choose whether to keep the result": "เลือกว่าจะเก็บผลหรือไม่",
    "Self-check — pump stopped, do not touch the beaker": "Self-check — หยุดปั๊ม ห้ามแตะบีกเกอร์",
    "Self-check result": "ผล self-check",
    "ended with an error": "จบด้วยข้อผิดพลาด",
    "result not kept": "ไม่เก็บผล",
    "incomplete result saved": "บันทึกผลไม่ครบแล้ว",
    "saved": "บันทึกแล้ว",
    "Self-check passed": "Self-check ผ่าน",
    "Self-check did not pass": "Self-check ไม่ผ่าน",
    "{m:g} min · pump stopped": "{m:g} นาที · หยุดปั๊ม",

    # ---------------------------------------------------------------- กราฟ flow รายช่วง
    "Steps": "ขั้นบันได",
    "Points": "จุด",
    "Overall mean": "ค่าเฉลี่ยรวม",
    "Moving average": "Moving avg",
    "Click to hide this line": "กดเพื่อซ่อนเส้นนี้",
    "Click to show this line": "กดเพื่อแสดงเส้นนี้",
    "Pump-cycle capture": "การจับรอบปั๊ม",
    "Paired cycles (peak→peak and valley→valley)": "จับรอบคู่ (ยอด→ยอด และ ก้น→ก้น)",
    "Single cycle (one reference point)": "จับรอบเดียว (จุดอ้างอิงเดียว)",
    "Paired runs two chains of intervals side by side; single keeps only chain A":
        "รอบคู่วัด 2 สายคู่กัน · รอบเดียวใช้เฉพาะสาย A",

    "Change must exceed balance noise by": "ความต่างต้องเกิน noise ของตราชั่ง",
    "Not settled = the two halves differ by more than this many times their uncertainty (from 10 blocks)":
        "ไม่นิ่ง = ครึ่งแรกกับครึ่งหลังต่างกันเกินกี่เท่าของความไม่แน่นอน (คิดจาก 10 ช่วงย่อย)",
    "Always accept a change between halves up to": "ยอมรับความต่างครึ่งแรก/หลังเสมอ ถ้าไม่เกิน",
    "Smaller differences than this never count as unsettled — they are too small to matter":
        "ต่างกันน้อยกว่านี้ไม่ถือว่าไม่นิ่ง — เล็กจนไม่มีผลต่อการทดสอบ",
    "Result: OK": "ผล: ปกติ",
    "Result: check the items above": "ผล: ตรวจรายการข้างบน",

    # ---------------------------------------------------------------- ค่าแก้ g -> ml (ISO 4787)
    "Flow error (net)": "ค่าคลาดเคลื่อน (สุทธิ)",
    "Uncorrected": "ก่อนแก้",
    "Uncorrected (%)": "ก่อนแก้ (%)",
    "Uncorrected (1 g = 1 ml)": "ก่อนแก้ (1 g = 1 ml)",
    "Uncorrected flow Q₀": "Flow ก่อนแก้ Q₀",
    "Uncorrected error": "ค่าคลาดเคลื่อนก่อนแก้",
    "Correction factor Z": "ปัจจัยแก้ Z",
    "Factor Z": "ปัจจัย Z",
    "g → ml correction (audit)": "ค่าแก้ g → ml (สอบย้อนหลัง)",
    "Liquid temperature": "อุณหภูมิของเหลว",
    "Water density ρw": "ความหนาแน่นน้ำ ρw",
    "Air temperature": "อุณหภูมิอากาศ",
    "Humidity": "ความชื้น",
    "Air pressure": "ความดันอากาศ",
    "Air density ρa": "ความหนาแน่นอากาศ ρa",
    "Weight density ρb": "ความหนาแน่นตุ้มน้ำหนัก ρb",
    "Air buoyancy": "แรงลอยตัวอากาศ",
    "Not applied": "ไม่ได้ใช้",
    "Not applied (result from an earlier version)": "ไม่ได้แก้ (ผลจากโปรแกรมรุ่นก่อน)",
    "(derived)": "(คำนวณย้อนจากสูตร)",
    "Check (Q₀ − B) × Z": "ตรวจสูตร (Q₀ − B) × Z",
    "Self-check B": "Self-check B",
    "Standard": "มาตรฐาน",
    "Note": "หมายเหตุ",
    "entered": "กรอกในฟอร์ม",
    "= liquid temperature": "= อุณหภูมิของเหลว",
    "from temperature": "จากอุณหภูมิ",
    "Water density for g → ml": "ใช้หาความหนาแน่นน้ำ (g → ml)",
    "Air buoyancy — blank = Settings": "ใช้แก้แรงลอยตัว — ว่าง = ค่าในตั้งค่า",
    "Air temperature (°C)": "อุณหภูมิอากาศ (°C)",
    "Blank = liquid temperature": "ว่าง = ใช้อุณหภูมิของเหลว",
    "Air pressure (hPa)": "ความดันอากาศ (hPa)",
    "Blank = Settings": "ว่าง = ค่าในตั้งค่า",
    "Air buoyancy correction (ISO 4787)": "แก้แรงลอยตัวอากาศ (ISO 4787)",
    "g → ml with the Z factor: water density from liquid temperature, air density from "
    "air temperature, humidity and pressure (about +0.1 %)":
        "แปลง g → ml ด้วยปัจจัย Z: ความหนาแน่นน้ำจากอุณหภูมิของเหลว ความหนาแน่นอากาศจาก"
        "อุณหภูมิอากาศ ความชื้น และความดัน (ผลราว +0.1 %)",
    "Humidity if not entered": "ความชื้น เมื่อไม่ได้กรอก",
    "Air pressure if not entered": "ความดันอากาศ เมื่อไม่ได้กรอก",
    "Density of the balance's reference weights": "ความหนาแน่นตุ้มน้ำหนักที่สอบเทียบตราชั่ง",
    "Stainless steel calibration weights = 8.0 g/ml (OIML R111)": "ตุ้มน้ำหนักเหล็กกล้าไร้สนิม = 8.0 g/ml (OIML R111)",
    "Density {rho:.5f} g/ml from {temp:g} °C": "ความหนาแน่น {rho:.5f} g/ml จาก {temp:g} °C",
    "Density {rho:.5f} g/ml from Settings (no liquid temperature)":
        "ความหนาแน่น {rho:.5f} g/ml จากค่าตั้ง (ไม่ได้กรอกอุณหภูมิของเหลว)",
    "g → ml: Z = {z:.5f} ml/g (ISO 4787, {t:g} °C · {rh:g} %RH · {p:g} hPa)":
        "g → ml: Z = {z:.5f} ml/g (ISO 4787, {t:g} °C · {rh:g} %RH · {p:g} hPa)",
    "g → ml: 1/density = {z:.5f} ml/g (air buoyancy off)": "g → ml: 1/ความหนาแน่น = {z:.5f} ml/g (ปิดการแก้แรงลอยตัว)",
    "Air density {rho:.4f} kg/m³ ({t:g} °C, {rh:g} %RH, {p:g} hPa) · Z = {z:.5f} ml/g":
        "ความหนาแน่นอากาศ {rho:.4f} kg/m³ ({t:g} °C, {rh:g} %RH, {p:g} hPa) · Z = {z:.5f} ml/g",
    "Liquid temperature is outside 0–40 °C; the density in Settings was used":
        "อุณหภูมิของเหลวอยู่นอกช่วง 0–40 °C จึงใช้ความหนาแน่นในหน้าตั้งค่า",
    "No liquid temperature entered; the density in Settings was used":
        "ไม่ได้กรอกอุณหภูมิของเหลว จึงใช้ความหนาแน่นในหน้าตั้งค่า",
    "Humidity must be 0–100 %RH; the value in Settings was used": "ความชื้นต้องอยู่ระหว่าง 0–100 %RH จึงใช้ค่าในหน้าตั้งค่า",
    "Air pressure must be 500–1200 hPa; the value in Settings was used":
        "ความดันอากาศต้องอยู่ระหว่าง 500–1200 hPa จึงใช้ค่าในหน้าตั้งค่า",
    "Air conditions are outside the range of the air-density formula (10–30 °C, "
    "900–1100 hPa, below 80 %RH); the effect on the result is still very small":
        "สภาพอากาศอยู่นอกช่วงของสูตรความหนาแน่นอากาศ (10–30 °C, 900–1100 hPa, ต่ำกว่า 80 %RH) "
        "แต่ผลต่อค่าที่วัดยังเล็กมาก",
    # ---------------------------------------------------------------- ชนิดเครื่อง / รุ่นใหม่ / ปรับหน้าต่าง / ลายนิ้วมือ
    "Volumetric pump with an IV set · peak detection by default": "ปั๊มใช้ชุดสายให้น้ำเกลือ · ค่าเริ่มต้นจับรอบปั๊ม (peak)",
    "Syringe driver · time-based intervals by default": "ปั๊มกระบอกฉีดยา · ค่าเริ่มต้นจับตามเวลา",
    "No pump-cycle data for this model yet": "รุ่นนี้ยังไม่มีข้อมูลรอบปั๊ม",
    "{device} has not been measured before. Peak detection needs the pump cycle period, "
    "and the period gets longer as the rate gets lower, so measuring it first takes "
    "about three pump cycles:":
        "{device} ยังไม่เคยวัด — การจับ peak ต้องรู้คาบรอบปั๊มก่อน และคาบยาวขึ้นเมื่อ rate ต่ำลง "
        "การวัดคาบจึงต้องรอประมาณ 3 รอบปั๊ม:",
    "This pump": "ปั๊มนี้",
    "{s:.0f} s": "{s:.0f} วินาที",
    "{m:.0f} min": "{m:.0f} นาที",
    "Run the highest rate first (recommended)": "รัน rate สูงสุดก่อน (แนะนำ)",
    "Order becomes {order} ml/h. The first rate learns the volume per cycle within seconds; "
    "the lower rates then start without waiting.":
        "ลำดับจะเป็น {order} ml/h — rate แรกเรียนรู้ปริมาตรต่อรอบได้ในไม่กี่วินาที แล้ว rate ต่ำเริ่มได้ทันทีไม่ต้องรอ",
    "Measure the cycle before each rate, in this order": "วัดคาบก่อนแต่ละ rate ตามลำดับเดิม",
    "Measure the cycle at the first rate (already highest first)": "วัดคาบที่ rate แรก (เรียงสูงไปต่ำอยู่แล้ว)",
    "Nothing changes in the plan; low rates wait longer before measuring starts.":
        "แผนไม่เปลี่ยน — rate ต่ำต้องรอนานกว่าจะเริ่มวัด",
    "Use a default for this model for now": "ใช้ค่าเริ่มต้นของรุ่นนี้ไปก่อน",
    "Peak detection starts at once using the volume per cycle below. The first real measurement "
    "of this model replaces it.":
        "เริ่มจับ peak ได้ทันทีด้วยปริมาตรต่อรอบด้านล่าง — การวัดจริงครั้งแรกของรุ่นนี้จะแทนที่ค่านี้",
    "Enter brand and model in step 1 to keep a default for this model.": "กรอกยี่ห้อและรุ่นในขั้นที่ 1 เพื่อจำค่าเริ่มต้นของรุ่นนี้",
    "Use manual window sizes (Settings)": "ใช้ขนาดหน้าต่างกำหนดเอง (หน้าตั้งค่า)",
    "Same window size at every rate — only suitable if you know it fits.": "ขนาดเดียวทุก rate — ใช้เมื่อรู้ว่าเหมาะเท่านั้น",
    "Volume per cycle": "ปริมาตรต่อรอบ",
    "Back to settings": "กลับไปแก้ค่า",
    "Model default: {ml:.3f} ml per cycle (not measured yet)": "ค่าเริ่มต้นของรุ่น: {ml:.3f} ml ต่อรอบ (ยังไม่เคยวัด)",
    "This model uses a default of {ml:.3f} ml per cycle until it has been measured.":
        "รุ่นนี้ใช้ค่าเริ่มต้น {ml:.3f} ml ต่อรอบ จนกว่าจะได้วัดจริง",
    "Window sizes from this model's default volume per cycle (not measured yet): "
    "{n} points (cycle about {p:.1f} s)":
        "ขนาดหน้าต่างจากค่าเริ่มต้นของรุ่น (ยังไม่เคยวัด): {n} จุด (รอบละประมาณ {p:.1f} วินาที)",
    "Window / pump cycle {f:.2f} tuned from earlier tests of this model": "หน้าต่าง/คาบ {f:.2f} ปรับจากการทดสอบก่อนหน้าของรุ่นนี้",
    "Tuning the peak-detection window from stored tests in the background…": "กำลังปรับหน้าต่างจับ peak จากข้อมูลที่เก็บไว้ (เบื้องหลัง)…",
    "{rate:g} ml/h: window = {f:.2f} × cycle (score {s:.3f}; {c:.2f} × cycle scored {cs}) from {n} tests":
        "{rate:g} ml/h: หน้าต่าง = {f:.2f} × คาบ (คะแนน {s:.3f}; ค่าเดิม {c:.2f} × คาบ ได้ {cs}) จาก {n} การทดสอบ",
    "{rate:g} ml/h: no window size found the pump cycles reliably ({n} tests)":
        "{rate:g} ml/h: ไม่มีขนาดหน้าต่างไหนจับรอบได้สม่ำเสมอ ({n} การทดสอบ)",
    "Tune peak window": "ปรับหน้าต่างจับ peak",
    "Replay the stored tests of the selected pump model and find the window size "
    "that captures its pump cycles most consistently":
        "เล่นข้อมูลที่เก็บไว้ของรุ่นที่เลือกซ้ำ แล้วหาขนาดหน้าต่างที่จับรอบปั๊มได้สม่ำเสมอที่สุด",
    "Wait until the running test has finished.": "รอให้การทดสอบที่กำลังรันเสร็จก่อน",
    "No completed pump-cycle tests with raw data for {device}.": "ไม่มีการทดสอบแบบจับรอบปั๊มที่ครบและมีข้อมูลดิบของ {device}",
    "Replaying stored tests of {device}…": "กำลังเล่นข้อมูลของ {device} ซ้ำ…",
    "{device} — used from the next test:": "{device} — ใช้ตั้งแต่การทดสอบครั้งถัดไป:",
    "Data integrity": "ความครบถ้วนของข้อมูล",
    "✓ {n} files unchanged since saved (SHA-256)": "✓ {n} ไฟล์ ไม่ถูกแก้ตั้งแต่บันทึก (SHA-256)",
    "✗ changed: {files}": "✗ ถูกแก้: {files}",
    "✗ missing: {files}": "✗ หายไป: {files}",
    "Not recorded (result from an earlier version)": "ไม่ได้บันทึกไว้ (ผลจากโปรแกรมรุ่นก่อน)",
    "Default volume per cycle (new models)": "ปริมาตรต่อรอบเริ่มต้น (รุ่นใหม่)",
    "Used to estimate the pump cycle of a model that has not been measured, and when the cycle "
    "cannot be found before measuring. Your pumps so far: 0.12–0.21 ml":
        "ใช้เดาคาบรอบปั๊มของรุ่นที่ยังไม่เคยวัด และเมื่อหาคาบไม่ได้ก่อนเริ่มวัด · ปั๊มที่เคยวัด: 0.12–0.21 ml",
    "Pump cycle period not found; window sizes were estimated from the default volume per cycle":
        "หาคาบรอบปั๊มไม่ได้ จึงเดาขนาดหน้าต่างจากปริมาตรต่อรอบเริ่มต้น",
    # ---------------------------------------------------------------- เกณฑ์ช่วงก่อนวัด / ช่องกรอกอัจฉริยะ
    "Automatic start · Infusion, pump-cycle capture": "เริ่มวัดอัตโนมัติ · Infusion จับรอบปั๊ม",
    "Automatic start · Infusion, time-based capture": "เริ่มวัดอัตโนมัติ · Infusion จับตามเวลา",
    "Automatic start · Syringe, time-based capture": "เริ่มวัดอัตโนมัติ · Syringe จับตามเวลา",
    "Infusion · pump-cycle capture": "Infusion · จับรอบปั๊ม",
    "Infusion · time-based capture": "Infusion · จับตามเวลา",
    "Syringe · time-based capture": "Syringe · จับตามเวลา",
    "Block length unit": "หน่วยของช่วงเทียบ",
    "Pump cycles (needs the pump cycle)": "รอบปั๊ม (ต้องรู้คาบรอบปั๊ม)",
    "Seconds": "วินาที",
    "Cycles per block": "จำนวนรอบต่อช่วง",
    "Lengthen each block to at least": "ยืดแต่ละช่วงให้น้ำหนักได้อย่างน้อย",
    "Round up to whole pump cycles": "ปัดเป็นจำนวนเต็มรอบปั๊ม",
    "Start anyway after": "เริ่มวัดเลยเมื่อรอครบ",
    "0 = wait until stable. Each model can have its own values (test wizard, step 4)":
        "0 = รอจนกว่าจะนิ่ง · แต่ละรุ่นตั้งค่าเฉพาะได้ (หน้าสร้างการทดสอบ ขั้นที่ 4)",
    "Stable-flow criteria": "เกณฑ์ flow นิ่ง",
    "Stable-flow criteria for this model": "เกณฑ์ flow นิ่งของรุ่นนี้",
    "{device} · {group}": "{device} · {group}",
    "Currently: defaults from Settings": "ตอนนี้: ใช้ค่าเริ่มต้นจากหน้าตั้งค่า",
    "Currently: values set for this model": "ตอนนี้: ใช้ค่าที่ตั้งไว้เฉพาะรุ่นนี้",
    "“Start anyway” begins measuring after this time even if the flow is not stable yet, and the "
    "result records that stability was not confirmed. 0 = wait until stable.":
        "“เริ่มวัดเลย” = ครบเวลานี้แล้วเริ่มวัดแม้ flow ยังไม่นิ่ง และผลจะบันทึกว่ายังไม่ยืนยันว่านิ่ง · 0 = รอจนกว่าจะนิ่ง",
    "Use defaults": "ใช้ค่าเริ่มต้น",
    "Save for this model": "บันทึกสำหรับรุ่นนี้",
    "Adjust for this model…": "ปรับสำหรับรุ่นนี้…",
    "Enter brand and model in step 1 to keep values for this model.": "กรอกยี่ห้อและรุ่นในขั้นที่ 1 เพื่อเก็บค่าของรุ่นนี้",
    "Stable-flow criteria: {group} ({source})": "เกณฑ์ flow นิ่ง: {group} ({source})",
    "Stable-flow criteria: {group} · {source} · ±{pct:g} % · {wait}": "เกณฑ์ flow นิ่ง: {group} · {source} · ±{pct:g} % · {wait}",
    "this model": "ค่าของรุ่นนี้",
    "defaults": "ค่าเริ่มต้น",
    "start anyway after {m:g} min": "เริ่มวัดเลยเมื่อรอครบ {m:g} นาที",
    "no time limit": "รอจนกว่าจะนิ่ง",
    "starts anyway in {time}": "จะเริ่มวัดเลยในอีก {time}",
    "At {rates} ml/h the data needed to confirm stable flow takes longer than the limit — "
    "measuring will start without confirmation (recorded with the result).":
        "ที่ {rates} ml/h ต้องใช้ข้อมูลนานกว่าเวลารอสูงสุดจึงจะยืนยันว่านิ่งได้ — จะเริ่มวัดโดยยังไม่ยืนยัน (บันทึกไว้กับผล)",
    "Measurement started before the flow was confirmed stable (maximum wait reached or started by hand)":
        "เริ่มวัดก่อนยืนยันว่า flow นิ่ง (ครบเวลารอสูงสุด หรือกดเริ่มเอง)",
    "Faint text is a suggestion from earlier tests — press Tab or Enter to accept it, "
    "↓ for more, Esc to ignore. Nothing is filled in until you accept.":
        "ตัวอักษรจางคือคำแนะนำจากงานที่เคยบันทึก — กด Tab หรือ Enter เพื่อรับ, ↓ ดูตัวเลือกอื่น, Esc ไม่เอา "
        "· ไม่มีอะไรถูกกรอกจนกว่าคุณจะกดรับ",
    # ---------------------------------------------------------------- Calibration รอบปั๊ม / ต่างจากข้อมูลเดิม
    "Calibration…": "Calibration…",
    "{n} pts ({f:.2f} × cycle)": "{n} จุด ({f:.2f} × คาบ)",
    "Learn this model's pump cycle again and replace its earlier data": "เรียนรู้รอบปั๊มของรุ่นนี้ใหม่ แทนที่ข้อมูลเดิม",
    "Calibrate the pump cycle again (replace this model's data)": "Calibration รอบปั๊มใหม่ (แทนที่ข้อมูลเดิมของรุ่นนี้)",
    "Calibration: the first rate measures the pump cycle; when its result is kept, this model's earlier "
    "pump-cycle data stops being used (kept for audit).":
        "Calibration: rate แรกวัดคาบรอบปั๊มก่อนเริ่ม เมื่อกดเก็บผลแล้ว ข้อมูลรอบปั๊มเดิมของรุ่นนี้จะเลิกใช้ (ยังเก็บไว้สอบย้อนหลัง)",
    "Pump cycle calibration": "Calibration รอบปั๊ม",
    "Calibrate the pump cycle again": "Calibration รอบปั๊มใหม่",
    "{device}: the first rate measures the pump cycle before it starts. When that result is kept, the earlier "
    "pump-cycle data and window sizes of this model are no longer used (they stay stored for audit). "
    "Each rate then gets its own window sizes again.":
        "{device}: rate แรกจะวัดคาบรอบปั๊มก่อนเริ่มวัด เมื่อกดเก็บผลแล้ว ข้อมูลรอบปั๊มและขนาดหน้าต่างเดิมของรุ่นนี้จะเลิกใช้ "
        "(ยังเก็บไว้สอบย้อนหลัง) แล้วแต่ละ rate จะได้ขนาดหน้าต่างของตัวเองใหม่",
    "What is stored now": "ข้อมูลที่จำไว้ตอนนี้",
    "Volume per cycle {ml:.3f} ml from {n} runs": "ปริมาตรต่อรอบ {ml:.3f} ml จาก {n} ครั้ง",
    "Last calibration {date}": "Calibration ล่าสุด {date}",
    "Nothing yet": "ยังไม่มี",
    "Rate": "Rate",
    "Regression window": "หน้าต่าง regression",
    "n̄ (peak left/right)": "n̄ (peak ซ้าย/ขวา)",
    "Run the rates from highest to lowest ({order} ml/h) — recommended": "รัน rate จากสูงไปต่ำ ({order} ml/h) — แนะนำ",
    "Use calibration for this test": "ใช้ Calibration ในการทดสอบนี้",
    "Pump cycle calibration — earlier data of this model will be replaced": "Calibration รอบปั๊ม — ข้อมูลเดิมของรุ่นนี้จะถูกแทนที่",
    "Pump cycle calibration: earlier data of this model is no longer used (kept for audit)":
        "Calibration รอบปั๊ม: เลิกใช้ข้อมูลเดิมของรุ่นนี้แล้ว (ยังเก็บไว้สอบย้อนหลัง)",
    "Pump cycle differs from earlier data": "รอบปั๊มต่างจากข้อมูลเดิม",
    "{device} at {rate:g} ml/h. The test result is saved either way — this only decides whether the program "
    "learns from it.":
        "{device} ที่ {rate:g} ml/h — ผลการทดสอบถูกบันทึกแล้วไม่ว่าจะเลือกอะไร คำถามนี้แค่ตัดสินว่าจะให้โปรแกรมเรียนรู้จากผลนี้ไหม",
    "This test": "ครั้งนี้",
    "Earlier at this rate": "ข้อมูลเดิมที่ rate นี้",
    "Earlier ({n} runs, volume per cycle)": "ข้อมูลเดิม ({n} ครั้ง, ปริมาตรต่อรอบ)",
    "Per cycle": "เวลาต่อรอบ",
    "Difference {d:+.1f} % (limit ±{limit:g} %)": "ต่างกัน {d:+.1f} % (เกณฑ์ ±{limit:g} %)",
    "Possible causes: cycles caught wrongly (check the live-flow graph), a different IV set lot or a set not "
    "seated properly, or the pump was repaired or adjusted.":
        "สาเหตุที่เป็นไปได้: จับรอบพลาด (ดูกราฟ flow ขณะนั้น), ชุดสายต่างล็อตหรือใส่ไม่เข้าที่, หรือปั๊มถูกซ่อม/ปรับตั้ง",
    "This is the {n}th time in a row that it differs — the pump has probably really changed. "
    "Calibrating again is recommended.":
        "ต่างจากข้อมูลเดิมติดกัน {n} ครั้งแล้ว — ปั๊มน่าจะเปลี่ยนไปจริง แนะนำให้ Calibration รอบปั๊มใหม่",
    "Do not learn from it": "ไม่เก็บ",
    "Add to earlier data": "เก็บรวมกับข้อมูลเดิม",
    "Calibrate again (replace earlier data)": "Calibration ใหม่ (แทนที่ข้อมูลเดิม)",
    "Windows for {rate:g} ml/h ({fit}): regression {r:.2f} × cycle, n̄ {h:.2f} × cycle":
        "หน้าต่างของ {rate:g} ml/h ({fit}): regression {r:.2f} × คาบ, n̄ {h:.2f} × คาบ",
    "tuned for this rate": "ปรับไว้สำหรับ rate นี้",
    "between tuned rates": "เทียบจาก rate ข้างเคียงที่ปรับแล้ว",
    "Window sizes {rate:g} ml/h: regression {n} pts, n̄ {h} pts (cycle about {p:.1f} s)":
        "ขนาดหน้าต่าง {rate:g} ml/h: regression {n} จุด, n̄ {h} จุด (รอบละประมาณ {p:.1f} วินาที)",
    "{rate:g} ml/h: regression {r:.2f} × cycle ({rp} pts), n̄ {h:.2f} × cycle ({hp} pts) · "
    "score {s:.3f} (before {cs}) · {n} tests":
        "{rate:g} ml/h: regression {r:.2f} × คาบ ({rp} จุด), n̄ {h:.2f} × คาบ ({hp} จุด) · คะแนน {s:.3f} (เดิม {cs}) · {n} การทดสอบ",
    "n̄ / pump cycle": "n̄ / คาบรอบปั๊ม",
    "0 = same as the regression window. Each model, IV set and rate gets its own values once tuned":
        "0 = เท่ากับหน้าต่าง regression · แต่ละรุ่น ชุดสาย และ rate จะได้ค่าของตัวเองหลังปรับจากข้อมูล",
    "Regression window as a fraction of the pump cycle — starting value for rates not tuned yet":
        "หน้าต่าง regression เป็นสัดส่วนของคาบรอบปั๊ม — ค่าเริ่มต้นของ rate ที่ยังไม่ได้ปรับ",
    "2 SD (±%)": "2 SD (±%)",
    "Uncorrected flow (ml/h)": "Flow ก่อนแก้ (ml/h)",
    "Uncorrected error (%)": "ค่าคลาดเคลื่อนก่อนแก้ (%)",

    # ---------------------------------------------------------------- หน้าต่างราย rate / สอบเทียบรอบปั๊ม (2026-11-13)
    '(checked afterwards — this result was saved as {verdict} before the check existed)':
        '(ตรวจย้อนหลัง — ผลนี้ถูกบันทึกเป็น {verdict} ก่อนมีการตรวจนี้)',
    '(no name)':
        '(ไม่มีชื่อ)',
    'Add rate':
        'เพิ่ม rate',
    'At {rates} ml/h the balance gives few points per pump cycle, so peak detection is coarse. Time-based capture over whole cycles is more precise there; a faster balance output (9600 baud or stream mode, set on the balance) also helps.':
        'ที่ {rates} ml/h ตราชั่งให้จุดต่อรอบปั๊มน้อย การจับ peak จึงหยาบ — จับตามเวลาเป็นจำนวนเต็มรอบจะแม่นกว่า หรือเพิ่มความถี่ตราชั่ง (9600 baud หรือโหมด stream ตั้งที่ตัวตราชั่ง) ก็ช่วยได้',
    'Balance points per pump cycle (fewer than 12 = coarse, fewer than 8 = not allowed)':
        'จำนวนจุดของตราชั่งต่อ 1 รอบปั๊ม (น้อยกว่า 12 = หยาบ, น้อยกว่า 8 = ไม่ให้ใช้)',
    'Calibrate from the highest rate to the lowest (recommended: the high rate learns the cycle within seconds)':
        'สอบเทียบจาก rate สูงไปต่ำ (แนะนำ: rate สูงเรียนรู้รอบปั๊มได้ในไม่กี่วินาที)',
    'Calibrate now (recommended)':
        'สอบเทียบเลย (แนะนำ)',
    'Cannot use peak detection at {rates} ml/h with these values — fix them or switch to time-based capture.':
        'ใช้การจับ peak ที่ {rates} ml/h ด้วยค่านี้ไม่ได้ — แก้ค่า หรือเปลี่ยนเป็นจับตามเวลา',
    'Capture check':
        'ตรวจการจับรอบ',
    'Captured cycles do not match the pump cycle: {d:.1f} s per cycle vs {p:.2f} s expected ({ratio:.2f} ×) — the result cannot be judged':
        'รอบที่จับได้ไม่ตรงกับรอบปั๊ม: {d:.1f} วินาทีต่อรอบ แต่คาบที่คาดไว้ {p:.2f} วินาที ({ratio:.2f} เท่า) — ตัดสินผลไม่ได้',
    'Captured cycles match the pump cycle ({ratio:.2f} ×)':
        'รอบที่จับได้ตรงกับรอบปั๊ม ({ratio:.2f} เท่า)',
    'Check before starting':
        'ตรวจก่อนเริ่ม',
    'Continue':
        'ดำเนินการต่อ',
    'Delete rate':
        'ลบ rate',
    'Delete the windows of {rate:g} ml/h for {device}? That rate goes back to the default values.':
        'ลบหน้าต่างของ {rate:g} ml/h ของ {device}? rate นี้จะกลับไปใช้ค่าเริ่มต้น',
    'From neighbouring calibrated rates':
        'เทียบจาก rate ข้างเคียงที่สอบเทียบแล้ว',
    'INVALID':
        'ผลใช้ไม่ได้',
    'If kept, it is stored for audit only: this step is not advanced and the result is not used for learning.':
        'ถ้ากดเก็บ จะเก็บไว้เพื่อสอบย้อนหลังเท่านั้น: ขั้นนี้ไม่เลื่อน และผลนี้ไม่ถูกนำไปเรียนรู้',
    'Infusion':
        'Infusion',
    'Syringe':
        'Syringe',
    'Intervals of whole pump cycles (at least 30 s) instead of peak detection':
        'แบ่งช่วงเป็นจำนวนเต็มรอบปั๊ม (อย่างน้อย 30 วินาที) แทนการจับ peak',
    'Measuring with regression {n} pts, n̄ {h} pts · cycle {p} · source {src}':
        'เริ่มวัดด้วย regression {n} จุด, n̄ {h} จุด · คาบ {p} · ที่มา {src}',
    'No pump-cycle data yet. It is created by pump-cycle tests, or saved from the calibration prompt when a test is created.':
        'ยังไม่มีข้อมูลรอบปั๊ม — จะเกิดจากการทดสอบแบบจับรอบปั๊ม หรือจากการกดบันทึกใน popup สอบเทียบตอนสร้างการทดสอบ',
    'Not calibrated at {rates} ml/h. Each rate needs its own regression and n̄ window — calibrating measures the pump cycle and tunes them from the result.':
        'ยังไม่ได้สอบเทียบที่ {rates} ml/h — แต่ละ rate ต้องมีหน้าต่าง regression และ n̄ ของตัวเอง การสอบเทียบจะวัดคาบรอบปั๊มแล้วปรับหน้าต่างจากผลที่ได้',
    'Not enough pump cycles were captured ({n}, at least {min} needed) — the result cannot be judged':
        'จับรอบปั๊มได้ไม่พอ ({n} รอบ ต้องมีอย่างน้อย {min}) — ตัดสินผลไม่ได้',
    'Not saved yet':
        'ยังไม่ได้บันทึก',
    'Points are estimated with {dt:.2f} s per balance reading ({src}).':
        'จำนวนจุดประมาณจาก {dt:.2f} วินาทีต่อการอ่านตราชั่ง 1 ครั้ง ({src})',
    'Points per cycle':
        'จุดต่อรอบ',
    'Points per cycle known once the balance is read':
        'รู้จุดต่อรอบเมื่ออ่านตราชั่งแล้ว',
    'Pump cycle':
        'คาบรอบปั๊ม',
    'Pump cycles were not captured correctly — result kept for audit only. Press Start to run this step again.':
        'จับรอบปั๊มไม่ถูกต้อง — เก็บผลไว้เพื่อสอบย้อนหลังเท่านั้น กดเริ่มเพื่อทำขั้นนี้ซ้ำ',
    'Pump-cycle calibration':
        'สอบเทียบรอบปั๊ม',
    'Pump-cycle calibration data':
        'ข้อมูลสอบเทียบรอบปั๊ม',
    'Pump-cycle calibration data…':
        'ข้อมูลสอบเทียบรอบปั๊ม…',
    'Regression':
        'Regression',
    'Regression / n̄ of every rate, per brand + model + pump type + IV set':
        'Regression / n̄ ทุก rate แยกตาม ยี่ห้อ + รุ่น + ชนิดเครื่อง + Set IV',
    'Regression and n̄ windows of every rate, per brand + model + pump type + IV set. Values are stored as a fraction of the pump cycle, so the number of points follows the real cycle and balance speed. Edited values are kept as "set by hand": they are not replaced by automatic tuning, and tests still ask for calibration until the model is calibrated.':
        'หน้าต่าง regression และ n̄ ของทุก rate แยกตาม ยี่ห้อ + รุ่น + ชนิดเครื่อง + Set IV — เก็บเป็นสัดส่วนของคาบ จำนวนจุดจึงตามคาบจริงและความเร็วตราชั่ง ค่าที่แก้จะถูกเก็บเป็น "แก้เอง": การปรับอัตโนมัติไม่ทับ และตอนสร้างการทดสอบยังเตือนให้สอบเทียบจนกว่ารุ่นนี้จะสอบเทียบจริง',
    'Regression must be between 0.1 and 0.75 × cycle':
        'Regression ต้องอยู่ระหว่าง 0.1–0.75 × คาบ',
    'n̄ must be between 0.1 and 0.75 × cycle':
        'n̄ ต้องอยู่ระหว่าง 0.1–0.75 × คาบ',
    'Regression outside 0.3–0.5 × cycle (below catches half cycles, above skips cycles)':
        'Regression อยู่นอก 0.3–0.5 × คาบ (ต่ำกว่าจับครึ่งรอบ สูงกว่าข้ามรอบ)',
    'n̄ outside 0.3–0.5 × cycle (below catches half cycles, above skips cycles)':
        'n̄ อยู่นอก 0.3–0.5 × คาบ (ต่ำกว่าจับครึ่งรอบ สูงกว่าข้ามรอบ)',
    'Result kept for audit but it cannot be judged — run this step again':
        'เก็บผลไว้สอบย้อนหลัง แต่ตัดสินผลไม่ได้ — ทำขั้นนี้ซ้ำ',
    'Review windows…':
        'ดูหน้าต่าง…',
    'Save changes':
        'บันทึกการแก้ไข',
    'Save for this model and use':
        'บันทึกให้รุ่นนี้แล้วใช้',
    'Save or discard the changes first.':
        'บันทึกหรือยกเลิกการแก้ไขก่อน',
    'Saved {n} rates':
        'บันทึกแล้ว {n} rate',
    'See and edit the regression and n̄ windows of every rate, per model and IV set':
        'ดูและแก้หน้าต่าง regression และ n̄ ของทุก rate แยกตามรุ่นและ Set IV',
    'Set by hand · not calibrated':
        'แก้เอง · ยังไม่ได้สอบเทียบ',
    'Set for this test':
        'กำหนดสำหรับการทดสอบนี้',
    'Skip calibration…':
        'ข้ามการสอบเทียบ…',
    'Switch to time-based capture':
        'เปลี่ยนเป็นจับตามเวลา',
    'The balance has not been read yet, so the number of points is not known.':
        'ยังไม่ได้อ่านตราชั่ง จึงยังไม่รู้จำนวนจุด',
    'The balance speed is not known yet — windows are shown as a fraction of the pump cycle. Connect the balance to see and edit points.':
        'ยังไม่รู้ความเร็วตราชั่ง — แสดงหน้าต่างเป็นสัดส่วนของคาบ ต่อตราชั่งแล้วจะดู/แก้เป็นจำนวนจุดได้',
    'The pump cycle was not known, so the captured cycles could not be checked':
        'ไม่รู้คาบรอบปั๊ม จึงตรวจรอบที่จับได้ไม่ได้',
    'The pump cycles were not captured correctly':
        'จับรอบปั๊มไม่ถูกต้อง',
    'These are the defaults for each rate (or what you saved for this model before). Change them if you know better values. Saved values are marked "not calibrated": you will still be asked to calibrate next time, and skipping again uses them.':
        'นี่คือค่าเริ่มต้นของแต่ละ rate (หรือค่าที่เคยบันทึกไว้ให้รุ่นนี้) แก้ได้ถ้ารู้ค่าที่ดีกว่า ค่าที่บันทึกจะถูกทำเครื่องหมาย "ยังไม่ได้สอบเทียบ": ครั้งหน้ายังเตือนให้สอบเทียบ และถ้าข้ามอีกจะใช้ค่านี้',
    'Time per cycle':
        'เวลาต่อรอบ',
    'Use for this test only':
        'ใช้กับการทดสอบนี้เท่านั้น',
    'Values at {rates} ml/h are outside the usable range and were not saved.':
        'ค่าที่ {rates} ml/h อยู่นอกช่วงที่ใช้ได้ จึงไม่ได้บันทึก',
    'Volume per cycle (this model has not been measured)':
        'ปริมาตรต่อรอบ (รุ่นนี้ยังไม่เคยวัด)',
    'Window source':
        'ที่มาของหน้าต่าง',
    'Window values':
        'ค่าหน้าต่าง',
    'Windows used without calibration':
        'หน้าต่างที่จะใช้โดยไม่สอบเทียบ',
    'cannot be judged (pump cycles not captured correctly)':
        'ตัดสินผลไม่ได้ (จับรอบปั๊มไม่ถูกต้อง)',
    'cycle':
        'คาบ',
    'cycle {p} · reg {r:.2f} · n̄ {h:.2f} × cycle':
        'คาบ {p} · reg {r:.2f} · n̄ {h:.2f} × คาบ',
    'cycle {p} · reg {r} · n̄ {h} · {ppc:.1f} pts/cycle':
        'คาบ {p} · reg {r} · n̄ {h} · {ppc:.1f} จุด/รอบ',
    'default':
        'ค่าเริ่มต้น',
    'estimated':
        'ประมาณ',
    'few points per cycle':
        'จุดต่อรอบน้อย',
    'from volume per cycle':
        'จากปริมาตรต่อรอบ',
    'last_test':
        'ผลล่าสุดที่บันทึกไว้',
    'manual':
        'กำหนดเอง',
    'measured':
        'วัดได้',
    'model default':
        'ค่าแทนของรุ่น',
    'model_default':
        'ค่าแทนของรุ่น',
    'no IV set':
        'ไม่ระบุ Set IV',
    'plan':
        'กำหนดในแผน',
    'profile':
        'โปรไฟล์',
    'pts':
        'จุด',
    'reg {r:.2f} · n̄ {h:.2f} × cycle':
        'reg {r:.2f} · n̄ {h:.2f} × คาบ',
    'reg {r} · n̄ {h} pts · {ppc:.0f} pts/cycle':
        'reg {r} · n̄ {h} จุด · {ppc:.0f} จุด/รอบ',
    'simulator':
        'ตราชั่งจำลอง',
    '{device} is not calibrated for pump-cycle capture':
        '{device} ยังไม่ได้สอบเทียบการจับรอบปั๊ม',
    '{r:.2f} × cycle / {h:.2f} × cycle':
        '{r:.2f} × คาบ / {h:.2f} × คาบ',
    '{rate:g} ml/h: only {n:.1f} balance points per pump cycle — peak detection is coarse. Time-based capture (whole cycles) or a faster balance output is more precise.':
        '{rate:g} ml/h: ตราชั่งให้แค่ {n:.1f} จุดต่อรอบปั๊ม — การจับ peak หยาบ จับตามเวลา (จำนวนเต็มรอบ) หรือเพิ่มความถี่ตราชั่งจะแม่นกว่า',
    '{rate:g} ml/h: the pump cycle is measured before measuring starts; window sizes follow from it':
        '{rate:g} ml/h: วัดคาบรอบปั๊มก่อนเริ่มวัด แล้วตั้งขนาดหน้าต่างจากคาบนั้น',
    '{rate:g} ml/h: window sizes set by hand were kept (run Calibration to replace them)':
        '{rate:g} ml/h: คงค่าหน้าต่างที่แก้เองไว้ (สั่ง Calibration เพื่อแทนที่)',
    '⚠ Few points per cycle':
        '⚠ จุดต่อรอบน้อย',
    '⚠ Not calibrated (default)':
        '⚠ ยังไม่ได้สอบเทียบ (ค่าเริ่มต้น)',
    '⚠ Saved default · not calibrated':
        '⚠ ค่าเริ่มต้นที่บันทึกไว้ · ยังไม่ได้สอบเทียบ',
    '⛔ Too few points per cycle — use time-based capture':
        '⛔ จุดต่อรอบน้อยเกิน — ใช้การจับตามเวลา',
    '✓ Calibrated':
        '✓ สอบเทียบแล้ว',
    'Peak-detection windows':
        'หน้าต่างจับ peak',
    'OK':
        'ผ่าน',
    'Not enough cycles':
        'รอบไม่พอ',
    'Does not match the cycle':
        'ไม่ตรงกับคาบ',
    'Not checked (cycle unknown)':
        'ตรวจไม่ได้ (ไม่รู้คาบ)',
    'Slope graph window (time-based capture)':
        'หน้าต่างกราฟ slope (จับตามเวลา)',
    "Only smooths the live slope graph of time-based tests. Pump-cycle capture uses each rate's own windows (Pump-cycle calibration data below)":
        'ใช้ทำให้กราฟ slope สดของการจับตามเวลาเรียบขึ้นเท่านั้น — การจับรอบปั๊มใช้หน้าต่างของแต่ละ rate (ข้อมูลสอบเทียบรอบปั๊ม ด้านล่าง)',
    "Pump cycle period not found before measuring; the model's known cycle was used":
        'หาคาบรอบปั๊มก่อนเริ่มวัดไม่ได้ จึงใช้คาบที่รู้ของรุ่นนี้',
    # ---------------------------------------------------------------- 2026-11-13: ฟอร์มงาน / ตรวจเครื่อง / ประกัน / กราฟ
    "Job no.": "เลขงาน (Job)",
    "Hospital / site": "โรงพยาบาล / สถานที่",
    "Province": "จังหวัด",
    "MCI… = Infusion · MCS… = Syringe": "MCI… = Infusion · MCS… = Syringe",
    "Type the model — brand and pump type follow": "พิมพ์รุ่น — ยี่ห้อและชนิดเครื่องจะตามมาเอง",
    "IV set": "IV set (รุ่น)",
    "IV set brand": "ยี่ห้อ IV set",
    "Syringe used": "Syringe ที่ใช้ (รุ่น/ขนาด)",
    "Syringe brand": "ยี่ห้อ Syringe",
    "Model — part of the pump profile": "รุ่น — ใช้เป็นส่วนหนึ่งของโปรไฟล์ปั๊ม",
    "↹ Tab / Enter in Model confirms what {model} was recorded as: {values}":
        "↹ กด Tab / Enter ที่ช่องรุ่น เพื่อยืนยันค่าที่ {model} เคยบันทึกไว้: {values}",
    "Reference balance: {balance} — change it in Settings": "ตราชั่งมาตรฐาน: {balance} — เปลี่ยนได้ที่หน้าตั้งค่า",
    "{kind} differs from before": "{kind} ต่างจากที่เคยใช้",
    "{site} usually uses {standard} with {device}.\nThis time: {new}":
        "{site} ใช้ {standard} กับ {device} เป็นมาตรฐาน\nครั้งนี้กรอก: {new}",
    "Is this a temporary change, or the new standard for this hospital?":
        "ใช้ชั่วคราว หรือจะเปลี่ยนมาใช้รุ่นนี้เป็นมาตรฐานของโรงพยาบาลนี้ถาวร?",
    "Temporary (this time only)": "ใช้ชั่วคราว (ครั้งนี้เท่านั้น)",
    "New standard from now on": "เปลี่ยนเป็นมาตรฐานใหม่ถาวร",
    "Go back and edit": "กลับไปแก้",
    "hospital standard": "มาตรฐานของโรงพยาบาล",
    "temporary": "ใช้ชั่วคราว",
    "new hospital standard": "เปลี่ยนเป็นมาตรฐานใหม่",
    "first time — set as standard": "ครั้งแรก — ตั้งเป็นมาตรฐาน",
    "Syringe / IV set brand": "ยี่ห้อ Syringe / ชุดสาย",
    "IV set vs. hospital standard": "ชุดสายเทียบมาตรฐานโรงพยาบาล",
    "Parts under warranty": "อะไหล่ที่เคลมประกัน",
    "warranty": "ประกัน",
    "Search — Tab or Enter ticks it, then type the next one…": "ค้นหา — Tab หรือ Enter เพื่อติ๊ก แล้วพิมพ์ตัวถัดไปได้เลย…",
    "Nothing ticked yet": "ยังไม่ได้ติ๊กรายการใด",
    "Untick": "เอาออก",
    "Warranty ✓": "ประกัน ✓",
    "Warranty?": "ประกัน?",
    "Replaced under warranty — click to change": "เปลี่ยนแบบเคลมประกัน — คลิกเพื่อเปลี่ยน",
    "Click if this part is replaced under warranty": "คลิกถ้าอะไหล่ชิ้นนี้เปลี่ยนแบบเคลมประกัน",
    "Add a new item?": "เพิ่มรายการใหม่?",
    "\"{name}\" is not in the list.\n\nAdd it as a new item? It will be remembered for this model.":
        "\"{name}\" ยังไม่มีในรายการ\n\nเพิ่มเป็นรายการใหม่ไหม? (จะจำไว้กับรุ่นนี้)",
    "Nothing ticked": "ยังไม่ได้ติ๊ก",
    "Nothing is ticked in:": "ยังไม่ได้ติ๊กรายการใดใน:",
    "Is that correct — really none? It is easy to forget.": "ถูกต้องไหม — ไม่มีจริงๆ ใช่ไหม? (กันลืมกรอก)",
    "Correct, none": "ถูกต้อง ไม่มี",
    "Go back and tick": "กลับไปติ๊ก",
    "Warranty history": "ประวัติอะไหล่ / ประกัน",
    "This device had {n} parts replaced before · {m} still under warranty or late.":
        "เครื่องนี้เคยเปลี่ยนอะไหล่ {n} รายการ · ยังอยู่ในประกันหรือ late {m} รายการ",
    "Parts replaced before": "อะไหล่ที่เคยเปลี่ยน",
    "This device has had parts replaced — any warranty claim this time?":
        "เครื่องนี้เคยเปลี่ยนอะไหล่ — รอบนี้มีเคลมประกันไหม?",
    "{device} · {n} parts still claimable. Tick the ones to claim; they are added to \"Parts replaced\" marked as warranty. The warranty start date stays the same.":
        "{device} · ยังเคลมได้ {n} รายการ — ติ๊กชิ้นที่จะเคลม แล้วจะลงช่อง \"อะไหล่ที่เปลี่ยน\" พร้อมสถานะประกันให้เอง (วันเริ่มประกันเดิม ไม่นับใหม่)",
    "Part": "อะไหล่",
    "Warranty from": "ประกันตั้งแต่",
    "Warranty until": "ประกันถึง",
    "In warranty · {d} days left": "ในประกัน · เหลือ {d} วัน",
    "Late · {d} days past warranty — consider": "Late · เกินประกันมา {d} วัน — พิจารณาเคลม",
    "Warranty ended": "หมดประกัน",
    "replaced {n}×": "เปลี่ยนแล้ว {n} ครั้ง",
    "Last replaced {date}": "เปลี่ยนล่าสุด {date}",
    "No claim this time": "รอบนี้ไม่มีเคลม",
    "Claim ticked parts": "เคลมรายการที่ติ๊ก",
    "Claim ticked parts ({n})": "เคลมรายการที่ติ๊ก ({n})",
    "Could not save the parts history: {error}": "บันทึกประวัติอะไหล่ไม่ได้: {error}",
    "Part warranty": "ประกันอะไหล่",
    "Late claims considered for": "ผ่อนผันเคลมหลังหมดประกัน (late)",
    "Counted from the first time a part is recorded for a device — a warranty claim never restarts it":
        "นับจากวันที่อะไหล่ชนิดนั้นลงระบบครั้งแรกของเครื่อง — การเคลมไม่เริ่มนับใหม่",
    "Reference balance": "ตราชั่งมาตรฐาน",
    "Balance model": "รุ่นตราชั่ง",
    "Balance serial no.": "Serial ตราชั่ง",
    "Saved with every result for traceability (replaces the Balance ID field in the test form)":
        "บันทึกลงทุกผลเพื่อการสอบย้อนกลับ (แทนช่องรหัสตราชั่งในฟอร์มสร้างการทดสอบ)",
    "Graph view": "มุมมองกราฟ",
    "Full": "เต็ม",
    "Auto": "อัตโนมัติ",
    "Zoom": "ซูม",
    "Whole test from the start, start point fixed": "ทั้งการทดสอบตั้งแต่เริ่ม ตรึงจุดเริ่มไว้",
    "Follow the latest data, width = several pump cycles (detected automatically)":
        "ตามข้อมูลล่าสุด กว้างหลายรอบปั๊ม (หาคาบให้อัตโนมัติ)",
    "Follow the latest data closely (width set in Settings)": "ตามข้อมูลล่าสุดแบบใกล้ (ความกว้างตั้งได้ในหน้าตั้งค่า)",
    "Full — whole test, start fixed": "เต็ม — ทั้งการทดสอบ ตรึงจุดเริ่ม",
    "Auto — several pump cycles": "อัตโนมัติ — หลายรอบปั๊ม",
    "Zoom — latest data, close up": "ซูม — ข้อมูลล่าสุดแบบใกล้",
    "Also switchable on the Test page; applies to all four graphs": "สลับได้ที่หน้าทดสอบด้วย ใช้กับกราฟทั้ง 4 ช่อง",
    "Auto view width": "ความกว้างโหมดอัตโนมัติ",
    "Pump cycles (or time-based intervals) shown in Auto view — the cycle is detected while testing":
        "จำนวนรอบปั๊ม (หรือช่วงวัดตามเวลา) ที่เห็นในโหมดอัตโนมัติ — หาคาบระหว่างทดสอบ",
    "Auto view width before the cycle is known": "ความกว้างโหมดอัตโนมัติตอนยังไม่รู้คาบ",
    "Zoom view width": "ความกว้างโหมดซูม",
    " cycles": " รอบ",
}
