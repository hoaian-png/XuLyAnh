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
XuLyAnh/
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

Bản đầy đủ cần Windows 10/11 64-bit, Python 3.10–3.12 (khuyến nghị 3.12) và Internet khi cài thư viện hoặc tải mô hình OCR lần đầu. Ứng dụng có thể chạy bằng CPU.

```powershell
git clone https://github.com/hoaian-png/XuLyAnh.git
cd XuLyAnh
```

### Tệp cần có trước khi cài

Bản trên GitHub hiện thiếu bốn tệp mà chương trình cần. Lấy chúng từ bản đầy đủ của dự án và đặt đúng vị trí:

- `models/best.pt` — trọng số đã huấn luyện để phát hiện biển số.
- `services/plate_detector.py`, `services/plate_ocr.py` và `services/parking_database.py` — các mô-đun được `main.py` nhập trực tiếp.

`yolo11n.pt` trong kho là tệp riêng. `main.py` và `CHAY_CHUONG_TRINH.bat` đều tìm `models/best.pt`. Kho hiện tại chỉ có thể chuẩn bị môi trường cho đến khi đủ các tệp trên.

### Cài đặt và chạy bản đầy đủ

Bấm đúp `CAI_DAT_LAN_DAU.bat` để tạo môi trường ảo, cài thư viện và tải trước mô hình FastPlateOCR. Khi bộ cài báo thành công, bấm đúp `CHAY_CHUONG_TRINH.bat`.

Nếu cài bằng PowerShell, chạy tại thư mục dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe KIEM_TRA_HE_THONG.py
.\.venv\Scripts\python.exe main.py
```

`KIEM_TRA_HE_THONG.py` kiểm tra thư viện và trọng số. Kiểm tra thêm thư mục `services/` trước khi chạy `main.py`.

## Cách sử dụng

1. Chọn **CỔNG VÀO**, bấm **Tải Ảnh Kiểm Tra**, chọn `test_plate.jpg` hoặc ảnh biển số của bạn rồi bấm **QUÉT BIỂN SỐ**.
2. Chọn **CỔNG RA** và quét lại cùng biển số để xem thời gian gửi, phí và nhật ký vào/ra.
3. Để dùng webcam, bấm **Cam Cổng Vào (Webcam)** hoặc **Cam Cổng Ra (Webcam)**. Nếu webcam chưa hoạt động, kiểm tra quyền truy cập camera trong cài đặt Windows.
4. Nhập biển số rồi bấm **Tra Cứu Biển Số Trong Bãi** để tra cứu xe. Bấm **CSV** trong khung nhật ký để chọn nơi lưu tệp xuất.

## Dữ liệu lưu trữ

Bản đầy đủ lưu dữ liệu SQLite tại `data/parking.db`. Khi chuyển sang máy khác, sao chép mã nguồn, `services/`, `models/` và cơ sở dữ liệu nếu cần giữ lịch sử. Tạo lại môi trường `.venv` bằng bộ cài trên máy mới.
