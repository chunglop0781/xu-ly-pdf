"""Gộp ảnh slide_1.png / slide_01.png / slide_001.png thành PDF.

Hỗ trợ các cấu trúc:
1) ROOT/<tên bất kỳ>/slide_001.png ...
2) ROOT/<tên>.pdf/slide_001.png ...
3) ROOT/slide_001.png ... (ảnh nằm trực tiếp trong ROOT)

Nếu DELETE_SOURCE=True, chỉ xóa thư mục nguồn con sau khi PDF tạo thành công.
Không bao giờ xóa ROOT vì có thể chứa chính script này và các tệp khác.
"""

import re
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image

# ====== CẤU HÌNH ======
ROOT = Path(r"C:\Users\Admin\Downloads\slide-dstt")
IMAGE_PREFIX = "slide_"
IMAGE_EXT = ".png"
MAX_ERRORS = 5
DELETE_SOURCE = True
RESOLUTION = 150.0
# ======================


def natural_key(value: str):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", value)]


def image_number(path: Path) -> Optional[int]:
    """Trả về số slide nếu tên đúng dạng slide_<số>.png."""
    pattern = rf"^{re.escape(IMAGE_PREFIX)}(\d+){re.escape(IMAGE_EXT)}$"
    match = re.match(pattern, path.name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def contains_slide_images(folder: Path) -> bool:
    try:
        return any(
            p.is_file() and image_number(p) is not None
            for p in folder.iterdir()
        )
    except OSError:
        return False


def find_image(folder: Path, number: int) -> Optional[Path]:
    """Tìm các cách đặt tên phổ biến cho cùng một số slide."""
    candidates = (
        f"{IMAGE_PREFIX}{number:02d}{IMAGE_EXT}",
        f"{IMAGE_PREFIX}{number}{IMAGE_EXT}",
        f"{IMAGE_PREFIX}{number:03d}{IMAGE_EXT}",
    )
    for name in dict.fromkeys(candidates):
        path = folder / name
        if path.is_file():
            return path

    # Hỗ trợ khác biệt chữ hoa/chữ thường trên Windows và tên có nhiều số 0.
    for path in folder.iterdir():
        if path.is_file() and image_number(path) == number:
            return path
    return None


def load_rgb(path: Path) -> Image.Image:
    """Đọc ảnh và chuyển về RGB; nền trong suốt được đặt thành trắng."""
    with Image.open(path) as source:
        if source.mode in ("RGBA", "LA", "P") or "transparency" in source.info:
            rgba = source.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            rgba.close()
            return background
        return source.convert("RGB")


def collect_images(folder: Path):
    images = []
    errors = 0
    number = 1

    while errors < MAX_ERRORS:
        path = find_image(folder, number)
        if path is None:
            errors += 1
            print(f"    [lỗi {errors}/{MAX_ERRORS}] thiếu ảnh số {number}")
        else:
            try:
                images.append(load_rgb(path))
                errors = 0
                print(f"    Đã đọc: {path.name}")
            except Exception as exc:
                errors += 1
                print(f"    [lỗi {errors}/{MAX_ERRORS}] {path.name}: {exc}")
        number += 1

    print(
        f"    Gặp {MAX_ERRORS}/{MAX_ERRORS} lỗi liên tiếp -> dừng; "
        f"đọc được {len(images)} ảnh."
    )
    return images


def discover_sources(root: Path):
    """Tìm ảnh trực tiếp trong ROOT và trong mọi thư mục con có ảnh slide."""
    sources = []

    if contains_slide_images(root):
        sources.append(root)

    child_folders = [
        folder for folder in root.rglob("*")
        if folder.is_dir() and contains_slide_images(folder)
    ]
    # Xử lý thư mục sâu trước để khi xóa thư mục cha, các thư mục con
    # đã được chuyển đổi xong. Cùng độ sâu thì sắp xếp tự nhiên.
    child_folders.sort(
        key=lambda folder: (
            -len(folder.relative_to(root).parts),
            natural_key(str(folder.relative_to(root))),
        )
    )
    sources.extend(child_folders)

    return sources


def output_path_for(root: Path, source: Path, index: int) -> Path:
    if source == root:
        base_name = root.name
    else:
        # Giữ tên thư mục làm tên tài liệu; số thứ tự tránh trùng tên.
        base_name = source.name

    # Nếu thư mục đã có đuôi .pdf thì không thêm .pdf lần thứ hai.
    if base_name.lower().endswith(".pdf"):
        base_name = base_name[:-4]

    return root / f"{index}. {base_name}.pdf"


def create_pdf(source: Path, output: Path) -> int:
    images = collect_images(source)
    if not images:
        print("    Không có ảnh hợp lệ, bỏ qua (không xóa nguồn).")
        return 0

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(
            output,
            "PDF",
            resolution=RESOLUTION,
            save_all=True,
            append_images=images[1:],
        )
    finally:
        for image in images:
            image.close()

    if not output.is_file() or output.stat().st_size <= 0:
        raise RuntimeError("PDF không được tạo hoặc có dung lượng bằng 0.")

    print(f"    -> {output.name} ({len(images)} trang)")

    if DELETE_SOURCE and source != ROOT:
        shutil.rmtree(source)
        print("    Đã xóa thư mục ảnh nguồn.")
    elif DELETE_SOURCE and source == ROOT:
        print("    Giữ ROOT: không xóa thư mục chứa script và các tệp khác.")

    return len(images)


def main():
    if not ROOT.exists():
        print(f"Không tìm thấy thư mục ROOT: {ROOT}")
        return
    if not ROOT.is_dir():
        print(f"ROOT không phải thư mục: {ROOT}")
        return

    sources = discover_sources(ROOT)
    if not sources:
        print(f"Không tìm thấy ảnh dạng {IMAGE_PREFIX}001{IMAGE_EXT} trong:")
        print(f"  {ROOT}")
        print("Kiểm tra ảnh đang nằm trực tiếp trong ROOT hay trong thư mục con.")
        return

    print(f"Tìm thấy {len(sources)} thư mục nguồn:")
    for source in sources:
        print(f"  - {source}")

    total_pages = 0
    completed = 0

    for index, source in enumerate(sources, start=1):
        output = output_path_for(ROOT, source, index)
        print(f"\n[{index}/{len(sources)}] {source}")

        if output.exists():
            print(f"    Đã tồn tại {output.name}; bỏ qua để không ghi đè.")
            continue

        try:
            page_count = create_pdf(source, output)
            if page_count:
                completed += 1
                total_pages += page_count
        except Exception as exc:
            print(f"    LỖI tạo PDF: {exc}")

    print("\n========== TỔNG KẾT ==========")
    print(f"Số nguồn tìm thấy: {len(sources)}")
    print(f"PDF tạo thành công: {completed}")
    print(f"Tổng số trang: {total_pages}")
    print("Hoàn tất.")


if __name__ == "__main__":
    main()
