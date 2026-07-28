import re
from dataclasses import asdict, dataclass


@dataclass
class MasterCheck:
    id: int
    category: str
    title: str
    method: str
    priority: str
    status: str = "Chưa kiểm tra"
    evidence: str = ""


TASKS_TEXT = """
1. Phân tích log server để xác định Googlebot đang crawl website như thế nào.
2. Đánh giá Crawl Budget và xác định những URL đang gây lãng phí tài nguyên crawl.
3. Tìm các trang Orphan Page không nhận được internal link.
4. Xác định các trang Dead-end không dẫn tới bất kỳ nội dung nào khác.
5. Đánh giá Click Depth để phát hiện những trang quá sâu trong cấu trúc website.
6. Phân tích Crawl Depth để đảm bảo Googlebot có thể tiếp cận các trang quan trọng.
7. Xác định các URL được Googlebot crawl quá nhiều nhưng không mang lại giá trị SEO.
8. Tìm các trang quan trọng chưa được Googlebot crawl hoặc crawl quá ít.
9. So sánh hành vi crawl giữa Googlebot Smartphone và Googlebot Desktop.
10. Kiểm tra việc phân phối Internal Link tới các Landing Page quan trọng.
11. Đánh giá tỷ lệ Index Coverage của toàn bộ website.
12. Phát hiện tình trạng Index Bloat.
13. Phát hiện các trang đã index nhưng không tạo ra Organic Traffic.
14. Phân tích các URL bị Google loại khỏi chỉ mục và tìm nguyên nhân.
15. Điều tra các trang ở trạng thái Crawled – currently not indexed.
16. Điều tra các trang ở trạng thái Discovered – currently not indexed.
17. Kiểm tra robots.txt để đảm bảo Googlebot không bị chặn nhầm.
18. Kiểm tra Robots Meta Tag và X-Robots-Tag trên toàn website.
19. Phát hiện các trang bị gắn noindex do lỗi template hoặc CMS.
20. Kiểm tra các quy tắc Disallow có đang chặn nhầm nội dung quan trọng hay không.
21. Rà soát toàn bộ Canonical trên website.
22. Phát hiện Canonical Chain.
23. Phát hiện Canonical trỏ tới Redirect hoặc URL Noindex.
24. Bổ sung Canonical cho các trang còn thiếu.
25. Chuẩn hóa phiên bản HTTP và HTTPS.
26. Chuẩn hóa WWW và Non-WWW.
27. Chuẩn hóa URL có hoặc không có dấu gạch chéo cuối.
28. Chuẩn hóa URL viết hoa và viết thường.
29. Kiểm soát URL Parameter gây trùng lặp nội dung.
30. Ngăn chặn việc sinh vô hạn URL từ Faceted Navigation hoặc bộ lọc.
31. Rà soát toàn bộ Redirect trên website.
32. Khắc phục Redirect Loop.
33. Thay thế Redirect 302 bằng Redirect 301 khi phù hợp.
34. Khôi phục giá trị SEO cho các URL 404 vẫn còn backlink.
35. Phát hiện và xử lý Soft 404.
36. Kiểm tra Broken Internal Link.
37. Kiểm tra Broken External Link.
38. Đối chiếu HTTP Status Code giữa CDN và Origin Server.
39. Điều tra các lỗi máy chủ như 5xx, timeout hoặc response bất thường.
40. Kiểm tra XML Sitemap có phản ánh đúng cấu trúc website.
41. Loại bỏ URL Redirect, Noindex hoặc lỗi khỏi Sitemap.
42. Kiểm tra Lastmod trong Sitemap.
43. Chia nhỏ Sitemap hợp lý cho website quy mô lớn.
44. Kiểm tra triển khai hreflang giữa các phiên bản ngôn ngữ.
45. Phát hiện lỗi Return Tag hoặc x-default.
46. Đánh giá chiến lược International SEO (ccTLD, Subfolder hoặc Subdomain).
47. Kiểm tra khả năng Google index nội dung được render bằng JavaScript.
48. So sánh HTML ban đầu và HTML sau khi render.
49. Đánh giá việc sử dụng CSR, SSR, SSG, ISR hoặc Dynamic Rendering.
50. Kiểm tra quá trình Hydration có gây ảnh hưởng tới SEO hay không.
51. Phân tích Core Web Vitals.
52. Tối ưu Largest Contentful Paint (LCP).
53. Tối ưu Interaction to Next Paint (INP).
54. Giảm Cumulative Layout Shift (CLS).
55. Cải thiện Time to First Byte (TTFB).
56. Loại bỏ các tài nguyên chặn quá trình render.
57. Tối ưu Critical Rendering Path.
58. Loại bỏ CSS không sử dụng.
59. Loại bỏ JavaScript không sử dụng.
60. Áp dụng Tree Shaking để giảm kích thước bundle.
61. Minify CSS và JavaScript.
62. Bật Gzip hoặc Brotli Compression.
63. Preload các tài nguyên quan trọng.
64. Thiết lập Preconnect và DNS Prefetch.
65. Tối ưu quá trình tải Font.
66. Triển khai Async hoặc Defer cho JavaScript.
67. Giảm ảnh hưởng của Third-party Script.
68. Thiết lập Cache Header hợp lý.
69. Tối ưu cấu hình CDN.
70. Chuyển đổi hình ảnh sang WebP hoặc AVIF.
71. Tạo Responsive Image bằng srcset và sizes.
72. Resize hình ảnh đúng kích thước hiển thị.
73. Triển khai Lazy Loading đúng cách.
74. Đảm bảo không Lazy Load hình ảnh LCP.
75. Khai báo Width và Height cho hình ảnh.
76. Đặt tên file hình ảnh theo chuẩn SEO.
77. Viết Alt Text đúng ngữ cảnh.
78. Tối ưu Video Embed.
79. Thiết kế Site Architecture.
80. Giảm Click Depth của các Landing Page quan trọng.
81. Xây dựng Topic Cluster.
82. Thiết kế Hub Page.
83. Xây dựng Silo Structure.
84. Triển khai Breadcrumb.
85. Tạo HTML Sitemap.
86. Tối ưu Mega Menu và Footer Navigation.
87. Rà soát toàn bộ Internal Link.
88. Phân phối Link Equity hợp lý.
89. Tối ưu Anchor Text nội bộ.
90. Bổ sung Internal Link từ các trang có độ uy tín cao.
91. Loại bỏ Internal Link trỏ tới Redirect hoặc URL lỗi.
92. Triển khai Schema phù hợp với từng loại nội dung.
93. Kiểm tra Rich Results.
94. Sửa lỗi Structured Data.
95. Khai báo Entity thông qua Organization, Person và sameAs.
96. Nghiên cứu bộ từ khóa mục tiêu.
97. Mở rộng từ khóa từ Google Search Console và dữ liệu tìm kiếm.
98. Phân nhóm từ khóa theo chủ đề và Search Intent.
99. Mapping từ khóa vào đúng Landing Page.
100. Phát hiện và xử lý Keyword Cannibalization.
101. Phân tích SERP và Content Gap với đối thủ.
102. Xây dựng Content Brief cho từng bài viết.
103. Biên tập nội dung theo tiêu chuẩn SEO.
104. Bổ sung dữ liệu gốc, nghiên cứu hoặc Case Study.
105. Tăng cường Experience Signals theo E-E-A-T.
106. Tối ưu Title, Meta Description và Heading.
107. Tối ưu nội dung để tăng khả năng xuất hiện ở Featured Snippet.
108. Bổ sung bảng biểu, hình ảnh và nội dung trực quan.
109. Làm mới các bài viết bị giảm thứ hạng.
110. Gộp hoặc loại bỏ Thin Content.
111. Theo dõi Content Decay theo từng quý.
112. Xây dựng chiến dịch Digital PR.
113. Triển khai Broken Link Building.
114. Khôi phục các Brand Mention chưa gắn liên kết.
115. Xây dựng Guest Post trên website có lượng truy cập thật.
116. Kiểm tra và xử lý Backlink độc hại.
117. Theo dõi Backlink bị mất.
118. Phân tích khoảng cách backlink với đối thủ.
119. Xây dựng và tối ưu hồ sơ tác giả (Author Profile).
120. Tối ưu Google Business Profile.
121. Đồng bộ thông tin NAP trên toàn hệ thống.
122. Quản lý và phản hồi đánh giá của khách hàng.
123. Xây dựng Landing Page cho từng khu vực.
124. Tối ưu Category Page.
125. Tối ưu Product Page.
126. Xử lý sản phẩm hết hàng mà vẫn giữ giá trị SEO.
127. Triển khai Product Schema và Review Schema.
128. Khắc phục nội dung mô tả sản phẩm bị trùng lặp.
129. Thiết lập GA4 và các sự kiện đo lường.
130. Kiểm tra Conversion Tracking.
131. Xây dựng Dashboard SEO trên Looker Studio.
132. Đo lường Organic Traffic, Leads và Revenue.
133. Phân tích Attribution của Organic Search.
134. Dự báo Traffic và Doanh thu từ SEO.
135. Theo dõi khả năng hiển thị trên AI Overviews.
136. Đo lường Share of Voice trên AI Search.
137. Theo dõi lượng truy cập từ ChatGPT, Gemini, Claude và Perplexity.
138. Kiểm tra AI Crawler có được phép truy cập website.
139. Tối ưu nội dung để tăng khả năng được AI trích dẫn.
140. Xây dựng Entity nhất quán trên các nguồn tri thức.
141. Tăng cường Topical Authority.
142. Đo lường AI Visibility theo từng chủ đề.
143. Xây dựng SEO Roadmap.
144. Lập kế hoạch Technical SEO.
145. Lập kế hoạch Content SEO.
146. Ưu tiên công việc dựa trên Business Impact.
147. Thiết lập KPI SEO.
148. Dự báo ROI cho các hoạt động SEO.
149. Trình bày chiến lược SEO với các bên liên quan.
150. Theo dõi và điều chỉnh chiến lược SEO theo các bản cập nhật của Google và AI Search.
"""


def category_for(number):
    ranges = (
        (1, 10, "Crawl Budget & Log"),
        (11, 20, "Indexation & Robots"),
        (21, 43, "URL, Canonical & Sitemap"),
        (44, 50, "International & JavaScript"),
        (51, 78, "Performance & Media"),
        (79, 95, "Architecture & Structured Data"),
        (96, 111, "Keyword & Content"),
        (112, 128, "Authority, Local & Ecommerce"),
        (129, 142, "Measurement & AI Search"),
        (143, 150, "Strategy & Governance"),
    )
    return next(name for start, end, name in ranges if start <= number <= end)


def method_for(number):
    if number in {1, 2, 7, 8, 9}:
        return "Server Log"
    if number in {11, 12, 13, 14, 15, 16, 97, 109, 111, 132, 133}:
        return "GSC/GA4 Import"
    if 17 <= number <= 43 or number in {
        3, 4, 5, 6, 10, 44, 45, 62, 63, 64, 66, 68, 70, 71, 73, 75, 77,
        80, 84, 87, 89, 91, 92, 94, 106, 110, 138,
    }:
        return "Auto Audit"
    if 51 <= number <= 69 or number in {72, 74, 78}:
        return "PageSpeed"
    if number in {96, 98, 99, 100, 101, 102, 107, 108, 135, 136, 139, 141, 142}:
        return "SERP Research"
    return "Chuyên viên"


def priority_for(number):
    if number in set(range(1, 43)) | set(range(51, 56)) | {80, 87, 91, 94, 96, 99, 100, 129, 130, 132, 143, 146, 147}:
        return "P0"
    if number <= 111 or number in {116, 117, 118, 127, 128, 133, 134, 135, 138, 139, 141, 142, 144, 145, 148}:
        return "P1"
    return "P2"


def build_master_checks():
    checks = []
    for raw in TASKS_TEXT.strip().splitlines():
        match = re.match(r"(\d+)\.\s*(.+)", raw.strip())
        if not match:
            continue
        number = int(match.group(1))
        checks.append(
            MasterCheck(
                id=number,
                category=category_for(number),
                title=match.group(2),
                method=method_for(number),
                priority=priority_for(number),
            )
        )
    return checks


def checks_to_rows(checks):
    return [asdict(check) for check in checks]

