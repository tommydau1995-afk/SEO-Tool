"""Generate the detailed Vietnamese guide bundled with SEO AI Studio V4.6."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT = (
    Path(__file__).resolve().parent
    / "output"
    / "pdf"
    / "Huong_Dan_Chi_Tiet_SEO_AI_Studio_V46.pdf"
)
NAVY = "#17324D"
BLUE = "#1769C2"
TEAL = "#0E8A7A"
GREEN = "#2E7D32"
AMBER = "#F59E0B"
RED = "#C62828"
PURPLE = "#7454B3"
LIGHT = "#F5F7FA"
PALE_BLUE = "#E9F3FF"
PALE_GREEN = "#E8F7EC"
PALE_AMBER = "#FFF2D8"
PALE_PURPLE = "#F1EAFE"
GRAY = "#64748B"
WHITE = "#FFFFFF"


def find_fonts():
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    ]
    for normal, bold in candidates:
        if Path(normal).exists() and Path(bold).exists():
            return normal, bold
    return None, None


def safe(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate(path=OUTPUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normal_path, bold_path = find_fonts()
    normal_font, bold_font = "Helvetica", "Helvetica-Bold"
    if normal_path and bold_path:
        pdfmetrics.registerFont(TTFont("V46Guide", normal_path))
        pdfmetrics.registerFont(TTFont("V46GuideBold", bold_path))
        normal_font, bold_font = "V46Guide", "V46GuideBold"

    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
        title="Hướng dẫn chi tiết SEO AI Studio V4.6",
        author="SEO AI Studio",
        subject="Hướng dẫn từng mục, Full SEO Audit và quy trình SEO 30/60/90",
    )
    width, height = A4
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content"
    )

    def header_footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.rect(0, height - 11 * mm, width, 11 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(bold_font, 8.3)
        canvas.drawString(
            15 * mm,
            height - 7.2 * mm,
            "SEO AI STUDIO V4.6 - HƯỚNG DẪN CHI TIẾT",
        )
        canvas.setFillColor(colors.HexColor(GRAY))
        canvas.setFont(normal_font, 7.8)
        canvas.drawString(15 * mm, 6.5 * mm, "Easy + Pro Complete SEO Workflow")
        canvas.drawRightString(
            width - 15 * mm, 6.5 * mm, f"Trang {document.page}"
        )
        canvas.restoreState()

    doc.addPageTemplates(
        [PageTemplate(id="content", frames=[frame], onPage=header_footer)]
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="V46Title",
            fontName=bold_font,
            fontSize=23,
            leading=29,
            textColor=colors.HexColor(NAVY),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46Sub",
            fontName=normal_font,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor(GRAY),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46H1",
            fontName=bold_font,
            fontSize=16.5,
            leading=21,
            textColor=colors.HexColor(NAVY),
            spaceAfter=3.5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46H2",
            fontName=bold_font,
            fontSize=11.2,
            leading=14,
            textColor=colors.HexColor(BLUE),
            spaceBefore=2.5 * mm,
            spaceAfter=1.5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46Body",
            fontName=normal_font,
            fontSize=8.7,
            leading=12.7,
            textColor=colors.HexColor(NAVY),
            spaceAfter=1.7 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46Small",
            fontName=normal_font,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor(NAVY),
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46Callout",
            fontName=normal_font,
            fontSize=8.4,
            leading=12,
            textColor=colors.HexColor(NAVY),
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46Metric",
            fontName=bold_font,
            fontSize=15,
            leading=19,
            alignment=TA_CENTER,
            textColor=colors.HexColor(BLUE),
        )
    )
    styles.add(
        ParagraphStyle(
            name="V46MetricLabel",
            fontName=normal_font,
            fontSize=7.5,
            leading=9.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor(GRAY),
        )
    )
    body = styles["V46Body"]
    small = styles["V46Small"]
    story = []

    def h1(text):
        return Paragraph(safe(text), styles["V46H1"])

    def h2(text):
        return Paragraph(safe(text), styles["V46H2"])

    def p(text):
        return Paragraph(text, body)

    def bullet(text):
        return Paragraph("• " + text, body)

    def page(title, intro=""):
        if story:
            story.append(PageBreak())
        story.append(h1(title))
        if intro:
            story.append(p(intro))

    def callout(title, text, color=PALE_BLUE, border=BLUE):
        table = Table(
            [[Paragraph(f"<b>{safe(title)}</b><br/>{text}", styles["V46Callout"])]],
            colWidths=[doc.width],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 2.5 * mm))

    def step(number, title, text):
        table = Table(
            [
                [
                    Paragraph(
                        str(number),
                        ParagraphStyle(
                            f"StepV46{number}",
                            parent=styles["V46Metric"],
                            textColor=colors.white,
                        ),
                    ),
                    Paragraph(
                        f"<b>{safe(title)}</b><br/>{text}",
                        styles["V46Callout"],
                    ),
                ]
            ],
            colWidths=[12 * mm, doc.width - 12 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(BLUE)),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(PALE_BLUE)),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#BDD3EA")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (1, 0), (1, 0), 8),
                    ("RIGHTPADDING", (1, 0), (1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(KeepTogether([table, Spacer(1, 1.8 * mm)]))

    def table(headers, rows, widths=None):
        data = [
            [Paragraph(f"<b>{safe(value)}</b>", small) for value in headers]
        ] + [
            [Paragraph(safe(value), small) for value in row]
            for row in rows
        ]
        item = Table(data, colWidths=widths, repeatRows=1)
        item.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(LIGHT)]),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(item)
        story.append(Spacer(1, 2.5 * mm))

    # 1 - Cover
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("SEO AI STUDIO V4.6", styles["V46Title"]))
    story.append(
        Paragraph(
            "Hướng dẫn chi tiết theo từng mục - Dành cho người mới và người làm SEO chuyên nghiệp",
            styles["V46Sub"],
        )
    )
    metrics = [
        ("5", "Khu vực làm việc"),
        ("1 nút", "Full SEO Audit"),
        ("150", "SEO Checklist"),
        ("30/60/90", "SEO Roadmap"),
    ]
    metric_table = Table(
        [
            [Paragraph(value, styles["V46Metric"]) for value, _ in metrics],
            [Paragraph(label, styles["V46MetricLabel"]) for _, label in metrics],
        ],
        colWidths=[doc.width / 4] * 4,
    )
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PALE_BLUE)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C6D9EE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C6D9EE")),
                ("TOPPADDING", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 14),
            ]
        )
    )
    story.append(metric_table)
    story.append(Spacer(1, 8 * mm))
    callout(
        "Mục tiêu của tài liệu",
        "Giúp bạn cài đặt, thiết lập, chạy Audit, nghiên cứu keyword, tạo Content Brief, "
        "xuất WordPress, theo dõi kết quả và xử lý lỗi mà không cần biết lập trình.",
        PALE_GREEN,
        GREEN,
    )
    story.append(p("<b>Phiên bản:</b> 4.6.0 &nbsp;&nbsp; <b>Nền tảng:</b> Windows 10/11 64-bit"))

    # 2
    page("1. Cài đặt và mở ứng dụng", "Bộ cài đã chứa ứng dụng và file hướng dẫn này.")
    for number, title, text in (
        (1, "Chạy bộ cài", "Mở SEO_AI_Studio_V46_Setup.exe và chọn Next."),
        (2, "Chọn Desktop icon", "Bật tùy chọn nếu muốn có biểu tượng ngoài Desktop."),
        (3, "Hoàn tất", "Chọn Launch SEO AI Studio V4.6."),
        (4, "SmartScreen", "Nếu Windows hiển thị cảnh báo, kiểm tra đúng tên file và SHA-256 trước khi chạy."),
    ):
        step(number, title, text)
    callout(
        "Dữ liệu dự án",
        "Project, snapshot và trạng thái được lưu trong thư mục dữ liệu ứng dụng của tài khoản Windows. "
        "Gỡ ứng dụng không tự xóa dữ liệu dự án.",
        PALE_AMBER,
        AMBER,
    )

    # 3
    page("2. Easy Mode và Pro Mode")
    table(
        ["Chế độ", "Dành cho", "Hiển thị"],
        [
            ["Easy", "Người mới", "Bắt đầu, trạng thái thiết lập, Demo và Full SEO Audit"],
            ["Pro", "SEOer/Developer", "Toàn bộ 5 khu vực và các module nâng cao"],
        ],
        [28 * mm, 45 * mm, 97 * mm],
    )
    for item in (
        "Ứng dụng mở ở Easy Mode để tránh quá nhiều tab.",
        "Chọn Pro ở góc trên để mở toàn bộ chức năng.",
        "Nút trong Easy Mode có thể tự chuyển sang đúng khu vực Pro.",
        "Việc chuyển chế độ không làm mất dữ liệu.",
    ):
        bullet(item)
    callout(
        "Khuyến nghị",
        "Người mới nên hoàn thành bảng Trạng thái thiết lập trước, sau đó mới dùng Pro Mode.",
    )

    # 4
    page("3. Trình hướng dẫn thiết lập lần đầu")
    steps = [
        ("Tạo dự án", "Đặt tên dễ nhận biết theo website hoặc thương hiệu."),
        ("Nhập website", "Dùng URL đầy đủ bắt đầu bằng https://."),
        ("Quốc gia/ngôn ngữ", "Ví dụ vn và vi cho thị trường Việt Nam."),
        ("Kiểm tra website", "Xác nhận URL trước khi Crawl."),
        ("Kết nối dữ liệu", "GSC, PageSpeed/CrUX và WordPress là tùy chọn."),
        ("Import Semrush", "Có thể bỏ qua và import sau."),
        ("Full SEO Audit", "Tự chạy quy trình tổng hợp."),
    ]
    for number, (title, text) in enumerate(steps, 1):
        step(number, title, text)
    callout("Trạng thái", "Mỗi bước hiển thị Chưa thiết lập, Đã kết nối hoặc Có lỗi.")

    # 5
    page("4. Khu vực Tổng quan")
    h2_items = [
        ("Bắt đầu", "Onboarding, Demo, Full Audit và hành động tiếp theo."),
        ("Dashboard", "SEO Score, số trang, lỗi P0 và tiến độ 150 Checklist."),
        ("Projects & History", "Tạo dự án, snapshot và so sánh hai lần Audit."),
    ]
    table(
        ["Mục", "Công dụng"],
        h2_items,
        [48 * mm, 122 * mm],
    )
    bullet("Luôn kiểm tra tên dự án ở góc trên bên phải trước khi chạy.")
    bullet("Snapshot lưu bằng chứng tại từng thời điểm.")
    bullet("Validation cho biết lỗi đã sửa, lỗi mới và lỗi còn lại.")

    # 6
    page("5. Demo, Recovery và cập nhật phiên bản")
    h2("5.1 Chế độ Demo")
    bullet("Nhấn Tải dữ liệu Demo để thử mà không cần API hoặc website thật.")
    bullet("Demo có trang Audit, lỗi SEO, keyword, GSC, PageSpeed/CrUX và Content Brief.")
    h2("5.2 Khôi phục khi ứng dụng đóng đột ngột")
    bullet("Tool checkpoint dự án, website, keyword và thao tác đang chạy.")
    bullet("Lần mở tiếp theo, chọn Khôi phục để tải lại đầu vào và dữ liệu đã lưu.")
    h2("5.3 Kiểm tra cập nhật")
    bullet("Nhấn Kiểm tra cập nhật ở thanh trên.")
    bullet("Nếu có bản mới, chọn Mở trang tải bộ cài mới.")
    callout(
        "An toàn",
        "Thông tin hỗ trợ và Recovery không lưu API Key hoặc WordPress Password.",
        PALE_GREEN,
        GREEN,
    )

    # 7
    page("6. Keyword Intelligence - Import Semrush")
    h2("6.1 File hỗ trợ")
    table(
        ["Định dạng", "Cột nên có"],
        [
            ["CSV/TSV", "Keyword, Volume, KD %, Intent, CPC, URL, Position"],
            ["XLSX/XLSM", "Các cột tương tự; có thể dùng tên tiếng Việt phổ biến"],
        ],
        [38 * mm, 132 * mm],
    )
    for number, title, text in (
        (1, "Chọn Import Semrush", "Chọn file đã export."),
        (2, "Kiểm tra số lượng", "Tool loại trùng và chuẩn hóa Volume/KD."),
        (3, "Kiểm tra Intent", "Sửa tay nếu ngữ cảnh kinh doanh khác gợi ý."),
        (4, "Map Landing Page", "Gắn URL đích trước khi lập Content Plan."),
    ):
        step(number, title, text)
    callout("Không bắt buộc Semrush", "Bạn có thể thêm keyword thủ công.")

    # 8
    page("7. Search Intent, Cluster và Landing Page")
    table(
        ["Intent", "Ý nghĩa", "Định dạng phù hợp"],
        [
            ["Informational", "Tìm thông tin", "Bài hướng dẫn"],
            ["Commercial", "So sánh trước khi mua", "Review/so sánh"],
            ["Transactional", "Muốn hành động", "Landing Page"],
            ["Navigational", "Tìm thương hiệu/trang", "Trang thương hiệu"],
        ],
        [35 * mm, 62 * mm, 73 * mm],
    )
    h2("Ba mức Cluster")
    bullet("<b>Broad:</b> nhóm rộng, phù hợp lên chiến lược chủ đề.")
    bullet("<b>Balanced:</b> cân bằng, nên dùng mặc định.")
    bullet("<b>Tight:</b> nhóm sát, phù hợp lập brief chi tiết.")
    callout(
        "Tránh Cannibalization",
        "Một keyword không nên được map vào nhiều Landing Page cùng mục tiêu.",
        PALE_AMBER,
        AMBER,
    )

    # 9
    page("8. Content Workflow và Content Brief")
    for number, title, text in (
        (1, "Tạo Brief từ Cluster", "Tool chọn Primary Keyword theo Volume và KD."),
        (2, "Kiểm tra Secondary Keywords", "Loại từ không cùng Search Intent."),
        (3, "Kiểm tra Title/Heading", "Chỉnh theo sản phẩm, khách hàng và lợi thế thật."),
        (4, "Đưa sang Top 5", "Phân tích đối thủ cho Primary Keyword."),
        (5, "Đưa sang Outline", "Dùng cấu trúc brief làm bản nháp."),
        (6, "Mapping Landing Page", "Gắn URL xuất bản hoặc URL cần tối ưu."),
        (7, "Recheck", "Kiểm tra Landing Page sau khi xuất bản/sửa."),
    ):
        step(number, title, text)
    callout(
        "Chuỗi hoàn chỉnh",
        "Keyword → Intent → Cluster → Landing Page → Brief → Top 5 → Outline → WordPress → Recheck.",
        PALE_GREEN,
        GREEN,
    )

    # 10
    page("9. Top 5 Google Direct và URL thủ công")
    h2("9.1 Chạy trực tiếp")
    bullet("Nhập keyword, quốc gia, ngôn ngữ rồi nhấn Phân tích Top 5.")
    bullet("Tool thử đọc kết quả, câu hỏi liên quan và AI Overview nếu HTML có sẵn.")
    h2("9.2 Khi Google trả CAPTCHA hoặc Consent")
    for number, title, text in (
        (1, "Nhấn Mở Google", "Tool mở đúng keyword và locale trong trình duyệt."),
        (2, "Sao chép 5 URL", "Chỉ lấy kết quả tự nhiên, không lấy quảng cáo."),
        (3, "Nhấn Dán URL từ clipboard", "Tool tự lọc URL trùng và giới hạn 5."),
        (4, "Chạy lại", "Tool đọc H1-H3 trực tiếp từ 5 trang."),
    ):
        step(number, title, text)
    callout(
        "Giới hạn",
        "Google Direct là best-effort. URL thủ công là phương án ổn định và không cần SerpApi.",
        PALE_AMBER,
        AMBER,
    )

    # 11
    page("10. Outline, câu hỏi và AI Overview")
    bullet("Cột bên trái hiển thị 5 nguồn và trạng thái đọc heading.")
    bullet("Cột bên phải là outline hợp nhất, câu hỏi và nội dung AI Overview tìm được.")
    bullet("Sao chép dùng để đưa outline sang công cụ viết nội dung.")
    bullet("Xuất TXT tạo file bàn giao cho writer/editor.")
    bullet("Gửi WordPress Draft chỉ chạy khi kết nối WordPress hợp lệ.")
    callout(
        "Nguyên tắc chất lượng",
        "Không sao chép nội dung đối thủ. Hãy dùng cấu trúc để phát hiện khoảng trống, sau đó bổ sung trải nghiệm, dữ liệu gốc và case study.",
        PALE_PURPLE,
        PURPLE,
    )

    # 12
    page("11. Website Audit")
    table(
        ["Nhóm", "Kiểm tra chính"],
        [
            ["HTTP", "Status, Redirect, response time"],
            ["On-page", "Title, Meta, H1, word count, ALT"],
            ["Index", "Canonical, robots meta, indexable"],
            ["Structure", "Depth, inlinks, dead-end, internal links"],
            ["Enhancement", "Schema và Open Graph"],
        ],
        [45 * mm, 125 * mm],
    )
    bullet("Chọn giới hạn URL phù hợp. Website mới nên bắt đầu 100 URL.")
    bullet("Nút Dừng gửi yêu cầu hủy và chờ kết thúc bước an toàn.")
    bullet("Sau Audit, tool tự cập nhật Dashboard, Fix Queue và Link Map.")
    callout("Audit lại", "Luôn Audit lại sau khi sửa để xác thực bằng dữ liệu.")

    # 13
    page("12. Crawl, Index, Sitemap và Internal Link Map")
    table(
        ["Phát hiện", "Ý nghĩa"],
        [
            ["Orphan Page", "Có trong Sitemap nhưng không thấy qua crawl link"],
            ["Dead-end", "Không dẫn tới trang nội bộ khác"],
            ["Depth > 3", "Trang nằm quá sâu"],
            ["Weak Inlinks", "Nhận rất ít internal link"],
            ["Sitemap Coverage", "Tỷ lệ URL sitemap được crawl thấy"],
        ],
        [45 * mm, 125 * mm],
    )
    bullet("Ưu tiên Landing Page quan trọng ở Click Depth thấp.")
    bullet("Xuất CSV Link Map để phân tích nguồn/đích.")
    bullet("Import Index Coverage CSV khi cần phân tích trạng thái loại trừ.")

    # 14
    page("13. Fix Queue chi tiết")
    table(
        ["Trường", "Cách dùng"],
        [
            ["Lỗi gì?", "Tên vấn đề phát hiện"],
            ["URL", "Trang bị ảnh hưởng"],
            ["Vì sao", "Tác động đến crawl/index/UX"],
            ["Cách sửa", "Hành động đề xuất"],
            ["Ưu tiên", "P0, P1 hoặc P2"],
            ["Độ khó", "Dễ, Trung bình hoặc Khó"],
            ["Tác động", "Cao, Trung bình hoặc Thấp"],
            ["Trạng thái", "Cần sửa hoặc Đã sửa"],
        ],
        [38 * mm, 132 * mm],
    )
    callout(
        "P0 trước",
        "Xử lý lỗi chặn crawl/index, HTTP nghiêm trọng và cấu hình sai trước nội dung/thẩm mỹ.",
        PALE_AMBER,
        AMBER,
    )

    # 15
    page("14. PageSpeed và CrUX")
    table(
        ["Nguồn", "Loại dữ liệu", "Cách hiểu"],
        [
            ["Lighthouse", "Lab Data", "Mô phỏng một lần chạy trên thiết bị/mạng chuẩn"],
            ["CrUX", "Field Data", "Trải nghiệm người dùng thật, p75 trong kỳ thu thập"],
        ],
        [38 * mm, 42 * mm, 90 * mm],
    )
    bullet("Đọc LCP, INP, CLS và TTFB theo từng nguồn; không trộn Lab và Field.")
    bullet("PageSpeed có thể chạy không key, nhưng key phù hợp cho chạy thường xuyên.")
    bullet("CrUX cần Google API Key và URL phải đủ dữ liệu người dùng thật.")
    callout(
        "Nguồn chính thức",
        "PageSpeed API: developers.google.com/speed/docs/insights/v5/get-started<br/>"
        "CrUX API: developer.chrome.com/docs/crux/api",
        PALE_GREEN,
        GREEN,
    )

    # 16
    page("15. Google Search Console")
    for number, title, text in (
        (1, "Tạo Service Account", "Bật Search Console API trong Google Cloud."),
        (2, "Thêm quyền GSC", "Cấp quyền đọc cho email Service Account."),
        (3, "Chọn JSON", "Chọn file trong API & Kết nối."),
        (4, "Nhập Property", "sc-domain:example.com hoặc URL-prefix có dấu / cuối."),
        (5, "Lấy 90 ngày", "Tool tải Query, Page, Click, Impression, CTR và Position."),
        (6, "URL Inspection", "Kiểm tra trạng thái phiên bản đang nằm trong Google Index."),
    ):
        step(number, title, text)
    callout(
        "Quan trọng",
        "URL Inspection API không phải Live Test. Kết quả là trạng thái của phiên bản trong chỉ mục Google.",
        PALE_AMBER,
        AMBER,
    )

    # 17
    page("16. Server Log Analyzer và Crawl Budget")
    table(
        ["Chỉ số", "Cách sử dụng"],
        [
            ["Googlebot hits", "Tổng lượt crawl xác định từ User-Agent"],
            ["Smartphone/Desktop", "So sánh thiết bị crawler"],
            ["Waste URL", "Parameter, asset, redirect hoặc lỗi bị crawl nhiều"],
            ["Low Crawl", "Trang quan trọng crawl 0-1 lần"],
            ["Crawl Efficiency", "Tỷ lệ crawl tạo giá trị"],
        ],
        [45 * mm, 125 * mm],
    )
    bullet("Import access log từ server/CDN; không dùng error log.")
    bullet("Đối chiếu IP khi cần xác minh Googlebot thật.")
    bullet("Ưu tiên xử lý vòng lặp URL, parameter và lỗi 3xx/4xx/5xx.")

    # 18
    page("17. Growth Pro: Backlink, Rank, Decay và đối thủ")
    table(
        ["Module", "Đầu vào", "Đầu ra"],
        [
            ["Backlink", "CSV Ahrefs/Semrush", "Risk, domain, anchor, authority"],
            ["Rank Tracking", "Keyword + Landing Page", "Vị trí và lịch sử"],
            ["Content Decay", "GSC/CSV", "Trang giảm click/visibility"],
            ["Content Gap", "Trang mình + Top 5", "Chủ đề còn thiếu"],
            ["Đối thủ", "Danh sách domain", "Rank và Share of Voice"],
        ],
        [38 * mm, 55 * mm, 77 * mm],
    )
    callout(
        "Dữ liệu đúng",
        "Rank Direct có thể bị Google giới hạn tương tự Top 5. Với dự án lớn, nên dùng nguồn dữ liệu chuyên dụng.",
    )

    # 19
    page("18. WordPress - kết nối an toàn")
    for number, title, text in (
        (1, "Mở wp-admin", "Đăng nhập tài khoản có quyền sửa bài."),
        (2, "Users → Profile", "Tìm Application Passwords."),
        (3, "Tạo mật khẩu", "Đặt tên SEO AI Studio rồi sao chép mật khẩu một lần."),
        (4, "Nhập vào tool", "Website, Username và Application Password."),
        (5, "Kiểm tra WordPress", "Chỉ tiếp tục khi trạng thái OK."),
        (6, "Lưu bí mật an toàn", "Lưu trong Windows Credential Manager."),
    ):
        step(number, title, text)
    callout(
        "Không dùng mật khẩu đăng nhập chính",
        "Dùng Application Password riêng để có thể thu hồi mà không đổi mật khẩu tài khoản.",
        PALE_AMBER,
        AMBER,
    )

    # 20
    page("19. WordPress Draft, Preview và Rollback")
    bullet("Gửi WordPress Draft tạo bài ở trạng thái nháp, không xuất bản tự động.")
    bullet("Preview tải title, content, status và danh sách revision.")
    bullet("Rollback khôi phục một revision; tool luôn yêu cầu xác nhận.")
    bullet("Sau khi xuất bản, dùng Kiểm tra Landing Page trong Content Workflow.")
    bullet("Audit lại để kiểm tra canonical, indexable, schema và internal link.")
    callout(
        "Quy trình an toàn",
        "Draft → người phụ trách duyệt → Publish → Recheck → Audit lại → theo dõi GSC.",
        PALE_GREEN,
        GREEN,
    )

    # 21
    page("20. Automation và cảnh báo")
    table(
        ["Tùy chọn", "Ý nghĩa"],
        [
            ["Tần suất", "Daily hoặc Weekly"],
            ["Giờ chạy", "HH:MM theo Windows"],
            ["Max pages", "Giới hạn URL mỗi lần"],
            ["Cảnh báo mới", "So sánh snapshot để phát hiện regression"],
        ],
        [42 * mm, 128 * mm],
    )
    bullet("Scheduled Audit dùng Windows Task Scheduler.")
    bullet("Máy cần bật và tài khoản phải có quyền chạy task.")
    bullet("Kiểm tra log scheduled khi không thấy báo cáo mới.")
    bullet("Xóa lịch không xóa dữ liệu dự án.")

    # 22
    page("21. Báo cáo PDF, Excel và Roadmap 30/60/90")
    table(
        ["Báo cáo", "Đối tượng"],
        [
            ["PDF 30/60/90", "Chủ doanh nghiệp, quản lý, khách hàng"],
            ["Excel đầy đủ", "SEOer, developer, content team"],
            ["Keyword Excel", "Content planner/writer"],
            ["CSV Fix Queue", "Theo dõi công việc và phân công"],
        ],
        [50 * mm, 120 * mm],
    )
    bullet("30 ngày: sửa Technical P0/P1 và đo baseline.")
    bullet("60 ngày: cluster, content, internal link và landing page.")
    bullet("90 ngày: authority, tối ưu chuyển đổi và mở rộng chủ đề.")

    # 23
    page("22. SEO 150 Checklist")
    bullet("Checklist bao phủ Technical, Content, Link, Local, Ecommerce, Data và AI Search.")
    bullet("Lọc theo nhóm hoặc phương pháp kiểm tra.")
    bullet("Trạng thái: Chưa kiểm tra, Đang làm, Hoàn thành.")
    bullet("Evidence lưu bằng chứng ngắn từ Audit/API/import.")
    bullet("Checklist không thay thế dữ liệu; dùng cùng Fix Queue và Roadmap.")
    callout(
        "Quy tắc",
        "Chỉ đánh dấu Hoàn thành khi có bằng chứng hoặc đã Audit lại.",
        PALE_AMBER,
        AMBER,
    )

    # 24
    page("23. Trung tâm kết nối và bảo mật")
    table(
        ["Kết nối", "Kiểm tra"],
        [
            ["Google Direct", "Số kết quả đọc được hoặc lỗi Consent/CAPTCHA"],
            ["PageSpeed/CrUX", "HTTP, quota và API Key"],
            ["Search Console", "File JSON, quyền và property"],
            ["WordPress", "URL, username, Application Password"],
        ],
        [48 * mm, 122 * mm],
    )
    bullet("Nhấn Kiểm tra tất cả kết nối trước Full Audit đầu tiên.")
    bullet("API Key và Password không được ghi vào project, snapshot hay report.")
    bullet("Dùng Windows Credential Manager để lưu bí mật theo từng dự án.")

    # 25
    page("24. Thông báo lỗi, tiến trình và thông tin hỗ trợ")
    table(
        ["Phần", "Ý nghĩa"],
        [
            ["Nguyên nhân", "Tool giải thích lỗi người dùng có thể hiểu"],
            ["Cách xử lý", "Hành động tiếp theo cụ thể"],
            ["Thử lại", "Chạy lại thao tác gần nhất"],
            ["Sao chép thông tin", "Gửi version, OS, thao tác và lỗi cho hỗ trợ"],
            ["Hủy", "Dừng ở bước an toàn gần nhất"],
            ["Thời gian", "Theo dõi thao tác đã chạy bao lâu"],
        ],
        [45 * mm, 125 * mm],
    )
    callout(
        "Không gửi bí mật",
        "Thông tin hỗ trợ không chứa API Key hoặc Password. Không chụp màn hình khi ô mật khẩu đang bật Hiện.",
        PALE_AMBER,
        AMBER,
    )

    # 26
    page("25. Full SEO Audit - quy trình một nút")
    for number, title, text in (
        (1, "Crawl website", "Thu thập HTTP, on-page, indexability và cấu trúc."),
        (2, "Technical SEO", "Tạo lỗi và ưu tiên P0/P1/P2."),
        (3, "Link Map & Sitemap", "Orphan, dead-end, depth và coverage."),
        (4, "Lighthouse & CrUX", "Tách Lab Data và Field Data."),
        (5, "Search Console", "Tự lấy 90 ngày nếu đã kết nối."),
        (6, "Fix Queue", "Bổ sung vì sao, cách sửa, độ khó và tác động."),
        (7, "Roadmap", "Tạo kế hoạch 30/60/90 và so sánh snapshot."),
    ):
        step(number, title, text)
    callout(
        "Bước bị bỏ qua",
        "Nếu GSC/CrUX chưa kết nối, Full Audit vẫn hoàn tất và ghi rõ phần đã bỏ qua.",
    )

    # 27
    page("26. Checklist vận hành hằng ngày, tuần và tháng")
    table(
        ["Chu kỳ", "Việc cần làm"],
        [
            ["Hằng ngày", "Xử lý cảnh báo P0, kiểm tra website và bài vừa xuất bản"],
            ["Hằng tuần", "GSC, rank, content brief, internal link và Fix Queue"],
            ["Hằng tháng", "Full Audit, snapshot comparison, backlink và báo cáo"],
            ["30 ngày", "Technical baseline và P0/P1"],
            ["60 ngày", "Content cluster, landing page và decay"],
            ["90 ngày", "Authority, CRO, Share of Voice và mở rộng roadmap"],
        ],
        [35 * mm, 135 * mm],
    )
    callout(
        "Thước đo chính",
        "Organic Traffic, Qualified Leads, Revenue, Index Coverage, CWV, Share of Voice và số lỗi được xác thực đã sửa.",
        PALE_GREEN,
        GREEN,
    )

    # 28
    page("27. Xử lý lỗi thường gặp và nguồn tham khảo")
    table(
        ["Lỗi", "Cách xử lý nhanh"],
        [
            ["Top 5 không đọc được", "Mở Google → sao chép 5 URL → Dán clipboard"],
            ["PageSpeed 429", "Chờ quota hoặc nhập API Key"],
            ["CrUX không có dữ liệu", "URL chưa đủ traffic; dùng Lighthouse"],
            ["GSC 403", "Kiểm tra quyền Service Account/property"],
            ["WordPress 401/403", "Tạo lại Application Password và kiểm tra quyền"],
            ["Scheduled Audit không chạy", "Kiểm tra Task Scheduler và log"],
        ],
        [55 * mm, 115 * mm],
    )
    h2("Nguồn chính thức")
    bullet("Search Console URL Inspection: developers.google.com/webmaster-tools/v1/urlInspection.index/inspect")
    bullet("PageSpeed Insights API: developers.google.com/speed/docs/insights/v5/get-started")
    bullet("CrUX API: developer.chrome.com/docs/crux/api")
    bullet("WordPress REST Authentication: developer.wordpress.org/rest-api/using-the-rest-api/authentication/")
    callout(
        "Khi cần hỗ trợ",
        "Mở hộp lỗi → Sao chép thông tin hỗ trợ → gửi kèm ảnh màn hình và mô tả bước đã làm.",
        PALE_PURPLE,
        PURPLE,
    )

    doc.build(story)
    return path


if __name__ == "__main__":
    result = generate()
    print(result)
