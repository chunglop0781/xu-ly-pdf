import cv2
import numpy as np


def _lanczos(img, w, h):
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4)


def ibp_upscale(img, scale, iters=6, step=1.0):
    """Siêu phân giải bằng iterative back-projection: ảnh phóng to phải khớp lại ảnh gốc khi thu nhỏ."""
    f = img.astype(np.float32)
    h, w = f.shape[:2]
    W, H = w * scale, h * scale
    up = _lanczos(f, W, H)
    for _ in range(iters):
        down = cv2.resize(up, (w, h), interpolation=cv2.INTER_AREA)
        err = f - down
        up = up + step * _lanczos(err, W, H)
    return np.clip(up, 0, 255)


def unsharp(img, sigma, amount):
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    return np.clip(img + amount * (img - blur), 0, 255)


def edge_steepen(img, radius, strength=0.9, gain=2):
    """Làm dốc biên: kéo điểm chuyển tiếp về hai phía (nền/nét) nhưng giữ nguyên màu vùng phẳng."""
    k = 2 * radius + 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    lo = cv2.erode(img, ker)
    hi = cv2.dilate(img, ker)
    rng = hi - lo
    t = np.where(rng > 24, (img - lo) / np.maximum(rng, 1e-3), 0.5)
    t = np.clip(t, 0, 1)
    for _ in range(gain):
        t = t * t * (3 - 2 * t)           # smoothstep -> dốc hơn
    steep = lo + t * rng
    out = np.where(rng > 24, steep, img)
    return np.clip((1 - strength) * img + strength * out, 0, 255)


def white_point(rgb):
    """Nếu nền ảnh gần trắng (viền ảnh), kéo về trắng tinh để không lộ khung xám nhạt trên slide trắng."""
    h, w = rgb.shape[:2]
    b = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(np.float32)
    med = np.median(b, axis=0)
    if med.min() >= 232 and (med.max() - med.min()) <= 14:
        gain = 255.0 / np.maximum(med, 1)
        return np.clip(rgb.astype(np.float32) * gain, 0, 255).astype(np.uint8)
    return rgb


def enhance_graphic(rgb, scale=4, jpeg=False):
    """Ảnh chụp màn hình / sơ đồ / chữ: nét, sạch viền."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h = 4 if jpeg else 2
    bgr = cv2.fastNlMeansDenoisingColored(bgr, None, h, h, 5, 15)
    up = ibp_upscale(bgr, scale, iters=6, step=1.0)
    up = edge_steepen(up, radius=scale, strength=0.9, gain=2)
    up = unsharp(up, sigma=1.0, amount=0.5)
    return white_point(cv2.cvtColor(up.astype(np.uint8), cv2.COLOR_BGR2RGB))


def enhance_photo(rgb, scale=4, jpeg=True, strong=False):
    """Ảnh chụp / minh hoạ nhiều sắc thái: khử nhiễu JPEG, phóng to, tăng chi tiết."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    # khử nhiễu: ưu tiên giữ chi tiết (luma nhẹ hơn, chroma mạnh hơn)
    hl, hc = (5, 7) if jpeg else (3, 4)
    if strong:                                    # ảnh dither (khung GIF): xoá chấm li ti trước
        bgr = cv2.medianBlur(bgr, 3)
        hl, hc = 5, 8
    bgr = cv2.fastNlMeansDenoisingColored(bgr, None, hl, hc, 7, 25)
    up = ibp_upscale(bgr, scale, iters=5, step=0.9)
    up = unsharp(up, sigma=1.6, amount=0.8)
    up = unsharp(up, sigma=0.7, amount=0.35)
    return cv2.cvtColor(up.astype(np.uint8), cv2.COLOR_BGR2RGB)
