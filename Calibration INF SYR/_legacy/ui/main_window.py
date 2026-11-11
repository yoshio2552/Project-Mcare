import sys
import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QLineEdit, QFormLayout, QFrame, 
                               QListWidget, QSpinBox, QGridLayout, QGraphicsProxyWidget, QSizePolicy)
from PySide6.QtCore import Qt
import numpy as np

# ---------------------------------------------------------
# 1. โมดูลกราฟ (Graph Module) - Pro Edition (No Lag / Pre-allocated + Modern Dashboard)
# ---------------------------------------------------------
class GraphBoard(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- ตั้งค่า Theme สากล ---
        pg.setConfigOption('background', '#1E1E1E')
        pg.setConfigOption('foreground', '#E0E0E0')

        # ==========================================
        # [NEW] MODERN STATS DASHBOARD 
        # ==========================================
        # ตัวแปรเก็บค่าสถิติล่าสุด (ป้องกัน Error กรณีไม่มีข้อมูล)
        self.cur_err_f = np.nan; self.cur_err_s = np.nan; self.cur_err_all = np.nan
        self.cur_ci_interval = np.nan; self.cur_std_interval = np.nan
        self.cur_avg_reg_mean = np.nan; self.cur_avg_reg_single = np.nan
        self.cur_avg_reg_mean_dev = np.nan; self.cur_avg_reg_single = np.nan
        self.cur_avg_time_reg = np.nan; self.cur_avg_time_single = np.nan
        self.cur_ci_time = np.nan; self.cur_std_time = np.nan

        self.dashboard_layout = QHBoxLayout()
        self.dashboard_layout.setSpacing(15)
        
        # สร้าง Card สถิติ 3 ใบ
        card1, self.labels_g1 = self.create_stat_card("📊 G1: Percent Error", "#00BCD4", [
            ("err_f", "FT Error:", "#00BCD4"),
            ("err_s", "SE Error:", "#FF4081"),
            ("err_all", "ALL Error:", "#00E676")
        ])
        
        card2, self.labels_g2 = self.create_stat_card("📈 G2: Flow Regression", "#FF9800", [
            ("mean", "Avg Mean:", "#FFEB3B"),
            ("single", "Single:", "#FF9800"),
            ("ci", "CI Interval:", "#E0E0E0"),
            ("std", "Std Dev:", "#E0E0E0")
        ])
        
        card3, self.labels_g3 = self.create_stat_card("⏱️ G3: Timing & Peaks", "#29B6F6", [
            ("avg_t", "Avg Time:", "#29B6F6"),
            ("sin_t", "Single Time:", "#81D4FA"),
            ("ci_t", "CI Time:", "#E0E0E0"),
            ("std_t", "Std Time:", "#E0E0E0")
        ])
        
        self.dashboard_layout.addWidget(card1)
        self.dashboard_layout.addWidget(card2)
        self.dashboard_layout.addWidget(card3)
        layout.addLayout(self.dashboard_layout)
        # ==========================================

        self.graph_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graph_widget)
        
        self.window_size = 350
        self.graph2_max_time = 350
        self.graph3_window_size = 300
        # ==========================================
        # SENIOR DEV NOTE: GRAPH GRID ARCHITECTURE
        # เปลี่ยนระบบ Grid เป็นรองรับคอลัมน์ใหม่ด้านขวาสุด
        # ==========================================

        # กราฟ 1 (ซ้ายบน): Rolling Window (3 เส้น)
        self.plot_1 = self.graph_widget.addPlot(row=0, col=0, colspan=2, title="Cumulative Averages (Rolling)")
        self.plot_1.setClipToView(True)            
        self.plot_1.setDownsampling(ds=True, auto=True, mode='peak')
        self.plot_1.showGrid(x=True, y=True, alpha=0.3)
        self.plot_1.addLegend(offset=(10, 10))
        
        self.curve_1_ft  = self.plot_1.plot(pen=pg.mkPen('#00BCD4', width=2), name="Avg Cum FT")
        self.curve_1_se  = self.plot_1.plot(pen=pg.mkPen('#FF4081', width=2), name="Avg Cum SE")
        self.curve_1_all = self.plot_1.plot(pen=pg.mkPen('#00E676', width=2), name="Avg Cum ALL")

        # กราฟ 2 (ขวาบน): Auto-Step 1 Min (Line + Scatter + Mean Line)
        self.plot_2 = self.graph_widget.addPlot(row=0, col=2, colspan=2, title="Flow Rate Regression (Step 1 Min)")
        self.plot_2.setClipToView(True)            
        self.plot_2.setDownsampling(ds=True, auto=True, mode='peak')
        self.plot_2.showGrid(x=True, y=True, alpha=0.3)
        self.plot_2.setXRange(0, self.graph2_max_time, padding=0)
        
        self.curve_2_even = self.plot_2.plot(
            pen=pg.mkPen('#FF9800', width=2), 
            symbol='o', symbolSize=7, symbolBrush='#FF9800', symbolPen='#FFFFFF',
            name="Even Points"
        )
        
        self.curve_2_odd = self.plot_2.plot(
            pen=pg.mkPen('#03A9F4', width=2), 
            symbol='o', symbolSize=7, symbolBrush='#03A9F4', symbolPen='#FFFFFF',
            name="Odd Points"
        )
        
        self.mean_line_2 = pg.InfiniteLine(angle=0, pen=pg.mkPen('#FFEB3B', width=2, style=Qt.PenStyle.DashLine))
        self.plot_2.addItem(self.mean_line_2)

        # กราฟ 3 (ซ้ายล่าง): Rolling Window แบบซ้อน Base Line กับ Point
        self.plot_3 = self.graph_widget.addPlot(row=1, col=0, colspan=2, title="Acceleration & Pump Rotation Loop")
        self.plot_3.setClipToView(True)            
        self.plot_3.setDownsampling(ds=True, auto=True, mode='peak')
        self.plot_3.showGrid(x=True, y=True, alpha=0.3)
        self.plot_3.addLegend(offset=(10, 10))
        
        self.curve_3_base = self.plot_3.plot(pen=pg.mkPen('#29B6F6', width=2), name="Avg Reg Ori")
        self.scatter_3_pk = pg.ScatterPlotItem(size=7, pen=pg.mkPen('#FFFFFF', width=1.2), brush=pg.mkBrush('#D50000'), name="Peaks")
        self.plot_3.addItem(self.scatter_3_pk)

        # กราฟ 4 (ขวาล่าง ส่วนซ้าย)
        self.plot_4 = self.graph_widget.addPlot(row=1, col=2, colspan=1, title="Future Feature Placeholder")
        self.plot_4.showGrid(x=True, y=True, alpha=0.3)

        # ==========================================
        # [NEW] Data/Info Panel (ขวาล่าง ส่วนขวา - ถัดจากกราฟ 4)
        # ==========================================
        self.info_panel = QFrame()
        self.info_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.info_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                border: 1px dashed #555555;
                margin: 10px;
            }
        """)
        
        info_layout = QVBoxLayout(self.info_panel)
        
        self.lbl_info_title = QLabel("📌 Extra Data Panel")
        self.lbl_info_title.setStyleSheet("color: #00BCD4; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        
        self.lbl_info_desc = QLabel("พื้นที่เว้นไว้สำหรับเพิ่ม Widget\nหรือแสดงข้อมูลต่างๆ ในอนาคต")
        self.lbl_info_desc.setStyleSheet("color: #9E9E9E; font-size: 12px; border: none; background: transparent;")
        self.lbl_info_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_layout.addWidget(self.lbl_info_title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_info_desc)
        info_layout.addStretch()

        self.proxy_info = QGraphicsProxyWidget()
        self.proxy_info.setWidget(self.info_panel)
        self.graph_widget.addItem(self.proxy_info, row=1, col=3, colspan=1)
        
        # ==========================================
        # [NEW] LONG RIGHT PANEL (คอลัมน์ขวายาว ครอบบนลงล่าง)
        # ถัดจากกราฟ 2 (col=2,3) และ Data Panel (col=3) -> ไปลงที่ col=4
        # ==========================================
        self.right_col_panel = QFrame()
        self.right_col_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_col_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 8px;
                border: 1px solid #3A3A3C;
                margin: 10px 10px 10px 0px;
            }
        """)
        
        right_panel_layout = QVBoxLayout(self.right_col_panel)
        right_panel_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_right_title = QLabel("📡 System Logs")
        lbl_right_title.setStyleSheet("color: #FFEB3B; font-weight: bold; font-size: 14px; border: none; background: transparent; border-bottom: 1px solid #444; padding-bottom: 5px;")
        
        self.mock_log_list = QListWidget()
        self.mock_log_list.setStyleSheet("""
            QListWidget {
                background-color: transparent; border: none; color: #A0A0A0; font-size: 12px;
            }
            QListWidget::item { padding: 4px 0; border-bottom: 1px dashed #333; }
        """)
        self.mock_log_list.addItems([
            "[SYS] Booted Sequence",
            "[SYS] Calibrating...",
            "[SYS] Memory Allocated",
            "[OK]  Ready for stream",
            "Waiting for START..."
        ])
        
        btn_clear_log = QPushButton("🧹 Clear Logs")
        btn_clear_log.setStyleSheet("QPushButton { background-color: #333; color: #FFF; padding: 6px; border-radius: 4px; border: 1px solid #555; } QPushButton:hover { background-color: #444; }")
        
        right_panel_layout.addWidget(lbl_right_title)
        right_panel_layout.addWidget(self.mock_log_list)
        right_panel_layout.addWidget(btn_clear_log)
        
        self.proxy_right_col = QGraphicsProxyWidget()
        self.proxy_right_col.setWidget(self.right_col_panel)
        
        # เพิ่มเข้าตารางที่ Column 4, คลุม 2 แถวเพื่อความยาวเต็มจอ (rowspan=2)
        self.graph_widget.addItem(self.proxy_right_col, row=0, col=4, rowspan=2, colspan=1)
        # ==========================================

        # ---------------------------------------------------------
        # Data Buffers (เปลี่ยนเป็น NumPy จองพื้นที่ล่วงหน้า)
        # ---------------------------------------------------------
        self.max_pts = 10000
        
        self.x1_cum = np.full(self.max_pts, np.nan); self.y1_ft = np.full(self.max_pts, np.nan)
        self.y1_se = np.full(self.max_pts, np.nan);  self.y1_all = np.full(self.max_pts, np.nan)
        self.ptr1 = 0
        
        self.x2_reg = np.full(self.max_pts, np.nan); self.y2_sig = np.full(self.max_pts, np.nan)
        self.ptr2 = 0
        
        self.x3_ori = np.full(self.max_pts, np.nan); self.y3_ori = np.full(self.max_pts, np.nan)
        self.x3_pk  = np.full(self.max_pts, np.nan); self.y3_pk  = np.full(self.max_pts, np.nan)
        self.ptr3 = 0; self.ptr3_pk = 0
        
        self.frame_count = 0

    def create_stat_card(self, title, accent_color, metrics):
        """ ฟังก์ชันผู้ช่วยสำหรับสร้าง Card สถิติสุดโมเดิร์น """
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #252526;
                border-radius: 8px;
                border: 1px solid #333333;
                border-top: 3px solid {accent_color};
            }}
            QLabel {{ border: none; background: transparent; }}
            .card-title {{ color: #FFFFFF; font-size: 13px; font-weight: bold; padding-bottom: 5px; }}
            .metric-name {{ color: #9E9E9E; font-size: 12px; }}
            .metric-value {{ font-size: 14px; font-weight: bold; }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "card-title")
        layout.addWidget(lbl_title)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(5)
        
        labels_dict = {}
        # Loop จัดวาง Label เป็นตาราง Grid
        for i, (m_key, m_name, val_color) in enumerate(metrics):
            row = i // 2
            col = (i % 2) * 2
            
            lbl_name = QLabel(m_name)
            lbl_name.setProperty("class", "metric-name")
            
            lbl_val = QLabel("--")
            lbl_val.setProperty("class", "metric-value")
            lbl_val.setStyleSheet(f"color: {val_color};")
            
            grid.addWidget(lbl_name, row, col)
            grid.addWidget(lbl_val, row, col + 1)
            
            labels_dict[m_key] = lbl_val
            
        layout.addLayout(grid)
        return card, labels_dict

    def format_val(self, val, unit=""):
        """ ช่วยแปลงตัวเลขให้แสดงผลสวยงาม (ทศนิยม 4 ตำแหน่ง) """
        if val is None or np.isnan(val):
            return "--"
        return f"{val:.4f}{unit}"

    def set_window_size(self, size_in_seconds: int):
        self.window_size = size_in_seconds

    def update_graphs(self, packets):
        if isinstance(packets, dict):
            packets = [packets]
            
        if not packets:
            return

        for packet in packets:
            # สถิติสำหรับกราฟ 1
            if packet.get("avg_cum_err_f") is not None and packet.get("avg_cum_err_f") != 0.0: self.cur_err_f = packet["avg_cum_err_f"]
            if packet.get("avg_cum_err_s") is not None and packet.get("avg_cum_err_s") != 0.0: self.cur_err_s = packet["avg_cum_err_s"]
            if packet.get("avg_cum_err_all") is not None and packet.get("avg_cum_err_all") != 0.0: self.cur_err_all = packet["avg_cum_err_all"]
            
            # สถิติสำหรับกราฟ 2
            if packet.get("ci_interval") is not None and packet.get("ci_interval") != 0.0: self.cur_ci_interval = packet["ci_interval"]
            if packet.get("std_interval") is not None and packet.get("std_interval") != 0.0: self.cur_std_interval = packet["std_interval"]
            
            if packet.get("avg_reg_mean") is not None and packet.get("avg_reg_mean") != 0.0: self.cur_avg_reg_mean = packet["avg_reg_mean"]
            if packet.get("avg_reg_mean_dev") is not None and packet.get("avg_reg_mean_dev") != 0.0: self.cur_avg_reg_mean_dev = packet["avg_reg_mean_dev"]
            if packet.get("avg_regression_single") is not None and packet.get("avg_regression_single") != 0.0: self.cur_avg_reg_single = packet["avg_regression_single"]
            
            # สถิติสำหรับกราฟ 3
            if packet.get("avg_time_elasped_reg") is not None and packet.get("avg_time_elasped_reg") != 0.0: self.cur_avg_time_reg = packet["avg_time_elasped_reg"]
            if packet.get("avg_time_elasped_reg_single") is not None and packet.get("avg_time_elasped_reg_single") != 0.0: self.cur_avg_time_single = packet["avg_time_elasped_reg_single"]
            if packet.get("ci_time_reg") is not None and packet.get("ci_time_reg") != 0.0: self.cur_ci_time = packet["ci_time_reg"]
            if packet.get("std_time_reg") is not None and packet.get("std_time_reg") != 0.0: self.cur_std_time = packet["std_time_reg"]

            # --- Graph 1 Logic ---
            t1 = packet.get("t_for_all_cum")
            if t1 is not None and t1 > 0:
                val_ft = packet.get("avg_cum_ft", 0.0)
                val_se = packet.get("avg_cum_se", 0.0)
                val_all = packet.get("avg_cum_all", 0.0)
                
                v_ft = val_ft if val_ft != 0.0 else np.nan
                v_se = val_se if val_se != 0.0 else np.nan
                v_all = val_all if val_all != 0.0 else np.nan
                
                if self.ptr1 < self.max_pts:
                    self.x1_cum[self.ptr1] = t1
                    self.y1_ft[self.ptr1] = v_ft
                    self.y1_se[self.ptr1] = v_se
                    self.y1_all[self.ptr1] = v_all
                    self.ptr1 += 1
                else:
                    self.x1_cum[:-1] = self.x1_cum[1:]; self.x1_cum[-1] = t1
                    self.y1_ft[:-1] = self.y1_ft[1:]; self.y1_ft[-1] = v_ft
                    self.y1_se[:-1] = self.y1_se[1:]; self.y1_se[-1] = v_se
                    self.y1_all[:-1] = self.y1_all[1:]; self.y1_all[-1] = v_all

            # --- Graph 2 Logic ---
            t2 = packet.get("t_reg_elasped")
            if t2 is not None and t2 > 0:
                val_sig = packet.get("avg_reg_sig", 0.0)
                if self.ptr2 < self.max_pts:
                    self.x2_reg[self.ptr2] = t2
                    self.y2_sig[self.ptr2] = val_sig
                    self.ptr2 += 1
                else:
                    self.x2_reg[:-1] = self.x2_reg[1:]; self.x2_reg[-1] = t2
                    self.y2_sig[:-1] = self.y2_sig[1:]; self.y2_sig[-1] = val_sig
                    
                mean_val = packet.get("avg_reg_mean")
                if mean_val is not None and mean_val != 0.0:
                    self.mean_line_2.setValue(mean_val)

            # --- Graph 3 Base Logic ---
            t3_base = packet.get("t_elasped_ori")
            if t3_base is not None and t3_base > 0:
                val_ori = packet.get("avg_reg_ori", 0.0)
                if self.ptr3 < self.max_pts:
                    self.x3_ori[self.ptr3] = t3_base
                    self.y3_ori[self.ptr3] = val_ori
                    self.ptr3 += 1
                else:
                    self.x3_ori[:-1] = self.x3_ori[1:]; self.x3_ori[-1] = t3_base
                    self.y3_ori[:-1] = self.y3_ori[1:]; self.y3_ori[-1] = val_ori

            # --- Graph 3 Peaks Logic ---
            t3_pk = packet.get("t_elasped_pk")
            if t3_pk is not None and t3_pk > 0:
                val_pk = packet.get("point_reg_pk", 0.0)
                if self.ptr3_pk == 0 or self.x3_pk[self.ptr3_pk - 1] != t3_pk:
                    if self.ptr3_pk < self.max_pts:
                        self.x3_pk[self.ptr3_pk] = t3_pk
                        self.y3_pk[self.ptr3_pk] = val_pk
                        self.ptr3_pk += 1
                    else:
                        self.x3_pk[:-1] = self.x3_pk[1:]; self.x3_pk[-1] = t3_pk
                        self.y3_pk[:-1] = self.y3_pk[1:]; self.y3_pk[-1] = val_pk

        self.frame_count += 1
        
        # ปรับอัปเดตกราฟเป็น % 1 ตามที่ใช้ในโค้ดเดิมของคุณ
        update_ui = (self.frame_count % 1 == 0)

        if update_ui:
            # --- อัปเดต Text Labels บน Dashboard ---
            self.labels_g1["err_f"].setText(self.format_val(self.cur_err_f, "%"))
            self.labels_g1["err_s"].setText(self.format_val(self.cur_err_s, "%"))
            self.labels_g1["err_all"].setText(self.format_val(self.cur_err_all, "%"))
            
            self.labels_g2["mean"].setText(self.format_val(self.cur_avg_reg_mean_dev))
            self.labels_g2["single"].setText(self.format_val(self.cur_avg_reg_single))
            self.labels_g2["ci"].setText(self.format_val(self.cur_ci_interval))
            self.labels_g2["std"].setText(self.format_val(self.cur_std_interval))
            
            self.labels_g3["avg_t"].setText(self.format_val(self.cur_avg_time_reg, "s"))
            self.labels_g3["sin_t"].setText(self.format_val(self.cur_avg_time_single, "s"))
            self.labels_g3["ci_t"].setText(self.format_val(self.cur_ci_time))
            self.labels_g3["std_t"].setText(self.format_val(self.cur_std_time))

            # --- อัปเดตกราฟ ---
            if self.ptr1 > 0:
                x1_view = self.x1_cum[:self.ptr1]
                self.curve_1_ft.setData(x1_view, self.y1_ft[:self.ptr1])
                self.curve_1_se.setData(x1_view, self.y1_se[:self.ptr1])
                self.curve_1_all.setData(x1_view, self.y1_all[:self.ptr1])
                
                t1_last = x1_view[-1]
                min_x = max(0, t1_last - self.window_size)
                self.plot_1.setXRange(min_x, max(self.window_size, t1_last), padding=0)

            # --- อัปเดตกราฟ (ตรงช่วง if self.ptr2 > 0) ---
            if self.ptr2 > 0:
                x2_view = self.x2_reg[:self.ptr2]
                y2_view = self.y2_sig[:self.ptr2]
                
                # ใช้ Slicing แยก: [0::2] คือ index 0, 2, 4... | [1::2] คือ index 1, 3, 5...
                self.curve_2_even.setData(x2_view[0::2], y2_view[0::2])
                self.curve_2_odd.setData(x2_view[1::2], y2_view[1::2])

                
                t2_last = x2_view[-1]
                if t2_last > self.graph2_max_time:
                    self.graph2_max_time = (int(t2_last / 60) + 1) * 60
                    self.plot_2.setXRange(0, self.graph2_max_time, padding=0)

            if self.ptr3 > 0:
                x3_view = self.x3_ori[:self.ptr3]
                self.curve_3_base.setData(x3_view, self.y3_ori[:self.ptr3])
                
                t3_last = x3_view[-1]
                min_x3 = max(0, t3_last - self.graph3_window_size)
                self.plot_3.setXRange(min_x3, max(self.graph3_window_size, t3_last), padding=0)

            if self.ptr3_pk > 0:
                self.scatter_3_pk.setData(self.x3_pk[:self.ptr3_pk], self.y3_pk[:self.ptr3_pk])

    def clear_graphs(self):
        """ ล้างข้อมูลเมื่อกดปุ่มเริ่มใหม่ """
        self.ptr1 = 0; self.ptr2 = 0; self.ptr3 = 0; self.ptr3_pk = 0
        
        self.x1_cum.fill(np.nan); self.y1_ft.fill(np.nan); self.y1_se.fill(np.nan); self.y1_all.fill(np.nan)
        self.x2_reg.fill(np.nan); self.y2_sig.fill(np.nan)
        self.x3_ori.fill(np.nan); self.y3_ori.fill(np.nan)
        self.x3_pk.fill(np.nan);  self.y3_pk.fill(np.nan)
        
        self.curve_1_ft.setData([], []); self.curve_1_se.setData([], []); self.curve_1_all.setData([], [])
        # ลบ curve_2_sig ออกแล้วใส่ 2 ตัวนี้แทน
        self.curve_2_even.setData([], [])
        self.curve_2_odd.setData([], [])
        
        self.curve_3_base.setData([], []); self.scatter_3_pk.setData([], [])
        
        self.mean_line_2.setValue(0) 
        self.graph2_max_time = 60
        self.plot_2.setXRange(0, self.graph2_max_time, padding=0)
        
        self.cur_err_f = np.nan; self.cur_err_s = np.nan; self.cur_err_all = np.nan
        self.cur_ci_interval = np.nan; self.cur_std_interval = np.nan
        self.cur_avg_reg_mean = np.nan; self.cur_avg_reg_single = np.nan
        self.cur_avg_reg_mean_dev = np.nan; self.cur_avg_reg_single = np.nan
        self.cur_avg_time_reg = np.nan; self.cur_avg_time_single = np.nan
        self.cur_ci_time = np.nan; self.cur_std_time = np.nan
        
        for lbl in self.labels_g1.values(): lbl.setText("--")
        for lbl in self.labels_g2.values(): lbl.setText("--")
        for lbl in self.labels_g3.values(): lbl.setText("--")


# ---------------------------------------------------------
# 2. โมดูลแผงควบคุมและแท็บ (Sidebar & Controls Module)
# ---------------------------------------------------------
class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        
        # เพิ่มความกว้างเผื่อแถบเครื่องมือด้านซ้าย (Left Icon Bar)
        self.setFixedWidth(260) 
        
        # เปลี่ยนเป็นแบบแนวนอนเพื่อซ้อน Icon Bar กับ Parameter Panel
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ==========================================
        # [NEW] Icon Sidebar (จำลองแถบเครื่องมือแบบ Qt Creator)
        # ==========================================
        self.icon_bar = QFrame()
        self.icon_bar.setFixedWidth(65)
        self.icon_bar.setStyleSheet("background-color: #333333; border-right: 1px solid #1E1E1E;")
        icon_layout = QVBoxLayout(self.icon_bar)
        icon_layout.setContentsMargins(5, 15, 5, 15)
        icon_layout.setSpacing(15)
        
        # ไอคอนหลักด้านบน (Welcome, Edit, Design, ...) ตามรูป
        menus = [
            ("▦\nWelcome", "#B0B0B0", False),
            ("⊟\nEdit", "#B0B0B0", False),
            ("✏️\nDesign", "#FF9800", True), # ไฮไลท์ตามรูปต้นฉบับ
            ("🐞\nDebug", "#B0B0B0", False),
            ("🔧\nProjects", "#B0B0B0", False),
            ("❓\nHelp", "#B0B0B0", False)
        ]
        
        for text, color, active in menus:
            btn = QPushButton(text)
            btn.setFixedSize(55, 55)
            bg_color = "#404040" if active else "transparent"
            border = "border-left: 3px solid #FF9800;" if active else "border: none;"
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {bg_color}; color: {color}; font-size: 10px; font-weight: bold; 
                    {border} border-radius: 4px; padding-bottom: 2px;
                }} 
                QPushButton:hover {{ background-color: #4A4A4A; }}
            """)
            icon_layout.addWidget(btn)
            
        icon_layout.addStretch()
        
        # ปุ่มรันด้านล่าง (Play, Debug, Build)
        bot_menus = [
            ("▶", "#8BC34A", 24),
            ("🐞", "#8BC34A", 20),
            ("🔨", "#757575", 20)
        ]
        for icon, color, size in bot_menus:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(f"""
                QPushButton {{ color: {color}; font-size: {size}px; background: transparent; border: none; }} 
                QPushButton:hover {{ background-color: #4A4A4A; border-radius: 20px; }}
            """)
            icon_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            
        main_layout.addWidget(self.icon_bar)
        
        # ==========================================
        # [ORIGINAL] Parameter & Navigation Bar 
        # ==========================================
        self.param_container = QWidget()
        self.param_container.setStyleSheet("""
            QWidget { background-color: #2D2D30; color: #E0E0E0; }
            QLabel { font-size: 13px; font-weight: bold; color: #CCCCCC; }
            QLineEdit, QSpinBox { background-color: #1E1E1E; border: 1px solid #444; padding: 6px; color: white; border-radius: 4px; }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #00BCD4; }
            QListWidget { background-color: #1E1E1E; border: 1px solid #444; border-radius: 4px; padding: 5px; outline: 0;}
            QListWidget::item { padding: 5px; border-radius: 3px; }
            QListWidget::item:selected { background-color: #00BCD4; color: black; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self.param_container)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ตัวแปรเดิม ไม่เปลี่ยนชื่อ
        self.nav_list = QListWidget()
        self.nav_list.addItems(["📊 Dashboard", "📜 Report History", "⚙️ Settings"])
        self.nav_list.setCurrentRow(0)
        self.nav_list.setFixedHeight(100)
        layout.addWidget(QLabel("Navigation"))
        layout.addWidget(self.nav_list)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine) 
        line.setStyleSheet("background-color: #555;")
        layout.addWidget(line)
        
        layout.addWidget(QLabel("Parameters Setup"))
        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(12)
        
        self.input_rate = QLineEdit("50")
        self.input_time = QLineEdit("30")
        self.input_limit = QLineEdit("40")
        
        self.input_window = QSpinBox()
        self.input_window.setRange(5, 300) 
        self.input_window.setValue(10)     
        self.input_window.setSuffix(" sec")
        
        form_layout.addRow("Target Rate:", self.input_rate)
        form_layout.addRow("Session (s):", self.input_time)
        form_layout.addRow("Interval:", self.input_limit)
        form_layout.addRow("Window:", self.input_window)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #2E7D32; color: white; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 6px;}
            QPushButton:hover { background-color: #388E3C; }
        """)
        
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #C62828; color: white; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 6px;}
            QPushButton:hover { background-color: #D32F2F; }
        """)
        
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        # นำคอนเทนเนอร์ใส่ใน layout หลัก
        main_layout.addWidget(self.param_container)