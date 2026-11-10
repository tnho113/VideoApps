# Tool cắt video Zoom (EWIT)

Quy trình: Zoom (MP4 + transcript .vtt) → Drive → AI đọc transcript ra `cong_thuc*.json` → sổ tay Colab `EWIT_Zoom_Cut.ipynb` cắt video, tạo phụ đề và thumbnail → lưu `ket_qua/` trên Drive → (tùy chọn) đăng YouTube ở chế độ Riêng tư.

| File | Việc |
|---|---|
| `transcript_compact.py` | Rút gọn .vtt để AI đọc ít token |
| `PROMPT_CAT_VIDEO.md` | Prompt mẫu để AI tạo công thức cắt (JSON) |
| `cut_video.py` | Báo cáo trước (`--dry-run`) và cắt bằng FFmpeg, xuất .srt khớp video mới |
| `make_thumbnail.py` | Thumbnail 1280×720 từ khung hình + chữ |
| `upload_youtube.py` | Đăng YouTube qua API (Riêng tư) + thumbnail + phụ đề |
| `EWIT_Zoom_Cut.ipynb` | Sổ tay Colab nối tất cả các bước |

## Cài đặt YouTube API (một lần, ~15 phút)
1. Vào console.cloud.google.com → tạo dự án mới (ví dụ `ewit-youtube`).
2. **APIs & Services → Library** → tìm **YouTube Data API v3** → **Enable**.
3. **OAuth consent screen** → chọn **External** → điền tên app, email → ở **Test users** thêm Gmail sở hữu kênh YouTube.
4. **Credentials → Create credentials → OAuth client ID** → loại **Desktop app** → **Download JSON**.
5. Đổi tên file thành `client_secret.json`, bỏ vào cùng thư mục Drive với video.
6. Trong sổ tay, Bước 7: đặt `DANG_YOUTUBE = True` và chạy. Mở link hiện ra, đăng nhập, cho phép; trình duyệt chuyển tới trang lỗi `localhost` → copy **toàn bộ địa chỉ** trên thanh trình duyệt, dán vào ô nhập.

Lưu ý: muốn gắn thumbnail tùy chỉnh, kênh cần xác minh tại youtube.com/verify. Dự án chưa được Google kiểm duyệt có thể chỉ đăng được ở chế độ Riêng tư; bạn tự chuyển sang Công khai trong YouTube Studio.
