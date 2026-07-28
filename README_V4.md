# SEO AI Studio V4 — Complete SEO Workflow for Windows

SEO AI Studio V4 là ứng dụng Windows Desktop đóng gói thành một file cài đặt:

```text
SEO_AI_Studio_V4_Setup.exe
```

Máy sử dụng không cần cài Python, pip hoặc chạy lệnh CMD.

## Quy trình V4

```text
Projects & History
→ Website Audit
→ Crawl & Index
→ Keyword Map
→ Top 5 + AI Overview
→ Fix Queue
→ Performance & Data
→ Validation
→ SEO 150 Checklist
```

## Các module chính

- **Projects & History:** quản lý nhiều website, lưu snapshot và so sánh hai lần Audit.
- **Website Audit:** crawl tối đa 500 URL cùng domain; kiểm tra HTTP, Title, Meta, H1/H2, Canonical, Robots, content, ALT, internal link, Schema, Open Graph và tốc độ phản hồi.
- **Crawl & Index:** import server access log, thống kê Googlebot Smartphone/Desktop, Crawl Waste, trang crawl ít, Orphan, Dead-end và Click Depth; import CSV Index Coverage từ Google Search Console.
- **Keyword Map:** gán keyword vào landing page, intent, mức ưu tiên, phát hiện cannibalization và rank tracking.
- **Top 5 + AI Overview:** dùng SerpApi để lấy 5 kết quả Google, crawl H1–H3, lấy AI Overview, câu hỏi liên quan và 4 hình ảnh; loại trùng và tạo Content Brief/outline tổng hợp.
- **Fix Queue:** tự chuyển lỗi Audit thành P0/P1/P2, kèm hướng xử lý và trạng thái.
- **Performance & Data:** PageSpeed Insights, Core Web Vitals, import CSV GSC/GA4.
- **WordPress:** kiểm tra kết nối và gửi Content Brief dưới dạng Draft bằng Application Password.
- **SEO 150 Checklist:** toàn bộ 150 hạng mục Technical, Content, Authority, Local, Ecommerce, Analytics và AI Search; phân biệt Auto Audit, Server Log, GSC/GA4, PageSpeed, SERP Research và công việc chuyên viên.

## API và dữ liệu

- SerpApi Key: dùng cho Google Top 5, AI Overview, Google Images và Rank Tracking.
- PageSpeed API Key: không bắt buộc với một số request, nhưng nên dùng để có quota ổn định.
- WordPress Application Password: dùng để tạo bài Draft.
- GSC/GA4 và Index Coverage: import CSV, không yêu cầu đăng nhập Google trong app.

Các khóa chỉ được giữ trong bộ nhớ của phiên làm việc. V4 không ghi khóa vào project, snapshot hoặc file export.

## Phạm vi tự động hóa của 150 hạng mục

Không phải mọi công việc SEO đều có thể kết luận chỉ bằng crawler. V4 gắn nguồn thực thi cho từng mục:

- `Auto Audit`: kiểm tra trực tiếp từ HTML, header, sitemap và link graph.
- `Server Log`: cần access log từ CDN/origin.
- `GSC/GA4 Import`: cần CSV được xuất từ tài khoản của website.
- `PageSpeed`: lấy dữ liệu Lighthouse/Core Web Vitals.
- `SERP Research`: lấy Google Top 5, AI Overview và rank.
- `Chuyên viên`: cần đánh giá kinh doanh, editorial, PR, backlink hoặc xác nhận thủ công.

## Build bộ cài Windows

Workflow `.github/workflows/build-v4.yml` tự chạy trên Windows:

1. Cài dependency.
2. Kiểm tra cú pháp và chạy unit test.
3. Đóng gói `SEO_AI_Studio_V4.exe` bằng PyInstaller.
4. Tạo `SEO_AI_Studio_V4_Setup.exe` bằng Inno Setup.
5. Tạo `SHA256SUMS.txt`.
6. Upload artifact `SEO-AI-Studio-V4-Setup`.

## Lưu ý dữ liệu

- Googlebot trong server log được nhận diện theo User-Agent. Khi cần quyết định bảo mật, phải xác minh reverse DNS tại máy chủ.
- Hình ảnh Google chỉ là gợi ý nghiên cứu; phải kiểm tra giấy phép/quyền sử dụng trước khi đăng.
- Content Brief yêu cầu viết nguyên bản và không sao chép câu chữ từ Top 5.
- Nên Audit lại sau khi sửa để xác thực thay đổi bằng module Validation.

