import os
import re
import uuid

# ===================== CẤU HÌNH =====================
STRIP_OLD_PREFIX = True   # Xóa tiền tố số cũ ("1-", "10. ", "3_") trước khi đánh số lại
PAD_ZEROS = False         # True -> 01., 02., ..., 10. (tự động theo số lượng file)
SEPARATOR = ". "          # Phần ngăn cách giữa số thứ tự và tên file
SKIP_HIDDEN = True        # Bỏ qua file ẩn (bắt đầu bằng dấu ".")
EXTENSIONS = None         # Ví dụ: {".mp4", ".mkv"} để chỉ đổi tên các đuôi này. None = tất cả
DRY_RUN = False           # True -> chỉ xem trước, KHÔNG đổi tên thật
# ====================================================

folder_path = os.path.dirname(os.path.abspath(__file__))
current_script = os.path.basename(__file__)


def natural_key(text):
    """Sắp xếp tự nhiên: 1, 2, 3, ..., 10, 11 (thay vì 1, 10, 11, 2, 3)."""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", text)
    ]


def strip_prefix(name):
    """Bỏ tiền tố dạng '12-', '12. ', '12_', '12)' ở đầu tên file."""
    stripped = re.sub(r"^\d+\s*[-._)]\s*", "", name)
    return stripped if stripped else name  # tránh trường hợp tên bị rỗng


def collect_files():
    result = []
    for f in os.listdir(folder_path):
        full = os.path.join(folder_path, f)
        if not os.path.isfile(full) or f == current_script:
            continue
        if SKIP_HIDDEN and f.startswith("."):
            continue
        if EXTENSIONS and os.path.splitext(f)[1].lower() not in EXTENSIONS:
            continue
        result.append(f)
    return sorted(result, key=natural_key)


def build_plan(files):
    width = len(str(len(files))) if PAD_ZEROS else 0
    plan = []
    for index, filename in enumerate(files, start=1):
        base = strip_prefix(filename) if STRIP_OLD_PREFIX else filename
        number = str(index).zfill(width) if width else str(index)
        plan.append((filename, f"{number}{SEPARATOR}{base}"))
    return plan


def main():
    files = collect_files()
    if not files:
        print("Không có file nào để đổi tên.")
        return

    plan = [(old, new) for old, new in build_plan(files) if old != new]
    if not plan:
        print("Tất cả file đã đúng thứ tự, không cần đổi.")
        return

    if DRY_RUN:
        print("=== CHẾ ĐỘ XEM TRƯỚC (chưa đổi tên thật) ===")
        for old, new in plan:
            print(f"'{old}' -> '{new}'")
        print(f"\nTổng cộng: {len(plan)} file sẽ được đổi.")
        return

    # Bước 1: đổi sang tên tạm (tránh trùng/ghi đè khi tên mới trùng tên file khác)
    staged = []
    for old, new in plan:
        temp = f"__tmp_{uuid.uuid4().hex}__"
        try:
            os.rename(os.path.join(folder_path, old), os.path.join(folder_path, temp))
            staged.append((temp, old, new))
        except OSError as e:
            print(f"[LỖI] Không thể đổi '{old}': {e}")

    # Bước 2: đổi từ tên tạm sang tên cuối cùng
    done = 0
    for temp, old, new in staged:
        try:
            os.rename(os.path.join(folder_path, temp), os.path.join(folder_path, new))
            print(f"Đã đổi: '{old}' -> '{new}'")
            done += 1
        except OSError as e:
            # Hoàn tác về tên gốc nếu đổi sang tên mới thất bại
            print(f"[LỖI] Không thể đổi thành '{new}': {e} -> khôi phục tên cũ")
            os.rename(os.path.join(folder_path, temp), os.path.join(folder_path, old))

    print(f"\nHoàn tất: đã đổi {done}/{len(plan)} file theo thứ tự tự nhiên!")


if __name__ == "__main__":
    main()