import os
# บังคับให้ pyqtgraph รันบนโครงสร้างของ PySide6
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
import pyqtgraph as pg
import sys
import queue  
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PySide6.QtCore import QThread, Slot, QTimer

# 1. ตั้งค่า Global Config ของ PyQtGraph ก่อนโหลดโมดูลอื่นๆ
pg.setConfigOption('useOpenGL', True)
pg.setConfigOption('antialias', False) # ปิดรอยหยักเส้นกราฟ จะช่วยให้ GPU วาดเส้นได้เร็วขึ้นไปอีกขั้น

from ui.main_window import ControlPanel, GraphBoard  
from hardware.steam_argos import SerialWorker     
from core.data_engine import DataEngine   
      

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DeltaM : Delta Mass|High Frequency Analysis 0.0.1")
        self.resize(1400, 900) 
        
        central_widget = QWidget()
        # บังคับให้พื้นหลังของหน้าต่างหลักเป็นสีมืดเพื่อลบขอบสีขาวกระดำกระด่าง
        central_widget.setStyleSheet("background-color: #1E1E1E;")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5) # เปิดช่องไฟเล็กน้อยให้ดูมีมิติ
        main_layout.setSpacing(10)
        
        self.control_panel = ControlPanel()
        self.graph_board = GraphBoard()
        
        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.graph_board)

        # คิวพักข้อมูลความเร็วสูงภายในฝั่ง UI สำหรับจัดกลุ่ม Render (Thread-Safe Queue)
        self.ui_data_queue = queue.Queue(maxsize=10000)

        self.setup_threads()
        self.connect_signals()
        
        # ตั้งค่า QTimer สำหรับคุมเฟรมเรตแอนิเมชันที่ ~30 FPS (33 มิลลิวินาที)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.animate)
        
    def setup_threads(self):
        self.shared_queue = queue.Queue(maxsize=1000)
        self.worker = SerialWorker(self.shared_queue, port="COM3", baudrate=9600)
        self.engine = DataEngine(self.shared_queue) 

        self.worker_thread = QThread()
        self.engine_thread = QThread()

        self.worker.moveToThread(self.worker_thread)
        self.engine.moveToThread(self.engine_thread)

    def connect_signals(self):
        self.control_panel.btn_start.clicked.connect(self.start_system)
        self.control_panel.btn_stop.clicked.connect(self.stop_system)
        self.control_panel.input_window.valueChanged.connect(self.graph_board.set_window_size)
        
        # เชื่อม Thread ให้เริ่มทำงาน
        self.worker_thread.started.connect(self.worker.start_reading)
        
        # เมื่อ Worker ใส่ของลงคิวแล้วเคาะระฆัง (data_available) -> Engine ตื่นมาทำงาน (engine_core)
        self.worker.data_available.connect(self.engine.engine_core)
        
        # ปรับเปลี่ยนแนวทาง: เบี่ยงสัญญาณผลลัพธ์จากคำนวณเสร็จ ไปพักลงคิวภายใน UI แทนการรุมพล็อตทันที
        self.engine.stats_updated.connect(self.collect_ui_data)

    @Slot(dict)
    def collect_ui_data(self, packet: dict):
        """ ทำหน้าที่รับข้อมูลดิบจากการคำนวณฝั่ง Engine สับหลีกไปบันทึกไว้ในคิวก่อน """
        try:
            # ใช้ put_nowait แทน put ธรรมดา
            self.ui_data_queue.put_nowait(packet)
        except queue.Full:
            # ถ้าคิวเต็ม (เช่น UI ค้างหนักมากจนกวาดข้อมูลไม่ทัน) 
            # ยอม "ทิ้ง" ข้อมูลเฟรมนั้นไป (Drop frame) ดีกว่าปล่อยให้ RAM บวมจนโปรแกรมแครช
            pass

    @Slot()
    def animate(self):
        """ ฟังก์ชันลูปการทำงานหลักของ QTimer ดึงข้อมูลออกจากคิวทั้งหมดรวดเดียวเพื่อวาดบนหน้าจอทีเดียว """
        packets_batch = []
        
        # เคลียร์และดึงข้อมูลสะสมทั้งหมดออกจากคิว ณ วินาทีนั้นๆ เพื่อนำไปพล็อตรวดเดียว
        while not self.ui_data_queue.empty():
            try:
                packet = self.ui_data_queue.get_nowait()
                packets_batch.append(packet)
            except queue.Empty:
                break
                
        if packets_batch:
            # ส่งข้อมูลไปประมวลผลวาดขึ้นจอเป็นกลุ่มก้อน (Batch Rendering)
            self.graph_board.update_graphs(packets_batch)

    @Slot()
    def start_system(self):
        print("System Starting...")
        self.control_panel.btn_start.setEnabled(False)
        self.control_panel.btn_stop.setEnabled(True)
        self.graph_board.clear_graphs() 
        
        # ล้างคิวค้างเก่าในฝั่ง UI ออกให้หมดก่อนเริ่มเซสชันใหม่
        while not self.ui_data_queue.empty():
            try: self.ui_data_queue.get_nowait()
            except queue.Empty: break


        # --- ส่วนที่เพิ่มเข้ามา ---
        try:
            # ดึง text จาก QLineEdit แล้วแปลงเป็น float
            target_value = float(self.control_panel.input_rate.text())
            self.engine.target_flow = target_value

            
        except ValueError:
            # ถ้าผู้ใช้พิมพ์อะไรที่ไม่ใช่ตัวเลข ให้ตั้งค่า Default หรือแจ้งเตือน
            print("Error: Invalid Target Rate input. Defaulting to 0.0")
            self.engine.target_flow = 50
            
        # เริ่มต้นการทำงานของระบบประมวลผลข้อมูล
        self.engine.is_running = True
        self.engine_thread.start()
        self.worker.is_running = True
        self.worker_thread.start()
        

        
        # ปรับเป็น 16 หรือ 17 มิลลิวินาที เพื่อให้ UI ตื่นขึ้นมากวาดกราฟที่ความเร็ว 60 FPS
        # สั่งเปิดสวิตช์ระบบลูปคุมเรตการวาดหน้าจอทันที (33 ms ~ 30 FPS)
        self.ui_timer.start(17)

    @Slot()
    def stop_system(self):
        print("System Stopping...")
        self.control_panel.btn_start.setEnabled(True)
        self.control_panel.btn_stop.setEnabled(False)
        
        # หยุดระบบอนิเมชันวาดรูปของฝั่ง UI 
        self.ui_timer.stop()
        
        if hasattr(self.worker, 'stop'):
            self.worker.stop()
        else:
            self.worker.is_running = False
        self.engine.is_running = False   
        
        self.worker_thread.quit()
        self.engine_thread.quit()
        self.worker_thread.wait()
        self.engine_thread.wait()
        
    def closeEvent(self, event):
        self.stop_system()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())