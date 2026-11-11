
import numpy as np
from config.cache_data import T_SCORE_LOOKUP 
from collections import deque 
from typing import Optional, Dict, Any, Tuple ,List

class MainFilterSelection:
    def __init__(self, receive_self):
        self.main = receive_self
        self.use_first = True

    # --- ฟังก์ชันสถิติพื้นฐาน (ใช้ @staticmethod เพื่อประหยัด Memory และเร็ว) ---
    @staticmethod
    def time_elapsed(now_time: float, start_time: float):
        return max(0.0, now_time - start_time) if now_time > 0 and start_time is not None else 0.0
        
    @staticmethod
    def weight_elapsed(now_weight: float, start_weight: float):
        return max(0.0, now_weight - start_weight) if now_weight > 0 and start_weight is not None else 0.0

    @staticmethod
    def cumulative_average(now_weight: float, start_weight: float, time_elapsed: float):
        if time_elapsed <= 0 or start_weight is None: return 0.0
        return max(0.0, ((now_weight - start_weight) / time_elapsed) * 3600.0)

    @staticmethod
    def calculate_average_final_val(x: float, y: float):
        return  (x + y) / 2 if x > 0 and y > 0 else 0.0
    
    @staticmethod
    def calculate_dev_error(x: float, y: float) -> float:
        if x <= 0 or y == 0:
            return 0.0
        
        # คำนวณเปอร์เซ็นต์ความคลาดเคลื่อน

        return ((x - y) / y) * 100

    @staticmethod
    def std_list(list_x):
        if not list_x or len(list_x) < 2: return 0.0
        return 2 * float(np.std(list_x, ddof=1)) 

    @staticmethod
    def average_list(list_x):
        return float(np.mean(list_x)) if list_x else 0.0


    # --- ฟังก์ชันใหม่ (CI & SE) ปรับเป็น StaticMethod ให้เรียกใช้ง่าย ---
    @staticmethod
    def get_t_score(n: int) -> float:
        """ 
        ดึงค่า t-score แบบ Hybrid:
        - n < 2: ป้องกัน Error
        - 2 <= n <= 30: ดึงจาก Cache (Lookup Table)
        - n > 30: ใช้ค่าคงที่ z-score (1.96) สำหรับ 95% CI 
        """
        if n < 2:
            return 0.0
        # ช่วงที่ต้องการความแม่นยำสูง
        if 2 <= n <= 30:
            return T_SCORE_LOOKUP[n]
        # ช่วงที่ n เยอะแล้ว ใช้ค่าคงที่แทน (1.96 คือค่า z-score ของ 95% CI)
        # วิธีนี้เร็วกว่าและแม่นยำเพียงพอสำหรับงานวิศวกรรม
        return 2

    @staticmethod
    def get_standard_error(list_x) -> float:
        n = len(list_x)
        if n < 2: return 0.0
        return  float(np.std(list_x, ddof=1) / np.sqrt(n))
        
    @staticmethod
    def get_confidence_interval(list_x) -> tuple:
        n = len(list_x)
        # แก้ตรงนี้: ถ้า n < 2 ให้คืนค่า 4 ค่า (0.0) เพื่อให้ index ไม่พัง
        if n < 2: return 0.0, 0.0, 0.0, 0.0 
        
        t_score = MainFilterSelection.get_t_score(n) 
        mean = np.mean(list_x)
        se = MainFilterSelection.get_standard_error(list_x)
        margin = t_score * se
        
        # คืนค่า 4 ค่าเสมอ
        return float(mean - margin), float(mean + margin), mean, float(margin)
        
        

    # --- ฟังก์ชันหลัก (Regression) ---
    def calculate_regression_slope(self, buffer: List[Tuple[float, float]]) -> float:
        n = len(buffer)
        if n < 3: return 0.0

        t0 = buffer[0][0]
        sum_t = sum_w = sum_t2 = sum_tw = 0.0
        
        # ลูปนี้ทำงานเร็วอยู่แล้ว
        for t, w in buffer:
            t_adj = t - t0
            sum_t += t_adj
            sum_w += w
            sum_t2 += t_adj * t_adj
            sum_tw += t_adj * w

        denominator = (n * sum_t2) - (sum_t ** 2)
        if abs(denominator) < 1e-6: return 0.0

        slope = ((n * sum_tw) - (sum_t * sum_w)) / denominator
        flow = slope * 3600.0 

        target_flow = getattr(self.main, 'target_flow', None)
        if target_flow is not None:
            flow =  min(flow, target_flow * 5.0)
            
        return flow
    

    
class IntervalLoopCountTime(MainFilterSelection):
    def calculate_final(self, now_time: float, now_weight: float):
        # ==========================================
        # 1. INITIALIZATION: ประกาศ Default Dictionary 
        # ==========================================
        result = {    
            "time_elasped_originals": 0.0,
            "avg_regression_original": 0.0,
            "point_regression_peak": 0.0,
            "time_elasped_peak": 0.0,
            "type_point_peak": "",
            "avg_regression_mean": 0.0,
            "avg_regression_mean_dev": 0.0,
            "avg_regression_single": 0.0,
            "time_regression_elasped": 0.0,
            "ci_interval": 0.0,
            "std_interval": 0.0,
            
            "avg_time_elasped_reg": 0.0,
            "avg_time_elasped_reg_single": 0.0,
            "ci_time_reg": 0.0,
            "std_time_reg": 0.0,
            
            "avg_cumulative_first": 0.0,
            "avg_cumulative_second": 0.0,
            "t_for_all_cum": 0.0,
            "avg_cumulative_all": 0.0,
            "avg_cum_err_f": 0.0,
            "avg_cum_err_s": 0.0,
            "avg_cum_err_all": 0.0,
        }
        

        # ==========================================
        # 2. EARLY RETURNS: เช็คเงื่อนไขและคืนค่ากลับถ้ายังไม่ถึงเวลา
        # ==========================================
        time_elasped_original = self.time_elapsed(now_time, self.main.start_time_original)
        
        if time_elasped_original < 2.00:
            return result

        self.main.sub_regression_buffer.append((time_elasped_original, now_weight))
        current_slope = self.calculate_regression_slope(self.main.sub_regression_buffer)  
        self.main.list_regression.append(current_slope)
        
        result["time_elasped_originals"] = time_elasped_original
        result["avg_regression_original"] = current_slope
        
        len_countfor_original_reg = self.main.buffer_regression 
        if len(self.main.list_regression) < len_countfor_original_reg:
            return result

        # ==========================================
        # 3. CYCLE ANALYSIS: วิเคราะห์จุด Peak และ Cycle
        # ==========================================
        res = self.main.cycle_analyzer.update(now_time, now_weight, current_slope)
        
        if res is not None:
            result["time_elasped_peak"] = self.time_elapsed(res["point"]["data"][0], self.main.start_time_original)
            result["point_regression_peak"] = res["point"]["data"][2]
            result["type_point_peak"] = res["point"]["type"]
            
            if res["cycle"] is not None:
                self.main.latest_cycle_detected = res["cycle"]
                self.main.cycle_history.append(res["cycle"])
                
                start_t, start_raw, start_slope = res["cycle"]["start"]
                end_t, end_raw, end_slope = res["cycle"]["end"]
                  
                # เก็บค่าเริ่มต้นของรอบแรกและรอบสอง
                if self.main.start_time_first is None:
                    self.main.start_time_first = start_t
                    self.main.start_weight_first = start_raw
     
                    
                elif self.main.start_time_second is None and self.main.start_time_first is not None:
                    self.main.start_time_second = start_t
                    self.main.start_weight_second = start_raw
   
                
                
                # เลือกตัวแปรตาม flag
                target_time = self.main.start_time_first if self.use_first else self.main.start_time_second
                time_starttoend = self.time_elapsed(end_t, target_time)

                # สลับ flag ให้เป็นค่าตรงข้าม (True -> False, False -> True)
                self.use_first = not self.use_first
                
                t_target_sec = self.main.limit_time_mode * 60
                
                # [แก้ไข] เช็คเงื่อนไขเฉพาะเส้นที่เพิ่งประมวลผลเสร็จเท่านั้น
                # เนื่องจากด้านบนสลับ flag ไปแล้ว ถ้าตอนนี้เป็น False แปลว่าเพิ่งทำ first (a) เสร็จ
                if not self.use_first:
                    t_st_ed_1 = self.time_elapsed(end_t, self.main.start_time_first)
                    if t_st_ed_1 >= t_target_sec and not self.main.inter_finis_f:
                        self.main.inter_finis_f = True
                else:
                    t_st_ed_2 = self.time_elapsed(end_t, self.main.start_time_second)
                    if t_st_ed_2 >= t_target_sec and not self.main.inter_finis_s:
                        self.main.inter_finis_s = True
                    
                time_elasped_first = self.time_elapsed(end_t, start_t) 
                
                           
                cumulative_average_first = self.cumulative_average(end_raw, start_raw, time_elasped_first)
   
                
                # เอาไว้ใช้กราฟสองและสาม
                self.main.list_interval_flowrate.append(cumulative_average_first)
                self.main.list_interval_time.append(time_elasped_first)
                
                # หา SE, Mean, CI
                list_low_high_me_mg_interval = self.get_confidence_interval(self.main.list_interval_flowrate)
                err_ci_dev = self.main.target_flow - list_low_high_me_mg_interval[3]
                err_std_dev = self.main.target_flow - self.std_list(self.main.list_interval_flowrate)
                

                list_low_high_me_mg_time_interval = self.get_confidence_interval(self.main.list_interval_time)

                
                # อัปเดตข้อมูล Flowrate ลง result
                result["avg_regression_mean"] = list_low_high_me_mg_interval[2]
                result["avg_regression_single"] = cumulative_average_first
                result["time_regression_elasped"] = time_starttoend
                result["avg_regression_mean_dev"] = self.calculate_dev_error(list_low_high_me_mg_interval[2], self.main.target_flow)
                result["ci_interval"] = self.calculate_dev_error(err_ci_dev,self.main.target_flow)
                result["std_interval"] = self.calculate_dev_error(err_std_dev,self.main.target_flow)
                
                # อัปเดตข้อมูล Time ลง result
                result["avg_time_elasped_reg"] = list_low_high_me_mg_time_interval[2]
                result["avg_time_elasped_reg_single"] = time_elasped_first
                result["ci_time_reg"] = list_low_high_me_mg_time_interval[3]
                result["std_time_reg"] = self.std_list(self.main.list_interval_time)
                
                self.main.avg_each_session = result["avg_time_elasped_reg"]
                
        # ==========================================
        # 4. CUMULATIVE CALCULATION: คำนวณค่าสะสมทั้งหมด
        # ==========================================
        if self.main.start_time_first is not None:
            result["t_for_all_cum"] = self.time_elapsed(now_time, self.main.start_time_first)
            result["avg_cumulative_first"] = self.cumulative_average(now_weight, self.main.start_weight_first, result["t_for_all_cum"])
            result["avg_cum_err_f"] = self.calculate_dev_error(result["avg_cumulative_first"], self.main.target_flow)
            
        if self.main.start_time_second is not None:
            second_cumulative_elasped_t = self.time_elapsed(now_time, self.main.start_time_second)  
            result["avg_cumulative_second"] = self.cumulative_average(now_weight, self.main.start_weight_second, second_cumulative_elasped_t)
            result["avg_cum_err_s"] = self.calculate_dev_error(result["avg_cumulative_second"], self.main.target_flow)
            
        if result["avg_cumulative_first"] > 0.0 and result["avg_cumulative_second"] > 0.0: 
            result["avg_cumulative_all"] = self.calculate_average_final_val(result["avg_cumulative_first"], result["avg_cumulative_second"])
            result["avg_cum_err_all"] = self.calculate_dev_error(result["avg_cumulative_all"], self.main.target_flow)

        return result
     
class IntervalLoopNBar(MainFilterSelection):
        def calculate_final(self): 
            pass

  
class TimeLoop(MainFilterSelection):
    def calculate_for_all(self):
        pass

class CombinationTimeInterval(MainFilterSelection):
    def calculate_for_all(self):
        pass
        

# ---------------------------------------------------------
# 4. CycleAnalyzer - Fixed Flat Extrema (Spamming Issue)
# ---------------------------------------------------------
from collections import deque
from typing import Optional, Tuple, Dict, Any

class CycleAnalyzer:
    def __init__(self, n_bar: int = 50):
        self.n_bar = n_bar
        self.window_size = 2 * n_bar + 1
        
        self.dq_raw = deque(maxlen=self.window_size)
        self.dq_slope = deque(maxlen=self.window_size)
        self.dq_time = deque(maxlen=self.window_size)
        
        self.last_top: Optional[Tuple[float, float, float]] = None
        self.last_down: Optional[Tuple[float, float, float]] = None
        
        self.last_point_type: Optional[str] = None 
        self.last_saved_time: Optional[float] = None

    def update(self, t: float, raw: float, slope: float) -> Optional[Dict[str, Any]]:
        self.dq_time.append(t)
        self.dq_raw.append(raw)
        self.dq_slope.append(slope)
        
        if len(self.dq_slope) < self.window_size:
            return None
            
        center_slope = self.dq_slope[self.n_bar]
        max_slope = max(self.dq_slope)
        min_slope = min(self.dq_slope)
        
        # [Fix 1] ป้องกันกรณี Flat Line ตลอดทั้ง Window (ไม่มี Peak/Valley จริง)
        if max_slope == min_slope:
            return None
            
        # ค้นหา Peak/Valley ภายใน Window
        is_valley = (center_slope == min_slope)
        is_peak = (center_slope == max_slope)
        
        if not (is_valley or is_peak):
            return None
            
        exact_time = self.dq_time[self.n_bar]
        
        if exact_time == self.last_saved_time:
            return None
            
        point_type = "TOP" if is_peak else "DOWN"
        current_point = (exact_time, self.dq_raw[self.n_bar], center_slope)
        
        # [Fix 2] บังคับ State Alternation กรองจุดที่ประเภทซ้ำกันทิ้ง
        if point_type == self.last_point_type:
            # แม้เราจะไม่พ่น Result ออกไปเพื่อกัน Spam แต่เราสามารถ "แอบจด" 
            # จุดที่ดีกว่าในระนาบเดียวกันไว้ได้ เพื่อให้ Cycle สมบูรณ์ที่สุด
            if point_type == "TOP" and self.last_top:
                if current_point[1] > self.last_top[1]:  # สนใจจุดที่ raw สูงกว่า
                    self.last_top = current_point
            elif point_type == "DOWN" and self.last_down:
                if current_point[1] < self.last_down[1]: # สนใจจุดที่ raw ต่ำกว่า
                    self.last_down = current_point
                    
            self.last_saved_time = exact_time
            return None  # คืนค่า None ไปเลย ระบบจะได้ไม่รัว
            
        self.last_saved_time = exact_time
        
        result = {
            "point": {"type": point_type, "data": current_point},
            "cycle": None 
        }
        
        # --- Multi-Phase Temporal Resolution ---
        if point_type == "TOP":
            if self.last_point_type == "DOWN" and self.last_top is not None:
                result["cycle"] = {
                    "pattern": "TOP-DOWN-TOP",
                    "start": self.last_top,
                    "end": current_point
                }
            self.last_top = current_point
            self.last_point_type = "TOP"
            
        elif point_type == "DOWN":
            if self.last_point_type == "TOP" and self.last_down is not None:
                result["cycle"] = {
                    "pattern": "DOWN-TOP-DOWN",
                    "start": self.last_down,
                    "end": current_point
                }
            self.last_down = current_point
            self.last_point_type = "DOWN"
            
        return result