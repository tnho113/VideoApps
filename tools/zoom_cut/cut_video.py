"""Cắt video theo "công thức cắt" (JSON do AI tạo từ PROMPT_CAT_VIDEO.md).

Cách dùng:
    # 1) Xem trước, không cắt: in báo cáo các đoạn sẽ bỏ (kèm lời thoại nếu có .vtt)
    python cut_video.py video.mp4 cong_thuc.json --vtt transcript.vtt --dry-run
    # 2) Cắt thật, kèm phụ đề .srt khớp video mới
    python cut_video.py video.mp4 cong_thuc.json --vtt transcript.vtt -o video_da_cat.mp4
    # Chạy thử 10 phút đầu:
    python cut_video.py video.mp4 cong_thuc.json --until 00:10:00 -o thu.mp4

Mặc định cắt đoạn có độ tin cậy "cao" và "vua"; đoạn "thap" được GIỮ LẠI
(thêm --cat-ca-thap để cắt luôn).
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

from transcript_compact import fmt, parse_time, read_vtt


def load_recipe(path):
    """Đọc JSON, chấp nhận cả khi AI trả về kèm ```json ... ```."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0) if m else raw)


def duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def plan(recipe, total, pad=0.3, min_cut=1.0, cut_low=False, until=None):
    """Trả về (cuts, keeps) dạng list (start, end, info) theo giây."""
    end_limit = min(total, until) if until else total
    cuts = []
    for c in recipe.get("cat", []):
        conf = str(c.get("do_tin_cay", "cao")).lower()
        if conf.startswith("th") and not cut_low:
            continue
        a, b = parse_time(c["tu"]), parse_time(c["den"])
        # Đầu/cuối video thì cắt sát, ở giữa thì chừa đệm an toàn để không mất chữ
        a = a if a <= 0.5 else a + pad
        b = b if b >= total - 0.5 else b - pad
        a, b = max(0.0, a), min(end_limit, b)
        if b - a >= min_cut:
            cuts.append([a, b, c])
    cuts.sort(key=lambda x: x[0])
    merged = []
    for c in cuts:
        if merged and c[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], c[1])
        else:
            merged.append(c)
    keeps, pos = [], 0.0
    for a, b, _ in merged:
        if a - pos > 0.05:
            keeps.append((pos, a))
        pos = b
    if end_limit - pos > 0.05:
        keeps.append((pos, end_limit))
    return merged, keeps


def report(cuts, keeps, total, cues=None, skipped_low=0):
    kept = sum(b - a for a, b in keeps)
    print(f"Video gốc: {fmt(total)} | Sau khi cắt: {fmt(kept)} | Bỏ: {fmt(total - kept)} "
          f"({len(cuts)} đoạn cắt, {skipped_low} đoạn 'thap' được giữ lại)\n")
    for i, (a, b, info) in enumerate(cuts, 1):
        print(f"#{i:02d} {fmt(a)} → {fmt(b)} ({int(b - a)}s) [{info.get('do_tin_cay', '')}] "
              f"{info.get('ly_do', '')}")
        if cues:
            said = " ".join(t for s, e, _, t in cues if s >= a - 0.5 and e <= b + 0.5)
            if said:
                print(f"     Lời bị bỏ: {said[:200]}{'…' if len(said) > 200 else ''}")


def cut(video, keeps, output):
    n = len(keeps)
    parts = [f"[0:v]split={n}" + "".join(f"[v{i}]" for i in range(n)),
             f"[0:a]asplit={n}" + "".join(f"[a{i}]" for i in range(n))] if n > 1 else []
    concat_in = ""
    for i, (a, b) in enumerate(keeps):
        vi, ai = (f"[v{i}]", f"[a{i}]") if n > 1 else ("[0:v]", "[0:a]")
        parts.append(f"{vi}trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[vo{i}]")
        parts.append(f"{ai}atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[ao{i}]")
        concat_in += f"[vo{i}][ao{i}]"
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[outv][outa]")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(";\n".join(parts))
        script = f.name
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats", "-i", video,
           "-filter_complex_script", script, "-map", "[outv]", "-map", "[outa]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output]
    subprocess.run(cmd, check=True)
    os.unlink(script)


def write_srt(cues, keeps, path):
    """Dời mốc phụ đề sang dòng thời gian của video đã cắt."""
    def srt_time(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"

    offsets, acc = [], 0.0
    for a, b in keeps:
        offsets.append((a, b, acc))
        acc += b - a
    lines, k = [], 0
    for s, e, spk, text in cues:
        for a, b, off in offsets:
            if s < b and e > a:  # câu nằm (một phần) trong đoạn giữ lại
                ns, ne = max(s, a) - a + off, min(e, b) - a + off
                if ne - ns >= 0.3:
                    k += 1
                    lines += [str(k), f"{srt_time(ns)} --> {srt_time(ne)}", text, ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Đã ghi phụ đề {path} ({k} câu)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("recipe", help="File JSON công thức cắt")
    ap.add_argument("-o", "--output", default="video_da_cat.mp4")
    ap.add_argument("--vtt", help="Transcript Zoom để in lời bị bỏ và tạo .srt")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ xem báo cáo, không cắt")
    ap.add_argument("--pad", type=float, default=0.3, help="Đệm an toàn mỗi đầu (giây)")
    ap.add_argument("--cat-ca-thap", action="store_true", help="Cắt cả đoạn độ tin cậy thấp")
    ap.add_argument("--until", help="Chạy thử: chỉ xử lý đến mốc này, ví dụ 00:10:00")
    a = ap.parse_args()

    recipe = load_recipe(a.recipe)
    total = duration(a.video)
    until = parse_time(a.until) if a.until else None
    cuts, keeps = plan(recipe, total, a.pad, cut_low=a.cat_ca_thap, until=until)
    low = sum(1 for c in recipe.get("cat", []) if str(c.get("do_tin_cay", "")).lower().startswith("th"))
    cues = read_vtt(a.vtt) if a.vtt else None
    report(cuts, keeps, min(total, until) if until else total, cues, 0 if a.cat_ca_thap else low)
    if a.dry_run or not keeps:
        return
    cut(a.video, keeps, a.output)
    print(f"\nĐã xuất {a.output}")
    if cues:
        write_srt(cues, keeps, os.path.splitext(a.output)[0] + ".srt")


if __name__ == "__main__":
    main()
