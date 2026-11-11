"""P1 – Tự lấy bản ghi Zoom Cloud mới → thư mục Drive theo lớp (MãKhóa-TàiKhoản-ZoomID) → thêm dòng ở tab Video.

Lớp được xác định từ tab "Danh sách lớp" của Sheet điều khiển (Zoom ID + khoảng ngày + giờ bắt đầu), không dựa vào tên phòng.

Cần ứng dụng Zoom "Server-to-Server OAuth" (Account ID, Client ID, Client Secret) có quyền đọc bản ghi.
Không tải lại buổi đã có (so theo cột "Zoom ID" ở tab Video).
"""
import base64
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

from sheet_job import SHEET_ID, drive_id, records

API = "https://api.zoom.us/v2"
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
VN = dt.timezone(dt.timedelta(hours=7))


# ---------------- Zoom API ----------------
def zoom_token(account_id, client_id, client_secret):
    req = urllib.request.Request(
        "https://zoom.us/oauth/token?" + urllib.parse.urlencode(
            {"grant_type": "account_credentials", "account_id": account_id}),
        method="POST",
        headers={"Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["access_token"]


def _get(token, path, params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def list_recordings(token, since, user="me"):
    """Mọi buổi có bản ghi từ ngày `since` (YYYY-MM-DD) đến nay. Zoom giới hạn 30 ngày/lần gọi."""
    start, today, out = dt.date.fromisoformat(since), dt.date.today(), []
    while start <= today:
        end = min(start + dt.timedelta(days=29), today)
        params = {"from": start.isoformat(), "to": end.isoformat(), "page_size": 300}
        while True:
            data = _get(token, f"/users/{user}/recordings", params)
            out += data.get("meetings", [])
            if not data.get("next_page_token"):
                break
            params["next_page_token"] = data["next_page_token"]
        start = end + dt.timedelta(days=1)
    return out


def pick_files(meeting):
    """Chọn 1 file MP4 (ưu tiên màn hình chia sẻ + người nói) và file transcript VTT nếu có."""
    files = [f for f in meeting.get("recording_files", []) if f.get("status", "completed") == "completed"]
    mp4 = [f for f in files if f.get("file_type") == "MP4"]
    prefer = ["shared_screen_with_speaker_view", "shared_screen_with_speaker_view(CC)",
              "active_speaker", "shared_screen_with_gallery_view", "gallery_view"]
    mp4.sort(key=lambda f: (prefer.index(f["recording_type"]) if f.get("recording_type") in prefer else 99,
                            -int(f.get("file_size", 0))))
    vtt = next((f for f in files if f.get("file_type") == "TRANSCRIPT"), None)
    return (mp4[0] if mp4 else None), vtt


def download(token, url, path):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(8 << 20)
            if not chunk:
                break
            f.write(chunk)
    return path


# ---------------- Logic thuần (chạy thử được ngoài Colab) ----------------
def vn_label(start_time):
    """'2026-11-09T14:03:55Z' → 'Thứ Hai · 21:03 · 09/11/2026' (giờ Việt Nam)."""
    t = dt.datetime.fromisoformat(start_time.replace("Z", "+00:00")).astimezone(VN)
    return f"{THU[t.weekday()]} · {t:%H:%M} · {t:%d/%m/%Y}"


def _date(text):
    text = str(text or "").strip()
    if not text:
        return None
    m, d, y = (int(x) for x in re.split(r"[/-]", text)[:3]) if "/" in text else (None, None, None)
    return dt.date(y, m, d) if m else dt.date.fromisoformat(text)


def _minutes(hhmm):
    h, m = (int(x) for x in str(hhmm).strip().split(":")[:2])
    return h * 60 + m


def digits(x):
    return re.sub(r"\D", "", str(x or ""))


def read_classes(values):
    """Tab 'Danh sách lớp' → list dict (chỉ dòng có Zoom ID)."""
    return [r for r in records(values) if digits(r.get("Zoom ID"))]


def acc_code(zoom_acc):
    """'ZKI-ewitkid.english' → 'ZKI'."""
    return str(zoom_acc or "").split("-")[0].strip().upper()


def match_class(meeting, classes, acc=None):
    """Lớp của buổi: cùng Zoom ID (và tài khoản), ngày trong Eff_From–Eff_To, giờ bắt đầu gần nhất."""
    t = dt.datetime.fromisoformat(meeting["start_time"].replace("Z", "+00:00")).astimezone(VN)
    mid = digits(meeting.get("id"))
    cands = []
    for c in classes:
        if digits(c["Zoom ID"]) != mid or (acc and acc_code(c.get("Tài khoản Zoom")) != acc):
            continue
        f, to = _date(c.get("Từ ngày")), _date(c.get("Đến ngày"))
        if (f and t.date() < f) or (to and t.date() > to):
            continue
        try:
            gap = abs(_minutes(c.get("Giờ bắt đầu", "")) - (t.hour * 60 + t.minute))
        except ValueError:
            gap = 9999
        cands.append((gap, c))
    return min(cands, key=lambda x: x[0])[1] if cands else None


def folder_name(cls, acc, zoom_id):
    """'EG2-01-ZKI-936 3686 9490'; buổi chưa có trong danh sách: 'CHUA-XEP-ZKI-936 3686 9490'."""
    return f"{cls['Mã khóa'] if cls else 'CHUA-XEP'}-{acc}-{zoom_id}"


def pretty_id(meeting_id):
    d = digits(meeting_id)
    return f"{d[:3]} {d[3:7]} {d[7:]}" if len(d) == 11 else d


def next_code(prefix, existing_codes):
    nums = [int(m.group(1)) for c in existing_codes if (m := re.fullmatch(re.escape(prefix) + r"(\d+)", c.strip()))]
    return f"{prefix}{(max(nums) + 1 if nums else 1):03d}"


def safe_name(text):
    return re.sub(r'[\\/:*?"<>|]+', "-", text).strip()[:80]


def parse_env(text):
    """Nội dung .env → dict (bỏ dòng trống/chú thích, 'export ', dấu nháy)."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.replace("export ", "").strip().upper()
        out[k] = v.strip().strip('"').strip("'")
    return out


def env_accounts(env, codes):
    """Lấy (account_id, client_id, client_secret) cho từng mã tài khoản.
    Chấp nhận ZOOM_<MÃ>_ACCOUNT_ID…; nếu chỉ 1 tài khoản thì chấp nhận cả ZOOM_ACCOUNT_ID / ACCOUNT_ID…"""
    fields = ("ACCOUNT_ID", "CLIENT_ID", "CLIENT_SECRET")
    out = {}
    for code in codes:
        names = [[f"ZOOM_{code}_{f}"] + ([f"ZOOM_{f}", f] if len(codes) == 1 else []) for f in fields]
        vals = [next((env[n] for n in opts if env.get(n)), "") for opts in names]
        if all(vals):
            out[code] = tuple(vals)
        else:
            missing = [opts[0] for opts, v in zip(names, vals) if not v]
            print(f"⚠️ Tài khoản {code}: thiếu {', '.join(missing)} trong .env")
    return out


# ---------------- Đồng bộ (dùng trong Colab / máy chạy) ----------------
class ZoomSync:
    def __init__(self, sheet_id=SHEET_ID, creds=None):
        import google.auth
        import gspread
        from googleapiclient.discovery import build
        creds = creds or google.auth.default()[0]
        self.ss = gspread.authorize(creds).open_by_key(sheet_id)
        self.drive = build("drive", "v3", credentials=creds)

    def load_env(self, name=".env"):
        """Đọc file .env nằm cùng thư mục với Sheet điều khiển → dict (không in giá trị)."""
        import io
        from googleapiclient.http import MediaIoBaseDownload
        parent = self.drive.files().get(fileId=self.ss.id, fields="parents",
                                        supportsAllDrives=True).execute()["parents"][0]
        f = self.drive.files().list(q=f"'{parent}' in parents and name='{name}' and trashed=false",
                                    fields="files(id)", supportsAllDrives=True,
                                    includeItemsFromAllDrives=True).execute()["files"]
        if not f:
            print(f"⚠️ Không thấy file {name} trong thư mục chứa Sheet điều khiển")
            return {}
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, self.drive.files().get_media(fileId=f[0]["id"]))
        done = False
        while not done:
            _, done = dl.next_chunk()
        env = parse_env(buf.getvalue().decode("utf-8-sig"))
        print("Các tên khóa có trong .env:", ", ".join(sorted(env)) or "(trống)")
        return env

    def accounts_from_env(self, codes, env=None):
        env = self.load_env() if env is None else env
        return env_accounts(env, [c.strip().upper() for c in codes])

    def config(self):
        return {r["Mục"]: r["Giá trị"] for r in records(self.ss.worksheet("Cấu hình").get_all_values())}

    def _folder(self, parent, name):
        q = (f"'{parent}' in parents and name='{name.replace(chr(39), ' ')}' and "
             "mimeType='application/vnd.google-apps.folder' and trashed=false")
        f = self.drive.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                                    includeItemsFromAllDrives=True).execute()["files"]
        if f:
            return f[0]["id"]
        return self.drive.files().create(body={"name": name, "parents": [parent],
                                               "mimeType": "application/vnd.google-apps.folder"},
                                         fields="id", supportsAllDrives=True).execute()["id"]

    def _upload(self, path, parent):
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(path, resumable=True, chunksize=64 << 20)
        req = self.drive.files().create(body={"name": os.path.basename(path), "parents": [parent]},
                                        media_body=media, fields="id", supportsAllDrives=True)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp["id"]

    def run(self, accounts, limit=None, dry_run=False, workdir="/content/zoom"):
        """accounts: {'ZKI': (account_id, client_id, client_secret), ...}.
        dry_run=True: chỉ liệt kê, không tải, không ghi Sheet."""
        if not accounts:
            print("⚠️ Chưa nạp được khóa của tài khoản Zoom nào. Kiểm tra tên khóa trong Secrets "
                  "(ZOOM_<MÃ>_ACCOUNT_ID / _CLIENT_ID / _CLIENT_SECRET), Notebook access, và dòng TAI_KHOAN.")
            return []
        cfg = self.config()
        root = drive_id(cfg.get("Thư mục gốc lưu video Zoom", ""))
        since = cfg.get("Lấy bản ghi từ ngày", "") or (dt.date.today() - dt.timedelta(days=30)).isoformat()
        classes = read_classes(self.ss.worksheet("Danh sách lớp").get_all_values())
        ws = self.ss.worksheet("Video")
        rows = ws.get_all_values()
        head = [re.sub(r"\s*\(.*$", "", h).strip() for h in rows[0]]
        vids = records(rows)
        seen = {v.get("Zoom ID", "").strip() for v in vids}
        codes = [v["Mã video"] for v in vids]
        os.makedirs(workdir, exist_ok=True)
        added, done = [], 0
        for acc, keys in accounts.items():
            token = zoom_token(*keys)
            meetings = sorted((m for m in list_recordings(token, since) if m.get("uuid") not in seen),
                              key=lambda m: m.get("start_time", ""))
            print(f"[{acc}] {len(meetings)} buổi mới từ {since}")
            for m in meetings:
                if limit is not None and done >= limit:
                    return added
                mp4, vtt = pick_files(m)
                cls = match_class(m, classes, acc)
                t = dt.datetime.fromisoformat(m["start_time"].replace("Z", "+00:00")).astimezone(VN)
                zid = cls["Zoom ID"] if cls else pretty_id(m.get("id"))
                fname = folder_name(cls, acc, zid)
                print(f"• {vn_label(m['start_time'])} | {m.get('topic')} → 📁 {fname}"
                      f"{'' if cls else '  (chưa có trong danh sách lớp)'} | MP4: {'có' if mp4 else 'KHÔNG'}"
                      f" | transcript: {'có' if vtt else 'KHÔNG'}")
                if dry_run or not mp4:
                    continue
                folder = self._folder(root, safe_name(fname))
                base = f"{cls['Mã khóa'] if cls else 'CHUA-XEP-' + acc}_{t:%Y-%m-%d_%H%M}"
                for f, ext in ((mp4, "mp4"), (vtt, "vtt")):
                    if f:
                        p = os.path.join(workdir, f"{base}.{ext}")
                        print(f"  tải {ext}…")
                        download(token, f["download_url"], p)
                        self._upload(p, folder)
                        os.remove(p)
                if cls:
                    n = sum(1 for c in codes if c.startswith(cls["Mã khóa"] + "-B")) + 1
                    code, buoi = f"{cls['Mã khóa']}-B{n:02d}", f"Buổi {n:02d}"
                else:
                    code, buoi = f"CHUA-XEP-{acc}-{t:%Y%m%d-%H%M}", ""
                codes.append(code)
                row = {"Mã video": code, "Loại video": (cls or {}).get("Loại video", ""), "Buổi số": buoi,
                       "Tiêu đề": cls["Tên lớp"] if cls else m.get("topic", ""),
                       "Người chính": (cls or {}).get("Giáo viên / Người chính", ""), "Ngày giờ": vn_label(m["start_time"]),
                       "Thư mục Drive của buổi": f"https://drive.google.com/drive/folders/{folder}",
                       "Chế độ": "Chờ duyệt", "Trạng thái": "Mới", "Zoom ID": m["uuid"],
                       "Ghi chú": ("" if cls else "Chưa có trong danh sách lớp – bổ sung rồi sửa Mã/Tiêu đề. ") +
                                  ("" if vtt else "Zoom không có transcript – bật 'Audio transcript'.")}
                # Ghi vào dòng trống đầu tiên (cột Mã video trống) – không dùng append_row vì
                # các cột ô tick làm Sheet tưởng bảng kéo dài tới dòng 500
                col_a = ws.col_values(1)
                r = next((i + 1 for i, v in enumerate(col_a) if i > 0 and not v.strip()), len(col_a) + 1)
                ws.update(range_name=f"A{r}", values=[[row.get(h, "") for h in head]],
                          value_input_option="USER_ENTERED")
                added.append(code)
                done += 1
                print(f"  ✅ {code}")
        return added
