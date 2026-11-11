"""P2 – AI đọc transcript → ghi các đoạn đề xuất cắt vào tab "Chi tiết cắt".

Nhà cung cấp chọn ở tab Cấu hình ("AI: nhà cung cấp", "AI: model"); khóa đọc từ .env:
  claude      → ANTHROPIC_API_KEY
  gemini      → GEMINI_API_KEY
  openrouter  → OPENROUTER_API_KEY   (dùng được nhiều model: Claude, Gemini, GPT, Llama…)
Thêm nhà cung cấp mới: viết 1 hàm _call_<tên> rồi khai báo trong PROVIDERS.
"""
import json
import re
import urllib.request

from sheet_job import records
from transcript_compact import compact, parse_time, read_vtt

PROVIDERS = {
    # tên: (biến khóa trong .env, model mặc định khi ô "AI: model" để trống)
    "claude": ("ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
    "gemini": ("GEMINI_API_KEY", "gemini-2.5-flash"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter/auto"),
}

SYSTEM = """Bạn là biên tập viên video cho tổ chức giáo dục EWIT (nội dung song ngữ Anh – Việt).
Đọc transcript (mỗi dòng: "bắt đầu-kết thúc Mã người nói: nội dung"; dòng "~im Ns" là im lặng N giây)
và đề xuất các đoạn CẮT BỎ để video gọn mà vẫn giữ nguyên nội dung chính.

Quy tắc chung:
- Cắt: chờ vào phòng, chào hỏi kéo dài, thử mic/lỗi mạng, im lặng dài (≥ 20 giây), chuyện riêng không liên quan, phần kết sau lời chào cuối.
- Tiếng ồn, lời thoại lẫn lộn KHÔNG RÕ nội dung → CẮT, do_tin_cay "vua".
- Nội dung ngoài lề / tranh luận mà bạn KHÔNG CHẮC có nên giữ → do_tin_cay "thap" (người duyệt sẽ quyết).
- Transcript do máy nhận dạng, sai chữ nhiều: hiểu theo đại ý, đừng cắt chỉ vì câu sai chính tả.
- Mốc thời gian dạng H:MM:SS theo transcript; các đoạn không chồng lấn, xếp theo thời gian.

LUẬT RIÊNG CỦA LOẠI VIDEO NÀY:
{luat}

Trả về DUY NHẤT một JSON, không giải thích:
{{"cat": [{{"tu": "0:00:00", "den": "0:02:46", "ly_do": "…", "do_tin_cay": "cao|vua|thap", "loi": "trích ngắn lời bị bỏ"}}]}}"""


def dense_transcript(vtt_path):
    """Transcript gọn nhất để gửi AI: gộp câu, mã ngắn cho người nói, bỏ chuỗi dấu chấm thừa."""
    names, out = {}, []
    for line in compact(read_vtt(vtt_path)).splitlines():
        m = re.match(r"\[(\d\d:\d\d:\d\d)-(\d\d:\d\d:\d\d)\] (?:([^:]{1,40}): )?(.*)", line)
        if not m:
            m2 = re.search(r"im lặng (\d+)", line)
            out.append(f"~im {m2.group(1)}s" if m2 else line)
            continue
        s, e, spk, t = m.groups()
        t = re.sub(r"\s+", " ", re.sub(r"\.{3,}", "…", t)).strip()
        if spk:
            spk = names.setdefault(spk, f"S{len(names) + 1}")
        out.append(f"{s[1:] if s.startswith('0') else s}-{e[1:] if e.startswith('0') else e} {spk or '?'}: {t}")
    legend = " | ".join(f"{v}={k}" for k, v in names.items())
    return f"NGƯỜI NÓI: {legend}\n" + "\n".join(out)


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def _call_claude(key, model, system, user):
    r = _post("https://api.anthropic.com/v1/messages",
              {"model": model, "max_tokens": 8000, "system": system,
               "messages": [{"role": "user", "content": user}]},
              {"x-api-key": key, "anthropic-version": "2023-06-01"})
    return "".join(b.get("text", "") for b in r.get("content", []))


def _call_gemini(key, model, system, user):
    r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
              {"systemInstruction": {"parts": [{"text": system}]},
               "contents": [{"role": "user", "parts": [{"text": user}]}],
               "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8000}}, {})
    return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])


def _call_openrouter(key, model, system, user):
    r = _post("https://openrouter.ai/api/v1/chat/completions",
              {"model": model, "messages": [{"role": "system", "content": system},
                                            {"role": "user", "content": user}]},
              {"Authorization": f"Bearer {key}"})
    return r["choices"][0]["message"]["content"]


def ask_ai(provider, model, env, system, user):
    provider = (provider or "claude").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Nhà cung cấp AI '{provider}' chưa hỗ trợ. Chọn: {', '.join(PROVIDERS)}")
    key_name, default_model = PROVIDERS[provider]
    key = env.get(key_name, "")
    if not key:
        raise ValueError(f"Thiếu {key_name} trong .env")
    model = (model or "").strip() or default_model
    text = globals()[f"_call_{provider}"](key, model, system, user)
    return text, f"{provider}/{model}"


def parse_cuts(text):
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0) if m else text)
    cuts = []
    for c in data.get("cat", []):
        try:
            a, b = parse_time(c["tu"]), parse_time(c["den"])
        except (KeyError, ValueError):
            continue
        if b - a >= 1:
            conf = str(c.get("do_tin_cay", "vua")).lower()
            conf = "thap" if conf.startswith("th") else "cao" if conf.startswith("c") else "vua"
            cuts.append({"tu": c["tu"], "den": c["den"], "giay": int(b - a), "ly_do": c.get("ly_do", ""),
                         "do_tin_cay": conf, "loi": str(c.get("loi", ""))[:200]})
    cuts.sort(key=lambda c: parse_time(c["tu"]))
    return cuts


def propose_cuts(job, env, vtt_path):
    """Gọi AI cho 1 video (Job của sheet_job), ghi Chi tiết cắt, cập nhật trạng thái. Trả về số đoạn."""
    job.refresh()
    code = job.video["Mã video"]
    ws = job.ss.worksheet("Chi tiết cắt")
    rows = ws.get_all_values()
    if any(r and r[0].strip() == code for r in rows[1:]):
        print(f"ℹ️ {code} đã có đoạn cắt trong tab Chi tiết cắt – bỏ qua (xóa các dòng đó nếu muốn AI làm lại).")
        return 0
    cfg = {r.get("Mục", ""): r.get("Giá trị", "") for r in records(job.ss.worksheet("Cấu hình").get_all_values())}
    luat = job.vtype.get("Luật cắt", "") or "(không có luật riêng – dùng quy tắc chung)"
    job.set(**{"Trạng thái": "Đang phân tích"})
    text, used = ask_ai(cfg.get("AI: nhà cung cấp"), cfg.get("AI: model"), env,
                        SYSTEM.format(luat=luat), "TRANSCRIPT:\n" + dense_transcript(vtt_path))
    cuts = parse_cuts(text)
    first = next((i + 1 for i, r in enumerate(rows) if i > 0 and not (r and r[0].strip())), len(rows) + 1)
    values = [[code, i + 1, c["tu"], c["den"], c["giay"], c["ly_do"], c["do_tin_cay"], c["loi"],
               c["do_tin_cay"] != "thap"] for i, c in enumerate(cuts)]
    if values:
        ws.update(range_name=f"A{first}", values=values, value_input_option="USER_ENTERED")
    auto = job.video.get("Chế độ") == "Tự động"
    job.set(**{"Trạng thái": "Đã duyệt" if auto else "Chờ duyệt",
               "Ghi chú": (job.video.get("Ghi chú", "") + f" | AI {used}: {len(cuts)} đoạn đề xuất").strip(" |")})
    print(f"✅ {code}: {len(cuts)} đoạn ({sum(c['do_tin_cay'] != 'thap' for c in cuts)} tick cắt) – {used}")
    return len(cuts)
