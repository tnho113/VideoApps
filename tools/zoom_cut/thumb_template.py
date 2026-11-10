"""Ghép thumbnail từ ảnh nền mẫu (do người dùng thiết kế) + chữ của buổi + ảnh người.

Bố cục mỗi họ mẫu nằm trong mau/<bo_cuc>.json; màu "{nhan}" được thay bằng Màu nhấn của mẫu.
Kiểu ảnh:
  "trong"  – ảnh chân dung cắt tròn nằm trong vòng tròn của mẫu
  "ngoai"  – ảnh đã tách nền (PNG trong suốt), thân nằm trong vòng tròn, đầu/vai tràn ra ngoài
"""
import json
import os

import numpy as np

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
ASSET_DIR = os.path.join(HERE, "assets")
W, H = 1280, 720
# Vị trí các ô ảnh trong vòng tròn, theo tỉ lệ bán kính: (dx, dy, bán kính)
SLOTS = {
    1: [(0, 0, 1.0)],
    2: [(-0.5, 0, 0.46), (0.5, 0, 0.46)],
    3: [(0, -0.47, 0.4), (-0.48, 0.34, 0.4), (0.48, 0.34, 0.4)],
    4: [(-0.42, -0.42, 0.38), (0.42, -0.42, 0.38), (-0.42, 0.42, 0.38), (0.42, 0.42, 0.38)],
}


def load_layout(name, accent="#1FAF6E", accent2=""):
    """{nhan} = màu nhấn chính (ngày giờ, viền), {nhan2} = màu nhấn phụ (ví dụ chữ LIVE)."""
    path = name if name.endswith(".json") else os.path.join(HERE, "mau", name + ".json")
    accent = accent or "#1FAF6E"
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read().replace("{nhan2}", accent2 or accent).replace("{nhan}", accent))


def font(spec, size=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, spec["font"]), size or spec["co"])
    if spec.get("bien_the"):
        f.set_variation_by_name(spec["bien_the"])
    return f


def _wrap(d, text, spec):
    size = spec["co"]
    while True:
        f, lines = font(spec, size), []
        for para in text.split("\n"):  # xuống dòng chủ động (Alt+Enter trong ô Sheet)
            start = len(lines)
            for word in para.split():
                test = (lines[-1] + " " + word) if len(lines) > start else word
                if len(lines) > start and d.textlength(test, font=f) <= spec["rong_toi_da"]:
                    lines[-1] = test
                else:
                    lines.append(word)
        if len(lines) <= spec["so_dong_toi_da"] or size <= spec["co_nho_nhat"]:
            return f, lines, spec["gian_dong"] * size / spec["co"]
        size -= 2


def chibi_path(gender, transparent=False):
    g = "nu" if str(gender).strip().lower() in ("nữ", "nu") else "nam"
    return os.path.join(ASSET_DIR, f"chibi_{g}{'_tachnen' if transparent else ''}.png")


def _circle(src, diameter, bg="#5B2A9E"):
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):  # ảnh tách nền → đặt lên màu nền của vòng tròn
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, bg)
        flat.paste(im, (0, 0), im)
        im = flat
    im = im.convert("RGB")
    side = min(im.size)
    left, top = (im.width - side) // 2, int((im.height - side) * 0.3)  # ưu tiên phần mặt
    im = im.crop((left, top, left + side, top + side)).resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter * 4,) * 2, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter * 4 - 1, diameter * 4 - 1], fill=255)
    return im, mask.resize((diameter, diameter), Image.LANCZOS)


def _name_tag(img, x, y, name, spec, size=20):
    """Nhãn tên ở chân ảnh: bóng đổ mờ + nền tối bán trong suốt + viền màu nhấn → chữ luôn rõ."""
    if not name:
        return
    from PIL import ImageFilter
    f = font({"font": "BeVietnamPro-Bold.ttf", "co": size})
    probe = ImageDraw.Draw(img)
    w, h = probe.textlength(name, font=f) + size * 1.4, size * 1.7
    y = min(y, H - h / 2 - 10)
    x = min(max(x, w / 2 + 10), W - w / 2 - 10)
    box = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([box[0], box[1] + 4, box[2], box[3] + 6], radius=h / 2,
                                             fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    tag = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    r, g, b = Image.new("RGB", (1, 1), spec["mau_nhan_ten"]).getpixel((0, 0))
    td.rounded_rectangle(box, radius=h / 2, fill=(r, g, b, 225), outline=spec["vien"], width=max(2, size // 10))
    td.text((x, y), name, font=f, fill="white", anchor="mm", stroke_width=1, stroke_fill=(0, 0, 0, 120))
    base = img.convert("RGBA")
    base.alpha_composite(shadow)
    base.alpha_composite(tag)
    img.paste(base.convert("RGB"))


def place_inside(img, people, spec, show_names=False):
    cx, cy = spec["tam"]
    R = spec["ban_kinh"]
    d = ImageDraw.Draw(img)
    n = len(people)
    if n > 1:  # phủ phần trang trí trong vòng tròn trước khi xếp nhiều ảnh nhỏ
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=spec["mau_trong"])
    for p, (dx, dy, rr) in zip(people, SLOTS[n]):
        r, x, y = int(R * rr), int(cx + dx * R), int(cy + dy * R)
        src = p.get("anh") or p.get("anh_tach_nen") or chibi_path(p.get("gioi_tinh"))
        face, mask = _circle(src, 2 * r, spec["mau_trong"])
        img.paste(face, (x - r, y - r), mask)
        if n > 1:
            d.ellipse([x - r, y - r, x + r, y + r], outline=spec["vien"], width=6)
        if show_names:
            _name_tag(img, x, y + r - (40 if n == 1 else 6), p.get("ten", ""), spec, 30 if n == 1 else 20)
            d = ImageDraw.Draw(img)


def place_outside(img, people, spec, show_names=False):
    """Người tách nền đứng trước vòng tròn: phần dưới tâm bị cắt theo vòng tròn, phía trên tràn ra."""
    cx, cy = spec["tam"]
    R = spec["ban_kinh"]
    x0, y0, x1, y1 = spec.get("hop_phu_ngoai") or [cx - R, cy - R - int(R * 0.6), cx + R, min(H, cy + R)]
    clip = Image.new("L", (W, H), 0)
    dc = ImageDraw.Draw(clip)
    dc.rectangle([0, 0, W, cy], fill=255)                 # trên tâm: được tràn ra
    dc.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)  # dưới tâm: gọn trong vòng tròn
    n = len(people)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    slot_w = (x1 - x0) / (1 + 0.6 * (n - 1))               # mỗi người chồng nhau 40%
    for i, p in enumerate(people):
        im = Image.open(p.get("anh_tach_nen") or chibi_path(p.get("gioi_tinh"), True)).convert("RGBA")
        box = im.getbbox()
        if box:
            im = im.crop(box)
        h_max = (y1 - y0) * (1 if n == 1 else 0.85)
        scale = min(slot_w / im.width, h_max / im.height)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        sx = int(x0 + i * slot_w * 0.6 + (slot_w - im.width) / 2)
        layer.alpha_composite(im, (sx, int(y1 - im.height)))
    alpha = Image.fromarray(np.minimum(np.asarray(layer.getchannel("A")), np.asarray(clip)))
    layer.putalpha(alpha)
    img.paste(layer, (0, 0), layer)
    if show_names:
        for i, p in enumerate(people):
            stagger = (i % 2) * 46 if n > 2 else 0          # 3–4 người: so le để nhãn không chồng
            _name_tag(img, int(x0 + i * slot_w * 0.6 + slot_w / 2), y1 - 45 - stagger, p.get("ten", ""), spec,
                      30 if n == 1 else 18 if n > 2 else 22)


def compose(layout, bg_path, content, out, people=None, kieu="trong", logo_path=None, show_names=False):
    """content: dong_tren, tieu_de, nguoi, ngay. people: list {ten, anh, anh_tach_nen, gioi_tinh}."""
    img = Image.open(bg_path).convert("RGB").resize((W, H))
    if people:
        (place_outside if kieu == "ngoai" else place_inside)(img, people[:4], layout["o_anh"], show_names)
    d = ImageDraw.Draw(img)
    if layout.get("logo") and logo_path:
        lg = Image.open(logo_path).convert("RGBA")
        x0, y0, x1, y1 = layout["logo"]["hop"]
        lg.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
        img.paste(lg, (x0 + (x1 - x0 - lg.width) // 2, y0 + (y1 - y0 - lg.height) // 2), lg)
    tag = layout.get("nhan_goc")
    if tag:
        d.rounded_rectangle(tag["hop"], radius=tag["bo_goc"], fill=tag["mau"])
        x, y = tag["xy"]
        for part in tag["phan"]:
            f = font(part)
            d.text((x, y), part["chu"], font=f, fill=part["mau"], anchor="la")
            x += d.textlength(part["chu"], font=f)
    for spec in layout.get("chu_co_dinh", []):
        d.text(spec["xy"], spec["chu"], font=font(spec), fill=spec["mau"], anchor="la")
    for key, spec in layout["chu"].items():
        text = content.get(key, "")
        if not text:
            continue
        text = text.upper() if spec.get("viet_hoa") else text
        x, y = spec["xy"]
        if "rong_toi_da" in spec:
            f, lines, gap = _wrap(d, text, spec)
            for i, line in enumerate(lines):
                d.text((x, y + i * gap), line, font=f, fill=spec["mau"], anchor="la")
            continue
        f = font(spec)
        if spec.get("nhan"):  # ô màu phía sau chữ, tự nới rộng
            l, t, r, b = spec["nhan"]["hop"]
            r = max(r, x + d.textlength(text, font=f) + spec["nhan"]["dem_phai"])
            d.rounded_rectangle([l, t, r, b], radius=spec["nhan"]["bo_goc"], fill=spec["nhan"]["mau"])
        d.text((x, y), text, font=f, fill=spec["mau"], anchor="la")
    img.save(out, quality=92)
    print(f"Đã tạo thumbnail {out}")
    return out
