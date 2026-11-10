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

## Cài đặt YouTube API (một lần)
1. console.cloud.google.com → Google Auth Platform → **Get started** (App info · Audience = **External** · Contact) → Create.
2. **Audience → Test users** → thêm Gmail sở hữu kênh.
3. **Clients → Create client → Desktop app** → Download JSON → đổi tên `client_secret.json` → để trong thư mục chứa Sheet điều khiển ("00 · Điều hành IT").
4. Bật **YouTube Data API v3** trong cùng dự án.
5. Tab **Loại video**: điền **Kênh YouTube** (tên kênh đúng như trên YouTube) và **Playlist YouTube** (tùy chọn).

Lần đầu đăng cho mỗi kênh: mở link → chọn đúng kênh → cho phép → copy địa chỉ trang `localhost` dán vào ô nhập.
Vé đăng nhập lưu thành `youtube_token_<ten-kenh>.json` cùng thư mục, dùng lại cho các lần sau.
Tool kiểm tra tên kênh: đăng nhập nhầm kênh sẽ dừng, không đăng. **Ai có quyền vào thư mục này thì dùng được vé đăng nhập** – chỉ chia sẻ cho người tin cậy.

Lưu ý: thumbnail tùy chỉnh cần kênh đã xác minh (youtube.com/verify). App ở chế độ Testing có thể phải đăng nhập lại sau khoảng 7 ngày.
