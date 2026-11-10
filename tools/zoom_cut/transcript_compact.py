"""Rút gọn transcript Zoom (.vtt) thành văn bản gọn để AI đọc, tiết kiệm token.

Gộp các câu liên tiếp của cùng một người nói thành một dòng:
    [00:12:05-00:12:40] Tên người nói: nội dung...

Cách dùng:
    python transcript_compact.py transcript.vtt -o transcript_gon.txt
    python transcript_compact.py transcript.vtt --until 00:10:00   # chạy thử 10 phút đầu
"""
import argparse
import re

TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[.,](\d{3})")


def to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def fmt(t):
    t = int(round(t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def parse_time(s):
    """'01:02:03', '02:03', '123.5' -> giây."""
    parts = [float(p) for p in str(s).strip().split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def read_vtt(path):
    """Trả về list (start, end, speaker, text)."""
    cues, cur = [], None
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            m = TIME_RE.search(line)
            if m:
                g = m.groups()
                cur = [to_sec(*g[:4]), to_sec(*g[4:]), []]
                cues.append(cur)
            elif line and cur is not None and not line.isdigit():
                cur[2].append(line)
            elif not line:
                cur = None
    out = []
    for start, end, lines in cues:
        text = " ".join(lines)
        speaker = ""
        m = re.match(r"^([^:]{1,40}):\s+(.*)$", text)
        if m:
            speaker, text = m.group(1).strip(), m.group(2)
        out.append((start, end, speaker, text))
    return out


def compact(cues, max_block=45.0, max_gap=3.0, until=None):
    blocks = []
    for start, end, spk, text in cues:
        if until is not None and start >= until:
            break
        b = blocks[-1] if blocks else None
        if b and b[2] == spk and start - b[1] <= max_gap and end - b[0] <= max_block:
            b[1] = end
            b[3].append(text)
        else:
            blocks.append([start, end, spk, [text]])
    lines = []
    for i, (s, e, spk, texts) in enumerate(blocks):
        if i and s - blocks[i - 1][1] >= 20:  # đánh dấu khoảng im lặng dài
            lines.append(f"--- (im lặng {int(s - blocks[i - 1][1])} giây) ---")
        who = f"{spk}: " if spk else ""
        lines.append(f"[{fmt(s)}-{fmt(e)}] {who}{' '.join(texts)}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vtt")
    ap.add_argument("-o", "--output")
    ap.add_argument("--until", help="Chỉ lấy đến mốc này, ví dụ 00:10:00")
    a = ap.parse_args()
    text = compact(read_vtt(a.vtt), until=parse_time(a.until) if a.until else None)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"Đã ghi {a.output}: {len(text.splitlines())} dòng, ~{len(text.split())} từ")
    else:
        print(text)


if __name__ == "__main__":
    main()
