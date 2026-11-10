"""Tạo thumbnail YouTube 1280x720: lấy 1 khung hình + chữ tiêu đề.

    python make_thumbnail.py video.mp4 --time 00:25:10 --text "Thì hiện tại hoàn thành" -o thumb.jpg
Mốc thời gian theo video được truyền vào (gốc hoặc đã cắt).
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--time", default="00:00:30")
    ap.add_argument("--text", required=True)
    ap.add_argument("--brand", default="EWIT")
    ap.add_argument("-o", "--output", default="thumbnail.jpg")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        frame = os.path.join(tmp, "frame.jpg")
        grab_frame(a.video, a.time, frame)
        make(frame, a.text, a.output, a.brand)


if __name__ == "__main__":
    main()
