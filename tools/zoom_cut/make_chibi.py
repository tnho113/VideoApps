"""Vẽ 2 avatar chibi đại diện (nam, nữ) theo màu EWIT – dùng khi người chia sẻ chưa có ảnh.

    python make_chibi.py      # tạo assets/chibi_nam.png, assets/chibi_nu.png (600x600)
"""
import os

from PIL import Image, ImageDraw

S = 4                       # vẽ lớn gấp 4 rồi thu nhỏ cho mịn
W = 600 * S
SKIN, HAIR, INK = "#FFDDC2", "#2B2238", "#2B2238"
GREEN, PURPLE, BG = "#1FAF6E", "#4A1D80", "#EDE4F7"


def e(d, cx, cy, rx, ry, **kw):
    d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], **kw)


def chibi(gender, transparent=False):
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0) if transparent else BG)
    d = ImageDraw.Draw(img)
    # Áo
    shirt = GREEN if gender == "nam" else "#7B3FBF"
    e(d, 300, 640, 200, 190, fill=shirt)
    d.polygon([(255 * S, 455 * S), (300 * S, 515 * S), (345 * S, 455 * S)], fill="white")  # cổ áo
    e(d, 300, 438, 48, 30, fill=SKIN)  # cổ
    if gender == "nu":  # tóc dài phía sau
        d.rounded_rectangle([118 * S, 190 * S, 482 * S, 520 * S], radius=150 * S, fill=HAIR)
    # Đầu
    e(d, 300, 285, 165, 158, fill=SKIN)
    e(d, 138, 300, 22, 30, fill=SKIN)
    e(d, 462, 300, 22, 30, fill=SKIN)  # tai
    # Tóc phía trước
    if gender == "nam":
        d.chord([130 * S, 110 * S, 470 * S, 400 * S], 180, 360, fill=HAIR)
        for x in (175, 235, 300, 365, 425):  # mái lởm chởm
            d.polygon([((x - 38) * S, 252 * S), (x * S, 300 * S), ((x + 38) * S, 252 * S)], fill=HAIR)
    else:
        d.chord([128 * S, 105 * S, 472 * S, 410 * S], 180, 360, fill=HAIR)
        d.pieslice([150 * S, 150 * S, 320 * S, 290 * S], 90, 270, fill=HAIR)   # mái lệch
        d.polygon([(330 * S, 258 * S), (420 * S, 250 * S), (450 * S, 300 * S), (440 * S, 258 * S)], fill=HAIR)
        # kẹp tóc hình lá EWIT
        d.polygon([(400 * S, 170 * S), (425 * S, 205 * S), (400 * S, 240 * S), (375 * S, 205 * S)], fill=GREEN)
        d.line([(400 * S, 178 * S), (400 * S, 234 * S)], fill="white", width=4 * S)
    # Mắt
    for cx in (238, 362):
        e(d, cx, 318, 26, 34, fill=INK)
        e(d, cx - 8, 306, 9, 11, fill="white")
        e(d, cx + 9, 330, 4, 5, fill="white")
    if gender == "nu":  # lông mi
        for cx, sgn in ((238, -1), (362, 1)):
            d.line([((cx + sgn * 22) * S, 296 * S), ((cx + sgn * 36) * S, 284 * S)], fill=INK, width=5 * S)
    # Má hồng, miệng
    e(d, 200, 362, 26, 14, fill="#FFB3B8")
    e(d, 400, 362, 26, 14, fill="#FFB3B8")
    d.arc([272 * S, 340 * S, 328 * S, 386 * S], 20, 160, fill=INK, width=6 * S)
    img = img.resize((600, 600), Image.LANCZOS)
    return img if transparent else img.convert("RGB")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(out, exist_ok=True)
    for g in ("nam", "nu"):
        chibi(g).save(os.path.join(out, f"chibi_{g}.png"))
        chibi(g, True).save(os.path.join(out, f"chibi_{g}_tachnen.png"))
        print("Đã tạo chibi", g)
