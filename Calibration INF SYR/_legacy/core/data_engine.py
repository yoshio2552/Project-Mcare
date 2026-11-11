
import time
from collections import deque                           # เรียกใช้งาน list deque สำหรับเก็บข้อมูล
import re
from hardware.steam_argos import SerialWorker
from PySide6.QtCore import QObject, Slot, Signal # เพิ่ม Slot กับ Signal เข้าไปตรงนี้ครับ
from core.class_filter_selection import (
    MainFilterSelection, 
    IntervalLoopCountTime, 
    CycleAnalyzer
)
from core.cal_ins_selection import InspectionCalibrationSelection

import queue


class DataEngine(QObject):                              # QObject เรียกคลาสแม่ ของ Pyside6 บ่งบอกถึงการคำนวณหลังบ้าน
    
    stats_updated = Signal(dict)
    
    def __init__(self,input_queue):
        super().__init__()
        self.input_queue = input_queue                  #รับ queue เข้ามา
        
        #ระบบ เปิดปิดเครื่องยนต์
        self.is_running: bool = False                   # ไว้สำหรับ เปิดปิด การอ่านและคำนวนตราชั่ง *
        
        #ระบบ ตั่งค่าการใช้งาน system และ value ต่างๆ 

        self.countdown_mode :bool = True                # True = จับตามเวลาหยุด False = ไม่จับเวลาแต่จะเป็นนับ รอบ finger pump แทน 
        self.interval_mode :int = 0                     # 0 = เปิดโหมดจับรอบ Finger Pump เพื่อทำ FlowRate ที่แม่นยำ 1 = ปิดโหมดจับรอบ finger pump แต่เปิดโหมด จับเวลา dt แต่ล้ะช่องแทน 2 = ทำทั้งคู่
        
        self.evaporate_mode = False                     # duo-06 True = ตรวจจับการระเหย ตราชั่ง False = ปิดระบบตรวจจับ *จะต้องทำตัวแยกแยะหากเปิดอย่ให้รันปกติไม่ได้*
        
        self.check_round_calibration :int = 2          # เอาไว้เก็บตัวแปร สำหรับนับรอบว่า calibration รอบที่เท่าไหร่แล้ว default ไว้ที่ 3 rate rate ไหนครบแล้วจะลบออก 
        
        self.styles_inscal :str = "inspection"              # ตัวแปรเก็บโหมด การรัน ตอนนี้จะมี Inspection,Calibration,Test *
        self.type_inscal :str = "infusion"                  # ตัวแปรเก็บโหมด การรัน ตอนนี้จะมี Infusion,Syringe *
        
        self.rate_calibration_inf : float = [10,50,200] # ตัวแปรเก็บ rate calibration สำหรับ inf
        self.rate_calibration_syr : float = [10,50,100] # ตัวแปรเก็บ rate calibration สำหรับ syr
        
        self.check_cal_ins_selection:bool = False          #ตัวแปรไว้เช็คว่า ได้ทำการเช็ค หน้า cal_ins_selection ไปหรือยัง จะได้ไม่ต้องเข้าไปในลูปทุกครั้ง *

        self.limit_interval_calibration_inf : int = [25,50,10] # ตัวแปรเก็บ จำนวนรอบ ปั้ม หลังจากเลือก mode interval แทน time เรียงตามลำดับ ตาม rate_calibration
        self.limit_interval_calibration_syr : int = [25,50,10] # ตัวแปรเก็บ จำนวนรอบ ปั้ม หลังจากเลือก mode interval แทน time เรียงตามลำดับ ตาม rate_calibration

        self.rate_inspection_inf : float = 50           # ตัวแปรเก็บ rate inspection inf
        self.rate_inspection_syr : float = 50           # ตัวแปรเก็บ rate inspection syr    
        
        self.rate_test : float = 50                     # ตัวแปรเก็บ rate สำหรับ mode test 
        
        self.target_flow :float = 10                    # ค่า flowrate ที่ตั้ง ณ ตอนนี้รอบนี้จริงๆ   *      
        
        self.data_cycle_zigzag = 50                    # จำนวนเก็บของ deq วงจรครบรอบของ zigzag regression พ่นออกมาเป็น ml/h 
        self.limit_interval_mode :int = 200            # duo-04 สำหรับเก็บ การนับจำนวน จับรอบ Finger Pump แทนการจับ เวลา แล้วเอาไว้ใช้กับ mode Inspection , Test ด้วย
        
        
        self.buffer_n_bar :int = 250                    # duo-03 จำนวนนับ ที่จะเฉลี่ยข้อมูลให้ Zigzag Bar สำหรับเริ่มต้น หรือก็คือ n_bar *
        self.buffer_regression :int = 250               # duo-02 จำนวนนับ ที่จะเฉลี่ยข้อมูลให้ linear regression slope สำหรับเริ่มต้น *
        
        self.limit_time_mode :int = 5                 # duo-04 สำหรับเก็บ การนับเวลา ตามรอบเวลาที่กำหนดไว้ หน่วยเป็น นาทีเท่านั้น
        
        self.time_session :int = 30                     # duo-05 สำหรับเก็บจำนวน วินาที interval แกน x แต่ล้ะช่วง
        self.time_session_counts :int = 10              # duo-05 เก็บจำนวนว่าจะเอา กี่ช่วง มาแสดง   
        
        # ตัวเช็คว่า ลูปแรก และ สองนั้น ครบเวลายังใน class_filter_selection
        self.inter_finis_f : bool = False
        self.inter_finis_s : bool = False
        
        #รอเก็บตอนรัน ระบบ และ ตอนจบการรัน
        self.interval_counts :int = None                # duo-04 สำหรับเก็บจำนวนนับรอบ interval ตอนเปิดโหมด จับรอบ Finger Pump    
        
        self.start_time_original :float = None                   # สำหรับเก็บค่า จุดเริ่มต้นเวลา *
        self.start_weight_original :float = None                 # สำหรับเก็บค่า จุดเริ่มนํ้าหนัก *
        self.end_time_original :float = None                     # สำหรับเก็บค่า จุดจบเวลา *
        self.end_weight_original :float = None                   # สำหรับเก็บค่า จุดจบนํ้าหนัก  *
        
        self.start_time_first :float = None                   # สำหรับเก็บค่า จุดเริ่มต้นเวลา *
        self.start_weight_first :float = None                 # สำหรับเก็บค่า จุดเริ่มนํ้าหนัก *
        self.end_time_first :float = None                     # สำหรับเก็บค่า จุดจบเวลา *
        self.end_weight_first :float = None                   # สำหรับเก็บค่า จุดจบนํ้าหนัก * 
        
        self.start_time_second :float = None                   # สำหรับเก็บค่า จุดเริ่มต้นเวลา *
        self.start_weight_second :float = None                 # สำหรับเก็บค่า จุดเริ่มนํ้าหนัก *
        self.end_time_second :float = None                     # สำหรับเก็บค่า จุดจบเวลา  *
        self.end_weight_second :float = None                   # สำหรับเก็บค่า จุดจบนํ้าหนัก  *
        
        self.evaporate_avg :float = None                # duo-06 สำหรับเก็บค่า เฉลี่ยการระเหย
        
        self.temperature_start :float = None            # สำหรับเก็บค่า อุณหภูมิเริ่ม
        self.temperature_end:float = None               # สำหรับเก็บค่า อุณหภูมิจบ        
        self.Humidity_start :float = None               # สำหรับเก็บค่า ความชื้นเริ่ม
        self.Humidity_end :float = None                 # สำหรับเก็บค่า ความชื้นจบ
                
        self.avg_each_session : float =None             # สำหรับเก็บเวลาเฉลี่ย แต่ล้ะรอบ เวลา หรือ ช่วงปั้ม ว่าเฉลี่ยกี่วินาที *
        self.sd_each_session : float =None              # สำหรับเก็บความผันผวนเวลา แต่ล้ะรอบ เวลา หรือ ช่วงปั้ม ว่าบวกลบกี่วินาที
        
        # buffer สำหรับ cumulative ต่างๆ


        
        self.buffer_cumulative_avg  :int = 50           # duo-01 จำนวนนับ ที่จะเฉลี่ยข้อมูลให้ standard devision average and norm distribution average สำหรับเริ่มต้น   

        self.sub_regression_buffer = deque(maxlen=self.buffer_regression)        # เก็บผลต่าง ของเวลา และ นํ้าหนัก ณ ตอนนี้ไว้ สำหรับให้ regression slope นำไปคำนวน

        
                
        # เพิ่ม CycleAnalyzer ไว้ใน DataEngine เพื่อให้มันจำค่าสะสมได้
        self.cycle_analyzer = CycleAnalyzer(n_bar=self.buffer_n_bar)
        
        
        #ตัวแปรเก็บค่าที่นี้ สำหรับ คำนวณ,เก็บค่าตัวแปร อะไรก็ตามที่ต้องใช้หลายข้อมูล list
        self.list_cumulative_avg = deque(maxlen=self.buffer_cumulative_avg)                 # duo-01 list เก็บค่า สำหรับคำนวณ SD ของ C.avg ตามจำนวนที่ตั้งไว้
        self.list_regression = deque(maxlen=self.buffer_regression)                         # duo-02 list เก็บค่า สำหรับคำนวณ ค่าเฉลี่ย ของ linear Regression slope ตามจำนวนที่ตั้งไว้
        self.list_cumulative_regression = deque(maxlen=self.buffer_n_bar)                   # duo-03 list เก็บค่า สำหรับคำนวณ Zigzag Bar ตามจำนวนที่ตั้งไว้ เช่น n_bar
        
        # list เก็บค่าไว้แสดง show report 
        self.list_interval_flowrate = deque(maxlen=self.limit_interval_mode)                # duo-04 list เก็บค่า สำหรับ show interval flowrate กราฟ report
        self.list_interval_time = deque(maxlen=self.limit_interval_mode)                    # duo-04 list เก็บค่า สำหรับ time interval flowrate กราฟ report

        self.list_session_flowrate = deque(maxlen=self.time_session_counts)                 # duo-05 list เก็บค่า flowrate สำหรับ show บนกราฟ
        self.list_session_time = deque(maxlen=self.time_session_counts)                     # duo-05 list เก็บค่า time ของ flowrate สำหรับ show บนกราฟ
        
        #ตัวแปรเก็บค่า std , ci ของ interval loop หรือ time
        self.std_interval = 0.0
        self.ci_interval = 0.0
        
        self.latest_cycle_detected = None                                                   # ตัวรับ zigzag bar ครบวงจร output: ml/h                                   
        

        self.number_pattern = re.compile(r"[-+]?\d*\.\d+|\d+")                              # ตัวคัดกรอง สำหรับข้อมูลดิบจากตราชั่ง

        self.cycle_history = deque(maxlen=self.data_cycle_zigzag)                           #คลังเก็บข้อมูลไว้หาค่าเฉลี่ยของ zigzag bar
        
        self.engine_calculate = IntervalLoopCountTime(self)                                 # เรียกใช้ คลาสสำหรับทำการคำนวนทุกอย่าง
        self.reset_session()                                                                # เรียกใช้ตอนสร้าง Class ครั้งแรก ไว้ลบตัวแปร

        
    @Slot()                                                                             # ระบุสเปกช่องรับ: ต้องเป็น (float, float) ตรงกับที่ Worker ส่งมา
    def engine_core(self):                                                               # ฟังชั่นหลักของการคำนวณ รอข้อมูล Realtime จาก ตราชั่ง Argos
        """ ฟังก์ชันนี้จะ 'ตื่นขึ้นมาทำเอง' ทุกครั้งที่ ยิงข้อมูลมา ความเร็วเทียบเท่า ความเร็ว 10hz จากการอ่านตราชั่ง"""
        

        # 1. เช็คสเตตัสระบบก่อน หากยังไม่ run ออกจากฟังชั่นนี้เลย
        if not self.is_running:
            return
        while not self.input_queue.empty():
            
            try:
                
                
                
                # ดึงข้อมูลจากคิว (แบบไม่รอ)
                t_receive, weight = self.input_queue.get_nowait() 
                

                
                if self.check_round_calibration < 0 :
                    self.is_running = False
                    return
                 

                    
                #หากไม่มีเวลาเริ่มและนํ้าหนักเริ่ม ตอนนี้ ก่ให้มีซะ
                if self.start_time_original is None: self.start_time_original = t_receive 
                if self.start_weight_original is None: self.start_weight_original = weight
                    
                # ทุกการคำนวนทุกอย่าง มาจากตรงนี้
                result = self.engine_calculate.calculate_final(now_time=t_receive, now_weight=weight)                                     
                

                    
                time_elasped_originals = result.get("time_elasped_originals", 0.0)
                avg_regression_original = result.get("avg_regression_original", 0.0)
                point_regression_peak = result.get("point_regression_peak", 0.0)
                time_elasped_peak = result.get("time_elasped_peak", 0.0)
                type_point_peak = result.get("type_point_peak", "")
                avg_regression_mean = result.get("avg_regression_mean", 0.0)
                avg_regression_mean_dev = result.get("avg_regression_mean_dev", 0.0)
                avg_regression_single = result.get("avg_regression_single", 0.0)
                time_regression_elasped = result.get("time_regression_elasped", 0.0)

                # Interval
                ci_interval = result.get("ci_interval", 0.0)
                std_interval = result.get("std_interval", 0.0)

                # Time Regression
                avg_time_elasped_reg = result.get("avg_time_elasped_reg", 0.0)
                avg_time_elasped_reg_single = result.get("avg_time_elasped_reg_single", 0.0)
                ci_time_reg = result.get("ci_time_reg", 0.0)
                std_time_reg = result.get("std_time_reg", 0.0)

                # Cumulative
                avg_cumulative_first = result.get("avg_cumulative_first", 0.0)
                avg_cumulative_second = result.get("avg_cumulative_second", 0.0)
                t_for_all_cum = result.get("t_for_all_cum", 0.0)
                avg_cumulative_all = result.get("avg_cumulative_all", 0.0)

                # Error Cumulative
                avg_cum_err_f = result.get("avg_cum_err_f", 0.0)
                avg_cum_err_s = result.get("avg_cum_err_s", 0.0)
                avg_cum_err_all = result.get("avg_cum_err_all", 0.0)
                

                
                packet = {
                    "t_elasped_ori": time_elasped_originals,
                    "avg_reg_ori": avg_regression_original,
                    
                    "point_reg_pk": point_regression_peak,
                    "t_elasped_pk": time_elasped_peak,
                    
                    "avg_reg_mean": avg_regression_mean,
                    "avg_reg_mean_dev":avg_regression_mean_dev,            
                    "ty_point_pk": type_point_peak,
                    "avg_reg_sig": avg_regression_single,
                    
                    "t_reg_elasped": time_regression_elasped,
                    
                    # Interval
                    "ci_interval": ci_interval,
                    "std_interval": std_interval,
                    
                    # Regression Time
                    "avg_time_elasped_reg": avg_time_elasped_reg,
                    "avg_time_elasped_reg_single": avg_time_elasped_reg_single,
                    "ci_time_reg": ci_time_reg,
                    "std_time_reg": std_time_reg,
                    
                    # สำหรับกราฟแรก ค่า flowrate ปกติ สำหรับ สามเส้น
                    "avg_cum_ft": avg_cumulative_first,  
                    "avg_cum_se": avg_cumulative_second,
                    "t_for_all_cum": t_for_all_cum,
                    "avg_cum_all": avg_cumulative_all,
                    
                    # err dev ของ ค่าเฉลี่ย สามเส้น
                    "avg_cum_err_f": avg_cum_err_f, 
                    "avg_cum_err_s": avg_cum_err_s,
                    "avg_cum_err_all": avg_cum_err_all
                }
                
                # ยิงต่อไปให้ UI วาดกราฟ
                #print(f"DEBUG: กำลังจะ Emit -> {result}")
                self.stats_updated.emit(packet)
                
                
                
                if self.inter_finis_f is True and self.inter_finis_s is True:
                    self.is_running = False
                    print("ครบเวลาที่กำหนดแล้ว")
                    break   

                
            except queue.Empty:
                break # หมดคิวแล้ว ออกจากลูป
            except ValueError:
                print(f"ขยะหลุดมา แปลงเป็นตัวเลขไม่ได้: {weight}")
            except Exception as e:
                print(f"Engine คำนวณพลาด: {e}")








    def reset_session(self):
            """ล้างค่าเก่าทั้งหมด เพื่อเตรียมพร้อมรันรอบใหม่"""
            
            # 1. ปิดการทำงานของระบบเพื่อความปลอดภัย (รอให้ UI สั่งรันใหม่)
            self.is_running = False
            
            # 2. รีเซตกลุ่มตัวแปรเวลาและน้ำหนัก (จุด Start/End)
            self.start_time_original = None
            self.start_weight_original = None
            self.end_time_original = None
            self.end_weight_original = None
            
            self.start_time_first = None
            self.start_weight_first = None
            self.end_time_first = None
            self.end_weight_first = None
            
            self.start_time_second = None
            self.start_weight_second = None
            self.end_time_second = None
            self.end_weight_second = None
            
            # 3. รีเซตกลุ่มตัวแปรสถานะและค่าเฉลี่ย
            self.interval_counts = None
            self.evaporate_avg = None
            self.temperature_start = None
            self.temperature_end = None
            self.Humidity_start = None
            self.Humidity_end = None
            self.avg_each_session = None
            self.sd_each_session = None
            self.latest_cycle_detected = None

            # 4. ล้างข้อมูลใน list และ deque ทั้งหมดให้เกลี้ยง
            self.sub_regression_buffer.clear()
            self.list_cumulative_avg.clear()
            self.list_regression.clear()
            self.list_cumulative_regression.clear()
            self.list_interval_flowrate.clear()
            self.list_interval_time.clear()
            self.list_session_flowrate.clear()
            self.list_session_time.clear()
            self.cycle_history.clear()

            # 5. รีเซต CycleAnalyzer (สำคัญมาก!)
            # ต้องสร้าง instance ใหม่ เพื่อลบความจำเดิม (เช่น last_top, last_down) ของรอบที่แล้วทิ้ง
            self.cycle_analyzer = CycleAnalyzer(n_bar=self.buffer_n_bar)
            
            print("Engine: ล้างข้อมูลเก่า พร้อมรันรอบใหม่แล้ว")
    
    def change_mode(self, mode_name: str):   # โครงสร้างฟังชั่นสำหรับ เปลี่ยนรูปแบบ การสอบเทียบ
        """ ฟังก์ชันสำหรับเปลี่ยนโหมดเมื่อผู้ใช้กดเลือกบน UI """
        if mode_name == "Inspection":
            self.type_inscal = ArgosInspection()
        elif mode_name == "Calibration":
            self.type_inscal = ArgosCalibration()
        elif mode_name == "Test":
            self.type_inscal = ArgosTest()
        print(f"Engine: เปลี่ยนโหมดการทำงานเป็น {mode_name}")