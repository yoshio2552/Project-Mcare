# --- ไฟล์: worker_serial.py ---
import time
import serial
import re
import queue  # 1. เพิ่มโมดูล queue เข้ามาครับ
from PySide6.QtCore import QObject, Slot, Signal

class SerialWorker(QObject):
    
    # ### 2. สร้าง Signal สำหรับ "เคาะระฆัง" บอก Engine ว่ามีของในคิวแล้ว
    data_available = Signal() 
    
    def __init__(self, data_queue, port="COM3", baudrate=9600):
        super().__init__()
        self.data_queue = data_queue 
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_running = False
        self.number_pattern = re.compile(r"[-+]?\d*\.\d+|\d+")

    @Slot()
    def start_reading(self):
        try:
            if self.ser is None:
                self.ser = serial.Serial(
                    self.port, 
                    self.baudrate, 
                    bytesize=7, 
                    parity='E', 
                    stopbits=1, 
                    timeout=0.15
                )
                print(f"Worker: เปิดพอร์ต {self.port} สำเร็จ")
        except Exception as e:
            print(f"Worker: เปิดพอร์ตไม่สำเร็จ! {e}")
            return 

        self.is_running = True
        while self.is_running:
            if not (self.ser and self.ser.is_open):
                time.sleep(0.1)
                continue

            raw_bytes = self.ser.readline()    
            t_receive = time.perf_counter() 
            
            if not raw_bytes:
                time.sleep(0.01)
                continue

            line = raw_bytes.decode('ascii', errors='ignore').strip()
            
            if len(line) < 11:
                time.sleep(0.01)
                continue

            match = self.number_pattern.search(line)
            if not match:
                time.sleep(0.01)
                continue

            # 3. โซนข้อมูลคุณภาพดี: แทนที่จะใช้ .emit() เราใช้ .put()
            try:
                weight = float(match.group())
                
                # นำข้อมูลใส่ tuple แล้วโยนลงตะกร้า (Queue)
                # วิธีนี้ปลอดภัยแม้ UI จะรันอยู่คนละ Thread
                self.data_queue.put((t_receive, weight))
                self.data_available.emit() # ### เคาะระฆังบอก Engine!
            except queue.Full:
                # ถ้าคิวเต็ม (กรณี UI อ่านไม่ทัน) ให้ข้ามข้อมูลไปบ้าง
                pass
            except ValueError:
                pass

            time.sleep(0.01)

    def stop(self):
        self.is_running = False
        if self.ser:
            self.ser.close()
            print("Worker: ปิดพอร์ตเรียบร้อย")