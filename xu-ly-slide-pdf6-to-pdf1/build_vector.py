"""Tách 92 slide từ 16 trang handout (6 slide/trang) thành PDF 16:9, mỗi slide 1 trang.
Giữ nguyên nội dung vector (chữ, đường, hình vẽ) và các ảnh gốc; chỉ cắt theo khung từng slide.
"""
import sys
import pikepdf
from pikepdf import Name, Dictionary, Array

SRC = "/home/claude/src.pdf"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/slides_vector.pdf"

# khung slide (4:3) trên trang handout, toạ độ PDF (gốc dưới-trái)
FW, FH = 221.76, 166.32
COLS = [47.52, 306.72]
ROWS = [514.08, 294.96, 75.6]                 # trên -> dưới
FRAMES = [(x, y) for y in ROWS for x in COLS]  # thứ tự đọc: trái->phải, trên->dưới

# trang đích 16:9 (13.333in x 7.5in), slide 4:3 đặt giữa, cao bằng trang
PW, PH = 960.0, 540.0
S = PH / FH
OX = (PW - FW * S) / 2


def frame_index(rect):
    x, y = rect[0], rect[1]
    for i, (fx, fy) in enumerate(FRAMES):
        if abs(x - fx) < 0.6 and abs(y - fy) < 0.6:
            return i
    return None


TEXT_OPS = {'BT', 'ET', 'Tm', 'Td', 'TD', 'T*', 'TJ', 'Tj', "'", '"'}
PATH_OPS = {'m', 'l', 'c', 'v', 'y', 're', 'h'}
PAINT_OPS = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'}


def op_points(o, operands):
    if o not in PATH_OPS:
        return []
    v = [float(x) for x in operands]
    if o in ('m', 'l'):
        return [(v[0], v[1])]
    if o == 'c':
        return [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]
    if o in ('v', 'y'):
        return [(v[0], v[1]), (v[2], v[3])]
    if o == 're':
        return [(v[0], v[1]), (v[0] + v[2], v[1] + v[3])]
    return []


def frame_of_point(pt):
    if pt is None:
        return None
    for i, (fx, fy) in enumerate(FRAMES):
        if fx - 1 <= pt[0] <= fx + FW + 1 and fy - 1 <= pt[1] <= fy + FH + 1:
            return i
    return None


def centroid(points):
    if not points:
        return None
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def split_page(page):
    """Trả về {frame_idx: [(operands, op), ...]} theo đúng thứ tự vẽ.
    - khối q..Q: gán theo khung cắt (hoặc theo vị trí nếu không có khung cắt)
    - đường/hình vẽ & chữ nằm ngoài q..Q: gán theo vị trí
    - lệnh trạng thái (màu, nét...) ở mức ngoài cùng: chép cho mọi slide để giữ đúng ngữ cảnh
    """
    out = {i: [] for i in range(6)}
    depth = 0
    grp = []
    path, ppts = [], []
    text, in_text = [], False
    for operands, op in pikepdf.parse_content_stream(page):
        o = str(op)
        if depth > 0:
            grp.append((operands, op))
            if o == 'q':
                depth += 1
            elif o == 'Q':
                depth -= 1
                if depth == 0:
                    rect, pts = None, []
                    for a, p in grp:
                        po = str(p)
                        if po == 're':
                            rect = [float(x) for x in a]
                        if po in ('W', 'W*') and rect is not None:
                            break
                    else:
                        rect = None
                    idx = frame_index(rect) if rect else None
                    if idx is None:
                        for a, p in grp:
                            pts += op_points(str(p), a)
                        idx = frame_of_point(centroid(pts))
                    if idx is not None:
                        out[idx].extend(grp)
                    grp = []
            continue
        # depth == 0
        if o == 'q':
            depth = 1
            grp = [(operands, op)]
        elif o in ('BDC', 'BMC', 'EMC', 'MP', 'DP'):
            continue
        elif in_text:
            text.append((operands, op))
            if o == 'ET':
                in_text = False
                pt = None
                for a, p in text:
                    if str(p) in ('Tm', 'Td', 'TD'):
                        v = [float(x) for x in a]
                        pt = (v[4], v[5]) if str(p) == 'Tm' else (v[0], v[1])
                        break
                idx = frame_of_point(pt)
                # lệnh trạng thái (màu g/G/rg/RG...) trong khối chữ vẫn phải giữ cho các slide khác
                state = [(a, p) for a, p in text if str(p) not in TEXT_OPS]
                for i in range(6):
                    if i == idx:
                        out[i].extend(text)
                    else:
                        out[i].extend(state)
                text = []
        elif o == 'BT':
            in_text = True
            text = [(operands, op)]
        elif o in PATH_OPS:
            path.append((operands, op))
            ppts += op_points(o, operands)
        elif o in PAINT_OPS:
            idx = frame_of_point(centroid(ppts))
            if idx is not None:
                out[idx].extend(path + [(operands, op)])
            path, ppts = [], []
        elif o in ('W', 'W*'):
            path.append((operands, op))
        else:
            for i in range(6):                      # lệnh trạng thái
                out[i].append((operands, op))
    return {i: v for i, v in out.items() if any(str(p) in ('Do', 'TJ', 'Tj', 'S', 'f', 'f*', 'B', 'b', 'F', 'sh')
                                               for a, p in v)}


def main():
    pdf = pikepdf.open(SRC)
    src_pages = list(pdf.pages)
    new_pages = []
    count = 0
    for pi, page in enumerate(src_pages):
        res = pdf.make_indirect(page.Resources)
        parts = split_page(page)
        for idx in range(6):
            if idx not in parts:
                continue
            fx, fy = FRAMES[idx]
            tx, ty = OX - S * fx, -S * fy
            head = [
                (Array([]), pikepdf.Operator('q')),
                (Array([1]), pikepdf.Operator('g')),
                (Array([0, 0, PW, PH]), pikepdf.Operator('re')),
                (Array([]), pikepdf.Operator('f')),
                (Array([S, 0, 0, S, tx, ty]), pikepdf.Operator('cm')),
            ]
            # pikepdf cần operands là list
            seq = [(list(a), o) for a, o in head] + [(list(a), o) for a, o in parts[idx]] \
                  + [([], pikepdf.Operator('Q'))]
            data = pikepdf.unparse_content_stream(seq)
            stream = pdf.make_stream(data)
            d = Dictionary(Type=Name.Page, MediaBox=Array([0, 0, PW, PH]),
                           Resources=res, Contents=stream)
            new_pages.append(pdf.make_indirect(d))
            count += 1
    # thay toàn bộ trang cũ
    while len(pdf.pages) > 0:
        del pdf.pages[0]
    for p in new_pages:
        pdf.pages.append(pikepdf.Page(p))
    pdf.docinfo['/Title'] = 'Cấu trúc dữ liệu và giải thuật - Danh sách liên kết đơn (slide 16:9)'
    pdf.remove_unreferenced_resources()
    pdf.save(OUT, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    print("số slide:", count)


main()
