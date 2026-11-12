# Hệ thống nhận diện biển số xe tự động

## Tên đề tài

**Xây dựng hệ thống nhận diện biển số xe tự động ứng dụng học sâu trong quản lý và thu phí bãi giữ xe**

## Chức năng

- Phát hiện vùng biển số bằng mô hình YOLO11 đã huấn luyện.
- Nhận dạng ký tự biển số bằng FastPlateOCR, có EasyOCR dự phòng.
- Hỗ trợ biển số ô tô và xe máy Việt Nam.
- Quản lý xe vào, xe ra và ngăn quét trùng.
- Tính phí theo thời gian gửi xe.
- Tra cứu và xử lý trường hợp mất thẻ.
- Lưu xe trong bãi, doanh thu và nhật ký bằng SQLite.
- Xuất nhật ký ra tệp CSV.
- Nhận hình từ tệp ảnh hoặc webcam.

## Công nghệ

- Python 3.10, 3.11 hoặc 3.12 (khuyến nghị Python 3.12 bản 64-bit)
- Ultralytics YOLO11
- PyTorch
- FastPlateOCR và EasyOCR
- OpenCV
- CustomTkinter
- SQLite

## Cấu trúc chính

```text
DoAn2/
|-- CAI_DAT_LAN_DAU.bat
|-- CHAY_CHUONG_TRINH.bat
|-- KIEM_TRA_HE_THONG.py
|-- main.py
|-- requirements.txt
|-- models/
|   `-- best.pt
|-- services/
|   |-- plate_detector.py
|   |-- plate_ocr.py
|   `-- parking_database.py
`-- data/
    `-- parking.db
```

## Cài đặt trên Windows

Yêu cầu khuyến nghị: Windows 10/11 64-bit, RAM từ 8 GB và còn khoảng 5 GB dung lượng trống. Không bắt buộc có GPU rời.

### Cách đơn giản cho máy mới

1. Sao chép **toàn bộ thư mục `DoAn2`** sang máy mới. Không cần đặt ở ổ C; có thể đặt ở Desktop, ổ D hoặc USB.
2. Cài **Python 3.12 64-bit** và chọn `Add Python to PATH` trong màn hình cài đặt.
3. Kết nối Internet.
4. Bấm đúp `CAI_DAT_LAN_DAU.bat` và chờ thông báo `CAI DAT THANH CONG`.
5. Từ lần sau, chỉ cần bấm đúp `CHAY_CHUONG_TRINH.bat`.

Bộ cài tự tạo `.venv`, cài thư viện CPU và tải sẵn mô hình OCR. Vì vậy máy không có card đồ họa NVIDIA vẫn chạy được.

### Cài thủ công trong Terminal

Tạo môi trường ảo bằng Python 3.12:

```powershell
py -3.12 -m venv .venv
```

Kích hoạt môi trường:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Cài các thư viện:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

## Chạy chương trình

Có thể bấm đúp:

```text
CHAY_CHUONG_TRINH.bat
```

Hoặc chạy trong Terminal:

```powershell
.\.venv\Scripts\python.exe main.py
```

Có thể kiểm tra máy đã đủ thư viện hay chưa bằng:

```powershell
.\.venv\Scripts\python.exe KIEM_TRA_HE_THONG.py
```

## Cách kiểm tra

1. Chọn **CỔNG VÀO**.
2. Bấm **Tải Ảnh Kiểm Tra** hoặc mở webcam.
3. Bấm **QUÉT BIỂN SỐ**.
4. Chuyển sang **CỔNG RA** và quét lại cùng xe.
5. Kiểm tra trạng thái mở cổng, thời gian, phí, doanh thu và nhật ký.

## Dữ liệu lưu trữ

Cơ sở dữ liệu được tạo tự động tại `data/parking.db`. Dữ liệu vẫn còn sau khi tắt và mở lại chương trình.

## Lưu ý

- Khi chuyển sang máy khác phải sao chép các tệp `main.py`, `requirements.txt`, hai tệp `.bat`, thư mục `services` và thư mục `models`.
- Không cần sao chép `.venv`; mỗi máy nên chạy `CAI_DAT_LAN_DAU.bat` để tạo môi trường riêng.
- Phải có tệp `models/best.pt` trước khi chạy.
- Chương trình dùng đường dẫn tương đối theo vị trí dự án nên không phụ thuộc vào `C:\BaoCao\DoAn2`.
- Máy Windows 10/11 64-bit không có GPU vẫn chạy bằng CPU; GPU chỉ giúp xử lý nhanh hơn.
- Ảnh càng rõ, biển số càng thẳng và đủ sáng thì kết quả càng chính xác.
- Webcam cần được cấp quyền trong **Settings > Privacy & security > Camera**.
- Không khuyến nghị Python 3.13 trở lên; không dùng Python 3.15 cho dự án này.
