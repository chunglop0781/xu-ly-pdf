import io, struct, zlib, sys, time
import numpy as np, cv2, pikepdf
from pikepdf import Name, Dictionary, PdfImage
from PIL import Image
import enhance as E

SRC = "/home/claude/slides_vector.pdf"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/slides_final.pdf"
LOGO = "/mnt/user-data/uploads/Logo-DH-Cong-Nghe-Thong-Tin-UIT-V.webp"
SCALE = 4

# ảnh dạng "ảnh chụp/minh hoạ nhiều sắc thái" (khử nhiễu + tăng chi tiết) theo kích thước gốc
PHOTO = {(195, 132), (330, 330), (205, 107), (532, 224), (99, 99), (120, 105),
         (500, 376), (165, 150), (410, 308), (153, 154), (333, 191)}
GRADIENT = {(376, 344)}            # kim tự tháp gradient 16 màu -> làm mịn bậc màu
JPEG_GRAPHIC_HINT = True


def png_idat(arr):
    """Nén PNG rồi lấy luồng IDAT để nhúng thẳng vào PDF (Flate + PNG predictor)."""
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='PNG', optimize=True)
    data = buf.getvalue()
    pos, idat = 8, b''
    while pos < len(data):
        ln, = struct.unpack('>I', data[pos:pos + 4]); typ = data[pos + 4:pos + 8]
        if typ == b'IDAT': idat += data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    return idat


def jpeg_bytes(arr, q=94):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format='JPEG', quality=q, subsampling=0, optimize=True)
    return buf.getvalue()


def smooth_gradient(rgb, scale):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    up = cv2.resize(bgr, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    for _ in range(2):
        up = cv2.bilateralFilter(up, 9, 14, 8)
    rng = np.random.default_rng(1)
    up = up + rng.normal(0, 0.8, up.shape).astype(np.float32)      # phá bậc màu (banding)
    up = E.unsharp(np.clip(up, 0, 255), 1.2, 0.5)
    return cv2.cvtColor(up.astype(np.uint8), cv2.COLOR_BGR2RGB)


def set_image(obj, arr, as_jpeg):
    h, w = arr.shape[:2]
    for k in ('/Decode', '/Mask', '/SMask', '/DecodeParms', '/Filter'):
        if k in obj: del obj[k]
    if as_jpeg:
        obj.write(jpeg_bytes(arr), filter=Name.DCTDecode)
    else:
        obj.write(png_idat(arr), filter=Name.FlateDecode,
                  decode_parms=Dictionary(Predictor=15, Colors=3, Columns=w, BitsPerComponent=8))
    obj.Width = w; obj.Height = h
    obj.ColorSpace = Name.DeviceRGB
    obj.BitsPerComponent = 8
    obj.Interpolate = True


def main():
    pdf = pikepdf.open(SRC)
    logo = Image.open(LOGO)
    if logo.mode in ('RGBA', 'LA', 'P'):
        logo = logo.convert('RGBA')
        bg = Image.new('RGBA', logo.size, (255, 255, 255, 255)); bg.alpha_composite(logo); logo = bg
    logo = np.asarray(logo.convert('RGB'))

    imgs = [o for o in pdf.objects if isinstance(o, pikepdf.Stream) and o.get('/Subtype') == '/Image']
    print("số ảnh:", len(imgs))
    t0 = time.time()
    for obj in imgs:
        w, h = int(obj.Width), int(obj.Height)
        key = (w, h)
        flt = str(obj.get('/Filter'))
        is_jpeg = 'DCT' in flt
        rgb = np.asarray(PdfImage(obj).as_pil_image().convert('RGB'))
        if key == (92, 110):                      # logo UIT -> thay bằng bản gốc độ phân giải cao
            out, jp, kind = logo, False, 'logo (thay bằng file bạn gửi)'
        elif key in GRADIENT:
            out, jp, kind = smooth_gradient(rgb, SCALE), False, 'gradient'
        elif key in PHOTO:
            out, jp, kind = E.enhance_photo(rgb, SCALE, jpeg=is_jpeg), True, 'ảnh'
        else:
            out, jp, kind = E.enhance_graphic(rgb, SCALE, jpeg=is_jpeg), False, 'đồ hoạ/chữ'
        set_image(obj, out, jp)
        print(f"{w}x{h} -> {out.shape[1]}x{out.shape[0]}  [{kind}]")
    print("thời gian xử lý ảnh: %.1fs" % (time.time() - t0))
    pdf.docinfo['/Title'] = 'Cấu trúc dữ liệu và giải thuật - Tổng quan về CTDL và GT (slide)'
    pdf.save(OUT, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)


main()
