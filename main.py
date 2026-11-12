import customtkinter as ctk
from PIL import Image
import cv2
import re
import time
import math
import csv
import numpy as np
from tkinter import filedialog, ttk, messagebox
import datetime
import torch
import warnings
import threading
from queue import Queue
from pathlib import Path
from services.plate_detector import PlateDetector
from services.plate_ocr import PlateOCR
from services.parking_database import ParkingDatabase

warnings.filterwarnings("ignore", category=UserWarning)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"
DATABASE_PATH = PROJECT_ROOT / "data" / "parking.db"

device = 'cuda' if torch.cuda.is_available() else 'cpu'
use_gpu = torch.cuda.is_available()

print(f"--> [Parking ANPR Engine Pro] Engine started on: {device.upper()}")


class SmartParkingANPRSystem(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Hệ Thống Nhận Diện Biển Số Xe Tự Động - Quản Lý và Thu Phí Bãi Giữ Xe [{device.upper()}]")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = max(900, min(1420, screen_width - 40))
        window_height = max(650, min(880, screen_height - 80))
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(min(1050, window_width), min(680, window_height))

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        #Set giá tiền,bào khách hàng
        self.HOURLY_RATE = 10000         
        self.LOST_CARD_PENALTY = 50000  

        self.database = ParkingDatabase(DATABASE_PATH)
        saved_state = self.database.load_state()
        self.parked_vehicles = saved_state["parked_vehicles"]
        self.logs_history = saved_state["logs"]
        self.total_entries = saved_state["total_entries"]
        self.total_exits = saved_state["total_exits"]
        self.total_revenue = saved_state["total_revenue"]

        # Biến quản lý camera
        self.cap = None
        self.active_gate = None  
        self.recent_gate_events = {}
        self.EVENT_COOLDOWN_SECONDS = 30

        self.ui_queue = Queue()
        self.plate_detector = PlateDetector(
            MODEL_PATH,
            confidence=0.25
        )
        self.plate_ocr = PlateOCR(
            use_gpu=use_gpu
        )

        self.create_top_bar()
        self.create_body()
        for log_entry in self.logs_history:
            self.tree.insert("", 0, values=log_entry)
        self.update_metrics_display()
        self.check_ui_queue()

    def check_ui_queue(self):
        while not self.ui_queue.empty():
            task, args = self.ui_queue.get()
            if task == "display_frame":
                frame_bgr, gate_type = args
                self._display_frame_internal(frame_bgr, gate_type)
            elif task == "gate_event":
                plate_str, crop_img, gate_type = args
                self._process_gate_event_internal(plate_str, crop_img, gate_type)
        self.after(30, self.check_ui_queue)

    def create_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#0f172a")
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(1, weight=1)

        logo_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        brand_icon = ctk.CTkLabel(logo_frame, text="🅿️", font=ctk.CTkFont(size=32))
        brand_icon.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box, 
            text=f"HỆ THỐNG NHẬN DIỆN BIỂN SỐ XE ({device.upper()})", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#38bdf8"
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_box, 
            text="Ứng dụng học sâu trong quản lý và thu phí bãi giữ xe", 
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        app_subtitle.pack(anchor="w")

        status_bar = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        status_bar.grid(row=0, column=1, padx=20, sticky="e")

        self.stat_parked_label = self.create_metric_badge(status_bar, "XE TRONG BÃI", "0", "#eab308")
        self.stat_in_label = self.create_metric_badge(status_bar, "LƯỢT VÀO", "0", "#10b981")
        self.stat_out_label = self.create_metric_badge(status_bar, "LƯỢT RA", "0", "#3b82f6")
        self.stat_rev_label = self.create_metric_badge(status_bar, "DOANH THU", "0 VNĐ", "#a855f7")

        self.theme_menu = ctk.CTkOptionMenu(
            status_bar, values=["Dark", "Light"], width=85, height=28,
            font=ctk.CTkFont(size=11), command=self.change_theme
        )
        self.theme_menu.pack(side="right", padx=10)

    def create_metric_badge(self, parent, title, value, color):
        frame = ctk.CTkFrame(parent, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#334155")
        frame.pack(side="left", padx=5, pady=8)

        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color="#94a3b8")
        lbl_title.pack(padx=10, pady=(4, 0))

        lbl_val = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=13, weight="bold"), text_color=color)
        lbl_val.pack(padx=10, pady=(0, 4))
        return lbl_val

    def create_body(self):
        self.body_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.body_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        self.body_frame.grid_columnconfigure(0, weight=2)
        self.body_frame.grid_columnconfigure(1, weight=6)
        self.body_frame.grid_columnconfigure(2, weight=4)
        self.body_frame.grid_rowconfigure(0, weight=1)

        self.create_left_controls()
        self.create_center_viewport()
        self.create_right_panel()

    def create_left_controls(self):
        panel = ctk.CTkFrame(self.body_frame, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#334155")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(panel, text="🎛️ ĐIỀU KHIỂN BÃI XE", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f8fafc").pack(padx=15, pady=(15, 10), anchor="w")
        ctk.CTkFrame(panel, height=2, fg_color="#334155").pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(panel, text="Chế Độ Quét Ảnh Thủ Công:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#cbd5e1").pack(padx=15, anchor="w")
        
        self.gate_selector = ctk.CTkSegmentedButton(
            panel, values=["CỔNG VÀO", "CỔNG RA"],
            selected_color="#0284c7", unselected_color="#0f172a"
        )
        self.gate_selector.set("CỔNG VÀO")
        self.gate_selector.pack(padx=15, pady=8, fill="x")

        self.btn_open_img = ctk.CTkButton(
            panel, text="📁 Tải Ảnh Kiểm Tra", height=36, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7", hover_color="#0369a1", command=self.open_image_file
        )
        self.btn_open_img.pack(padx=15, pady=4, fill="x")

        self.btn_process = ctk.CTkButton(
            panel, text="⚡ QUÉT BIỂN SỐ", height=38, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ea580c", hover_color="#c2410c", command=self.process_manual_image
        )
        self.btn_process.pack(padx=15, pady=4, fill="x")

        ctk.CTkFrame(panel, height=2, fg_color="#334155").pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(panel, text="Giám Sát Live Camera (1 Webcam):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#cbd5e1").pack(padx=15, anchor="w")

        self.btn_webcam_in = ctk.CTkButton(
            panel, text="📷 Cam Cổng Vào (Webcam)", height=34, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#059669", hover_color="#047857", command=lambda: self.toggle_webcam("IN")
        )
        self.btn_webcam_in.pack(padx=15, pady=4, fill="x")

        self.btn_webcam_out = ctk.CTkButton(
            panel, text="🎥 Cam Cổng Ra (Webcam)", height=34, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#4f46e5", hover_color="#4338ca", command=lambda: self.toggle_webcam("OUT")
        )
        self.btn_webcam_out.pack(padx=15, pady=4, fill="x")

        ctk.CTkFrame(panel, height=2, fg_color="#334155").pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(panel, text="🔍 TRA CỨU / MẤT THẺ XE", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f59e0b").pack(padx=15, anchor="w")

        self.entry_search_plate = ctk.CTkEntry(
            panel, placeholder_text="Nhập biển số (VD: 30F12345)", height=35,
            font=ctk.CTkFont(size=12)
        )
        self.entry_search_plate.pack(padx=15, pady=6, fill="x")

        self.btn_search = ctk.CTkButton(
            panel, text="🔎 Tra Cứu Biển Số Trong Bãi", height=36, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d97706", hover_color="#b45309", command=self.search_plate
        )
        self.btn_search.pack(padx=15, pady=4, fill="x")

    def create_center_viewport(self):
        center_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        center_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_rowconfigure(1, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        self.card_in = ctk.CTkFrame(center_frame, corner_radius=12, fg_color="#0f172a", border_width=1, border_color="#10b981")
        self.card_in.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        
        header_in = ctk.CTkFrame(self.card_in, fg_color="#10b981", height=28, corner_radius=0)
        header_in.pack(fill="x", side="top")
        ctk.CTkLabel(header_in, text="🟢 LÀN VÀO (ENTRY GATE)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff").pack(side="left", padx=10)

        self.lbl_view_in = ctk.CTkLabel(self.card_in, text="[ Chờ hình ảnh Cổng Vào ]", font=ctk.CTkFont(size=12), text_color="#64748b")
        self.lbl_view_in.pack(expand=True, fill="both", padx=5, pady=5)

        self.card_out = ctk.CTkFrame(center_frame, corner_radius=12, fg_color="#0f172a", border_width=1, border_color="#3b82f6")
        self.card_out.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        header_out = ctk.CTkFrame(self.card_out, fg_color="#3b82f6", height=28, corner_radius=0)
        header_out.pack(fill="x", side="top")
        ctk.CTkLabel(header_out, text="🔵 LÀN RA (EXIT GATE)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff").pack(side="left", padx=10)

        self.lbl_view_out = ctk.CTkLabel(self.card_out, text="[ Chờ hình ảnh Cổng Ra ]", font=ctk.CTkFont(size=12), text_color="#64748b")
        self.lbl_view_out.pack(expand=True, fill="both", padx=5, pady=5)

    def create_right_panel(self):
        right_panel = ctk.CTkFrame(self.body_frame, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#334155")
        right_panel.grid(row=0, column=2, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=0)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        result_card = ctk.CTkFrame(right_panel, fg_color="#0f172a", corner_radius=10, border_width=1, border_color="#334155")
        result_card.grid(row=0, column=0, sticky="ew", padx=12, pady=12)

        ctk.CTkLabel(result_card, text="KẾT QUẢ XỬ LÝ BARIE", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(padx=10, pady=(10, 4), anchor="w")

        self.status_badge = ctk.CTkFrame(result_card, fg_color="#334155", corner_radius=8)
        self.status_badge.pack(fill="x", padx=10, pady=4)

        self.lbl_valid_status = ctk.CTkLabel(
            self.status_badge, text="SẴN SÀNG QUÉT", 
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#f8fafc"
        )
        self.lbl_valid_status.pack(pady=8)

        details_box = ctk.CTkFrame(result_card, fg_color="transparent")
        details_box.pack(fill="x", padx=10, pady=8)
        details_box.grid_columnconfigure(0, weight=1)
        details_box.grid_columnconfigure(1, weight=2)

        self.crop_label = ctk.CTkLabel(details_box, text="[ Cắt Biển ]", fg_color="#1e293b", corner_radius=6, height=60)
        self.crop_label.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        info_frame = ctk.CTkFrame(details_box, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="nsew")

        self.lbl_plate_number = ctk.CTkLabel(info_frame, text="--- ---", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color="#facc15")
        self.lbl_plate_number.pack(anchor="w")

        self.lbl_time_info = ctk.CTkLabel(info_frame, text="Thời gian: --:--:--", font=ctk.CTkFont(size=11), text_color="#cbd5e1")
        self.lbl_time_info.pack(anchor="w")

        self.lbl_fee_info = ctk.CTkLabel(info_frame, text="Phí đỗ xe: 0 VNĐ", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8")
        self.lbl_fee_info.pack(anchor="w")

        log_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        log_header.grid(row=1, column=0, sticky="ew", padx=12, pady=(5, 5))
        ctk.CTkLabel(log_header, text="📋 NHẬT KÝ VÀO / RA", font=ctk.CTkFont(size=13, weight="bold"), text_color="#f8fafc").pack(side="left")

        btn_export = ctk.CTkButton(log_header, text="📥 CSV", width=60, height=24, font=ctk.CTkFont(size=10, weight="bold"), command=self.export_csv)
        btn_export.pack(side="right")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#0f172a", foreground="#f8fafc", fieldbackground="#0f172a", rowheight=26, font=('Segoe UI', 9))
        style.configure("Treeview.Heading", background="#1e293b", foreground="#38bdf8", font=('Segoe UI', 9, 'bold'), relief="flat")
        style.map("Treeview", background=[('selected', '#0284c7')])

        tree_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree = ttk.Treeview(tree_frame, columns=("Time", "Plate", "Gate", "Status", "Fee"), show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")

        self.tree.heading("Time", text="Giờ")
        self.tree.heading("Plate", text="Biển Số")
        self.tree.heading("Gate", text="Cổng")
        self.tree.heading("Status", text="Trạng Thái")
        self.tree.heading("Fee", text="Tiền Phí")

        self.tree.column("Time", width=65, anchor="center")
        self.tree.column("Plate", width=95, anchor="center")
        self.tree.column("Gate", width=55, anchor="center")
        self.tree.column("Status", width=90, anchor="center")
        self.tree.column("Fee", width=70, anchor="center")

        self.tree.pack(expand=True, fill="both")

    def parse_unified_string(self, raw_str):
        s = re.sub(r'[^A-Z0-9]', '', raw_str.upper())
        valid_starts = set('0123456789OQDIZSBG')
        start_idx = -1
        for i, c in enumerate(s):
            if c in valid_starts:
                start_idx = i
                break
                
        if start_idx != -1:
            s = s[start_idx:]
        if len(s) < 5: 
            return None
        char_to_num = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6'}
        num_to_char = {'0': 'D', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '4': 'A'}
        tail_len = 5 if len(s) >= 8 else 4

        prov_str = s[:2]
        tail_str = s[-tail_len:]
        mid_str = s[2:-tail_len]
        prov = "".join([char_to_num.get(c, c) for c in prov_str])
        tail = "".join([char_to_num.get(c, c) for c in tail_str])
        if len(tail) == 5:
            tail = f"{tail[:3]}.{tail[3:]}"
        mid = ""
        if len(mid_str) > 0:
            mid += num_to_char.get(mid_str[0], mid_str[0])
            if len(mid_str) > 1:
                c2 = mid_str[1]
                if c2 == 'I': c2 = '1'
                elif c2 == 'O': c2 = '0'
                mid += c2
            if len(mid_str) > 2:
                mid += mid_str[2:]

        return f"{prov}-{mid} {tail}".strip('- ')

    def perform_anpr_pipeline(self, frame):
        if frame is None or frame.size == 0:
            return frame, []

        detections = self.plate_detector.detect(frame)
        print(f"[YOLO] Số vùng biển số: {len(detections)}")
        results = []

        for detection in detections:
            crop = detection["crop"]

            ocr_result = self.plate_ocr.recognize(crop)
            print(f"[OCR] Kết quả: {ocr_result}")

            if ocr_result is None:
                continue

            formatted_plate = self.parse_unified_string(
                ocr_result["plate"]
            )

            if not formatted_plate:
                continue

            combined_confidence = (
                detection["confidence"]
                * ocr_result["confidence"]
                * 100
            )

            x1, y1, x2, y2 = detection["box"]

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 230, 255),
                3
            )

            cv2.putText(
                frame,
                formatted_plate,
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 230, 255),
                2,
                cv2.LINE_AA
            )

            results.append({
                "plate": formatted_plate,
                "conf": round(combined_confidence, 1),
                "crop": crop,
                "box": detection["box"],
                "det_conf": detection["confidence"],
                "ocr_conf": ocr_result["confidence"],
                "raw_text": ocr_result["raw_text"]
            })

        return frame, results
    def process_gate_event(self, plate_str, crop_img, gate_type="IN"):
        self.ui_queue.put(("gate_event", (plate_str, crop_img, gate_type)))

    def _process_gate_event_internal(self, plate_str, crop_img, gate_type="IN"):
        now = datetime.datetime.now()
        now_str = now.strftime("%H:%M:%S")
        
        plate_clean = re.sub(r'[^A-Z0-9]', '', plate_str.upper())
        if len(plate_clean) < 5:
            return

        event_key = (gate_type, plate_clean)
        last_event_time = self.recent_gate_events.get(event_key)
        if (
            last_event_time is not None
            and (now - last_event_time).total_seconds() < self.EVENT_COOLDOWN_SECONDS
        ):
            return
        self.recent_gate_events[event_key] = now

        is_valid = False
        status_text = ""
        fee = 0

        if gate_type == "IN":
            if plate_str in self.parked_vehicles:
                is_valid = False
                status_text = "KHÔNG HỢP LỆ (XE ĐÃ Ở TRONG BÃI)"
            else:
                is_valid = True
                status_text = "HỢP LỆ - MỞ CỔNG VÀO"
                self.parked_vehicles[plate_str] = {
                    "entry_time": now,
                    "crop": crop_img
                }
                self.total_entries += 1
                self.database.add_entry(plate_str, now)

        elif gate_type == "OUT":
            if plate_str in self.parked_vehicles:
                is_valid = True
                status_text = "HỢP LỆ - CỔNG RA MỞ"
                
                entry_data = self.parked_vehicles.pop(plate_str)
                duration = now - entry_data["entry_time"]
                hours = max(1, math.ceil(duration.total_seconds() / 3600))
                fee = hours * self.HOURLY_RATE
                
                self.total_exits += 1
                self.total_revenue += fee
                self.database.add_exit(plate_str, now, fee)
            else:
                is_valid = False
                status_text = "KHÔNG HỢP LỆ (KHÔNG THẤY THẺ VÀO)"

        if is_valid:
            self.status_badge.configure(fg_color="#059669")
            self.lbl_valid_status.configure(text=f"✅ {status_text}", text_color="#ffffff")
        else:
            self.status_badge.configure(fg_color="#dc2626")
            self.lbl_valid_status.configure(text=f"❌ {status_text}", text_color="#ffffff")

        self.lbl_plate_number.configure(text=plate_str)
        self.lbl_time_info.configure(text=f"Thời gian: {now_str}")
        self.lbl_fee_info.configure(text=f"Phí đỗ xe: {fee:,} VNĐ")

        if crop_img is not None and crop_img.size > 0:
            crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            crop_pil = Image.fromarray(crop_rgb)
            crop_resized = self.resize_image(crop_pil, 120, 50)
            ctk_crop = ctk.CTkImage(light_image=crop_resized, dark_image=crop_resized, size=crop_resized.size)
            self.crop_label.configure(image=ctk_crop, text="")

        log_entry = (now_str, plate_str, gate_type, "HỢP LỆ" if is_valid else "CẢNH BÁO", f"{fee:,}đ")
        self.tree.insert("", 0, values=log_entry)
        self.logs_history.append(log_entry)
        self.database.add_log(
            now,
            plate_str,
            gate_type,
            "HỢP LỆ" if is_valid else "CẢNH BÁO",
            fee
        )

        self.update_metrics_display()

    def search_plate(self):
        query = self.entry_search_plate.get().strip()
        if not query:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập biển số cần tra cứu!")
            return

        clean_query = re.sub(r'[^A-Z0-9]', '', query.upper())
        found_key = None

        for key in self.parked_vehicles:
            clean_key = re.sub(r'[^A-Z0-9]', '', key.upper())
            if clean_query in clean_key:
                found_key = key
                break

        if found_key:
            self.open_lost_card_dialog(found_key, self.parked_vehicles[found_key])
        else:
            messagebox.showerror("Không tìm thấy", f"Không tìm thấy xe mang biển số '{query}' đang gửi trong bãi!")

    def open_lost_card_dialog(self, plate_str, vehicle_data):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"🚨 Giải Quyết Mất Thẻ - Biển Số: {plate_str}")
        dialog.geometry("500x580")
        dialog.resizable(False, False)
        dialog.grab_set()  

        now = datetime.datetime.now()
        entry_time = vehicle_data["entry_time"]
        duration = now - entry_time
        hours = max(1, math.ceil(duration.total_seconds() / 3600))
        
        parking_fee = hours * self.HOURLY_RATE
        total_fee = parking_fee + self.LOST_CARD_PENALTY

        ctk.CTkLabel(dialog, text="⚠️ XỬ LÝ MẤT THẺ XE THỦ CÔNG", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f59e0b").pack(pady=(15, 5))
        ctk.CTkLabel(dialog, text="Đã xác minh hình ảnh đối chiếu lúc vào bãi:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(pady=(0, 10))

        img_frame = ctk.CTkFrame(dialog, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#38bdf8")
        img_frame.pack(padx=20, pady=5, fill="x")

        crop_bgr = vehicle_data["crop"]
        if crop_bgr is not None and crop_bgr.size > 0:
            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            crop_pil = Image.fromarray(crop_rgb)
            crop_resized = self.resize_image(crop_pil, 240, 90)
            ctk_img = ctk.CTkImage(light_image=crop_resized, dark_image=crop_resized, size=crop_resized.size)
            lbl_img = ctk.CTkLabel(img_frame, image=ctk_img, text="")
            lbl_img.pack(pady=10)
        else:
            ctk.CTkLabel(img_frame, text="[Không có ảnh lúc vào]", text_color="#64748b").pack(pady=20)

        box_info = ctk.CTkFrame(dialog, fg_color="#1e293b", corner_radius=8)
        box_info.pack(padx=20, pady=10, fill="x")

        def add_info_row(lbl, val, col="#ffffff"):
            ctk.CTkLabel(
                box_info, text=f"{lbl}: {val}", font=ctk.CTkFont(size=12, weight="bold" if col != "#ffffff" else "normal"), text_color=col
            ).pack(anchor="w", padx=15, pady=3)

        add_info_row("🚘 Biển số xe", plate_str, "#facc15")
        add_info_row("🕒 Thời gian vào bãi", entry_time.strftime("%H:%M:%S (%d/%m/%Y)"))
        add_info_row("⏱️ Thời gian đỗ", f"{hours} giờ")
        add_info_row("💰 Phí đỗ xe", f"{parking_fee:,} VNĐ", "#38bdf8")
        add_info_row("⚠️ Phí đền bù mất thẻ", f"{self.LOST_CARD_PENALTY:,} VNĐ", "#ef4444")

        ctk.CTkFrame(box_info, height=2, fg_color="#334155").pack(fill="x", padx=10, pady=5)
        
        lbl_total = ctk.CTkLabel(
            box_info, text=f"TỔNG THU: {total_fee:,} VNĐ", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#10b981"
        )
        lbl_total.pack(pady=8)

        def confirm_lost_card_exit():
            self.parked_vehicles.pop(plate_str, None)
            self.total_exits += 1
            self.total_revenue += total_fee
            self.database.add_exit(plate_str, now, total_fee)

            now_str = now.strftime("%H:%M:%S")
            log_entry = (now_str, plate_str, "OUT", "RA (MẤT THẺ)", f"{total_fee:,}đ")
            self.tree.insert("", 0, values=log_entry)
            self.logs_history.append(log_entry)
            self.database.add_log(now, plate_str, "OUT", "RA (MẤT THẺ)", total_fee)

            self.status_badge.configure(fg_color="#0284c7")
            self.lbl_valid_status.configure(text=f"✅ MỞ CỔNG (ĐÃ XỬ LÝ MẤT THẺ)", text_color="#ffffff")
            self.lbl_plate_number.configure(text=plate_str)
            self.lbl_time_info.configure(text=f"Giờ ra: {now_str}")
            self.lbl_fee_info.configure(text=f"Tổng thu: {total_fee:,} VNĐ")

            self.update_metrics_display()
            dialog.destroy()
            messagebox.showinfo("Hoàn tất", f"Đã thanh toán {total_fee:,} VNĐ và mở cổng cho xe {plate_str} ra!")

        btn_confirm = ctk.CTkButton(
            dialog, text="🚨 XÁC NHẬN CHO XE RA (ĐÃ THU PHÍ)", height=45,
            font=ctk.CTkFont(size=14, weight="bold"), fg_color="#059669", hover_color="#047857",
            command=confirm_lost_card_exit
        )
        btn_confirm.pack(padx=20, pady=15, fill="x")

    def update_metrics_display(self):
        self.stat_parked_label.configure(text=str(len(self.parked_vehicles)))
        self.stat_in_label.configure(text=str(self.total_entries))
        self.stat_out_label.configure(text=str(self.total_exits))
        self.stat_rev_label.configure(text=f"{self.total_revenue:,}đ")

    def open_image_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if file_path:
            self.loaded_image_path = file_path
            img_bgr = self.read_image_file(file_path)
            if img_bgr is None:
                messagebox.showerror("Lỗi", "Không thể đọc tệp ảnh đã chọn!")
                return
            gate = "IN" if self.gate_selector.get() == "CỔNG VÀO" else "OUT"
            self.display_frame_to_viewport(img_bgr, gate)

    def process_manual_image(self):
        if not hasattr(self, 'loaded_image_path') or not self.loaded_image_path:
            messagebox.showwarning("Thông báo", "Vui lòng bấm 'Tải Ảnh Kiểm Tra' trước!")
            return

        frame = self.read_image_file(self.loaded_image_path)
        if frame is None:
            messagebox.showerror("Lỗi", "Không thể đọc tệp ảnh đã chọn!")
            return
        gate_type = "IN" if self.gate_selector.get() == "CỔNG VÀO" else "OUT"

        annotated_frame, results = self.perform_anpr_pipeline(frame)
        self.display_frame_to_viewport(annotated_frame, gate_type)

        if results:
            item = results[0]
            self._process_gate_event_internal(item["plate"], item["crop"], gate_type)
        else:
            messagebox.showinfo("Kết quả", "Không tìm thấy biển số trong ảnh!")

    def toggle_webcam(self, gate_type="IN"):
        if gate_type == "IN":
            if self.active_gate == "IN":
                self.stop_camera()
                self.btn_webcam_in.configure(text="📷 Cam Cổng Vào (Webcam)", fg_color="#059669")
            else:
                self.stop_camera()
                self.cap = self.open_available_camera()
                if self.cap is None:
                    messagebox.showerror("Lỗi", "Không thể kết nối Webcam. Hãy kiểm tra quyền Camera của Windows!")
                    return
                self.active_gate = "IN"
                self.btn_webcam_in.configure(text="🛑 Dừng Cam Vào", fg_color="#dc2626")
                self.btn_webcam_out.configure(text="🎥 Cam Cổng Ra (Webcam)", fg_color="#4f46e5")
                threading.Thread(target=self.stream_loop, args=("IN",), daemon=True).start()

        elif gate_type == "OUT":
            if self.active_gate == "OUT":
                self.stop_camera()
                self.btn_webcam_out.configure(text="🎥 Cam Cổng Ra (Webcam)", fg_color="#4f46e5")
            else:
                self.stop_camera()
                self.cap = self.open_available_camera()
                if self.cap is None:
                    messagebox.showerror("Lỗi", "Không thể kết nối Webcam. Hãy kiểm tra quyền Camera của Windows!")
                    return
                self.active_gate = "OUT"
                self.btn_webcam_out.configure(text="🛑 Dừng Cam Ra", fg_color="#dc2626")
                self.btn_webcam_in.configure(text="📷 Cam Cổng Vào (Webcam)", fg_color="#059669")
                threading.Thread(target=self.stream_loop, args=("OUT",), daemon=True).start()

    def stop_camera(self):
        self.active_gate = None
        if self.cap:
            self.cap.release()
            self.cap = None
        time.sleep(0.1)

    def stream_loop(self, gate_type):
        last_process_time = 0
        while self.active_gate == gate_type and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: break

            now = time.time()
            interval = 2.5 if gate_type == "IN" else 3.0
            
            if now - last_process_time > interval:
                annotated_frame, results = self.perform_anpr_pipeline(frame.copy())
                if results:
                    self.process_gate_event(results[0]["plate"], results[0]["crop"], gate_type)
                last_process_time = now
                self.display_frame_to_viewport(annotated_frame, gate_type)
            else:
                self.display_frame_to_viewport(frame, gate_type)

            time.sleep(0.03)

    @staticmethod
    def read_image_file(file_path):
        """Đọc được cả đường dẫn Windows có dấu tiếng Việt hoặc ký tự Unicode."""
        try:
            encoded = np.fromfile(str(file_path), dtype=np.uint8)
            return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            return None

    @staticmethod
    def open_available_camera():
        """Tự tìm webcam ở các chỉ số thông dụng thay vì buộc mọi máy dùng camera 0."""
        for camera_index in range(3):
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def display_frame_to_viewport(self, frame_bgr, gate_type="IN"):
        self.ui_queue.put(("display_frame", (frame_bgr, gate_type)))

    def _display_frame_internal(self, frame_bgr, gate_type="IN"):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)
        img_resized = self.resize_image(img_pil, 420, 220)
        ctk_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=img_resized.size)

        if gate_type == "IN":
            self.lbl_view_in.configure(image=ctk_img, text="")
        else:
            self.lbl_view_out.configure(image=ctk_img, text="")

    def resize_image(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        return img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.Resampling.LANCZOS)

    def change_theme(self, mode):
        ctk.set_appearance_mode(mode)

    def export_csv(self):
        if not self.logs_history:
            messagebox.showinfo("Xuất CSV", "Chưa có nhật ký dữ liệu!")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Thời Gian",
                    "Biển Số",
                    "Cổng",
                    "Trạng Thái",
                    "Tiền Phí"
                ])
                writer.writerows(self.logs_history)
            messagebox.showinfo("Thành công", f"Đã xuất nhật ký ra: {file_path}")

    def on_closing(self):
        self.stop_camera()
        self.destroy()

if __name__ == "__main__":
    app = SmartParkingANPRSystem()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

