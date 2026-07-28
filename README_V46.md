# SEO AI Studio V4.6 - Complete Guided Workflow

V4.6 giữ toàn bộ tính năng V4.4 và bổ sung lớp trải nghiệm hoàn chỉnh cho người mới, quy trình Full SEO Audit, Content Workflow và các cải tiến kỹ thuật cho GSC, PageSpeed/CrUX và WordPress.

## Trải nghiệm mới

- Easy Mode chỉ hiển thị quy trình bắt đầu.
- Pro Mode hiển thị toàn bộ chức năng trong 5 khu vực:
  - Tổng quan
  - Nghiên cứu
  - Audit
  - Kế hoạch & Thực thi
  - Theo dõi
- Wizard thiết lập 7 bước.
- Bảng trạng thái `Chưa thiết lập` / `Đã kết nối` / `Có lỗi`.
- Demo offline có sẵn Audit, Keyword, GSC, PageSpeed/CrUX và Content Brief.
- Recovery khôi phục dự án, đầu vào và keyword sau khi ứng dụng đóng đột ngột.
- Thanh tiến trình có bước hiện tại, thời gian, Hủy và Chạy lại.
- Hộp lỗi thông minh có Nguyên nhân, Cách xử lý và Sao chép thông tin hỗ trợ.
- Kiểm tra phiên bản mới từ manifest GitHub.

## Full SEO Audit

Một nút tự chạy:

1. Website Crawl.
2. Technical SEO.
3. Sitemap Coverage và Internal Link Map.
4. Lighthouse Lab Data và CrUX Field Data.
5. Google Search Console 90 ngày nếu đã kết nối.
6. Fix Queue chi tiết.
7. Roadmap 30/60/90 và snapshot comparison.

## Google Top 5 Direct

- Bộ đọc hỗ trợ nhiều cấu trúc HTML Google hơn.
- Phát hiện CAPTCHA, unusual traffic và Consent.
- Nút mở đúng truy vấn Google theo quốc gia/ngôn ngữ.
- Dán tối đa 5 URL từ clipboard, tự loại trùng.
- URL thủ công tiếp tục là fallback ổn định không cần SerpApi.

## Content Workflow

```text
Keyword
→ Search Intent
→ Cluster
→ Landing Page
→ Content Brief
→ Top 5
→ Content Gap
→ Outline
→ WordPress Draft
→ Recheck Landing Page
```

Content Brief gồm Primary Keyword, Secondary Keywords, Search Intent, định dạng, Title, Heading, câu hỏi, Volume, KD và Landing Page.

## Fix Queue chi tiết

Mỗi lỗi có:

- Lỗi gì?
- URL bị ảnh hưởng
- Vì sao quan trọng
- Cách sửa
- P0/P1/P2
- Độ khó
- Tác động dự kiến
- Trạng thái

## PageSpeed, CrUX, GSC và WordPress

- Tách Lighthouse Lab Data khỏi CrUX Field Data.
- CrUX dùng Chrome UX Report API khi có Google API Key.
- URL Inspection ghi rõ đây là trạng thái phiên bản trong Google Index, không phải Live Test.
- WordPress dùng Application Password.
- PageSpeed/CrUX API Key và WordPress Password có thể lưu trong Windows Credential Manager; không ghi vào project, snapshot hoặc report.

## Tài liệu

Bộ cài kèm PDF:

```text
Huong_Dan_Chi_Tiet_SEO_AI_Studio_V46.pdf
```

Tài liệu gồm 28 trang, hướng dẫn từng khu vực, từng module, lỗi thường gặp và checklist vận hành.

## Build

```bash
python generate_user_guide_v46.py
python -m unittest tests/test_v46_core.py tests/test_v44_keywords.py tests/test_v43_core.py tests/test_v4_core.py -v
pyinstaller --clean --noconfirm SEO_AI_Studio_V46.spec
```

GitHub Actions tạo:

- `SEO_AI_Studio_V46_Setup.exe`
- `SHA256SUMS.txt`
- `Huong_Dan_Chi_Tiet_SEO_AI_Studio_V46.pdf`
