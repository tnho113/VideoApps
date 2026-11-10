# Hướng dẫn làm việc cho Claude trong repo VideoApps

## Nguyên tắc tiết kiệm token (bắt buộc)
Khi một việc có thể tốn nhiều token (xử lý hàng loạt file/ảnh, đọc nhiều dữ liệu, gọi công cụ lặp lại hàng chục lần trở lên):
1. **Dừng lại trước khi làm** – chưa gọi công cụ hàng loạt.
2. **Đưa ra phương án** kèm ước tính token, ưu tiên cách tốn ít nhất. Ví dụ: Apps Script chạy ngay trong Google Sheet/Drive, script cục bộ, xử lý theo lô, lọc dữ liệu trước khi đọc.
3. **Để người dùng chọn phương án.**
4. **Chạy thử trên một mẫu nhỏ** (khoảng 5–10 mục) để người dùng duyệt.
5. **Chỉ triển khai toàn bộ** sau khi người dùng đồng ý kết quả chạy thử.

## Bài học đã rút ra
- Đổi tên/xử lý hàng loạt file Drive → dùng Apps Script do người dùng chạy (0 token), không gọi `update_file` từng file (~1.5k token/lần).
- Ảnh Drive nhỏ (<~38KB) trả về base64 trong kết quả → rất tốn token; tải xuống và xử lý cục bộ hoặc nhờ người dùng gõ tay.

## Dự án
- App cắt video EWIT: xem `docs/HANDOFF_VIDEO_APP.md`.
- Tool xử lý video Zoom của IT Team (đang làm): quy trình tổng thể ở `docs/QUY_TRINH_TONG_THE.md`, code ở `tools/zoom_cut/`.
- Kho Quotes (Google Sheet "Kho Quotes", tab Quotes Q001… và tab Infographic I001…; ảnh trên Drive đặt tên theo STT).
