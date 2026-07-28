# SEO AI Studio V4.4 - Keyword Intelligence

V4.4 giữ toàn bộ chức năng V4.3 Pro và bổ sung quy trình keyword dành cho dữ liệu xuất từ Semrush.

## Điểm mới

- Import Semrush CSV, TSV và XLSX.
- Tự nhận các cột Keyword, Volume, Keyword Difficulty, Intent, CPC, URL, Position và Trend.
- Chuẩn hóa số như `1,200`, `1.200`, `1,2K` và `1.2K`.
- Loại keyword trùng khi gộp nhiều file.
- Tự phân loại Search Intent:
  - Informational
  - Commercial
  - Transactional
  - Navigational
- Tự tạo Keyword Cluster ở ba mức Broad, Balanced và Tight.
- Bảng Cluster hiển thị Total Volume, Average KD, Intent chính và Primary Keyword.
- Bộ lọc keyword, Intent, Cluster và Volume tối thiểu.
- Chỉnh sửa thủ công Intent/Cluster/Landing Page.
- Xuất Excel gồm Tổng quan, Keywords và Clusters.
- Giao diện màu theo Search Intent, KPI rõ ràng và nút mở hướng dẫn cho người mới.

## Quy trình gợi ý

```text
Semrush Export
-> Import Keyword Intelligence
-> Review Intent & Cluster
-> Map Landing Page
-> Top 5 Direct
-> Content Gap
-> Content Brief
-> Internal Link
-> Validation
-> Report 30/60/90
```

## File Semrush

File bắt buộc phải có cột Keyword. Nên export thêm:

- Volume/Search Volume
- KD %/Keyword Difficulty
- Intent/Search Intent
- CPC
- Position/Rank
- URL/Ranking URL

Tool hỗ trợ tên cột tiếng Anh và một số tên tiếng Việt phổ biến.

## Tài liệu

Bộ cài đặt kèm:

```text
Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf
```

Người dùng có thể mở tài liệu từ Start Menu hoặc nút `Hướng dẫn người mới` trong ứng dụng.

## Build

```bash
python generate_user_guide_v44.py
python -m unittest tests/test_v44_keywords.py tests/test_v43_core.py tests/test_v4_core.py -v
pyinstaller --clean --noconfirm SEO_AI_Studio_V44.spec
```

GitHub Actions tạo:

- `SEO_AI_Studio_V44_Setup.exe`
- `SHA256SUMS.txt`
- `Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf`
