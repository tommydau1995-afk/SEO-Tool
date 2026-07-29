# SEO AI Studio V4.8 - SEO Intelligence

V4.8 giữ toàn bộ V4.7 và bổ sung lớp dữ liệu, chẩn đoán index và xác thực kết quả sau khi sửa SEO.

## Tính năng mới

### Keyword Planner tùy chọn

- Kết nối Google Ads API qua file JSON OAuth do người dùng quản lý.
- Lấy Average Monthly Searches, monthly trend, CPC range và Ads Competition.
- Import CSV/XLSX từ Keyword Planner khi không muốn kết nối API.
- Ghi nguồn, thời gian cập nhật và độ tin cậy.
- Không chuyển Ads Competition thành SEO Keyword Difficulty.

### Opportunity 2.0

Điểm 0-100 sử dụng các tín hiệu có thể giải thích:

- Volume thật khi có Keyword Planner.
- GSC impressions/clicks/position.
- Search Intent và business value.
- Landing Page đã có hoặc còn thiếu.
- SERP Weakness ước tính từ Top 5.

SERP Weakness không có backlink authority nên luôn được ghi là ước tính, không phải KD chính xác.

### Cannibalization và Content Gap

- Nhóm query GSC xuất hiện trên nhiều URL.
- Tính tổng impressions, tỷ lệ URL mạnh nhất và mức ưu tiên.
- Đề xuất chọn URL chính, gộp nội dung hoặc tách intent.
- Nhóm keyword chưa có Landing Page thành Content Gap theo Cluster.

### Index Debugger

- Lấy trạng thái phiên bản trong Google Index bằng Search Console URL Inspection.
- Tải URL live riêng bằng Googlebot user agent.
- Kiểm tra HTTP, redirect, robots.txt, Robots Meta, X-Robots-Tag, canonical, Title, H1 và content hash.
- So sánh Google canonical với canonical live.
- Ghi rõ URL Inspection không phải Live Test.

### Audit Diff và dự phòng

- So sánh hai snapshot Audit gần nhất.
- Hiển thị lỗi đã sửa, lỗi mới/tái phát, lỗi còn lại và thay đổi SEO Score.
- So sánh 4xx/5xx, indexable, orphan và dead-end.
- Xuất/khôi phục project backup ZIP an toàn; không chứa API secret.

### Trải nghiệm

- Tìm chức năng toàn ứng dụng bằng `Ctrl+K`.
- Hiển thị cảnh báo giới hạn dữ liệu GSC.
- Giữ Easy Mode, Pro Mode, Demo, Full Audit, Recovery và thông báo lỗi chi tiết.

## Build và kiểm thử

```bash
python generate_user_guide_v48.py
python -m unittest tests/test_v48_intelligence.py tests/test_v47_keywords.py tests/test_v46_core.py tests/test_v44_keywords.py tests/test_v43_core.py tests/test_v4_core.py -v
pyinstaller --clean --noconfirm SEO_AI_Studio_V48.spec
```

GitHub Actions tạo:

- `SEO_AI_Studio_V48_Setup.exe`
- `SHA256SUMS.txt`
- `Huong_Dan_Chi_Tiet_SEO_AI_Studio_V48.pdf`

## Nâng cấp từ V4.7

Bộ cài dùng cùng AppId để nâng cấp tại chỗ. Installer chỉ xóa executable và guide V4.6/V4.7; dữ liệu project trong AppData được giữ nguyên.
