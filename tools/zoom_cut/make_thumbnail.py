"""Tạo thumbnail YouTube 1280x720: lấy 1 khung hình + chữ tiêu đề.

    python make_thumbnail.py video.mp4 --time 00:25:10 --text "Thì hiện tại hoàn thành" -o thumb.jpg
Mốc thời gian theo video được truyền vào (gốc hoặc đã cắt).
"""
import argparse
import json
import os
import subprocess
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Colab / Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",                                # Windows
]


def grab_frame(video, t, path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", video,
                    "-frames:v", "1", "-q:v", "2", path], check=True)


def make(frame_path, text, out, brand="EWIT"):
    W, H = 1280, 720
    img = Image.open(frame_path).convert("RGB")
    scale = max(W / img.width, H / img.height)  # phủ kín khung, cắt phần thừa
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))

    # Dải tối phía dưới để chữ dễ đọc
    shade = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(shade)
    for y in range(H // 3, H):
        d.line([(0, y), (W, y)], fill=int(215 * (y - H // 3) / (H - H // 3)))
    img = Image.composite(Image.new("RGB", (W, H), "black"), img, shade)

    font_path = next((f for f in FONTS if os.path.exists(f)), None)
    draw = ImageDraw.Draw(img)
    size = 96
    while size > 40:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        lines = textwrap.wrap(text.upper(), width=max(8, int(1150 / (size * 0.62))))
        if len(lines) <= 3:
            break
        size -= 8
    y = H - 50 - len(lines) * int(size * 1.15)
    for line in lines:
        draw.text((60, y), line, font=font, fill="#FFD400", stroke_width=6, stroke_fill="black")
        y += int(size * 1.15)
    bfont = ImageFont.truetype(font_path, 44) if font_path else font
    draw.text((W - 60, 40), brand, font=bfont, fill="white", anchor="ra",
              stroke_width=4, stroke_fill="black")
    img.save(out, quality=90)
    print(f"Đã tạo thumbnail {out}")


FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _font(spec, size=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, spec["font"]), size or spec["co"])
    if spec.get("bien_the"):
        f.set_variation_by_name(spec["bien_the"])
    return f


def _wrap(draw, text, spec):
    """Ngắt dòng theo chiều rộng; tự giảm cỡ chữ nếu vượt số dòng."""
    size = spec["co"]
    while True:
        font, lines = _font(spec, size), []
        for word in text.split():
            test = (lines[-1] + " " + word) if lines else word
            if lines and draw.textlength(test, font=font) <= spec["rong_toi_da"]:
                lines[-1] = test
            else:
                lines.append(word)
        if len(lines) <= spec["so_dong_toi_da"] or size <= spec["co_nho_nhat"]:
            return font, lines, spec["gian_dong"] * size / spec["co"]
        size -= 2


ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
# Vị trí các ô ảnh trong vòng tròn, theo tỉ lệ bán kính: (dx, dy, bán kính)
SLOTS = {
    1: [(0, 0, 1.0)],
    2: [(-0.5, 0, 0.46), (0.5, 0, 0.46)],
    3: [(0, -0.47, 0.4), (-0.48, 0.34, 0.4), (0.48, 0.34, 0.4)],
    4: [(-0.42, -0.42, 0.38), (0.42, -0.42, 0.38), (-0.42, 0.42, 0.38), (0.42, 0.42, 0.38)],
}


def _circle(photo_path, diameter):
    """Cắt ảnh thành hình tròn (ưu tiên phần trên – nơi có khuôn mặt)."""
    im = Image.open(photo_path).convert("RGB")
    side = min(im.size)
    left = (im.width - side) // 2
    top = int((im.height - side) * 0.3)
    im = im.crop((left, top, left + side, top + side)).resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter * 4, diameter * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter * 4 - 1, diameter * 4 - 1], fill=255)
    return im, mask.resize((diameter, diameter), Image.LANCZOS)


def place_people(img, people, spec):
    """people: list dict {ten, anh (đường dẫn hoặc None), gioi_tinh}. Thiếu ảnh → chibi."""
    cx, cy = spec["tam"]
    R = spec["ban_kinh"]
    d = ImageDraw.Draw(img)
    n = len(people)
    if n > 1:  # phủ logo trong vòng tròn trước khi xếp nhiều ảnh nhỏ
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=spec["mau_trong"])
    name_font = _font({"font": "BeVietnamPro-SemiBold.ttf", "co": 20})
    for p, (dx, dy, rr) in zip(people, SLOTS[n]):
        r = int(R * rr)
        x, y = int(cx + dx * R), int(cy + dy * R)
        src = p.get("anh") or os.path.join(
            ASSET_DIR, "chibi_nu.png" if str(p.get("gioi_tinh", "")).lower() in ("nữ", "nu") else "chibi_nam.png")
        face, mask = _circle(src, 2 * r)
        img.paste(face, (x - r, y - r), mask)
        if n > 1:
            d.ellipse([x - r, y - r, x + r, y + r], outline=spec["vien"], width=6)
            name = p.get("ten", "")
            w = d.textlength(name, font=name_font) + 24
            d.rounded_rectangle([x - w / 2, y + r - 22, x + w / 2, y + r + 10], radius=14, fill=spec["mau_nhan_ten"])
            d.text((x, y + r - 6), name, font=name_font, fill="white", anchor="mm")


def make_from_template(cfg_path, bg_path, content, out, people=None):
    """Ghép chữ (và ảnh người nếu có) vào ảnh nền mẫu. content: dong_tren, tieu_de, nguoi, ngay."""
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    img = Image.open(bg_path).convert("RGB").resize((1280, 720))
    if people:
        place_people(img, people[:4], cfg["o_anh"])
    d = ImageDraw.Draw(img)
    for key in ("dong_tren", "tieu_de", "nguoi", "ngay"):
        text, spec = content.get(key, ""), cfg[key]
        if not text:
            continue
        x, y = spec["xy"]
        if key == "tieu_de":
            text = text.upper() if spec.get("viet_hoa") else text
            font, lines, gap = _wrap(d, text, spec)
            for i, line in enumerate(lines):
                d.text((x, y + i * gap), line, font=font, fill=spec["mau"], anchor="la")
            continue
        font = _font(spec)
        if spec.get("nhan"):  # nhãn màu (ví dụ ô ngày): nới rộng nếu chữ dài hơn
            l, t, r, b = spec["nhan"]["hop"]
            r = max(r, x + d.textlength(text, font=font) + spec["nhan"]["dem_phai"])
            d.rounded_rectangle([l, t, r, b], radius=spec["nhan"]["bo_goc"], fill=spec["nhan"]["mau"])
        d.text((x, y), text, font=font, fill=spec["mau"], anchor="la")
    img.save(out, quality=92)
    print(f"Đã tạo thumbnail theo mẫu {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--time", default="00:00:30")
    ap.add_argument("--text", required=True)
    ap.add_argument("--brand", default="EWIT")
    ap.add_argument("-o", "--output", default="thumbnail.jpg")
    ap.add_argument("--mau", help="File bố cục mẫu, ví dụ mau/training.json")
    ap.add_argument("--nen", help="Ảnh nền của mẫu")
    ap.add_argument("--dong-tren", default="")
    ap.add_argument("--nguoi", default="")
    ap.add_argument("--ngay", default="")
    ap.add_argument("--anh-nguoi", action="append", default=[],
                    help='Lặp lại tối đa 4 lần: "Tên|đường dẫn ảnh (trống = chibi)|Nam/Nữ"')
    a = ap.parse_args()
    if a.mau:
        people = []
        for item in a.anh_nguoi:
            ten, anh, gt = (item.split("|") + ["", ""])[:3]
            people.append({"ten": ten, "anh": anh or None, "gioi_tinh": gt})
        make_from_template(a.mau, a.nen, {"dong_tren": a.dong_tren, "tieu_de": a.text,
                                          "nguoi": a.nguoi, "ngay": a.ngay}, a.output, people)
        return
    with tempfile.TemporaryDirectory() as tmp:
        frame = os.path.join(tmp, "frame.jpg")
        grab_frame(a.video, a.time, frame)
        make(frame, a.text, a.output, a.brand)


if __name__ == "__main__":
    main()
