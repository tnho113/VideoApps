# HANDOFF – App tự động cắt lọc video (EWIT)

> Trạng thái: **Đang làm rõ nhu cầu – chưa code.** Tạm dừng ngày 2026-11-06 để làm việc chuẩn bị dữ liệu (kho Quotes). Mở lại chủ đề này bằng cách dán phần "Câu mở đầu" ở cuối file.

## 1. Mục tiêu
Kéo thả video thô (lớp học, Zoom, video nói) vào app → app tự cắt khoảng lặng / đoạn thừa / đoạn nói lại → ra video sạch, giữ nguyên ý, thay cho việc cắt tay bằng CapCut.

Ảnh tham khảo: một app có màn hình "Kiểm tra 11 tiêu chí" (71:05 → 43:39, loại 386 "đúp quay lại", 26 khoảng lặng, đệm an toàn 350ms).
Nhận xét về app tham khảo: số liệu lệch nhẹ (71:05.10 − 43:39.15 = 1645.95s, app báo 1649.31s); 386 retake / 71 phút có vẻ đang đếm mọi đoạn cắt là retake.

## 2. Đã chốt
| Hạng mục | Quyết định |
|---|---|
| Giai đoạn 1 | Team EWIT dùng nội bộ, cắt video **lớp học tiếng Anh**. Ra bản dùng thử → hiệu chỉnh dần |
| Giai đoạn 2 | Hoàn thiện → bán cho người có nhu cầu |
| Nội dung video | Song ngữ Anh – Việt, có trao đổi giữa giáo viên và học viên |
| Chế độ | (1) Tự động ra MP4, (2) Duyệt từng đoạn cắt, (3) Xem & chỉnh sửa trên timeline – người dùng tự chọn |
| Máy | Core i5 (cần xác nhận "core 15"), RAM 8GB, không card đồ họa rời |

## 3. Rủi ro / lưu ý kỹ thuật đã nêu
1. **Lặp lại trong lớp học là phương pháp dạy, không phải lỗi** ("repeat after me", nhắc lại câu hỏi). Không được dùng logic "giữ lần nói cuối" như app tham khảo → phải định nghĩa lại "đoạn thừa" cho lớp học.
2. **Song ngữ + nhiều người nói** → nhận dạng giọng nói kém chính xác hơn → nguyên tắc: không chắc thì giữ lại và đánh dấu cho người duyệt.
3. **8GB RAM, CPU-only** → Whisper medium chạy được nhưng chậm (ước tính ~1–2× thời lượng video, cần đo thực tế); large-v3 gần vượt RAM. Đề xuất bộ nhận dạng giọng nói thay thế được: offline (miễn phí, riêng tư) / cloud (nhanh, có phí) – đo thử trên video mẫu EWIT rồi chọn.

## 4. Kiến trúc sơ bộ
```
Video → Tách audio (FFmpeg) → Nhận dạng giọng nói + mốc thời gian từng từ
      → Phân biệt người nói (GV / HV) → Bộ luật cắt "lớp học"
      → Danh sách đoạn đề xuất cắt (kèm độ tin cậy)
      → [Tự động | Duyệt | Chỉnh sửa] → Xuất MP4 (+ phụ đề .srt)
```

## 5. Câu hỏi còn mở (cần trả lời trước khi viết spec)
- **Q1:** Team đang cắt bỏ thủ công những gì trong video lớp EWIT? (chờ vào lớp, test mic, im lặng làm bài, nói vấp, ngoài lề, lỗi mạng…). Có cặp video gốc + bản đã cắt tay để làm chuẩn không?
- **Q2:** Video ghi bằng Zoom hay quay màn hình (Bandicam/OBS)? Nếu Zoom: có bật "Record a separate audio file for each participant" được không?
- Cần thêm: 1 video mẫu 5–10 phút.

## 6. Bước tiếp theo
Trả lời Q1, Q2 → viết `docs/SPEC_MVP.md` (tài liệu yêu cầu bản dùng thử) → team góp ý → bắt đầu code.

## 7. Việc liên quan đang làm song song
Kho **Quotes** (ảnh trên Google Drive → Google Sheet) – chuẩn bị dữ liệu cho làm video sau này.

## Câu mở đầu để quay lại chủ đề
> Đọc `docs/HANDOFF_VIDEO_APP.md` trong repo VideoApps. Mình tiếp tục làm rõ nhu cầu App cắt video EWIT. Trả lời Q1: … ; Q2: …
