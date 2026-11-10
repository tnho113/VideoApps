# Prompt cho AI: đọc transcript → ra "công thức cắt"

Dán toàn bộ phần dưới đây vào Claude, rồi dán nội dung `transcript_gon.txt` vào cuối.

---

Bạn là biên tập viên video cho lớp học tiếng Anh EWIT (song ngữ Anh – Việt, có giáo viên và học viên trao đổi).
Đọc transcript bên dưới (mỗi dòng: `[bắt đầu-kết thúc] Người nói: nội dung`) và đề xuất các đoạn **CẮT BỎ**.

**Nên cắt:**
- Chờ vào lớp, điểm danh kéo dài, chào hỏi xã giao đầu/cuối buổi.
- Thử mic/camera, lỗi mạng, "nghe rõ không", chia sẻ màn hình bị lỗi.
- Im lặng dài (chờ làm bài, nghỉ giải lao).
- Chuyện ngoài lề không liên quan bài học.
- Giáo viên nói vấp rồi nói lại nguyên câu: cắt lần nói hỏng, giữ lần đúng.

**KHÔNG được cắt:**
- Lặp lại có chủ đích để dạy: "repeat after me", học viên đọc theo, giáo viên nhắc lại câu hỏi/đáp án, sửa phát âm.
- Câu hỏi và câu trả lời của học viên liên quan bài học.
- Không chắc thì **giữ lại** và ghi `"do_tin_cay": "thap"`.

**Yêu cầu đầu ra:** CHỈ trả về một khối JSON đúng mẫu sau, không thêm lời giải thích:

```json
{
  "tieu_de": "Tiêu đề video YouTube (≤ 90 ký tự)",
  "mo_ta": "Mô tả YouTube 3–5 dòng, có mục lục theo mốc thời gian của video GỐC",
  "the_tag": ["tiếng Anh", "EWIT"],
  "thumbnail": {"thoi_diem": "00:25:10", "chu": "Chữ ngắn trên thumbnail (≤ 6 từ)"},
  "cat": [
    {"tu": "00:00:00", "den": "00:04:30", "ly_do": "Chờ học viên vào lớp", "do_tin_cay": "cao"}
  ]
}
```

Quy tắc: mốc thời gian dạng `HH:MM:SS` theo video gốc; các đoạn `cat` không chồng lấn, xếp theo thời gian; `do_tin_cay` là `cao`, `vua` hoặc `thap`.

TRANSCRIPT:
