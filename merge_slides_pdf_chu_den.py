"""
Nối các file PDF có tên dạng "1. abc.pdf", "2. xyz.pdf", ... "n. ....pdf"
(cùng thư mục với file script) theo thứ tự số, rồi đánh dấu số trang
ở góc phải dưới cùng, ghi tên file (bỏ .pdf) + " - MNHA", ví dụ:
    "1. ĐSTT_Chương 1_Ma trận và định thức_Phần 1 - MNHA"

Cài thư viện:  pip install pypdf reportlab
Chạy:          python merge_pdf.py
"""

import io
import re
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ====== CẤU HÌNH ======
FOLDER = Path(__file__).resolve().parent   # thư mục chứa PDF (mặc định: cùng thư mục script)
OUTPUT_NAME = "merged_MNHA.pdf"            # tên file kết quả
NOTE = " - MNHA"                           # ghi chú thêm sau số trang
# Font hỗ trợ tiếng Việt (chọn font đầu tiên tìm thấy)
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\times.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_NAME = "VNFont"
FONT_SIZE = 10                             # cỡ chữ tối đa (tên dài sẽ tự thu nhỏ cho vừa trang)
MARGIN_RIGHT = 2                           # cách mép phải (pt) - càng nhỏ càng sát góc
MARGIN_BOTTOM = 2                          # cách mép dưới (pt) - càng nhỏ càng sát góc
# ======================

PATTERN = re.compile(r"^\s*(\d+)\s*\.\s*.*\.pdf$", re.IGNORECASE)


def find_pdfs(folder: Path):
    """Lấy các file '<số>. *.pdf' và sắp xếp theo số."""
    files = []
    for f in folder.iterdir():
        if not f.is_file() or f.name == OUTPUT_NAME:
            continue
        m = PATTERN.match(f.name)
        if m:
            files.append((int(m.group(1)), f))
    files.sort(key=lambda x: x[0])
    return [f for _, f in files]


def register_font():
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            return
    print("Không tìm thấy font hỗ trợ tiếng Việt! Sửa FONT_CANDIDATES trong script.")
    sys.exit(1)


def make_stamp(text: str, box) -> PdfReader:
    """Tạo 1 trang PDF trong suốt chỉ chứa dòng chữ ở sát góc phải dưới của trang."""
    left, bottom = float(box.left), float(box.bottom)
    right, top = float(box.right), float(box.top)

    # Tự thu nhỏ cỡ chữ nếu tên quá dài so với bề rộng trang
    size = FONT_SIZE
    max_w = (right - left) - MARGIN_RIGHT * 2
    while size > 5 and pdfmetrics.stringWidth(text, FONT_NAME, size) > max_w:
        size -= 0.5

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(right, top))
    c.setFont(FONT_NAME, size)
    # Tính cả trường hợp trang có gốc toạ độ khác (0,0)
    c.drawRightString(right - MARGIN_RIGHT, bottom + MARGIN_BOTTOM, text)
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def main():
    register_font()
    pdfs = find_pdfs(FOLDER)
    if not pdfs:
        print('Không tìm thấy file nào dạng "1. *.pdf", "2. *.pdf", ...')
        sys.exit(1)

    print("Thứ tự nối file:")
    for p in pdfs:
        print("  ", p.name)

    writer = PdfWriter()
    page_no = 0

    for pdf_path in pdfs:
        reader = PdfReader(str(pdf_path))
        label = f"{pdf_path.stem}{NOTE}"   # tên file bỏ .pdf + " - MNHA"
        if reader.is_encrypted:
            reader.decrypt("")
        for page in reader.pages:
            page_no += 1

            # Nếu trang bị xoay thì "đóng" góc xoay vào nội dung để toạ độ góc phải dưới luôn đúng
            if (page.get("/Rotate") or 0) % 360 != 0:
                page.transfer_rotation_to_content()

            stamp_page = make_stamp(label, page.mediabox).pages[0]
            page.merge_page(stamp_page)

            writer.add_page(page)

    out_path = FOLDER / OUTPUT_NAME
    with open(out_path, "wb") as f:
        writer.write(f)

    print(f"\nXong! {len(pdfs)} file, {page_no} trang -> {out_path}")


if __name__ == "__main__":
    main()