"""Đọc/ghi "Bảng điều khiển video – IT Team" (Google Sheet) và Drive cho sổ tay Colab.

Phần logic thuần (không gọi mạng) có thể chạy thử ngoài Colab:
    build_people, build_recipe, fill_template
Phần gọi Google (gspread + Drive API) chỉ dùng trong Colab: class Job.
"""
import io
import os
import re

from transcript_compact import fmt, parse_time

SHEET_ID = "1nQJCLzBykSoSAGejiv_zukv42UKv6Ddv-VNbGMZhlfY"
PEOPLE_COLS = ["Người chính", "Đi kèm 1", "Đi kèm 2", "Đi kèm 3"]


def records(values):
    """Bảng (list list) → list dict theo dòng tiêu đề; khóa = phần chữ trước dấu '('."""
    head = [re.sub(r"\s*\(.*$", "", h).strip() for h in values[0]]
    return [dict(zip(head, row + [""] * (len(head) - len(row)))) for row in values[1:]]


def drive_id(link):
    m = re.search(r"/(?:d|folders)/([\w-]+)", link or "") or re.search(r"id=([\w-]+)", link or "")
    return m.group(1) if m else ""


def build_people(video, people_table):
    """Trả về (danh sách người cho thumbnail, ghi chú).
    Quy tắc: 1 người/nhóm có avatar → ảnh; 1 người thiếu avatar → không ảnh;
    2–4 người: thiếu avatar thì dùng chibi; không ai có avatar → không ảnh; 'Ép không ảnh' → không ảnh."""
    lookup = {p["Tên"].strip(): p for p in people_table if p.get("Tên")}
    names = [video.get(c, "").strip() for c in PEOPLE_COLS if video.get(c, "").strip()]
    notes = [n for n in names if n not in lookup]
    people = [{"ten": n, "link": lookup.get(n, {}).get("Link ảnh avatar", "").strip(),
               "link_tach": lookup.get(n, {}).get("Link ảnh tách nền", "").strip(),
               "gioi_tinh": lookup.get(n, {}).get("Giới tính", "")} for n in names]
    for p in people:
        p["co_anh"] = bool(p["link"] or p["link_tach"])
    note = f"Không có trong tab Người & Nhóm: {', '.join(notes)}. " if notes else ""
    if str(video.get("Ép không ảnh", "")).upper() == "TRUE" or not any(p["co_anh"] for p in people):
        return [], note
    if len(people) == 1 and not people[0]["co_anh"]:
        return [], note
    missing = [p["ten"] for p in people if not p["co_anh"]]
    if missing:
        note += f"Dùng chibi cho: {', '.join(missing)}. "
    return people, note


def photo_style(video, people):
    """'ngoai' nếu chọn Phủ ngoài và mọi người có ảnh đều có ảnh tách nền; ngược lại 'trong' (kèm ghi chú)."""
    if not str(video.get("Kiểu ảnh", "")).startswith("Phủ"):
        return "trong", ""
    lack = [p["ten"] for p in people if p["co_anh"] and not p["link_tach"]]
    if lack:
        return "trong", f"Chưa có ảnh tách nền: {', '.join(lack)} → tạm dùng kiểu Trong vòng tròn. "
    return "ngoai", ""


def choose_template(video, vtype, templates):
    code = (video.get("Mẫu thumbnail") or vtype.get("Mẫu thumbnail mặc định") or "").strip()
    tpl = next((t for t in templates if t.get("Mã mẫu", "").strip() == code), None)
    if not tpl:
        raise ValueError(f"Không tìm thấy mẫu thumbnail '{code}' trong tab Mẫu thumbnail")
    return tpl


def speaker_line(video):
    names = [video.get(c, "").strip() for c in PEOPLE_COLS if video.get(c, "").strip()]
    return "Chia sẻ: " + ", ".join(names) if names else ""


def fill_template(text, video):
    return (text or "").replace("{buoi_so}", video.get("Buổi số", "")) \
        .replace("{tieu_de}", video.get("Tiêu đề", "")).replace("{ngay}", video.get("Ngày giờ", "")) \
        .replace("{nguoi}", ", ".join(video.get(c, "") for c in PEOPLE_COLS if video.get(c)))


def build_recipe(video, vtype, cuts):
    """Công thức cắt từ các dòng 'Chi tiết cắt' đã tick 'Cắt'."""
    chosen = [c for c in cuts if c.get("Mã video") == video["Mã video"]
              and str(c.get("Cắt", "")).upper() == "TRUE"]
    return {
        "tieu_de": video.get("Tiêu đề", ""),
        "mo_ta": fill_template(vtype.get("Mẫu mô tả YouTube", ""), video),
        "the_tag": ["EWIT", video.get("Loại video", "")],
        "cat": [{"tu": c["Từ"], "den": c["Đến"], "ly_do": c.get("Lý do", ""), "do_tin_cay": "cao"}
                for c in sorted(chosen, key=lambda c: parse_time(c["Từ"]))],
    }


class Job:
    """Một video trong Sheet. Chỉ dùng trong Colab sau google.colab.auth.authenticate_user()."""

    def __init__(self, ma_video, sheet_id=SHEET_ID):
        import google.auth
        import gspread
        from googleapiclient.discovery import build
        creds, _ = google.auth.default()
        self.ss = gspread.authorize(creds).open_by_key(sheet_id)
        self.drive = build("drive", "v3", credentials=creds)
        self.ma_video = ma_video
        self.refresh()

    def refresh(self):
        """Đọc lại Sheet (gọi trước mỗi bước để nhận thay đổi người dùng vừa sửa)."""
        ma_video = self.ma_video
        self.ws = self.ss.worksheet("Video")
        rows = self.ws.get_all_values()
        self.head = rows[0]
        vids = records(rows)
        idx = next((i for i, v in enumerate(vids) if v["Mã video"].strip() == ma_video), None)
        if idx is None:
            raise ValueError(f"Không thấy mã video {ma_video} trong tab Video")
        self.row = idx + 2
        self.video = vids[idx]
        types = records(self.ss.worksheet("Loại video").get_all_values())
        self.vtype = next((t for t in types if t["Loại video"] == self.video["Loại video"]), {})
        self.people_table = records(self.ss.worksheet("Người & Nhóm").get_all_values())
        self.templates = records(self.ss.worksheet("Mẫu thumbnail").get_all_values())
        self.cuts = records(self.ss.worksheet("Chi tiết cắt").get_all_values())
        self.folder = drive_id(self.video.get("Thư mục Drive của buổi", ""))

    # ---------- Sheet ----------
    def set(self, **cols):
        """Ghi giá trị theo tên cột (phần trước dấu '('), ví dụ set(**{'Trạng thái': 'Xong'})."""
        short = [re.sub(r"\s*\(.*$", "", h).strip() for h in self.head]
        for k, v in cols.items():
            self.ws.update_cell(self.row, short.index(k) + 1, v)

    # ---------- Drive ----------
    def _list(self, q):
        return self.drive.files().list(q=q, fields="files(id,name,mimeType,size)",
                                       supportsAllDrives=True, includeItemsFromAllDrives=True).execute()["files"]

    def find_inputs(self):
        files = self._list(f"'{self.folder}' in parents and trashed=false")
        mp4 = [f for f in files if f["name"].lower().endswith(".mp4")]
        vtt = [f for f in files if f["name"].lower().endswith(".vtt")]
        if not mp4:
            raise FileNotFoundError("Thư mục của buổi chưa có file .mp4")
        return max(mp4, key=lambda f: int(f.get("size", 0))), (vtt[0] if vtt else None)

    def download(self, file_id, path):
        from googleapiclient.http import MediaIoBaseDownload
        with io.FileIO(path, "wb") as fh:
            dl = MediaIoBaseDownload(fh, self.drive.files().get_media(fileId=file_id), chunksize=64 << 20)
            done = False
            while not done:
                status, done = dl.next_chunk()
                print(f"  tải {os.path.basename(path)}: {int(status.progress() * 100)}%", end="\r")
        print()
        return path

    def result_folder(self):
        q = (f"'{self.folder}' in parents and name='ket_qua' and "
             "mimeType='application/vnd.google-apps.folder' and trashed=false")
        found = self._list(q)
        if found:
            return found[0]["id"]
        meta = {"name": "ket_qua", "mimeType": "application/vnd.google-apps.folder", "parents": [self.folder]}
        return self.drive.files().create(body=meta, fields="id", supportsAllDrives=True).execute()["id"]

    def upload(self, path):
        """Tải lên ket_qua/ (ghi đè nếu trùng tên). Trả về link xem."""
        from googleapiclient.http import MediaFileUpload
        parent, name = self.result_folder(), os.path.basename(path)
        media = MediaFileUpload(path, resumable=True)
        same = self._list(f"'{parent}' in parents and name='{name}' and trashed=false")
        if same:
            f = self.drive.files().update(fileId=same[0]["id"], media_body=media, fields="id,webViewLink",
                                          supportsAllDrives=True).execute()
        else:
            f = self.drive.files().create(body={"name": name, "parents": [parent]}, media_body=media,
                                          fields="id,webViewLink", supportsAllDrives=True).execute()
        return f["webViewLink"]

    def _get(self, link, workdir="/content/anh"):
        fid = drive_id(link)
        if not fid:
            return None
        os.makedirs(workdir, exist_ok=True)
        path = os.path.join(workdir, fid)
        return path if os.path.exists(path) else self.download(fid, path)

    def thumbnail(self, out):
        """Chọn mẫu, tải nền/logo/ảnh người, ghép thumbnail. Trả về ghi chú."""
        from thumb_template import compose, load_layout
        self.refresh()  # lấy lựa chọn mới nhất trên Sheet (mẫu, kiểu ảnh, hiện tên, người)
        tpl = choose_template(self.video, self.vtype, self.templates)
        people, note = build_people(self.video, self.people_table)
        kieu, note2 = photo_style(self.video, people)
        for p in people:
            p["anh"] = self._get(p["link"])
            p["anh_tach_nen"] = self._get(p["link_tach"])
        layout = load_layout(tpl["Bố cục"], tpl.get("Màu nhấn"), tpl.get("Màu nhấn 2"))
        content = {"dong_tren": fill_template(self.vtype.get("Dòng trên thumbnail", ""), self.video),
                   "tieu_de": self.video.get("Tiêu đề", ""), "nguoi": speaker_line(self.video),
                   "ngay": self.video.get("Ngày giờ", "")}
        logo = self._get(tpl.get("Link logo", ""))
        if layout.get("logo") and not logo:
            note2 += f"Mẫu {tpl['Mã mẫu']} chưa có link logo. "
        show = str(self.video.get("Hiện tên dưới ảnh", "")).upper() == "TRUE"
        compose(layout, self._get(tpl["Link ảnh nền"]), content, out, people, kieu, logo, show)
        return f"Mẫu {tpl['Mã mẫu']}, kiểu {kieu}. " + note + note2


__all__ = ["Job", "build_people", "photo_style", "choose_template", "build_recipe", "fill_template", "speaker_line", "records", "fmt"]
