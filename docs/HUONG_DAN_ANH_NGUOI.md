# Hướng dẫn cho trợ lý EW-WORK: thêm ảnh người/nhóm cho thumbnail

## Mục tiêu
Khi Nery gửi ảnh của một người (hoặc nhóm) mới: lưu ảnh gốc + ảnh tách nền lên Drive, rồi điền link vào Google Sheet để tool tự đưa ảnh lên thumbnail.

## Thông tin cố định
- Thư mục Drive "Ảnh người & nhóm": ID `1Bxx8hAHEfOoO9wWX7xNgTJoJk8Ui3W0Q`
- Google Sheet "Bảng điều khiển video – IT Team": ID `1nQJCLzBykSoSAGejiv_zukv42UKv6Ddv-VNbGMZhlfY`, tab **Người & Nhóm**
  - Cột: A Tên · B Loại (Người/Nhóm) · C Giới tính (Nam/Nữ) · D Link ảnh avatar · E Link ảnh tách nền (PNG) · F Ghi chú
  - Tên ở cột A phải viết **đúng chính tả có dấu** như sẽ chọn ở tab Video.

## Đầu vào cần có (hỏi lại nếu thiếu, gộp trong 1 câu)
Ảnh · Họ tên đầy đủ có dấu · Giới tính · Loại (Người/Nhóm) · Ghi chú/vai trò (không bắt buộc).

## Quy tắc đặt tên
- Người: `nguoi_<ho-ten-khong-dau>`; Nhóm: `nhom_<ten-nhom-khong-dau>` (chữ thường, gạch ngang).
- Ảnh gốc `.jpg`, ảnh tách nền `.png`, **cùng tên**. Ví dụ: `nguoi_tran-van-thua.jpg` + `nguoi_tran-van-thua.png`.

## Các bước
1. **Ảnh gốc** → lưu JPG, cạnh dài tối đa 1200px, chất lượng 90.
2. **Tách nền** (nếu chạy được lệnh Python):
   ```bash
   pip install -q "rembg[cpu]"
   python3 - <<'PY'
   from PIL import Image
   from rembg import remove, new_session
   im = Image.open("anh_goc").convert("RGB")
   im.thumbnail((1200, 1200)); im.save("nguoi_x.jpg", quality=90)
   model = "u2net_human_seg"          # ảnh nhóm: đổi thành "u2net"
   out = remove(im, session=new_session(model), alpha_matting=True)
   out.crop(out.getbbox()).save("nguoi_x.png")
   PY
   ```
   Nếu **không** chạy được lệnh: nhờ Nery tách nền bằng Canva (Chỉnh sửa ảnh → Xóa nền) hoặc remove.bg, rồi gửi lại file PNG.
3. **Kiểm tra 1 lần**: dán PNG lên nền tím, thu nhỏ còn ~300px rồi xem. Viền tóc/tay bị mất nhiều thì báo Nery, không thử lại nhiều lần.
4. **Kiểm tra trùng**: tìm trong thư mục Drive theo đúng tên file. Đã có thì hỏi Nery: ghi đè hay giữ.
5. **Tải lên Drive** (thư mục ở trên): 2 file `.jpg` và `.png`.
6. **Cập nhật Sheet**: đọc riêng cột `'Người & Nhóm'!A:A` để tìm dòng có tên đó; chưa có thì dùng dòng trống đầu tiên. Ghi **1 lần** cả dòng `A:F` (Tên, Loại, Giới tính, link jpg, link png, Ghi chú). Link dạng `https://drive.google.com/file/d/<ID>/view`.
7. **Báo lại** đúng 3 dòng: tên file, 2 link, dòng Sheet đã ghi.

## Tiết kiệm token (bắt buộc)
- **Không đọc lại ảnh gốc** sau khi nhận; chỉ xem **1 ảnh kiểm tra nhỏ** (~300px) ở bước 3.
- **Tải file lên Drive bằng tham chiếu file** (đường dẫn/sha256) nếu công cụ hỗ trợ — **không** dán chuỗi base64 vào lệnh.
- Tìm file trên Drive: chỉ lấy metadata (tắt nội dung/snippet), lọc theo thư mục + tên.
- Đọc Sheet: chỉ cột A, không đọc cả bảng. Ghi Sheet: 1 lệnh cho cả dòng.
- Không gọi lấy metadata từng file sau khi tải lên — dùng ID trả về ngay từ lệnh tải lên.
- Nhiều người cùng lúc: xử lý cả lô trong 1 script, ghi Sheet 1 lệnh cho nhiều dòng.
- Báo cáo ngắn, không nhắc lại hướng dẫn này.
