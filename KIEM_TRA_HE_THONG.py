import importlib
import platform
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"
REQUIRED_MODULES = {
    "customtkinter": "CustomTkinter",
    "cv2": "OpenCV",
    "PIL": "Pillow",
    "numpy": "NumPy",
    "torch": "PyTorch",
    "ultralytics": "Ultralytics",
    "easyocr": "EasyOCR",
    "fast_plate_ocr": "FastPlateOCR",
}


def main():
    print(f"Python: {platform.python_version()} ({platform.machine()})")
    if not ((3, 10) <= sys.version_info[:2] <= (3, 12)):
        print("[CANH BAO] Nen dung Python 3.10, 3.11 hoac 3.12.")

    missing = []
    for module_name, display_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module_name)
            print(f"[OK] {display_name}")
        except Exception as error:
            missing.append(display_name)
            print(f"[THIEU] {display_name}: {error}")

    if MODEL_PATH.is_file():
        print(f"[OK] Mo hinh YOLO: {MODEL_PATH}")
    else:
        missing.append("models/best.pt")
        print(f"[THIEU] Mo hinh YOLO: {MODEL_PATH}")

    if missing:
        print("\nHe thong chua san sang: " + ", ".join(missing))
        return 1

    print("\nHE THONG DA SAN SANG CHAY TREN MAY NAY.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
