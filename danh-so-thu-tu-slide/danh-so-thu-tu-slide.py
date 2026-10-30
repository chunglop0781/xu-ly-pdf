import os
import sys

# Lấy đường dẫn của chính thư mục chứa file Python này
folder_path = os.path.dirname(os.path.abspath(__file__))

# Lấy tên của chính file Python đang chạy để loại trừ
current_script = os.path.basename(__file__)

# Lấy danh sách tất cả các file trong thư mục (bỏ qua thư mục con và chính file script này)
files = [
    f
    for f in os.listdir(folder_path)
    if os.path.isfile(os.path.join(folder_path, f)) and f != current_script
]

# Sắp xếp tên file theo thứ tự bảng chữ cái A-Z
files.sort()

# Thực hiện đánh số thứ tự
for index, filename in enumerate(files, start=1):
    old_path = os.path.join(folder_path, filename)

    # Kiểm tra xem file đã được đánh số đúng thứ tự chưa để tránh trùng lặp
    if filename.startswith(f"{index}. "):
        continue

    new_filename = f"{index}. {filename}"
    new_path = os.path.join(folder_path, new_filename)

    # Thực hiện đổi tên file
    os.rename(old_path, new_path)
    print(f"Đã đổi: '{filename}' -> '{new_filename}'")

print("Hoàn tất đổi tên tất cả các file theo thứ tự Alpha-B!")
