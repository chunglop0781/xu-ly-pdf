import os
import re
import unicodedata

# Thư mục chứa file PDF/PPTX (mặc định: thư mục chứa file .py này)
FOLDER = os.path.dirname(os.path.abspath(__file__))
# Nếu file nằm chỗ khác thì bỏ dấu # và đổi thành đường dẫn cụ thể, ví dụ:
# FOLDER = r"C:\Users\Admin\Downloads\slide-dstt\danh-so-thu-tu-slide"

EXTENSIONS = ('.pdf', '.pptx')


def strip_prefix(name):
    """Xoá số thứ tự ở đầu, ví dụ '13. ABC.pdf' -> 'ABC.pdf'"""
    return re.sub(r'^\d+\s*\.\s*', '', name)


def normalize(text):
    """Bỏ dấu tiếng Việt, đưa về chữ thường: 'Chương' -> 'chuong'"""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower()


def natural(text):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', text)]


def sort_key(stem):
    """Sắp theo Chương -> Bài (kể cả 4.1, 4.2) -> Phần -> tên (so sánh số tự nhiên)"""
    s = normalize(stem)
    m = re.search(r'chuong[-_ ]*(\d+)', s)
    chuong = int(m.group(1)) if m else 999
    m = re.search(r'bai[-_ ]*(\d+)(?:\.(\d+))?', s)
    bai = int(m.group(1)) if m else 0
    sub = int(m.group(2)) if m and m.group(2) else 0
    m = re.search(r'phan[-_ ]*(\d+)', s)
    phan = int(m.group(1)) if m else 0
    return (chuong, bai, sub, phan, natural(s))


# Gom file theo tên gốc (không số thứ tự, không đuôi) để PDF và PPTX cùng tên có cùng số
groups = {}  # stem -> {ext: tên file cũ}
for f in os.listdir(FOLDER):
    if f.startswith('__tmp__'):
        continue
    stem, ext = os.path.splitext(strip_prefix(f))
    if ext.lower() not in EXTENSIONS:
        continue
    groups.setdefault(stem, {})[ext.lower()] = f

if not groups:
    print(f"Không tìm thấy file PDF/PPTX nào trong: {FOLDER}")
    raise SystemExit

ordered = sorted(groups.items(), key=lambda x: sort_key(x[0]))
numbers = {stem: i for i, (stem, _) in enumerate(ordered, start=1)}

# Xem trước kết quả
print(f"Thư mục: {FOLDER}\n")
plan = []
for stem, exts in ordered:
    for ext, old in sorted(exts.items()):
        new = f"{numbers[stem]}. {stem}{ext}"
        plan.append((stem, ext, old, new))
        print(f"  {old}\n    -> {new}")

if input("\nĐổi tên theo danh sách trên? (y/n): ").strip().lower() != 'y':
    print("Đã huỷ, không đổi gì.")
    raise SystemExit

# Bước 1: đổi sang tên tạm để tránh trùng tên
temp = []
for stem, ext, old, new in plan:
    tmp = f"__tmp__{stem}{ext}"
    os.rename(os.path.join(FOLDER, old), os.path.join(FOLDER, tmp))
    temp.append((tmp, old, new))

# Bước 2: đổi sang tên cuối cùng có đánh số
for tmp, old, new in temp:
    os.rename(os.path.join(FOLDER, tmp), os.path.join(FOLDER, new))
    print(f"Đã đổi: '{old}' -> '{new}'")
