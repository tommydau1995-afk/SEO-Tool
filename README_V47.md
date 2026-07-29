# SEO AI Studio V4.7 - Built-in Keyword Discovery

V4.7 giữ toàn bộ V4.6 và bổ sung quy trình tự tìm bộ từ khóa để người dùng không phải bắt đầu trên Semrush.

## Keyword Discovery không cần Semrush

Ba nguồn có thể dùng độc lập hoặc kết hợp:

- Google Suggest: mở rộng cách người dùng diễn đạt từ 1-10 seed, không cần API key.
- Google Search Console: gom query, clicks, impressions, position và URL hiện hữu.
- Website đã crawl: lấy chủ đề từ Title, H1, URL và gợi ý Landing Page phù hợp.

Tool tự:

1. Loại trùng keyword.
2. Ghi rõ nguồn của từng keyword.
3. Phân Search Intent.
4. Chia Cluster ở mức Broad, Balanced hoặc Tight.
5. Gợi ý Landing Page từ GSC và nội dung website.
6. Chấm điểm Cơ hội 0-100.
7. Chuyển dòng chọn sang Keyword Intelligence.
8. Tạo Content Brief từ nhóm Cơ hội cao.
9. Xuất CSV/Excel có nguồn và giải thích chỉ số.

### Nguyên tắc dữ liệu

- `Cơ hội` là điểm ưu tiên nội bộ, không phải Keyword Difficulty.
- `GSC Impressions` là số lần website đã xuất hiện trong dữ liệu GSC, không phải Search Volume toàn thị trường.
- Tool không tự bịa Volume/KD. Hai cột này chỉ có số khi người dùng nhập từ nguồn metrics thật.
- Google Suggest là best-effort. Khi gặp HTTP 429, giảm seed, chọn mức Nhanh và thử lại sau.

## Ba mức mở rộng

- Nhanh: ít request, phù hợp kiểm tra seed.
- Cân bằng: mặc định, cân đối số lượng và thời gian.
- Sâu: nhiều biến thể chữ cái/câu hỏi, có nguy cơ bị giới hạn tạm thời.

## Luồng nội dung hoàn chỉnh

```text
Seed
→ Google Suggest + GSC + Website
→ Opportunity
→ Search Intent
→ Cluster
→ Landing Page
→ Content Brief
→ Top 5
→ Outline
→ WordPress Draft
→ Recheck
```

## Tính năng kế thừa V4.6

- Easy Mode và Pro Mode trong 5 khu vực.
- Wizard thiết lập 7 bước và Demo offline.
- Full SEO Audit một nút.
- Website Crawl, Technical SEO, Sitemap Coverage, Orphan Page và Internal Link Map.
- Top 5 Google Direct, phát hiện CAPTCHA/Consent và 5 URL thủ công.
- Fix Queue chi tiết, Recovery, tiến trình/Hủy/Chạy lại và hộp lỗi thông minh.
- Lighthouse Lab Data tách riêng CrUX Field Data.
- Google Search Console, Server Log Analyzer, Crawl Budget, Scheduled Audit.
- WordPress Draft/Preview/Rollback và Windows Credential Manager.
- Rank Tracking, Content Decay, Content Gap, Backlink và Roadmap 30/60/90.

## Tài liệu

Bộ cài kèm:

```text
Huong_Dan_Chi_Tiet_SEO_AI_Studio_V47.pdf
```

Tài liệu gồm ít nhất 28 trang và có hướng dẫn chi tiết Keyword Discovery, ý nghĩa điểm Cơ hội, giới hạn Volume/KD, từng khu vực của tool và lỗi thường gặp.

## Build

```bash
python generate_user_guide_v47.py
python -m unittest tests/test_v47_keywords.py tests/test_v46_core.py tests/test_v44_keywords.py tests/test_v43_core.py tests/test_v4_core.py -v
pyinstaller --clean --noconfirm SEO_AI_Studio_V47.spec
```

GitHub Actions tạo:

- `SEO_AI_Studio_V47_Setup.exe`
- `SHA256SUMS.txt`
- `Huong_Dan_Chi_Tiet_SEO_AI_Studio_V47.pdf`
