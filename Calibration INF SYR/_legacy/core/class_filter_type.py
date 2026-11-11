import numpy as np
from core.function_math import FunctionMath, StreamingCycleAnalyzer


class SelectTypeInsCal:
    def __init__ (self, obj):
        self.select_type = obj
        self._handlers = {
            "Inspection": ArgosInspection,
            "Calibration": ArgosCalibration,
            "Test": ArgosTest
        }
    
    def get_handler_class(self):
        mode_name = self.select_type
        return self._handlers.get(mode_name) # คืนค่ากลับไปเป็น Class เฉยๆ




class ArgosInspection:
    def __init__(self, obj): # รับแค่เจ้านายพอ
        self.argos = obj
        self.mode_precise_handler = ModePrecise(self.argos)
        
    def calculate(self, time_now, weight_now): # ส่งตัวเลขเข้ามาทางนี้แทน
        if self.argos.mode == 1: 
            return self.mode_precise_handler.count_mode(time_now, weight_now)
        else:
            return self.mode_precise_handler.normal_count_mode(time_now, weight_now)
 
                      


# class_filter_type.py
class ModePrecise:
    def __init__(self, obj):
        self.mode_precise = obj # อันนี้เก็บไว้ถูกต้องแล้ว เพราะต้องใช้อ่านค่า/เซ็ตค่าโหมด
        self.fun_math_basic = FunctionMath() # สร้างเครื่องคิดเลขเปล่าๆ
        self.fun_math_advanced = StreamingCycleAnalyzer(n_bar=5)
        
    def count_mode(self, time_now: float, weight_now: float):
        # 1. ดึงตัวเลขออกมาก่อนเพื่อความสะอาดของโค้ด
        t_start = self.mode_precise.start_time
        w_start = self.mode_precise.start_weight
        
        # 2. โยน "ตัวเลข" เข้าเครื่องคิดเลข
        time_elapsed = self.fun_math_basic.time_elapsed(time_now, t_start)
        weight_elapsed = self.fun_math_basic.weight_elapsed(weight_now, w_start)
        
        self.mode_precise.regression_buffer.append((time_elapsed, weight_now))

        # สมมติว่าดึง safe_target_flow มาจากออบเจกต์หลัก
        limit_flow = self.mode_precise.safe_target_flow
        flow = self.fun_math_basic.calculate_regression_slope(self.mode_precise.regression_buffer,limit_flow)
        
        # 3. คำนวณ AVG โดยใช้ตัวเลขที่เตรียมไว้
        avg = self.fun_math_basic.cumulative_average(weight_now, w_start, time_elapsed)

        # ----- จุดจัดการลูปย่อย (โค้ดเดิมของคุณ) -----
        result_counting = self.fun_math_advanced.update(time_now, weight_now, flow)
        if result_counting is not None:
            self.mode_precise.start_weight = result_counting[3]
            self.mode_precise.start_time = result_counting[4]
            self.mode_precise.mode = 0 
            
        return {
            "elapsed": time_elapsed,
            "flow": flow,
            "avg": avg
        }
        
    def normal_count_mode(self,time_now:float,weight_now:float):
        time_elapsed = self.fun_math_basic.time_elapsed(time_now, t_start)
        weight_elapsed = self.fun_math_basic.weight_elapsed(weight_now, w_start)
        self.mode_precise.regression_buffer.append((time_elapsed, weight_now))
        flow = self.fun_math_basic.calculate_regression_slope(self.mode_precise.regression_buffer)
        avg = self.fun_math_basic.cumulative_average(weight_now, w_start, time_elapsed)
        
        return {
            "elapsed": time_elapsed,
            "flow": flow,
            "avg": avg
        }
