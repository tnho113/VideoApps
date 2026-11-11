# Quy trình tổng thể – Tool xử lý video IT Team EWIT

> Cập nhật 2026-11-10. Tài liệu chốt cách tool vận hành. Code: `tools/zoom_cut/`.
> Bảng điều khiển: Google Sheet "Bảng điều khiển video – IT Team" (ID `1nQJCLzBykSoSAGejiv_zukv42UKv6Ddv-VNbGMZhlfY`), thư mục Drive "00 · Điều hành IT".
> Tab: **Video** (mỗi video 1 dòng; Người chính + Đi kèm 1–3; ô "Ép không ảnh") · **Người & Nhóm** (tên, giới tính, link avatar) · **Chi tiết cắt** (ô tick "Cắt") · **Mẫu thumbnail** (mã mẫu, bố cục it_a/it_b/ewit, link nền, màu nhấn, logo) · **Loại video** (mẫu mặc định, luật cắt, mô tả YouTube).
> Kiểu ảnh (cột ở tab Video): Trong vòng tròn (ảnh cắt tròn) hoặc Phủ ngoài vòng tròn (cần ảnh tách nền; thiếu thì tạm dùng Trong vòng tròn).
> Thumbnail: 1 người có avatar → ảnh tròn; 1 người thiếu → mẫu không ảnh; 2–4 người → nhiều ảnh, ai thiếu dùng chibi nam/nữ; không ai có → không ảnh; ≥ 5 người → chọn tên nhóm (ảnh nhóm).

## 1. Sơ đồ
```
ZOOM ghi hình → (1) video .mp4 + transcript .vtt vào thư mục Drive của buổi
      ▼
GOOGLE SHEET "Bảng điều khiển video – IT Team"   ◄── người dùng điều khiển
  tab Buổi: mỗi buổi 1 dòng (Loại buổi, Buổi số, Tiêu đề, Người chia sẻ, Ngày giờ, Chế độ, Trạng thái)
      ▼ (2) tra tab "Hồ sơ loại buổi"
HỒ SƠ LOẠI BUỔI = mẫu thumbnail + luật cắt + mẫu mô tả/playlist YouTube
      ▼ (3) AI đọc transcript theo luật cắt → công thức cắt → tab "Chi tiết cắt"
Chế độ "Chờ duyệt": dừng, người dùng bỏ tick đoạn muốn giữ → đổi trạng thái "Đã duyệt"
Chế độ "Tự động": chạy tiếp ngay
      ▼ (4) cắt video + phụ đề .srt + thumbnail theo mẫu → lưu Drive (ket_qua/)
      ▼ (5) đăng YouTube (Riêng tư) → ghi link vào Sheet, trạng thái "Xong"
```

## 2. Phân vai
| Thành phần | Vai trò | Giới hạn |
|---|---|---|
| Google Sheet (+ Apps Script nhẹ) | Bảng điều khiển: dữ liệu, trạng thái, duyệt | Apps Script 6 phút/lần – không xử lý video nên không ảnh hưởng |
| Colab (GĐ1–3) / GitHub Actions (GĐ4) | Máy chạy: cắt, thumbnail, đăng YouTube | Colab cần người bấm chạy; Actions 6 giờ/lần |
| AI | Đọc transcript → công thức cắt | GĐ1–3: Claude trong chat (~60–80k token/buổi 150 phút, ước tính); GĐ4: Claude API (có phí) |

## 3. Trạng thái một buổi
`Mới → Đang phân tích → Chờ duyệt → Đã duyệt → Đang cắt → Xong` (hoặc `Lỗi`). Chế độ Tự động bỏ qua `Chờ duyệt`.

## 4. Hồ sơ loại buổi
| Loại buổi | Mẫu thumbnail | Luật cắt |
|---|---|---|
| Training nội bộ | A – Mạch lá (`mau/training.json`) | Giữ demo, hỏi đáp; cắt chờ, chào hỏi, lỗi chia sẻ màn hình, im lặng |
| Sinh hoạt định kỳ | B – Cửa sổ code (chưa nối) | Giữ chia sẻ, thảo luận; cắt chuyện riêng, chờ đợi |
| Lớp học – <tên lớp> | Mẫu riêng (chưa có) | Luật lớp tiếng Anh: giữ lặp lại có chủ đích để dạy |

Thêm loại buổi mới = thêm 1 dòng hồ sơ + 1 ảnh nền + 1 file bố cục `mau/<ten>.json`.

## 5. Lộ trình
| GĐ | Nội dung | Trạng thái |
|---|---|---|
| 1 | Kiểm chứng lõi: cắt + thumbnail, thử 10 phút | Đang chạy thử |
| 2 | Sheet điều khiển + hồ sơ loại buổi; Colab đọc/ghi Sheet; mẫu B | Đang làm |
| 3 | Đăng YouTube, ghi link vào Sheet | Code có, chưa cài đặt API |
| 4 | Tự động hoàn toàn: P1 Zoom → Drive + Sheet (`zoom_sync.py`, tab Danh sách lớp) · P2 AI ra công thức cắt (`ai_cut.py`: claude/gemini/openrouter, chọn ở tab Cấu hình) · P3 GitHub Actions chạy theo lịch · P4 thông báo | P1 xong; P2 đang thử |

## Lớp an toàn khi đăng YouTube
- Mặc định **không tải phụ đề tự động** (tab Cấu hình). Video IT_T001 kèm phụ đề sai chữ đã bị YouTube gỡ ("harassment"); bản không phụ đề thì không bị.
- Chế độ *Chờ duyệt*: chỉ đăng khi tick **Duyệt đăng YouTube** ở tab Video.
- Khóa bí mật tạm để ở `.env` (thư mục chứa Sheet); khi xong P3 sẽ chuyển một lần sang GitHub Secrets.
