import csv
import json
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from seo_v4_checks import build_master_checks, checks_to_rows
from seo_v4_core import (
    VERSION,
    PageResult,
    PageSpeedClient,
    ProjectStore,
    SerpResearcher,
    ServerLogAnalyzer,
    SiteAuditor,
    WordPressClient,
    audit_summary,
    build_fix_queue,
    clean_text,
    compare_snapshots,
    export_csv,
    import_performance_csv,
    normalize_url,
)


def resource_path(path):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), path)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"SEO AI Studio V{VERSION}")
        try:
            self.iconbitmap(resource_path("assets/seo_ai_studio_icon.ico"))
        except tk.TclError:
            pass
        self.geometry("1440x900")
        self.minsize(1100, 700)

        self.store = ProjectStore()
        self.current_project = None
        self.pages = []
        self.site_files = {}
        self.fix_items = []
        self.keyword_rows = []
        self.serp_result = None
        self.log_report = None
        self.performance_rows = []
        self.index_rows = []
        self.master_checks = build_master_checks()
        self.events = queue.Queue()
        self.stop_event = threading.Event()

        self.status = tk.StringVar(value="Sẵn sàng.")
        self.progress = tk.DoubleVar(value=0)
        self.website = tk.StringVar()
        self.max_pages = tk.IntVar(value=100)
        self.serp_key = tk.StringVar()
        self.pagespeed_key = tk.StringVar()
        self.wp_site = tk.StringVar()
        self.wp_user = tk.StringVar()
        self.wp_password = tk.StringVar()
        self.country = tk.StringVar(value="vn")
        self.language = tk.StringVar(value="vi")

        self._style()
        self._header()
        self._tabs()
        self._footer()
        self._refresh_projects()
        self._render_master_checks()
        self.after(100, self._poll_events)

    def _style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Head.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 25, "bold"))
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 12))
        frame.pack(fill="x")
        ttk.Label(frame, text="SEO AI Studio V4", style="Title.TLabel").pack(side="left")
        ttk.Label(
            frame,
            text="Complete SEO Workflow • Top 5 + AI Overview • 150-Point System",
            foreground="#1769c2",
        ).pack(side="left", padx=16)
        self.project_badge = ttk.Label(frame, text="Chưa chọn dự án")
        self.project_badge.pack(side="right")

    def _tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._dashboard_tab()
        self._projects_tab()
        self._audit_tab()
        self._crawl_index_tab()
        self._keyword_tab()
        self._serp_writer_tab()
        self._fix_queue_tab()
        self._performance_tab()
        self._master_tab()
        self._integrations_tab()

    def _tab(self, title):
        frame = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(frame, text=title)
        return frame

    def _footer(self):
        frame = ttk.Frame(self, padding=(12, 6))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status).pack(side="left")
        ttk.Progressbar(frame, variable=self.progress, maximum=100, length=250).pack(
            side="right", padx=(8, 0)
        )
        ttk.Label(frame, text=f"V{VERSION}").pack(side="right")

    def _dashboard_tab(self):
        frame = self._tab("Dashboard")
        ttk.Label(frame, text="Tổng quan dự án SEO", style="Head.TLabel").pack(anchor="w")
        cards = ttk.Frame(frame)
        cards.pack(fill="x", pady=14)
        self.metric_score = self._metric(cards, "--/100", "SEO Score")
        self.metric_pages = self._metric(cards, "0", "Trang đã quét")
        self.metric_p0 = self._metric(cards, "0", "Việc P0")
        self.metric_done = self._metric(cards, "0/150", "Master Checklist")
        self.dashboard_text = tk.Text(
            frame, wrap="word", font=("Segoe UI", 10), relief="flat"
        )
        self.dashboard_text.pack(fill="both", expand=True)
        self._set_text(
            self.dashboard_text,
            "1. Tạo/chọn dự án.\n"
            "2. Chạy Website Audit.\n"
            "3. Import server log và dữ liệu GSC/GA4.\n"
            "4. Tạo Keyword Map, SERP Research và xử lý Fix Queue.\n"
            "5. Audit lại để xác thực lỗi đã được sửa.",
        )

    def _metric(self, parent, value, label):
        card = ttk.LabelFrame(parent, text=label, padding=14)
        card.pack(side="left", fill="x", expand=True, padx=(0, 10))
        widget = ttk.Label(card, text=value, style="Metric.TLabel")
        widget.pack(anchor="center")
        return widget

    def _projects_tab(self):
        frame = self._tab("Projects & History")
        top = ttk.Frame(frame)
        top.pack(fill="x")
        self.project_name = tk.StringVar()
        self.project_url = tk.StringVar()
        ttk.Label(top, text="Tên dự án:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.project_name, width=28).grid(
            row=0, column=1, padx=6
        )
        ttk.Label(top, text="Website:").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.project_url, width=48).grid(
            row=0, column=3, padx=6, sticky="ew"
        )
        ttk.Button(
            top, text="Lưu dự án", style="Accent.TButton", command=self._save_project
        ).grid(row=0, column=4, padx=5)
        top.columnconfigure(3, weight=1)

        choose = ttk.Frame(frame)
        choose.pack(fill="x", pady=12)
        ttk.Label(choose, text="Dự án hiện có:").pack(side="left")
        self.project_combo = ttk.Combobox(choose, state="readonly", width=48)
        self.project_combo.pack(side="left", padx=7)
        self.project_combo.bind("<<ComboboxSelected>>", self._select_project)
        ttk.Button(choose, text="Tải dự án", command=self._select_project).pack(
            side="left"
        )
        ttk.Button(
            choose, text="Lưu snapshot hiện tại", command=self._save_snapshot
        ).pack(side="left", padx=7)

        body = ttk.Panedwindow(frame, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text="Lịch sử Audit", padding=8)
        right = ttk.LabelFrame(body, text="Validation: so sánh 2 lần Audit gần nhất", padding=8)
        body.add(left, weight=1)
        body.add(right, weight=2)
        self.history_tree = self._tree(
            left, ("file", "date"), ("Snapshot", "Thời gian"), (430, 160)
        )
        self.validation_text = tk.Text(right, wrap="word", font=("Segoe UI", 10))
        self.validation_text.pack(fill="both", expand=True)
        ttk.Button(
            right, text="So sánh 2 snapshot gần nhất", command=self._compare_latest
        ).pack(anchor="e", pady=(8, 0))

    def _audit_tab(self):
        frame = self._tab("Website Audit")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Label(bar, text="Website:").grid(row=0, column=0)
        ttk.Entry(bar, textvariable=self.website, width=55).grid(
            row=0, column=1, padx=7, sticky="ew"
        )
        ttk.Label(bar, text="Tối đa:").grid(row=0, column=2)
        ttk.Spinbox(bar, from_=1, to=500, textvariable=self.max_pages, width=7).grid(
            row=0, column=3, padx=5
        )
        self.audit_btn = ttk.Button(
            bar, text="Bắt đầu Audit", style="Accent.TButton", command=self._start_audit
        )
        self.audit_btn.grid(row=0, column=4, padx=5)
        self.stop_btn = ttk.Button(
            bar, text="Dừng", state="disabled", command=self.stop_event.set
        )
        self.stop_btn.grid(row=0, column=5, padx=5)
        ttk.Button(bar, text="Xuất CSV", command=self._export_audit).grid(
            row=0, column=6, padx=5
        )
        bar.columnconfigure(1, weight=1)

        columns = (
            "score", "status", "depth", "inlinks", "url", "title", "meta", "h1",
            "words", "alt", "ms", "index", "issues",
        )
        labels = (
            "Điểm", "HTTP", "Depth", "Inlinks", "URL", "Title", "Meta", "H1",
            "Từ", "Thiếu ALT", "ms", "Index", "Lỗi",
        )
        widths = (55, 55, 55, 55, 300, 55, 55, 45, 55, 75, 60, 55, 420)
        self.audit_tree = self._tree(frame, columns, labels, widths)

    def _crawl_index_tab(self):
        frame = self._tab("Crawl & Index")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(
            bar, text="Import Server Log", style="Accent.TButton", command=self._import_log
        ).pack(side="left")
        ttk.Button(bar, text="Import GSC Index CSV", command=self._import_index).pack(
            side="left", padx=7
        )
        ttk.Button(bar, text="Xuất báo cáo", command=self._export_crawl_report).pack(
            side="left"
        )
        ttk.Label(
            bar,
            text="Hỗ trợ Common/Combined Access Log; nhận diện Googlebot theo User-Agent.",
            foreground="#555",
        ).pack(side="right")
        pane = ttk.Panedwindow(frame, orient="vertical")
        pane.pack(fill="both", expand=True, pady=(10, 0))
        summary_box = ttk.LabelFrame(pane, text="Crawl Budget & Index Coverage", padding=8)
        detail_box = ttk.LabelFrame(pane, text="Orphan, Dead-end, Click Depth và URL lãng phí", padding=8)
        pane.add(summary_box, weight=1)
        pane.add(detail_box, weight=2)
        self.crawl_summary = tk.Text(summary_box, wrap="word", height=10)
        self.crawl_summary.pack(fill="both", expand=True)
        self.crawl_tree = self._tree(
            detail_box,
            ("type", "value", "metric", "note"),
            ("Loại", "URL/Trạng thái", "Số liệu", "Ghi chú"),
            (140, 560, 100, 420),
        )

    def _keyword_tab(self):
        frame = self._tab("Keyword Map")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.kw_keyword = tk.StringVar()
        self.kw_url = tk.StringVar()
        self.kw_intent = tk.StringVar(value="Informational")
        self.kw_priority = tk.StringVar(value="P1")
        ttk.Entry(bar, textvariable=self.kw_keyword, width=28).grid(row=0, column=0, padx=3)
        ttk.Entry(bar, textvariable=self.kw_url, width=48).grid(row=0, column=1, padx=3)
        ttk.Combobox(
            bar,
            textvariable=self.kw_intent,
            values=("Informational", "Commercial", "Transactional", "Navigational"),
            width=16,
            state="readonly",
        ).grid(row=0, column=2, padx=3)
        ttk.Combobox(
            bar, textvariable=self.kw_priority, values=("P0", "P1", "P2"), width=5,
            state="readonly",
        ).grid(row=0, column=3, padx=3)
        ttk.Button(bar, text="Thêm", command=self._add_keyword).grid(row=0, column=4, padx=3)
        ttk.Button(bar, text="Import CSV", command=self._import_keywords).grid(
            row=0, column=5, padx=3
        )
        ttk.Button(bar, text="Kiểm tra Rank", command=self._check_ranks).grid(
            row=0, column=6, padx=3
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_keywords).grid(
            row=0, column=7, padx=3
        )
        self.keyword_tree = self._tree(
            frame,
            ("keyword", "url", "intent", "priority", "rank", "status"),
            ("Từ khóa", "Landing Page", "Intent", "Ưu tiên", "Rank", "Trạng thái"),
            (260, 450, 130, 70, 70, 190),
        )

    def _serp_writer_tab(self):
        frame = self._tab("Top 5 + AI Overview")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.serp_keyword = tk.StringVar()
        ttk.Label(bar, text="Keyword:").pack(side="left")
        ttk.Entry(bar, textvariable=self.serp_keyword, width=48).pack(
            side="left", padx=7
        )
        ttk.Label(bar, text="Quốc gia:").pack(side="left")
        ttk.Entry(bar, textvariable=self.country, width=5).pack(side="left", padx=4)
        ttk.Label(bar, text="Ngôn ngữ:").pack(side="left")
        ttk.Entry(bar, textvariable=self.language, width=5).pack(side="left", padx=4)
        self.serp_btn = ttk.Button(
            bar,
            text="Phân tích Top 5 + AI Overview",
            style="Accent.TButton",
            command=self._start_serp_research,
        )
        self.serp_btn.pack(side="left", padx=7)
        ttk.Button(bar, text="Sao chép", command=self._copy_outline).pack(side="left")
        ttk.Button(bar, text="Xuất TXT", command=self._export_outline).pack(
            side="left", padx=5
        )
        ttk.Button(bar, text="Gửi WordPress Draft", command=self._send_wordpress).pack(
            side="left"
        )

        pane = ttk.Panedwindow(frame, orient="horizontal")
        pane.pack(fill="both", expand=True, pady=(10, 0))
        left = ttk.LabelFrame(pane, text="5 nguồn Google", padding=8)
        right = ttk.LabelFrame(pane, text="Outline tổng hợp + AI Overview + 4 ảnh", padding=8)
        pane.add(left, weight=1)
        pane.add(right, weight=2)
        self.serp_sources = self._tree(
            left,
            ("position", "title", "status"),
            ("#", "Tiêu đề", "Crawler"),
            (45, 330, 180),
        )
        self.outline_text = tk.Text(right, wrap="word", font=("Segoe UI", 10))
        self.outline_text.pack(fill="both", expand=True)

    def _fix_queue_tab(self):
        frame = self._tab("Fix Queue")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(bar, text="Đánh dấu Đã sửa", command=self._mark_fix_done).pack(
            side="left"
        )
        ttk.Button(bar, text="Đưa về Cần sửa", command=self._mark_fix_open).pack(
            side="left", padx=7
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_fixes).pack(side="left")
        ttk.Label(
            bar, text="Audit lại để xác thực thay vì chỉ đánh dấu thủ công.",
            foreground="#555",
        ).pack(side="right")
        self.fix_tree = self._tree(
            frame,
            ("priority", "issue", "url", "recommendation", "status"),
            ("Ưu tiên", "Lỗi", "URL", "Cách xử lý", "Trạng thái"),
            (70, 180, 380, 520, 100),
        )

    def _performance_tab(self):
        frame = self._tab("Performance & Data")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.psi_url = tk.StringVar()
        self.psi_strategy = tk.StringVar(value="mobile")
        ttk.Entry(bar, textvariable=self.psi_url, width=52).pack(side="left")
        ttk.Combobox(
            bar, textvariable=self.psi_strategy, values=("mobile", "desktop"),
            width=9, state="readonly",
        ).pack(side="left", padx=6)
        ttk.Button(
            bar, text="Chạy PageSpeed", style="Accent.TButton", command=self._run_pagespeed
        ).pack(side="left")
        ttk.Button(bar, text="Import GSC/GA4 CSV", command=self._import_performance).pack(
            side="left", padx=7
        )
        pane = ttk.Panedwindow(frame, orient="vertical")
        pane.pack(fill="both", expand=True, pady=(10, 0))
        top = ttk.LabelFrame(pane, text="Core Web Vitals & Lighthouse", padding=8)
        bottom = ttk.LabelFrame(pane, text="Dữ liệu GSC/GA4", padding=8)
        pane.add(top, weight=1)
        pane.add(bottom, weight=2)
        self.performance_text = tk.Text(top, wrap="word", height=10)
        self.performance_text.pack(fill="both", expand=True)
        self.performance_tree = self._tree(
            bottom,
            ("col1", "col2", "col3", "col4", "col5"),
            ("Cột 1", "Cột 2", "Cột 3", "Cột 4", "Cột 5"),
            (260, 260, 150, 150, 150),
        )

    def _master_tab(self):
        frame = self._tab("SEO 150 Checklist")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.master_category = tk.StringVar(value="Tất cả")
        self.master_method = tk.StringVar(value="Tất cả")
        categories = ["Tất cả"] + sorted({item.category for item in self.master_checks})
        methods = ["Tất cả"] + sorted({item.method for item in self.master_checks})
        ttk.Combobox(
            bar, textvariable=self.master_category, values=categories, width=28,
            state="readonly",
        ).pack(side="left")
        ttk.Combobox(
            bar, textvariable=self.master_method, values=methods, width=18,
            state="readonly",
        ).pack(side="left", padx=7)
        ttk.Button(bar, text="Lọc", command=self._render_master_checks).pack(side="left")
        ttk.Button(bar, text="Đang làm", command=lambda: self._set_master_status("Đang làm")).pack(
            side="left", padx=(14, 4)
        )
        ttk.Button(bar, text="Hoàn thành", command=lambda: self._set_master_status("Hoàn thành")).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Chưa kiểm tra", command=lambda: self._set_master_status("Chưa kiểm tra")).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_master).pack(side="right")
        self.master_tree = self._tree(
            frame,
            ("id", "category", "priority", "method", "title", "status", "evidence"),
            ("#", "Nhóm", "Ưu tiên", "Nguồn", "Hạng mục", "Trạng thái", "Bằng chứng"),
            (45, 190, 65, 120, 560, 110, 260),
        )

    def _integrations_tab(self):
        frame = self._tab("Integrations")
        ttk.Label(frame, text="API và kết nối", style="Head.TLabel").pack(anchor="w")
        note = (
            "Khóa chỉ giữ trong bộ nhớ của phiên làm việc, không ghi vào project, "
            "snapshot hoặc file export."
        )
        ttk.Label(frame, text=note, foreground="#555").pack(anchor="w", pady=(3, 12))
        form = ttk.Frame(frame)
        form.pack(fill="x")
        self._secret_row(form, 0, "SerpApi Key:", self.serp_key)
        self._secret_row(form, 1, "PageSpeed API Key:", self.pagespeed_key)
        ttk.Separator(frame).pack(fill="x", pady=16)
        wp = ttk.LabelFrame(frame, text="WordPress REST API", padding=12)
        wp.pack(fill="x")
        self._entry_row(wp, 0, "Website:", self.wp_site)
        self._entry_row(wp, 1, "Username:", self.wp_user)
        self._secret_row(wp, 2, "Application Password:", self.wp_password)
        ttk.Button(wp, text="Kiểm tra kết nối", command=self._test_wordpress).grid(
            row=3, column=1, sticky="w", pady=8
        )
        ttk.Label(
            frame,
            text=(
                "Search Console/GA4: V4 hỗ trợ import CSV để không yêu cầu đăng nhập "
                "Google trong ứng dụng. Rank Tracking và AI Overview sử dụng SerpApi."
            ),
            wraplength=1000,
        ).pack(anchor="w", pady=16)

    def _entry_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=5)
        ttk.Entry(parent, textvariable=variable, width=70).grid(
            row=row, column=1, sticky="ew", padx=6, pady=5
        )
        parent.columnconfigure(1, weight=1)

    def _secret_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=5)
        entry = ttk.Entry(parent, textvariable=variable, width=70, show="•")
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        visible = tk.BooleanVar(value=False)

        def toggle():
            entry.configure(show="" if visible.get() else "•")

        ttk.Checkbutton(parent, text="Hiện", variable=visible, command=toggle).grid(
            row=row, column=2, padx=5
        )
        parent.columnconfigure(1, weight=1)

    def _tree(self, parent, columns, labels, widths):
        holder = ttk.Frame(parent)
        holder.pack(fill="both", expand=True, pady=(10, 0))
        tree = ttk.Treeview(holder, columns=columns, show="headings", selectmode="extended")
        for key, label, width in zip(columns, labels, widths):
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=45, anchor="w")
        y = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        x = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        y.pack(side="right", fill="y")
        x.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        return tree

    def _save_project(self):
        try:
            project = self.store.upsert_project(
                self.project_name.get(), self.project_url.get()
            )
        except ValueError as exc:
            messagebox.showwarning("Thiếu thông tin", str(exc))
            return
        self.current_project = project
        self.website.set(project["website"])
        self.psi_url.set(project["website"])
        self.project_badge.configure(text=project["name"])
        self._refresh_projects(project["id"])
        self._load_project_state()
        self.status.set("Đã lưu dự án.")

    def _refresh_projects(self, selected_id=None):
        self.projects = self.store.list_projects()
        values = [f"{item['name']} — {item['website']}" for item in self.projects]
        self.project_combo["values"] = values
        if selected_id:
            index = next(
                (i for i, item in enumerate(self.projects) if item["id"] == selected_id),
                None,
            )
            if index is not None:
                self.project_combo.current(index)
        self._refresh_history()

    def _select_project(self, _event=None):
        index = self.project_combo.current()
        if index < 0 or index >= len(getattr(self, "projects", [])):
            return
        self.current_project = self.projects[index]
        self.project_name.set(self.current_project["name"])
        self.project_url.set(self.current_project["website"])
        self.website.set(self.current_project["website"])
        self.psi_url.set(self.current_project["website"])
        self.wp_site.set(self.current_project["website"])
        self.project_badge.configure(text=self.current_project["name"])
        self._load_project_state()
        self._refresh_history()
        self.status.set(f"Đã tải dự án {self.current_project['name']}.")

    def _load_project_state(self):
        if not self.current_project:
            return
        rows = self.store.load_project_state(
            self.current_project["id"], "keyword-map", []
        )
        self.keyword_rows = rows or []
        self._render_keywords()
        saved_checks = self.store.load_project_state(
            self.current_project["id"], "master-checklist", []
        )
        by_id = {int(item["id"]): item for item in (saved_checks or [])}
        for check in self.master_checks:
            if check.id in by_id:
                check.status = by_id[check.id].get("status", check.status)
                check.evidence = by_id[check.id].get("evidence", "")
        self._render_master_checks()

    def _save_state(self):
        if not self.current_project:
            return
        self.store.save_project_state(
            self.current_project["id"], "keyword-map", self.keyword_rows
        )
        self.store.save_project_state(
            self.current_project["id"], "master-checklist", checks_to_rows(self.master_checks)
        )

    def _refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        self._clear_tree(self.history_tree)
        if not self.current_project:
            return
        for path in self.store.list_snapshots(self.current_project["id"]):
            self.history_tree.insert("", "end", values=(path.name, path.stat().st_mtime))

    def _save_snapshot(self):
        if not self.current_project or not self.pages:
            messagebox.showinfo("Chưa có dữ liệu", "Chọn dự án và chạy Audit trước.")
            return
        path = self.store.save_snapshot(
            self.current_project,
            self.pages,
            self.site_files,
            self.keyword_rows,
            self.fix_items,
        )
        self._save_state()
        self._refresh_history()
        self.status.set(f"Đã lưu snapshot {path.name}.")

    def _compare_latest(self):
        if not self.current_project:
            return
        paths = self.store.list_snapshots(self.current_project["id"])
        if len(paths) < 2:
            messagebox.showinfo("Chưa đủ dữ liệu", "Cần ít nhất 2 snapshot.")
            return
        current = self.store.load_snapshot(paths[0])
        previous = self.store.load_snapshot(paths[1])
        result = compare_snapshots(previous, current)
        lines = [
            f"Trước: {paths[1].name}",
            f"Sau: {paths[0].name}",
            "",
            f"ĐÃ SỬA: {len(result['resolved'])}",
            *[f"✓ {url} — {issue}" for url, issue in result["resolved"][:100]],
            "",
            f"LỖI MỚI: {len(result['new'])}",
            *[f"! {url} — {issue}" for url, issue in result["new"][:100]],
            "",
            f"CÒN LẠI: {len(result['remaining'])}",
            *[f"• {url} — {issue}" for url, issue in result["remaining"][:100]],
        ]
        self._set_text(self.validation_text, "\n".join(lines))

    def _start_audit(self):
        url = normalize_url(self.website.get())
        if not url:
            messagebox.showwarning("Thiếu URL", "Nhập website hợp lệ.")
            return
        self.website.set(url)
        self.stop_event = threading.Event()
        self.audit_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._clear_tree(self.audit_tree)
        self.progress.set(0)
        threading.Thread(
            target=self._audit_worker,
            args=(url, max(1, min(500, int(self.max_pages.get())))),
            daemon=True,
        ).start()

    def _audit_worker(self, url, limit):
        try:
            auditor = SiteAuditor()
            pages = auditor.crawl(
                url,
                limit,
                callback=lambda current, count, total: self.events.put(
                    ("audit-progress", current, count, total)
                ),
                stop=self.stop_event,
            )
            files = auditor.site_files(url)
            self.events.put(
                (
                    "audit-done",
                    pages,
                    files,
                    getattr(auditor, "last_orphans", []),
                )
            )
        except Exception as exc:
            self.events.put(("error", "Audit thất bại", str(exc)))

    def _finish_audit(self, pages, files, orphans):
        self.pages = pages
        self.site_files = files
        self.potential_orphans = orphans
        for page in pages:
            self.audit_tree.insert(
                "",
                "end",
                values=(
                    page.score, page.status, page.depth, page.inlinks, page.url,
                    page.title_len, page.meta_len, page.h1_count, page.words,
                    page.missing_alt, page.response_ms, page.indexable,
                    page.issue_text or "Tốt",
                ),
            )
        self.fix_items = build_fix_queue(pages)
        self._render_fixes()
        score, summary = audit_summary(pages, files)
        p0 = sum(item.priority == "P0" and item.status != "Đã sửa" for item in self.fix_items)
        self.metric_score.configure(text=f"{score}/100")
        self.metric_pages.configure(text=str(len(pages)))
        self.metric_p0.configure(text=str(p0))
        self._set_text(
            self.dashboard_text,
            summary
            + "\n\nHÀNH ĐỘNG TIẾP THEO\n"
            + ("- Xử lý toàn bộ P0 trong Fix Queue.\n" if p0 else "- Không còn lỗi P0.\n")
            + f"- Potential Orphan Pages từ sitemap: {len(orphans)}.\n"
            + "- Import server log để đánh giá Crawl Budget.\n"
            + "- Chạy PageSpeed cho landing page quan trọng.\n"
            + "- Audit lại sau khi sửa để chạy Validation.",
        )
        self._render_crawl_structure()
        self._update_master_from_audit()
        if self.current_project:
            self._save_snapshot()
        self.audit_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress.set(100)
        self.status.set(f"Audit hoàn tất: {len(pages)} trang — {score}/100.")

    def _export_audit(self):
        if not self.pages:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy chạy Audit trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="seo-audit-v4.csv",
            filetypes=[("CSV", "*.csv")]
        )
        if path:
            rows = []
            for page in self.pages:
                row = asdict(page)
                row["issues"] = page.issue_text
                rows.append(row)
            export_csv(path, rows)
            self.status.set(f"Đã xuất {path}.")

    def _render_crawl_structure(self):
        self._clear_tree(self.crawl_tree)
        for url in getattr(self, "potential_orphans", []):
            self.crawl_tree.insert(
                "", "end", values=("Potential Orphan", url, "0 inlink", "Có trong sitemap, chưa thấy khi crawl")
            )
        for page in self.pages:
            if page.dead_end:
                self.crawl_tree.insert(
                    "", "end", values=("Dead-end", page.url, page.internal_links, "Không dẫn tới nội dung nội bộ khác")
                )
            if page.depth > 3:
                self.crawl_tree.insert(
                    "", "end", values=("Click Depth", page.url, page.depth, "Nên đưa landing page quan trọng gần homepage hơn")
                )
            if page.inlinks == 0 and page.depth > 0:
                self.crawl_tree.insert(
                    "", "end", values=("Weak Internal Link", page.url, page.inlinks, "Không nhận internal link trong tập crawl")
                )

    def _import_log(self):
        path = filedialog.askopenfilename(
            title="Chọn server access log",
            filetypes=[("Log/Text", "*.log *.txt"), ("Tất cả", "*.*")],
        )
        if not path:
            return
        known = [page.url for page in self.pages]
        try:
            self.log_report = ServerLogAnalyzer().analyze(path, known)
        except Exception as exc:
            messagebox.showerror("Không đọc được log", str(exc))
            return
        report = self.log_report
        lines = [
            f"Tổng dòng log: {report['total_lines']:,}",
            f"Googlebot hits: {report['googlebot_hits']:,}",
            f"Smartphone: {report['by_device'].get('Smartphone', 0):,}",
            f"Desktop: {report['by_device'].get('Desktop', 0):,}",
            f"URL gây lãng phí crawl: {len(report['waste_urls'])}",
            f"Trang quan trọng crawl 0–1 lần: {len(report['low_crawl_urls'])}",
            "",
            report["spoofing_note"],
        ]
        self._set_text(self.crawl_summary, "\n".join(lines))
        for row in report["waste_urls"]:
            self.crawl_tree.insert(
                "", "end", values=("Crawl Waste", row["url"], row["hits"], "Parameter, asset hoặc status không tối ưu")
            )
        for row in report["low_crawl_urls"]:
            self.crawl_tree.insert(
                "", "end", values=("Low Crawl", row["url"], row["hits"], "Trang Audit crawl ít/chưa thấy trong log")
            )
        self._mark_master(1, "Hoàn thành", f"{report['googlebot_hits']} Googlebot hits")
        self._mark_master(2, "Hoàn thành", f"{len(report['waste_urls'])} waste URLs")
        self._mark_master(7, "Hoàn thành", "Đã thống kê URL crawl nhiều")
        self._mark_master(8, "Hoàn thành", f"{len(report['low_crawl_urls'])} low-crawl URLs")
        self._mark_master(9, "Hoàn thành", json.dumps(report["by_device"], ensure_ascii=False))
        self._save_state()

    def _import_index(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            self.index_rows = import_performance_csv(path)
        except Exception as exc:
            messagebox.showerror("Lỗi CSV", str(exc))
            return
        states = {}
        for row in self.index_rows:
            value = next(
                (v for k, v in row.items() if "reason" in k or "trạng thái" in k or "status" in k),
                "Không rõ",
            )
            states[value] = states.get(value, 0) + 1
        indexed = sum(
            count for state, count in states.items() if "indexed" in state.lower() and "not" not in state.lower()
        )
        total = len(self.index_rows)
        coverage = round(indexed / total * 100, 1) if total else 0
        self._set_text(
            self.crawl_summary,
            f"GSC Index Coverage Import\nTổng URL: {total}\nIndexed ước tính: {indexed}\nCoverage: {coverage}%\n\n"
            + "\n".join(f"- {state}: {count}" for state, count in states.items()),
        )
        for state, count in states.items():
            self.crawl_tree.insert(
                "", "end", values=("Index Coverage", state, count, "Dữ liệu import từ GSC")
            )
        self._mark_master(11, "Hoàn thành", f"Coverage {coverage}%")
        for number in (12, 14, 15, 16):
            self._mark_master(number, "Đang làm", "Đã import dữ liệu GSC")
        self._save_state()

    def _export_crawl_report(self):
        if not self.log_report and not self.index_rows:
            messagebox.showinfo("Chưa có dữ liệu", "Import server log hoặc GSC Index CSV trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile="crawl-index-v4.json",
            filetypes=[("JSON", "*.json")]
        )
        if path:
            Path(path).write_text(
                json.dumps(
                    {"server_log": self.log_report, "index_rows": self.index_rows},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )

    def _add_keyword(self):
        keyword = clean_text(self.kw_keyword.get())
        url = normalize_url(self.kw_url.get())
        if not keyword or not url:
            messagebox.showwarning("Thiếu dữ liệu", "Nhập từ khóa và Landing Page.")
            return
        self.keyword_rows.append(
            {
                "keyword": keyword, "url": url, "intent": self.kw_intent.get(),
                "priority": self.kw_priority.get(), "rank": "", "status": "Mapped",
            }
        )
        self.kw_keyword.set("")
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()

    def _detect_cannibalization(self):
        mapping = {}
        for row in self.keyword_rows:
            mapping.setdefault(row["keyword"].lower(), set()).add(row["url"])
        for row in self.keyword_rows:
            row["status"] = (
                "Cannibalization"
                if len(mapping.get(row["keyword"].lower(), set())) > 1
                else "Mapped"
            )

    def _render_keywords(self):
        if not hasattr(self, "keyword_tree"):
            return
        self._clear_tree(self.keyword_tree)
        for row in self.keyword_rows:
            self.keyword_tree.insert(
                "", "end",
                values=tuple(row.get(key, "") for key in ("keyword", "url", "intent", "priority", "rank", "status")),
            )

    def _import_keywords(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        rows = import_performance_csv(path)
        for row in rows:
            keyword = row.get("keyword") or row.get("từ khóa") or row.get("query")
            url = row.get("url") or row.get("landing page") or row.get("page")
            if keyword and normalize_url(url):
                self.keyword_rows.append(
                    {
                        "keyword": keyword, "url": normalize_url(url),
                        "intent": row.get("intent", "Informational"),
                        "priority": row.get("priority", "P1"),
                        "rank": row.get("rank", ""), "status": "Mapped",
                    }
                )
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()

    def _export_keywords(self):
        if not self.keyword_rows:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="keyword-map-v4.csv",
            filetypes=[("CSV", "*.csv")]
        )
        if path:
            export_csv(path, self.keyword_rows)

    def _check_ranks(self):
        if not self.keyword_rows:
            messagebox.showinfo("Chưa có từ khóa", "Thêm Keyword Map trước.")
            return
        if not self.serp_key.get().strip():
            self.tabs.select(self.tabs.index("end") - 1)
            messagebox.showwarning("Thiếu SerpApi Key", "Nhập key trong tab Integrations.")
            return
        threading.Thread(target=self._rank_worker, daemon=True).start()

    def _rank_worker(self):
        try:
            researcher = SerpResearcher(self.serp_key.get())
            for index, row in enumerate(self.keyword_rows):
                result = researcher.rank(
                    row["keyword"], row["url"], self.country.get(), self.language.get()
                )
                row["rank"] = result["position"]
                self.events.put(("status", f"Rank {index + 1}/{len(self.keyword_rows)}"))
            self.events.put(("ranks-done",))
        except Exception as exc:
            self.events.put(("error", "Rank Tracking thất bại", str(exc)))

    def _start_serp_research(self):
        if not self.serp_key.get().strip():
            messagebox.showwarning("Thiếu SerpApi Key", "Nhập SerpApi Key trong Integrations.")
            return
        keyword = clean_text(self.serp_keyword.get())
        if not keyword:
            messagebox.showwarning("Thiếu keyword", "Nhập từ khóa cần phân tích.")
            return
        self.serp_btn.configure(state="disabled")
        self.progress.set(0)
        threading.Thread(
            target=self._serp_worker, args=(keyword,), daemon=True
        ).start()

    def _serp_worker(self, keyword):
        try:
            result = SerpResearcher(self.serp_key.get()).research(
                keyword,
                self.country.get(),
                self.language.get(),
                callback=lambda text, value: self.events.put(("serp-progress", text, value)),
            )
            self.events.put(("serp-done", result))
        except Exception as exc:
            self.events.put(("error", "SERP Research thất bại", str(exc)))

    def _finish_serp(self, result):
        self.serp_result = result
        self._clear_tree(self.serp_sources)
        for source in result.sources:
            self.serp_sources.insert(
                "", "end", values=(source.position, source.title, source.fetch_status)
            )
        self._set_text(self.outline_text, result.outline)
        self.serp_btn.configure(state="normal")
        self.progress.set(100)
        self.status.set(
            f"Đã tổng hợp {len(result.sources)} nguồn, "
            f"{'có' if result.ai_overview else 'không có'} AI Overview và {len(result.images)} ảnh."
        )
        for number in (101, 102, 107, 108, 135, 139):
            self._mark_master(number, "Hoàn thành", f"Keyword: {result.keyword}")
        self._save_state()

    def _copy_outline(self):
        value = self.outline_text.get("1.0", "end").strip()
        if value:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.status.set("Đã sao chép outline.")

    def _export_outline(self):
        value = self.outline_text.get("1.0", "end").strip()
        if not value:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile="content-brief-v4.txt",
            filetypes=[("Text", "*.txt")]
        )
        if path:
            Path(path).write_text(value, encoding="utf-8")

    def _send_wordpress(self):
        content = self.outline_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Chưa có nội dung", "Tạo outline trước.")
            return
        title = self.serp_keyword.get().strip() or "SEO Draft"
        try:
            result = WordPressClient(
                self.wp_site.get(), self.wp_user.get(), self.wp_password.get()
            ).create_draft(title, f"<pre>{content}</pre>")
        except Exception as exc:
            messagebox.showerror("Không gửi được WordPress", str(exc))
            return
        messagebox.showinfo(
            "Đã tạo Draft",
            f"Post ID: {result.get('id')}\n{result.get('link', '')}",
        )

    def _render_fixes(self):
        self._clear_tree(self.fix_tree)
        for index, item in enumerate(self.fix_items):
            self.fix_tree.insert(
                "", "end", iid=str(index),
                values=(item.priority, item.issue, item.url, item.recommendation, item.status),
            )

    def _set_fix_status(self, status):
        for item_id in self.fix_tree.selection():
            index = int(item_id)
            self.fix_items[index].status = status
        self._render_fixes()

    def _mark_fix_done(self):
        self._set_fix_status("Đã sửa")

    def _mark_fix_open(self):
        self._set_fix_status("Cần sửa")

    def _export_fixes(self):
        if not self.fix_items:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="fix-queue-v4.csv",
            filetypes=[("CSV", "*.csv")]
        )
        if path:
            export_csv(path, [asdict(item) for item in self.fix_items])

    def _run_pagespeed(self):
        url = normalize_url(self.psi_url.get() or self.website.get())
        if not url:
            return
        threading.Thread(
            target=self._pagespeed_worker, args=(url, self.psi_strategy.get()), daemon=True
        ).start()

    def _pagespeed_worker(self, url, strategy):
        try:
            result = PageSpeedClient(self.pagespeed_key.get()).analyze(url, strategy)
            self.events.put(("pagespeed-done", result))
        except Exception as exc:
            self.events.put(("error", "PageSpeed thất bại", str(exc)))

    def _finish_pagespeed(self, result):
        lines = [
            f"URL: {result['url']}",
            f"Thiết bị: {result['strategy']}",
            f"Performance: {result['performance']}/100",
            f"SEO: {result['seo']}/100",
            f"Accessibility: {result['accessibility']}/100",
            f"Best Practices: {result['best_practices']}/100",
            "",
            f"LCP: {result['lcp_ms']} ms",
            f"INP (field): {result['inp_ms']} ms",
            f"CLS: {result['cls']}",
            f"TTFB: {result['ttfb_ms']} ms",
            f"FCP: {result['fcp_ms']} ms",
            "",
            "CƠ HỘI TỐI ƯU",
        ]
        lines.extend(
            f"- {item['title']}: {item['display']}" for item in result["opportunities"]
        )
        self._set_text(self.performance_text, "\n".join(lines))
        for number in range(51, 79):
            self._mark_master(number, "Đang làm", f"PageSpeed {result['strategy']}")
        self._mark_master(51, "Hoàn thành", f"Performance {result['performance']}/100")
        self._save_state()

    def _import_performance(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        self.performance_rows = import_performance_csv(path)
        self._clear_tree(self.performance_tree)
        if not self.performance_rows:
            return
        keys = list(self.performance_rows[0].keys())[:5]
        for index, key in enumerate(keys):
            column = f"col{index + 1}"
            self.performance_tree.heading(column, text=key)
        for row in self.performance_rows[:5000]:
            values = [row.get(key, "") for key in keys]
            values += [""] * (5 - len(values))
            self.performance_tree.insert("", "end", values=values)
        for number in (97, 109, 111, 129, 132, 133):
            self._mark_master(number, "Đang làm", f"Imported {Path(path).name}")
        self._save_state()

    def _render_master_checks(self):
        if not hasattr(self, "master_tree"):
            return
        self._clear_tree(self.master_tree)
        category = self.master_category.get()
        method = self.master_method.get()
        for check in self.master_checks:
            if category != "Tất cả" and check.category != category:
                continue
            if method != "Tất cả" and check.method != method:
                continue
            self.master_tree.insert(
                "", "end", iid=str(check.id),
                values=(
                    check.id, check.category, check.priority, check.method,
                    check.title, check.status, check.evidence,
                ),
            )
        done = sum(check.status == "Hoàn thành" for check in self.master_checks)
        self.metric_done.configure(text=f"{done}/150")

    def _set_master_status(self, status):
        for item_id in self.master_tree.selection():
            check = next(item for item in self.master_checks if item.id == int(item_id))
            check.status = status
        self._render_master_checks()
        self._save_state()

    def _mark_master(self, number, status, evidence):
        check = next((item for item in self.master_checks if item.id == number), None)
        if check:
            check.status = status
            check.evidence = clean_text(evidence)[:240]
        self._render_master_checks()

    def _update_master_from_audit(self):
        issue_text = " ".join(page.issue_text for page in self.pages)
        automatic = {
            3: f"{len(getattr(self, 'potential_orphans', []))} potential orphan",
            4: f"{sum(page.dead_end for page in self.pages)} dead-end",
            5: f"{sum(page.depth > 3 for page in self.pages)} URL depth >3",
            6: f"Max depth {max((page.depth for page in self.pages), default=0)}",
            10: "Đã thống kê inlinks",
            17: str(self.site_files.get("robots.txt", {}).get("status", 0)),
            18: "Đã kiểm tra meta robots và X-Robots-Tag",
            19: f"{sum(page.indexable == 'No' for page in self.pages)} noindex",
            21: "Đã rà soát canonical",
            24: f"{sum(not page.canonical for page in self.pages)} thiếu canonical",
            36: f"{sum(page.status >= 400 for page in self.pages)} URL lỗi",
            39: f"{sum(page.status >= 500 or page.status == 0 for page in self.pages)} server errors",
            40: f"{self.site_files.get('sitemap.xml', {}).get('url_count', 0)} sitemap URLs",
            77: f"{sum(page.missing_alt for page in self.pages)} ảnh thiếu ALT",
            80: f"{sum(page.depth > 3 for page in self.pages)} URL sâu",
            87: "Đã crawl internal links",
            91: "Đã đối chiếu internal link/status",
            92: f"{sum(page.schema_count > 0 for page in self.pages)} trang có Schema",
            94: "Đã kiểm tra JSON-LD hiện diện",
            106: "Đã kiểm tra Title, Meta, H1/H2",
            110: f"{sum(page.words < 300 for page in self.pages)} thin pages",
            138: "Đã kiểm tra robots.txt cơ bản",
        }
        for number, evidence in automatic.items():
            self._mark_master(number, "Hoàn thành", evidence)
        if "Noindex" in issue_text:
            self._mark_master(19, "Đang làm", automatic[19])
        self._save_state()

    def _export_master(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="seo-150-checklist-v4.csv",
            filetypes=[("CSV", "*.csv")]
        )
        if path:
            export_csv(path, checks_to_rows(self.master_checks))

    def _test_wordpress(self):
        try:
            name = WordPressClient(
                self.wp_site.get(), self.wp_user.get(), self.wp_password.get()
            ).test()
        except Exception as exc:
            messagebox.showerror("WordPress", str(exc))
            return
        messagebox.showinfo("WordPress", f"Kết nối thành công: {name}")

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "audit-progress":
                    _, current, count, total = event
                    self.status.set("Đang crawl: " + current)
                    self.progress.set(min(95, count / max(1, total) * 100))
                elif kind == "audit-done":
                    self._finish_audit(event[1], event[2], event[3])
                elif kind == "serp-progress":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "serp-done":
                    self._finish_serp(event[1])
                elif kind == "pagespeed-done":
                    self._finish_pagespeed(event[1])
                elif kind == "ranks-done":
                    self._detect_cannibalization()
                    self._render_keywords()
                    self._save_state()
                    self.status.set("Đã kiểm tra thứ hạng.")
                elif kind == "status":
                    self.status.set(event[1])
                elif kind == "error":
                    self.audit_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.serp_btn.configure(state="normal")
                    messagebox.showerror(event[1], event[2])
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    @staticmethod
    def _clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)

    @staticmethod
    def _set_text(widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value)


if __name__ == "__main__":
    App().mainloop()

