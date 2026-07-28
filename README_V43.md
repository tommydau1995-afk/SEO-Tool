# SEO AI Studio V4.3 Pro

V4.3 Pro hợp nhất toàn bộ roadmap V4.1, V4.2 và V4.3 trong một ứng dụng Windows.

## V4.1 - nền tảng cần làm ngay

- Top 5 Direct không cần SerpApi; có chế độ 5 URL thủ công khi Google yêu cầu CAPTCHA.
- Google Search Console read-only qua Service Account: 90 ngày Search Analytics, Sitemap và URL Inspection.
- PageSpeed Insights/Core Web Vitals cho mobile và desktop.
- Internal Link Map, Click Depth, Sitemap Coverage, Orphan Page và Dead-end.
- Kiểm tra toàn bộ API, phân loại lỗi quyền/quota/timeout/CAPTCHA với hướng xử lý.

## V4.2 - vận hành chuyên nghiệp

- Server Log Analyzer và Crawl Budget: crawl efficiency, waste hits, Smartphone/Desktop, 4xx/5xx.
- Scheduled Audit bằng Windows Task Scheduler và cảnh báo lỗi mới theo snapshot.
- Báo cáo PDF quản trị 30/60/90 và Excel nhiều sheet.
- WordPress Preview, revisions và Rollback có xác nhận.

## V4.3 - tăng trưởng

- Import/phân tích backlink CSV/TSV, referring domains, dofollow và cảnh báo rủi ro.
- Rank Tracking Top 20 không cần SerpApi và Share of Voice với đối thủ.
- Content Decay tự động theo hai giai đoạn 30 ngày.
- Content Gap từ heading Top 5 so với trang hiện tại.
- Dashboard/Roadmap Technical, Content, Authority và Measurement 30/60/90 ngày.

## Google Search Console

1. Tạo Service Account trong Google Cloud và bật Search Console API.
2. Thêm email Service Account vào property Search Console với quyền đọc.
3. Trong `API & Kết nối`, chọn file JSON và nhập property:
   - Domain property: `sc-domain:example.com`
   - URL-prefix property: `https://www.example.com/`
4. Bấm `Kiểm tra tất cả kết nối`, sau đó mở tab `Search Console`.

File JSON và application password không được lưu vào project, snapshot hay báo cáo.

## Scheduled Audit

Chọn dự án, vào `Automation`, đặt tần suất `DAILY` hoặc `WEEKLY` và giờ `HH:MM`.
Ứng dụng tạo Windows Task chạy:

```text
SEO_AI_Studio_V43.exe --scheduled-audit PROJECT_ID --max-pages 100
```

Mỗi lần chạy tạo snapshot mới và lưu danh sách lỗi mới để hiển thị ở tab Automation.

## Backlink CSV

Importer tự nhận các tên cột phổ biến:

- source/referring page/backlink
- target/landing page
- anchor/anchor text
- DR/DA/domain rating/domain authority
- follow/dofollow/link type
- traffic/organic traffic

## Build

```bash
python -m unittest discover -s tests -v
pyinstaller --clean --noconfirm SEO_AI_Studio_V43.spec
```

Windows Setup được build tự động bằng GitHub Actions và Inno Setup.
