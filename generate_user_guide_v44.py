"""Generate the beginner guide bundled with SEO AI Studio V4.4."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
    / "Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf"
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
        (
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ),
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
        pdfmetrics.registerFont(TTFont("GuideFont", normal_path))
        pdfmetrics.registerFont(TTFont("GuideFontBold", bold_path))
        normal_font, bold_font = "GuideFont", "GuideFontBold"

    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=19 * mm,
        bottomMargin=16 * mm,
        title="Hướng dẫn sử dụng SEO AI Studio V4.4 cho người mới",
        author="SEO AI Studio",
        subject="Cài đặt, Semrush Keyword Intelligence và quy trình SEO 30/60/90",
    )
    width, height = A4
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="guide",
    )

    def header_footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.rect(0, height - 11 * mm, width, 11 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(bold_font, 8.5)
        canvas.drawString(
            16 * mm, height - 7.2 * mm, "SEO AI STUDIO V4.4 - HƯỚNG DẪN NGƯỜI MỚI"
        )
        canvas.setFillColor(colors.HexColor(GRAY))
        canvas.setFont(normal_font, 8)
        canvas.drawString(16 * mm, 7 * mm, "Complete SEO Workflow")
        canvas.drawRightString(
            width - 16 * mm, 7 * mm, f"Trang {document.page}"
        )
        canvas.restoreState()

    doc.addPageTemplates(
        [PageTemplate(id="guide", frames=[frame], onPage=header_footer)]
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="GuideTitle",
            fontName=bold_font,
            fontSize=24,
            leading=30,
            textColor=colors.HexColor(NAVY),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GuideSubtitle",
            fontName=normal_font,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor(GRAY),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1x",
            fontName=bold_font,
            fontSize=17,
            leading=22,
            textColor=colors.HexColor(NAVY),
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2x",
            fontName=bold_font,
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor(BLUE),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Bodyx",
            fontName=normal_font,
            fontSize=9,
            leading=13.2,
            textColor=colors.HexColor(NAVY),
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Smallx",
            fontName=normal_font,
            fontSize=7.7,
            leading=10.2,
            textColor=colors.HexColor(NAVY),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Calloutx",
            fontName=normal_font,
            fontSize=8.7,
            leading=12.4,
            textColor=colors.HexColor(NAVY),
            leftIndent=2 * mm,
            rightIndent=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverMetric",
            fontName=bold_font,
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor(BLUE),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverLabel",
            fontName=normal_font,
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor(GRAY),
        )
    )

    body = styles["Bodyx"]
    small = styles["Smallx"]
    story = []

    def h1(text):
        return Paragraph(safe(text), styles["H1x"])

    def h2(text):
        return Paragraph(safe(text), styles["H2x"])

    def p(text):
        return Paragraph(text, body)

    def bullet(text):
        return Paragraph("• " + text, body)

    def step(number, title, text):
        data = [
            [
                Paragraph(
                    str(number),
                    ParagraphStyle(
                        f"Step{number}",
                        parent=styles["CoverMetric"],
                        textColor=colors.white,
                    ),
                ),
                Paragraph(
                    f"<b>{safe(title)}</b><br/>{text}",
                    styles["Calloutx"],
                ),
            ]
        ]
        table = Table(data, colWidths=[13 * mm, doc.width - 13 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(BLUE)),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(PALE_BLUE)),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D8E8")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return KeepTogether([table, Spacer(1, 2.5 * mm)])

    def callout(title, text, color=PALE_AMBER, border=AMBER):
        table = Table(
            [
                [
                    Paragraph(
                        f"<b>{safe(title)}</b><br/>{text}",
                        styles["Calloutx"],
                    )
                ]
            ],
            colWidths=[doc.width],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return KeepTogether([table, Spacer(1, 3 * mm)])

    def data_table(headers, rows, widths=None, font_size=7.7):
        header_style = ParagraphStyle(
            "GuideTableHeader",
            fontName=bold_font,
            fontSize=font_size,
            leading=font_size + 2,
            textColor=colors.white,
        )
        cell_style = ParagraphStyle(
            "GuideTableCell",
            fontName=normal_font,
            fontSize=font_size,
            leading=font_size + 2.5,
            textColor=colors.HexColor(NAVY),
        )
        data = [[Paragraph(safe(value), header_style) for value in headers]]
        for row in rows:
            data.append([Paragraph(safe(value), cell_style) for value in row])
        table = Table(
            data,
            colWidths=widths or [doc.width / len(headers)] * len(headers),
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(LIGHT)]),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5DEE8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    # Page 1 - Cover
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("SEO AI STUDIO V4.4", styles["GuideTitle"]))
    story.append(
        Paragraph(
            "Hướng dẫn sử dụng cho người mới<br/>"
            "<b>Từ file Semrush đến Keyword Cluster, Content Plan và SEO Roadmap</b>",
            styles["GuideSubtitle"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    cards = [
        [
            [
                Paragraph("1 file", styles["CoverMetric"]),
                Paragraph("Cài đặt Windows", styles["CoverLabel"]),
            ],
            [
                Paragraph("0 SerpApi", styles["CoverMetric"]),
                Paragraph("Top 5 Direct", styles["CoverLabel"]),
            ],
            [
                Paragraph("150 mục", styles["CoverMetric"]),
                Paragraph("SEO Checklist", styles["CoverLabel"]),
            ],
        ],
        [
            [
                Paragraph("90 ngày", styles["CoverMetric"]),
                Paragraph("GSC & Decay", styles["CoverLabel"]),
            ],
            [
                Paragraph("30/60/90", styles["CoverMetric"]),
                Paragraph("SEO Roadmap", styles["CoverLabel"]),
            ],
            [
                Paragraph("PDF/Excel", styles["CoverMetric"]),
                Paragraph("Báo cáo", styles["CoverLabel"]),
            ],
        ],
    ]
    card_table = Table(
        cards,
        colWidths=[doc.width / 3] * 3,
        rowHeights=[31 * mm, 31 * mm],
    )
    card_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PALE_BLUE)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D8E8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D8E8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(card_table)
    story.append(Spacer(1, 8 * mm))
    story.append(
        callout(
            "Mục tiêu của tài liệu",
            "Giúp bạn cài phần mềm, tạo dự án, import keyword Semrush, hiểu các "
            "chỉ số, chạy audit và xuất kế hoạch SEO mà không cần biết lập trình.",
            PALE_GREEN,
            GREEN,
        )
    )
    story.append(
        p(
            "<b>Phiên bản:</b> 4.4.0 &nbsp;&nbsp; "
            "<b>Nền tảng:</b> Windows 10/11 64-bit &nbsp;&nbsp; "
            "<b>Ngôn ngữ:</b> Tiếng Việt"
        )
    )
    story.append(PageBreak())

    # Page 2 - Quick start
    story.append(h1("1. Bắt đầu trong 10 phút"))
    story.append(
        p(
            "Quy trình dưới đây là đường đi ngắn nhất để người mới có dữ liệu hữu ích. "
            "Không cần cấu hình tất cả API ngay từ đầu."
        )
    )
    story.append(step(1, "Cài đặt", "Mở <b>SEO_AI_Studio_V44_Setup.exe</b>, chọn Install, sau đó mở ứng dụng từ Desktop hoặc Start Menu."))
    story.append(step(2, "Tạo dự án", "Vào <b>Projects & History</b>, nhập tên dự án và website, rồi bấm <b>Lưu dự án</b>."))
    story.append(step(3, "Audit website", "Vào <b>Website Audit</b>, chọn số URL tối đa và bấm <b>Bắt đầu Audit</b>."))
    story.append(step(4, "Import Semrush", "Vào <b>Keyword Intelligence</b>, bấm <b>Import file Semrush</b> và chọn CSV/TSV/XLSX."))
    story.append(step(5, "Kiểm tra nhóm", "Xem Search Intent, Cluster, Primary Keyword và map Landing Page quan trọng."))
    story.append(step(6, "Tạo nội dung", "Dùng <b>Top 5 Direct</b> và <b>Content Gap</b> để tạo outline/brief cho cluster ưu tiên."))
    story.append(step(7, "Xuất kế hoạch", "Trong Keyword Intelligence xuất Excel; trong Automation xuất báo cáo PDF/Excel 30/60/90."))
    story.append(
        callout(
            "Nguyên tắc an toàn",
            "Tool hỗ trợ phân tích và ưu tiên công việc. Không tự thay đổi website trừ khi "
            "bạn chủ động gửi WordPress Draft hoặc xác nhận Rollback.",
        )
    )
    story.append(PageBreak())

    # Page 3 - Interface map
    story.append(h1("2. Bản đồ giao diện"))
    story.append(
        data_table(
            ["Tab", "Dùng khi nào", "Kết quả chính"],
            [
                ("Dashboard", "Muốn xem điểm SEO và việc P0", "Tổng quan dự án"),
                ("Projects & History", "Quản lý nhiều website", "Snapshot và Validation"),
                ("Website Audit", "Kiểm tra on-page/technical", "Trang lỗi và Fix Queue"),
                ("Crawl & Index", "Có server log hoặc GSC CSV", "Crawl Budget, Index Coverage"),
                ("Keyword Intelligence", "Có danh sách Semrush", "Volume, KD, Intent, Cluster"),
                ("Top 5 Direct", "Nghiên cứu bài viết", "Outline H1-H3 từ 5 nguồn"),
                ("Fix Queue", "Cần biết sửa gì trước", "P0/P1/P2 và hướng xử lý"),
                ("Performance & Data", "Đo Core Web Vitals", "LCP, INP, CLS, TTFB"),
                ("Link Map", "Kiểm tra kiến trúc website", "Orphan, Dead-end, Depth"),
                ("Search Console", "Có Service Account GSC", "Clicks, query, URL Inspection"),
                ("Automation", "Muốn chạy định kỳ/báo cáo", "Schedule, cảnh báo, PDF/Excel"),
                ("Growth Pro", "Theo dõi tăng trưởng", "Backlink, Rank, Decay, Competitor"),
            ],
            [34 * mm, 68 * mm, 76 * mm],
            7.1,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(h2("Cách đọc màu trong Keyword Intelligence"))
    color_rows = [
        [Paragraph("<b>Informational</b><br/>Người dùng muốn tìm hiểu", small)],
        [Paragraph("<b>Commercial</b><br/>Đang so sánh, cân nhắc", small)],
        [Paragraph("<b>Transactional</b><br/>Có xu hướng mua/đăng ký", small)],
        [Paragraph("<b>Navigational</b><br/>Muốn đến thương hiệu/trang cụ thể", small)],
    ]
    color_table = Table(color_rows, colWidths=[doc.width])
    color_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PALE_BLUE)),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor(PALE_AMBER)),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor(PALE_GREEN)),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor(PALE_PURPLE)),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DEE8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DEE8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(color_table)
    story.append(PageBreak())

    # Page 4 - Semrush export/import
    story.append(h1("3. Import keyword từ Semrush"))
    story.append(h2("3.1. Xuất file từ Semrush"))
    story.append(bullet("Trong Semrush, mở báo cáo Keyword Magic Tool hoặc Organic Research."))
    story.append(bullet("Chọn các cột cần dùng rồi bấm Export CSV/XLSX."))
    story.append(
        bullet(
            "Nên có ít nhất: <b>Keyword</b>, <b>Volume</b>, <b>Keyword Difficulty</b>. "
            "Có thêm Intent, CPC, Position và URL càng tốt."
        )
    )
    story.append(h2("3.2. Nhập vào SEO AI Studio"))
    story.append(step(1, "Mở Keyword Intelligence", "Chọn đúng dự án trước khi import để dữ liệu được lưu theo website."))
    story.append(step(2, "Chọn file", "Bấm <b>Import file Semrush</b>; tool tự dò dấu phẩy, chấm phẩy, tab và encoding."))
    story.append(step(3, "Chọn Thay thế hay Gộp", "<b>Yes</b> thay danh sách cũ; <b>No</b> gộp và loại keyword trùng."))
    story.append(step(4, "Đọc kết quả", "Dòng thông báo cho biết cột nào đã nhận diện và số keyword trùng đã loại."))
    story.append(Spacer(1, 2 * mm))
    story.append(
        data_table(
            ["Dữ liệu", "Tên cột thường gặp", "Nếu file không có"],
            [
                ("Keyword", "Keyword, Query, Từ khóa", "Không thể import"),
                ("Volume", "Volume, Search Volume", "Mặc định 0"),
                ("KD", "KD %, Keyword Difficulty", "Mặc định 0"),
                ("Intent", "Intent, Search Intent", "Tool tự phân loại"),
                ("CPC", "CPC, Cost per Click", "Mặc định 0"),
                ("Landing Page", "URL, Ranking URL", "Đánh dấu Chưa map"),
                ("Position", "Position, Rank, Pos.", "Để trống"),
            ],
            [32 * mm, 69 * mm, 77 * mm],
        )
    )
    story.append(
        callout(
            "Lưu ý",
            "Semrush có thể dùng dấu chấm hoặc dấu phẩy cho số. Tool tự chuẩn hóa "
            "1,200; 1.200; 1,2K và 1.2K về giá trị số.",
        )
    )
    story.append(PageBreak())

    # Page 5 - Intent and clustering
    story.append(h1("4. Search Intent và Keyword Cluster"))
    story.append(h2("4.1. Search Intent dùng để làm gì?"))
    story.append(
        data_table(
            ["Intent", "Ví dụ", "Loại trang nên dùng", "CTA phù hợp"],
            [
                ("Informational", "seo là gì", "Blog/guide", "Đọc thêm, tải checklist"),
                ("Commercial", "top công ty seo", "Trang so sánh/review", "Xem bảng so sánh"),
                ("Transactional", "báo giá dịch vụ seo", "Service/Landing Page", "Nhận báo giá"),
                ("Navigational", "semrush login", "Trang thương hiệu/hỗ trợ", "Đăng nhập/truy cập"),
            ],
            [31 * mm, 42 * mm, 55 * mm, 50 * mm],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(h2("4.2. Ba mức phân nhóm"))
    story.append(
        data_table(
            ["Mức", "Cách gom", "Nên dùng khi"],
            [
                ("Broad", "Nhóm rộng theo chủ đề chính", "Lập chiến lược tổng thể"),
                ("Balanced", "Hai tín hiệu chủ đề, mặc định", "Content Plan thông thường"),
                ("Tight", "Nhóm hẹp, chi tiết hơn", "Website lớn/nhiều keyword gần nhau"),
            ],
            [30 * mm, 73 * mm, 75 * mm],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(h2("4.3. Cách duyệt kết quả tự động"))
    story.append(step(1, "Sắp xếp theo Total Volume", "Cluster có nhu cầu lớn thường được xem trước, nhưng vẫn phải xét Business Impact."))
    story.append(step(2, "Chọn Primary Keyword", "Ưu tiên keyword volume cao, KD phù hợp và thể hiện đúng mục tiêu trang."))
    story.append(step(3, "Sửa Intent/Cluster nếu cần", "Double-click keyword hoặc bấm <b>Sửa dòng chọn</b>."))
    story.append(step(4, "Map Landing Page", "Mỗi cluster nên có một trang chính; tránh nhiều trang cùng cạnh tranh một intent."))
    story.append(
        callout(
            "Không dùng tự động một cách máy móc",
            "Intent và Cluster là gợi ý từ ngôn ngữ keyword. Hãy kiểm tra Google Top 5 "
            "đối với cluster quan trọng trước khi chốt loại trang.",
            PALE_PURPLE,
            PURPLE,
        )
    )
    story.append(PageBreak())

    # Page 6 - Keyword workflow
    story.append(h1("5. Từ Cluster đến Content Plan"))
    story.append(
        p(
            "Sau khi import, hãy xử lý theo thứ tự dưới đây để biến danh sách keyword "
            "thành kế hoạch có thể giao cho content/SEO."
        )
    )
    story.append(step(1, "Lọc cơ hội", "Lọc Volume tối thiểu, Intent và Cluster. Bắt đầu với P0 có volume tốt, KD trong khả năng website."))
    story.append(step(2, "Map Landing Page", "Cluster Transactional map vào trang dịch vụ/sản phẩm; Informational map vào blog hoặc hub page."))
    story.append(step(3, "Kiểm tra Cannibalization", "Nếu một keyword có nhiều URL, trạng thái sẽ cảnh báo để gộp, canonical hoặc phân tách intent."))
    story.append(step(4, "Phân tích Top 5 Direct", "Nhập Primary Keyword. Nếu Google CAPTCHA, dán 5 URL thủ công, mỗi dòng một URL."))
    story.append(step(5, "Chạy Content Gap", "So sánh heading trang của bạn với Top 5 để tìm chủ đề còn thiếu."))
    story.append(step(6, "Tạo Content Brief", "Dùng outline tổng hợp làm khung, viết nội dung nguyên bản và thêm dữ liệu/kinh nghiệm thực tế."))
    story.append(step(7, "Internal Link", "Liên kết bài hỗ trợ về trang hub/landing page bằng anchor mô tả, không nhồi exact match."))
    story.append(
        callout(
            "Mẫu quyết định nhanh",
            "<b>Volume cao + KD vừa + Transactional:</b> ưu tiên Landing Page.<br/>"
            "<b>Volume cao + Informational:</b> tạo Hub/Guide.<br/>"
            "<b>Volume thấp nhưng giá trị đơn hàng cao:</b> vẫn có thể là P0 theo Business Impact.",
            PALE_GREEN,
            GREEN,
        )
    )
    story.append(PageBreak())

    # Page 7 - Technical SEO
    story.append(h1("6. Quy trình Technical SEO"))
    story.append(h2("6.1. Website Audit"))
    story.append(
        p(
            "Audit kiểm tra HTTP, Title, Meta, H1/H2, Canonical, Robots, độ dài nội dung, "
            "ALT, Internal Link, Schema, Open Graph và thời gian phản hồi. Fix Queue tự "
            "chuyển lỗi thành P0/P1/P2."
        )
    )
    story.append(
        data_table(
            ["Ưu tiên", "Xử lý trước", "Ví dụ"],
            [
                ("P0", "Lỗi chặn index/truy cập", "HTTP 5xx, Noindex nhầm, thiếu Title/H1"),
                ("P1", "Tối ưu chất lượng/cấu trúc", "Meta, Canonical, Thin Content, Depth"),
                ("P2", "Hoàn thiện trình bày", "ALT, Open Graph, Schema bổ sung"),
            ],
            [28 * mm, 76 * mm, 74 * mm],
        )
    )
    story.append(h2("6.2. Link Map và Sitemap"))
    story.append(bullet("<b>Orphan:</b> có trong sitemap nhưng crawler không tìm thấy từ internal link."))
    story.append(bullet("<b>Dead-end:</b> trang không dẫn đến nội dung nội bộ khác."))
    story.append(bullet("<b>Depth &gt; 3:</b> trang quá sâu, cần đưa gần homepage/hub hơn nếu quan trọng."))
    story.append(bullet("<b>Weak inlinks:</b> trang chỉ nhận 0-1 internal link trong tập crawl."))
    story.append(h2("6.3. PageSpeed và Search Console"))
    story.append(
        data_table(
            ["Nguồn", "Dữ liệu", "Khi nào chạy"],
            [
                ("PageSpeed", "LCP, INP, CLS, TTFB, cơ hội tối ưu", "Landing Page chính"),
                ("GSC 90 ngày", "Clicks, impressions, query, position", "Theo dõi tuần/tháng"),
                ("URL Inspection", "Coverage, robots, canonical, last crawl", "URL quan trọng/lỗi index"),
            ],
            [34 * mm, 79 * mm, 65 * mm],
        )
    )
    story.append(PageBreak())

    # Page 8 - Crawl budget
    story.append(h1("7. Server Log và Crawl Budget"))
    story.append(
        p(
            "Server log cho biết Googlebot thực sự đã truy cập URL nào. Đây là dữ liệu khác "
            "với crawler của tool. Hãy export access log từ hosting, CDN hoặc máy chủ."
        )
    )
    story.append(step(1, "Import log", "Vào <b>Crawl & Index</b>, bấm Import Server Log. Hỗ trợ Common/Combined Access Log."))
    story.append(step(2, "Đọc Crawl Efficiency", "Tỷ lệ hit hữu ích so với tổng Googlebot hit. Waste hit gồm URL tham số, asset và HTTP lỗi."))
    story.append(step(3, "So sánh thiết bị", "Xem Googlebot Smartphone/Desktop để phát hiện khác biệt crawl."))
    story.append(step(4, "Xử lý URL lãng phí", "Sửa internal link, redirect, parameter/faceted navigation, sitemap và response lỗi."))
    story.append(step(5, "Tìm trang crawl ít", "Đối chiếu URL Audit với log; ưu tiên trang kinh doanh quan trọng có 0-1 hit."))
    story.append(
        data_table(
            ["Tín hiệu", "Ý nghĩa", "Hành động"],
            [
                ("Waste hits cao", "Googlebot tốn tài nguyên", "Giảm URL tham số/asset/lỗi"),
                ("4xx/5xx cao", "Trải nghiệm crawl kém", "Sửa link và máy chủ"),
                ("Landing Page 0 hit", "Có thể khó tiếp cận", "Tăng internal link, sitemap"),
                ("Desktop khác Mobile", "Cấu hình/HTML có khác biệt", "Kiểm tra mobile rendering"),
            ],
            [40 * mm, 65 * mm, 73 * mm],
        )
    )
    story.append(
        callout(
            "Giới hạn",
            "Tool nhận diện Googlebot theo User-Agent. Với quyết định bảo mật, cần xác minh "
            "reverse DNS ở phía máy chủ.",
        )
    )
    story.append(PageBreak())

    # Page 9 - Growth
    story.append(h1("8. Growth Pro và báo cáo"))
    story.append(
        data_table(
            ["Module", "Đầu vào", "Đầu ra"],
            [
                ("Backlinks", "CSV/TSV Ahrefs/Semrush", "Domain, dofollow, risk, anchor"),
                ("Rank Tracking", "Keyword đã map URL", "Vị trí Top 20 không cần SerpApi"),
                ("Content Decay", "GSC/CSV có Date, Page, Clicks", "So sánh 30 ngày với 30 ngày trước"),
                ("Content Gap", "Keyword + URL trang của bạn", "Heading/chủ đề đối thủ có"),
                ("Competitors", "Domain đối thủ + Keyword Map", "Rank và Share of Voice"),
                ("Roadmap", "Fix, Decay, Backlink, GSC", "Danh sách 30/60/90 ngày"),
            ],
            [39 * mm, 65 * mm, 74 * mm],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(h2("Xuất báo cáo"))
    story.append(bullet("<b>Keyword Intelligence Excel:</b> Tổng quan, Keywords và Clusters."))
    story.append(bullet("<b>Automation PDF:</b> KPI, Fix Queue, Crawl/Sitemap và Roadmap."))
    story.append(bullet("<b>Automation Excel:</b> Audit, Fix Queue, Internal Links, GSC, Decay, Backlinks, Rank, Roadmap và SEO 150."))
    story.append(
        callout(
            "Dành cho báo cáo khách hàng",
            "Trước khi xuất, hãy chọn đúng dự án, chạy Audit mới, cập nhật GSC và đánh dấu "
            "Fix Queue. Báo cáo sẽ phản ánh dữ liệu đang có trong phiên.",
            PALE_BLUE,
            BLUE,
        )
    )
    story.append(h2("Cách đọc Content Decay"))
    story.append(
        data_table(
            ["Trạng thái", "Ngưỡng gợi ý", "Hành động"],
            [
                ("Decay nặng", "Clicks giảm từ 30%", "Audit intent, refresh và internal link"),
                ("Cần làm mới", "Clicks giảm từ 15%", "Cập nhật dữ liệu/heading/FAQ"),
                ("Ổn định", "Biến động nhỏ", "Theo dõi"),
                ("Tăng trưởng", "Clicks tăng trên 15%", "Mở rộng cluster liên quan"),
            ],
            [35 * mm, 58 * mm, 85 * mm],
        )
    )
    story.append(PageBreak())

    # Page 10 - Automation and WordPress
    story.append(h1("9. Scheduled Audit và WordPress"))
    story.append(h2("9.1. Scheduled Audit"))
    story.append(step(1, "Chọn dự án", "Scheduled Audit luôn chạy theo project ID của dự án hiện tại."))
    story.append(step(2, "Chọn DAILY/WEEKLY", "Nhập giờ theo định dạng 24 giờ HH:MM, ví dụ 02:00."))
    story.append(step(3, "Tạo lịch Windows", "Tool tạo Task Scheduler gọi ứng dụng ở chế độ nền."))
    story.append(step(4, "Xem cảnh báo", "Mỗi lần chạy tạo snapshot và lưu danh sách lỗi mới trong tab Automation."))
    story.append(h2("9.2. WordPress Preview và Rollback"))
    story.append(bullet("Dùng WordPress Username + Application Password, không dùng mật khẩu đăng nhập chính."))
    story.append(bullet("Preview tải title, status, modified time, nội dung và danh sách Revision."))
    story.append(bullet("Rollback sẽ cập nhật bài viết về Revision đã chọn hoặc Revision mới nhất."))
    story.append(
        callout(
            "Cảnh báo thao tác thật",
            "Rollback thay đổi nội dung trên WordPress. Luôn đọc Preview, kiểm tra Post ID và "
            "Revision ID. Tool sẽ hỏi xác nhận trước khi gửi yêu cầu.",
            "#FDECEC",
            RED,
        )
    )
    story.append(h2("Cấu hình API tối thiểu"))
    story.append(
        data_table(
            ["Kết nối", "Bắt buộc?", "Ghi chú"],
            [
                ("Top 5 Direct", "Không", "Không cần SerpApi; có fallback URL thủ công"),
                ("PageSpeed key", "Không", "Key giúp quota ổn định hơn"),
                ("GSC JSON", "Có nếu dùng GSC", "Service Account quyền đọc property"),
                ("WordPress", "Có nếu dùng WP", "Application Password"),
            ],
            [42 * mm, 32 * mm, 104 * mm],
        )
    )
    story.append(PageBreak())

    # Page 11 - Troubleshooting
    story.append(h1("10. Xử lý lỗi thường gặp"))
    story.append(
        data_table(
            ["Thông báo", "Nguyên nhân thường gặp", "Cách xử lý"],
            [
                ("Google CAPTCHA", "Google giới hạn request", "Dán 5 URL thủ công, thử lại sau"),
                ("HTTP 401", "Sai/hết hạn xác thực", "Kiểm tra key, JSON, Application Password"),
                ("HTTP 403", "Thiếu quyền/API chưa bật", "Cấp quyền property hoặc bật API"),
                ("HTTP 429", "Vượt quota", "Chờ và giảm số lần chạy"),
                ("Timeout", "Website/API chậm", "Kiểm tra mạng, CDN, chạy ít URL"),
                ("Không thấy Keyword", "Tên cột/file sai", "Export Semrush có cột Keyword"),
                ("Volume/KD bằng 0", "Cột không được nhận diện", "Xem dòng Detected Columns, đổi header"),
                ("Không mở hướng dẫn", "Cài app không qua Setup", "Đặt PDF cạnh EXE hoặc cài lại Setup"),
                ("Scheduled Audit lỗi", "Task Scheduler/đường dẫn", "Tạo lại lịch khi app đã cài"),
                ("WordPress 401/403", "Application Password/quyền", "Tạo lại password, kiểm tra user role"),
            ],
            [40 * mm, 63 * mm, 75 * mm],
            7.2,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(h2("Nút Kiểm tra tất cả kết nối"))
    story.append(
        p(
            "Vào <b>API & Kết nối</b> và bấm <b>Kiểm tra tất cả kết nối</b>. Mỗi dịch vụ "
            "được kiểm tra độc lập, vì vậy một dịch vụ lỗi không làm mất dữ liệu của các "
            "phần khác."
        )
    )
    story.append(
        callout(
            "Khi gửi lỗi cho kỹ thuật",
            "Gửi ảnh toàn bộ thông báo, tên phiên bản V4.4, bước vừa thực hiện, loại file "
            "đã import và một file mẫu đã xóa dữ liệu nhạy cảm.",
            PALE_BLUE,
            BLUE,
        )
    )
    story.append(PageBreak())

    # Page 12 - 30/60/90 and checklist
    story.append(h1("11. Checklist vận hành 30/60/90 ngày"))
    story.append(
        data_table(
            ["Giai đoạn", "Việc chính", "KPI kiểm tra"],
            [
                (
                    "0-30 ngày",
                    "Audit, sửa P0, import Semrush, cluster, map Landing Page, GSC/PageSpeed baseline",
                    "P0 giảm; URL quan trọng index/crawl được",
                ),
                (
                    "31-60 ngày",
                    "Xuất Content Plan, viết/refresh content, internal link, backlink/competitor baseline",
                    "Impressions, keyword Top 20 và coverage tăng",
                ),
                (
                    "61-90 ngày",
                    "Theo dõi rank/decay, tối ưu CTR/CWV, mở rộng cluster thắng, đánh giá ROI",
                    "Clicks, leads/revenue và Share of Voice tăng",
                ),
            ],
            [28 * mm, 90 * mm, 60 * mm],
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(h2("Checklist trước khi kết thúc mỗi phiên"))
    checks = [
        "Đã chọn đúng dự án/website.",
        "Đã lưu snapshot sau Audit.",
        "Keyword mới đã kiểm tra Intent và Cluster.",
        "Cluster ưu tiên đã có Landing Page hoặc Content Brief.",
        "Fix Queue P0 đã có người phụ trách.",
        "GSC/PageSpeed/log được cập nhật theo lịch phù hợp.",
        "Đã xuất file Excel/PDF cần bàn giao.",
        "Không lưu/chia sẻ Service Account JSON và Application Password trong báo cáo.",
    ]
    for item in checks:
        story.append(bullet("☐ " + item))
    story.append(Spacer(1, 4 * mm))
    story.append(
        callout(
            "Quy trình ngắn gọn để nhớ",
            "<b>DATA → CLUSTER → MAP → AUDIT → CONTENT → VALIDATE → REPORT</b><br/>"
            "Dữ liệu tốt và kiểm tra lại sau khi sửa quan trọng hơn việc chạy nhiều tính năng cùng lúc.",
            PALE_GREEN,
            GREEN,
        )
    )
    story.append(
        p(
            "<b>File cài:</b> SEO_AI_Studio_V44_Setup.exe<br/>"
            "<b>Hướng dẫn:</b> Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf<br/>"
            "<b>Mã nguồn:</b> github.com/tommydau1995-afk/SEO-Tool"
        )
    )

    doc.build(story)
    return path


if __name__ == "__main__":
    result = generate()
    print(result)

