"""SEO AI Studio V4.3 Pro desktop application."""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from app_v4 import App as V4App
from seo_v4_checks import checks_to_rows
from seo_v4_core import (
    SiteAuditor,
    clean_text,
    export_csv,
    normalize_url,
)
from seo_v43_core import (
    VERSION,
    AdvancedServerLogAnalyzer,
    BacklinkAnalyzer,
    DirectGoogleResearcher,
    FriendlyError,
    ProjectStoreV43,
    SearchConsoleClient,
    WindowsAuditScheduler,
    WordPressProClient,
    analyze_content_decay,
    analyze_content_gap,
    build_link_map,
    build_roadmap,
    competitor_share_of_voice,
    explain_exception,
    parse_number,
    run_scheduled_audit,
    utc_now,
)
from seo_v43_reports import export_excel, export_pdf, report_payload


class AppV43(V4App):
    def __init__(self):
        self.pro_events = queue.Queue()
        self.internal_graph = {}
        self.sitemap_urls = set()
        self.link_map_report = {}
        self.gsc_rows = []
        self.gsc_sitemaps = []
        self.latest_pagespeed = {}
        self.backlink_rows = []
        self.backlink_summary = {}
        self.decay_rows = []
        self.rank_history = []
        self.competitor_sov = []
        self.roadmap_rows = []
        self.content_gap_report = {}
        self.latest_alerts = {}
        super().__init__()
        self.store = ProjectStoreV43()
        self._refresh_projects()
        self.title(f"SEO AI Studio V{VERSION} Pro")
        self.after(120, self._poll_pro_events)

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 12))
        frame.pack(fill="x")
        ttk.Label(
            frame, text="SEO AI Studio V4.3 Pro", style="Title.TLabel"
        ).pack(side="left")
        ttk.Label(
            frame,
            text="Direct Top 5 • GSC • Crawl Budget • Automation • Growth 30/60/90",
            foreground="#1769c2",
        ).pack(side="left", padx=16)
        self.project_badge = ttk.Label(frame, text="Chưa chọn dự án")
        self.project_badge.pack(side="right")

    def _tabs(self):
        super()._tabs()
        self._link_map_tab()
        self._gsc_tab()
        self._automation_tab()
        self._growth_tab()

    def _footer(self):
        frame = ttk.Frame(self, padding=(12, 6))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status).pack(side="left")
        ttk.Progressbar(
            frame, variable=self.progress, maximum=100, length=250
        ).pack(side="right", padx=(8, 0))
        ttk.Label(frame, text=f"V{VERSION} Pro").pack(side="right")

    def _serp_writer_tab(self):
        frame = self._tab("Top 5 Direct")
        top = ttk.Frame(frame)
        top.pack(fill="x")
        self.serp_keyword = tk.StringVar()
        ttk.Label(top, text="Keyword:").pack(side="left")
        ttk.Entry(top, textvariable=self.serp_keyword, width=44).pack(
            side="left", padx=7
        )
        ttk.Label(top, text="Quốc gia:").pack(side="left")
        ttk.Entry(top, textvariable=self.country, width=5).pack(side="left", padx=4)
        ttk.Label(top, text="Ngôn ngữ:").pack(side="left")
        ttk.Entry(top, textvariable=self.language, width=5).pack(side="left", padx=4)
        self.serp_btn = ttk.Button(
            top,
            text="Phân tích Top 5 không cần API",
            style="Accent.TButton",
            command=self._start_serp_research,
        )
        self.serp_btn.pack(side="left", padx=7)
        ttk.Button(top, text="Sao chép", command=self._copy_outline).pack(side="left")
        ttk.Button(top, text="Xuất TXT", command=self._export_outline).pack(
            side="left", padx=5
        )
        ttk.Button(top, text="Gửi WordPress Draft", command=self._send_wordpress).pack(
            side="left"
        )

        fallback = ttk.LabelFrame(
            frame,
            text="URL thủ công (tùy chọn) - mỗi dòng một URL, tối đa 5",
            padding=6,
        )
        fallback.pack(fill="x", pady=(9, 0))
        self.manual_serp_urls = tk.Text(fallback, height=3, wrap="none")
        self.manual_serp_urls.pack(fill="x")
        ttk.Label(
            fallback,
            text=(
                "Để trống để lấy trực tiếp từ Google. Dùng ô này khi Google yêu cầu "
                "CAPTCHA/consent; không cần SerpApi."
            ),
            foreground="#555",
        ).pack(anchor="w", pady=(4, 0))

        pane = ttk.Panedwindow(frame, orient="horizontal")
        pane.pack(fill="both", expand=True, pady=(10, 0))
        left = ttk.LabelFrame(pane, text="5 nguồn Google", padding=8)
        right = ttk.LabelFrame(
            pane, text="Outline hợp nhất + câu hỏi + ảnh nguồn", padding=8
        )
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

    def _integrations_tab(self):
        frame = self._tab("API & Kết nối")
        ttk.Label(frame, text="Kiểm tra API chủ động", style="Head.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            frame,
            text=(
                "Thông tin xác thực chỉ giữ trong bộ nhớ phiên chạy. Top 5 Direct "
                "không cần API key; PageSpeed vẫn chạy được khi để trống key."
            ),
            foreground="#555",
        ).pack(anchor="w", pady=(3, 10))
        ttk.Button(
            frame,
            text="Kiểm tra tất cả kết nối",
            style="Accent.TButton",
            command=self._test_all_apis,
        ).pack(anchor="w")

        self.gsc_credential_path = tk.StringVar()
        self.gsc_property = tk.StringVar()
        page_speed = ttk.LabelFrame(frame, text="PageSpeed Insights", padding=10)
        page_speed.pack(fill="x", pady=(12, 6))
        self._secret_row(page_speed, 0, "API Key (tùy chọn):", self.pagespeed_key)

        gsc = ttk.LabelFrame(
            frame, text="Google Search Console - Service Account read-only", padding=10
        )
        gsc.pack(fill="x", pady=6)
        ttk.Label(gsc, text="Service Account JSON:").grid(
            row=0, column=0, sticky="e", padx=6, pady=5
        )
        ttk.Entry(gsc, textvariable=self.gsc_credential_path, width=70).grid(
            row=0, column=1, sticky="ew", padx=6, pady=5
        )
        ttk.Button(gsc, text="Chọn file", command=self._choose_gsc_json).grid(
            row=0, column=2, padx=5
        )
        self._entry_row(gsc, 1, "Property:", self.gsc_property)
        ttk.Label(
            gsc,
            text="Ví dụ: sc-domain:example.com hoặc https://www.example.com/",
            foreground="#555",
        ).grid(row=2, column=1, sticky="w", padx=6)

        wp = ttk.LabelFrame(frame, text="WordPress REST API", padding=10)
        wp.pack(fill="x", pady=6)
        self._entry_row(wp, 0, "Website:", self.wp_site)
        self._entry_row(wp, 1, "Username:", self.wp_user)
        self._secret_row(wp, 2, "Application Password:", self.wp_password)
        ttk.Button(wp, text="Kiểm tra WordPress", command=self._test_wordpress).grid(
            row=3, column=1, sticky="w", pady=8
        )

        self.api_diagnostic_text = tk.Text(frame, height=8, wrap="word")
        self.api_diagnostic_text.pack(fill="both", expand=True, pady=(8, 0))
        self._set_text(
            self.api_diagnostic_text,
            "Chưa kiểm tra. Nút phía trên sẽ kiểm tra từng kết nối độc lập và "
            "hiển thị hướng xử lý cho lỗi quyền, quota, CAPTCHA hoặc timeout.",
        )

    def _link_map_tab(self):
        frame = self._tab("Link Map")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Label(
            bar, text="Internal Link Map & Sitemap Coverage", style="Head.TLabel"
        ).pack(side="left")
        ttk.Button(bar, text="Làm mới", command=self._render_link_map).pack(
            side="right"
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_link_map).pack(
            side="right", padx=7
        )
        self.link_summary = ttk.Label(
            frame,
            text="Chạy Website Audit để tạo bản đồ liên kết.",
            foreground="#1769c2",
        )
        self.link_summary.pack(anchor="w", pady=(8, 2))
        self.link_tree = self._tree(
            frame,
            ("type", "source", "sdepth", "target", "tdepth", "inlinks", "status"),
            ("Loại", "Nguồn", "Depth", "Đích/URL", "Depth", "Inlinks", "HTTP"),
            (100, 390, 55, 430, 55, 65, 90),
        )

    def _gsc_tab(self):
        frame = self._tab("Search Console")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Label(bar, text="Google Search Console", style="Head.TLabel").pack(
            side="left"
        )
        ttk.Button(
            bar,
            text="Lấy dữ liệu 90 ngày",
            style="Accent.TButton",
            command=self._fetch_gsc,
        ).pack(side="left", padx=10)
        ttk.Button(bar, text="Kiểm tra URL", command=self._inspect_gsc_url).pack(
            side="left"
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_gsc).pack(
            side="left", padx=7
        )
        self.gsc_inspect_url = tk.StringVar()
        ttk.Entry(bar, textvariable=self.gsc_inspect_url, width=48).pack(
            side="right"
        )
        ttk.Label(bar, text="URL Inspection:").pack(side="right", padx=5)
        self.gsc_summary = ttk.Label(
            frame,
            text="Chọn Service Account JSON và property trong tab API & Kết nối.",
            foreground="#555",
        )
        self.gsc_summary.pack(anchor="w", pady=(8, 2))
        self.gsc_tree = self._tree(
            frame,
            ("date", "page", "query", "clicks", "impressions", "ctr", "position"),
            ("Ngày", "Trang", "Truy vấn", "Clicks", "Impressions", "CTR", "Position"),
            (95, 400, 300, 80, 100, 80, 80),
        )

    def _automation_tab(self):
        frame = self._tab("Automation")
        pane = ttk.Panedwindow(frame, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left = ttk.Frame(pane)
        right = ttk.Frame(pane)
        pane.add(left, weight=1)
        pane.add(right, weight=1)

        schedule = ttk.LabelFrame(left, text="Scheduled Audit & cảnh báo lỗi mới", padding=10)
        schedule.pack(fill="x")
        self.schedule_frequency = tk.StringVar(value="DAILY")
        self.schedule_time = tk.StringVar(value="02:00")
        ttk.Label(schedule, text="Tần suất:").grid(row=0, column=0, sticky="e", pady=4)
        ttk.Combobox(
            schedule,
            textvariable=self.schedule_frequency,
            values=("DAILY", "WEEKLY"),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(schedule, text="Giờ HH:MM:").grid(row=1, column=0, sticky="e", pady=4)
        ttk.Entry(schedule, textvariable=self.schedule_time, width=15).grid(
            row=1, column=1, sticky="w", padx=6
        )
        ttk.Button(
            schedule,
            text="Tạo/ cập nhật lịch Windows",
            style="Accent.TButton",
            command=self._create_schedule,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Button(schedule, text="Xóa lịch", command=self._delete_schedule).grid(
            row=2, column=2, padx=5
        )
        ttk.Button(
            schedule, text="Làm mới cảnh báo", command=self._refresh_alerts
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        self.alert_text = tk.Text(schedule, height=12, wrap="word")
        self.alert_text.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        schedule.columnconfigure(2, weight=1)
        schedule.rowconfigure(4, weight=1)
        self._set_text(self.alert_text, "Chưa có cảnh báo từ Scheduled Audit.")

        reports = ttk.LabelFrame(left, text="Báo cáo quản trị", padding=10)
        reports.pack(fill="x", pady=(10, 0))
        ttk.Button(
            reports, text="Xuất PDF 30/60/90", command=self._export_pdf_report
        ).pack(side="left")
        ttk.Button(
            reports, text="Xuất Excel đầy đủ", command=self._export_excel_report
        ).pack(side="left", padx=8)

        wp = ttk.LabelFrame(right, text="WordPress Preview & Rollback", padding=10)
        wp.pack(fill="both", expand=True)
        row = ttk.Frame(wp)
        row.pack(fill="x")
        self.wp_post_id = tk.StringVar()
        self.wp_revision_id = tk.StringVar()
        ttk.Label(row, text="Post ID:").pack(side="left")
        ttk.Entry(row, textvariable=self.wp_post_id, width=10).pack(
            side="left", padx=5
        )
        ttk.Button(row, text="Tải Preview", command=self._wp_preview).pack(side="left")
        ttk.Label(row, text="Revision ID (trống = mới nhất):").pack(
            side="left", padx=(12, 3)
        )
        ttk.Entry(row, textvariable=self.wp_revision_id, width=12).pack(side="left")
        ttk.Button(row, text="Rollback", command=self._wp_rollback).pack(
            side="left", padx=6
        )
        self.wp_preview_text = tk.Text(wp, wrap="word")
        self.wp_preview_text.pack(fill="both", expand=True, pady=(8, 0))
        self._set_text(
            self.wp_preview_text,
            "Nhập Post ID để xem title, status và nội dung hiện tại trước khi rollback.",
        )

    def _growth_tab(self):
        frame = self._tab("Growth Pro")
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)
        self._backlink_panel(notebook)
        self._decay_panel(notebook)
        self._content_gap_panel(notebook)
        self._competitor_panel(notebook)
        self._roadmap_panel(notebook)

    def _nested_tab(self, notebook, title):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text=title)
        return frame

    def _backlink_panel(self, notebook):
        frame = self._nested_tab(notebook, "Backlinks")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(
            bar,
            text="Import Backlink CSV",
            style="Accent.TButton",
            command=self._import_backlinks,
        ).pack(side="left")
        ttk.Button(bar, text="Xuất CSV chuẩn hóa", command=self._export_backlinks).pack(
            side="left", padx=7
        )
        self.backlink_summary_label = ttk.Label(
            bar, text="Chưa có backlink.", foreground="#555"
        )
        self.backlink_summary_label.pack(side="left", padx=12)
        self.backlink_tree = self._tree(
            frame,
            ("source", "domain", "target", "anchor", "authority", "follow", "risk"),
            ("Nguồn", "Domain", "Đích", "Anchor", "DR/DA", "Follow", "Rủi ro"),
            (360, 220, 340, 220, 70, 70, 90),
        )

    def _decay_panel(self, notebook):
        frame = self._nested_tab(notebook, "Content Decay")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(bar, text="Phân tích dữ liệu hiện có", command=self._render_decay).pack(
            side="left"
        )
        ttk.Label(
            bar,
            text="So sánh 30 ngày gần nhất với 30 ngày liền trước từ GSC/CSV.",
            foreground="#555",
        ).pack(side="left", padx=10)
        self.decay_tree = self._tree(
            frame,
            ("page", "previous", "current", "click_change", "imp_change", "status"),
            ("Trang", "Clicks trước", "Clicks nay", "% Clicks", "% Impressions", "Phân loại"),
            (580, 100, 100, 100, 120, 140),
        )

    def _content_gap_panel(self, notebook):
        frame = self._nested_tab(notebook, "Content Gap")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.gap_keyword = tk.StringVar()
        self.gap_own_url = tk.StringVar()
        ttk.Label(bar, text="Keyword:").pack(side="left")
        ttk.Entry(bar, textvariable=self.gap_keyword, width=32).pack(
            side="left", padx=5
        )
        ttk.Label(bar, text="Trang của tôi:").pack(side="left")
        ttk.Entry(bar, textvariable=self.gap_own_url, width=48).pack(
            side="left", padx=5
        )
        ttk.Button(
            bar,
            text="Phân tích tự động",
            style="Accent.TButton",
            command=self._start_content_gap,
        ).pack(side="left")
        self.gap_tree = self._tree(
            frame,
            ("priority", "topic", "coverage"),
            ("Ưu tiên", "Chủ đề/heading còn thiếu", "Đối thủ có"),
            (85, 850, 120),
        )

    def _competitor_panel(self, notebook):
        frame = self._nested_tab(notebook, "Competitors & Rank")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.competitor_domains = tk.StringVar()
        ttk.Label(bar, text="Domain đối thủ (cách nhau dấu phẩy):").pack(side="left")
        ttk.Entry(bar, textvariable=self.competitor_domains, width=68).pack(
            side="left", padx=7
        )
        ttk.Button(
            bar,
            text="Theo dõi Rank",
            style="Accent.TButton",
            command=self._start_competitor_rank,
        ).pack(side="left")
        self.competitor_tree = self._tree(
            frame,
            ("checked", "keyword", "domain", "position", "link"),
            ("Thời điểm", "Từ khóa", "Domain", "Vị trí", "URL xếp hạng"),
            (160, 280, 240, 80, 520),
        )

    def _roadmap_panel(self, notebook):
        frame = self._nested_tab(notebook, "Dashboard 30/60/90")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(
            bar,
            text="Tạo Roadmap mới",
            style="Accent.TButton",
            command=self._render_roadmap,
        ).pack(side="left")
        self.sov_label = ttk.Label(
            bar, text="Share of Voice: chưa có dữ liệu", foreground="#555"
        )
        self.sov_label.pack(side="left", padx=12)
        self.roadmap_tree = self._tree(
            frame,
            ("days", "workstream", "priority", "action", "url", "metric", "status"),
            ("Ngày", "Nhóm", "Ưu tiên", "Hành động", "URL", "KPI/tiêu chí", "Trạng thái"),
            (60, 130, 70, 330, 360, 370, 100),
        )

    def _choose_gsc_json(self):
        path = filedialog.askopenfilename(
            title="Chọn Service Account JSON",
            filetypes=[("Google JSON", "*.json"), ("Tất cả", "*.*")],
        )
        if path:
            self.gsc_credential_path.set(path)

    def _select_project(self, event=None):
        super()._select_project(event)
        if self.current_project:
            host = urlparse(self.current_project["website"]).netloc.removeprefix("www.")
            if not self.gsc_property.get().strip():
                self.gsc_property.set("sc-domain:" + host)
            self.gsc_inspect_url.set(self.current_project["website"])
            self.gap_own_url.set(self.current_project["website"])
            self._refresh_alerts()

    def _load_project_state(self):
        super()._load_project_state()
        if not self.current_project:
            return
        project_id = self.current_project["id"]
        self.backlink_rows = self.store.load_project_state(
            project_id, "backlinks", []
        ) or []
        self.backlink_summary = BacklinkAnalyzer.summarize(self.backlink_rows)
        self.gsc_rows = self.store.load_project_state(project_id, "gsc-rows", []) or []
        self.rank_history = self.store.load_project_state(
            project_id, "rank-history", []
        ) or []
        self.decay_rows = analyze_content_decay(self.gsc_rows)
        self.latest_alerts = self.store.load_project_state(
            project_id, "latest-alerts", {}
        ) or {}
        if hasattr(self, "backlink_tree"):
            self._render_backlinks()
            self._render_gsc()
            self._render_decay()
            self._render_competitors()
            self._render_roadmap()
            self._refresh_alerts()

    def _save_state(self):
        super()._save_state()
        if not self.current_project:
            return
        project_id = self.current_project["id"]
        self.store.save_project_state(project_id, "backlinks", self.backlink_rows)
        self.store.save_project_state(project_id, "gsc-rows", self.gsc_rows)
        self.store.save_project_state(project_id, "rank-history", self.rank_history)

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
            self.internal_graph = getattr(auditor, "last_graph", {})
            self.sitemap_urls = getattr(auditor, "last_sitemap_urls", set())
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
            error = explain_exception(exc, "Website Audit")
            self.events.put(("error", error.title, error.user_message))

    def _finish_audit(self, pages, files, orphans):
        super()._finish_audit(pages, files, orphans)
        self._render_link_map()
        self._render_roadmap()
        self._refresh_alerts()

    def _render_link_map(self):
        if not hasattr(self, "link_tree"):
            return
        self.link_map_report = build_link_map(
            self.pages, self.internal_graph, self.sitemap_urls
        )
        report = self.link_map_report
        self._clear_tree(self.link_tree)
        for edge in report["edges"]:
            self.link_tree.insert(
                "",
                "end",
                values=(
                    "Internal Link",
                    edge["source"],
                    edge["source_depth"],
                    edge["target"],
                    edge["target_depth"],
                    edge["target_inlinks"],
                    edge["target_status"],
                ),
            )
        for kind, values in (
            ("Orphan", report["orphans"]),
            ("Dead-end", report["dead_ends"]),
            ("Depth > 3", report["deep_pages"]),
            ("Weak inlinks", report["weak_pages"]),
        ):
            for value in values:
                self.link_tree.insert(
                    "", "end", values=(kind, "", "", value, "", "", "")
                )
        self.link_summary.configure(
            text=(
                f"{report['crawled_urls']} URL crawl • {report['sitemap_urls']} URL sitemap • "
                f"Coverage {report['sitemap_coverage']}% • {len(report['edges'])} links • "
                f"{len(report['orphans'])} orphan • {len(report['dead_ends'])} dead-end • "
                f"{len(report['deep_pages'])} depth > 3"
            )
        )

    def _export_link_map(self):
        if not self.link_map_report.get("edges"):
            messagebox.showinfo("Chưa có dữ liệu", "Chạy Website Audit trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="internal-link-map-v43.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            export_csv(path, self.link_map_report["edges"])

    def _start_serp_research(self):
        keyword = clean_text(self.serp_keyword.get())
        if not keyword:
            messagebox.showwarning("Thiếu keyword", "Nhập từ khóa cần phân tích.")
            return
        manual_urls = [
            clean_text(value)
            for value in self.manual_serp_urls.get("1.0", "end").splitlines()
            if clean_text(value)
        ]
        self.serp_btn.configure(state="disabled")
        self.progress.set(0)
        threading.Thread(
            target=self._serp_worker,
            args=(keyword, manual_urls),
            daemon=True,
        ).start()

    def _serp_worker(self, keyword, manual_urls=None):
        try:
            result = DirectGoogleResearcher().research(
                keyword,
                self.country.get(),
                self.language.get(),
                manual_urls=manual_urls,
                callback=lambda text, value: self.events.put(
                    ("serp-progress", text, value)
                ),
            )
            self.events.put(("serp-done", result))
        except Exception as exc:
            error = explain_exception(exc, "Top 5 Direct")
            self.events.put(("error", error.title, error.user_message))

    def _check_ranks(self):
        if not self.keyword_rows:
            messagebox.showinfo("Chưa có từ khóa", "Thêm Keyword Map trước.")
            return
        threading.Thread(target=self._rank_worker, daemon=True).start()

    def _rank_worker(self):
        try:
            researcher = DirectGoogleResearcher()
            for index, row in enumerate(self.keyword_rows):
                result = researcher.rank(
                    row["keyword"], row["url"], self.country.get(), self.language.get()
                )
                row["rank"] = result["position"]
                self.rank_history.append(
                    {
                        "checked_at": result["checked_at"],
                        "keyword": row["keyword"],
                        "domain": urlparse(row["url"]).netloc,
                        "position": result["position"],
                        "link": result["link"],
                    }
                )
                self.events.put(("status", f"Rank {index + 1}/{len(self.keyword_rows)}"))
            self.events.put(("ranks-done",))
        except Exception as exc:
            error = explain_exception(exc, "Rank Tracking")
            self.events.put(("error", error.title, error.user_message))

    def _finish_pagespeed(self, result):
        self.latest_pagespeed = result
        super()._finish_pagespeed(result)

    def _import_log(self):
        path = filedialog.askopenfilename(
            title="Chọn server access log",
            filetypes=[("Log/Text", "*.log *.txt"), ("Tất cả", "*.*")],
        )
        if not path:
            return
        try:
            self.log_report = AdvancedServerLogAnalyzer().analyze(
                path, [page.url for page in self.pages]
            )
        except Exception as exc:
            error = explain_exception(exc, "Server Log")
            messagebox.showerror(error.title, error.user_message)
            return
        report = self.log_report
        self._set_text(
            self.crawl_summary,
            "\n".join(
                [
                    f"Tổng dòng log: {report['total_lines']:,}",
                    f"Googlebot hits: {report['googlebot_hits']:,}",
                    f"Crawl efficiency: {report['crawl_efficiency']}%",
                    f"Useful hits: {report['useful_hits']:,}",
                    f"Waste hits: {report['waste_hits']:,}",
                    f"Smartphone: {report['by_device'].get('Smartphone', 0):,} ({report['mobile_share']}%)",
                    f"Desktop: {report['by_device'].get('Desktop', 0):,} ({report['desktop_share']}%)",
                    f"Error hits 4xx/5xx: {report['error_hits']:,}",
                    f"URL gây lãng phí crawl: {len(report['waste_urls'])}",
                    f"Trang quan trọng crawl 0-1 lần: {len(report['low_crawl_urls'])}",
                    "",
                    report["spoofing_note"],
                ]
            ),
        )
        self._render_crawl_structure()
        for row in report["waste_urls"]:
            self.crawl_tree.insert(
                "",
                "end",
                values=(
                    "Crawl Waste",
                    row["url"],
                    row["hits"],
                    "Parameter, asset hoặc HTTP status không tạo giá trị SEO",
                ),
            )
        for row in report["low_crawl_urls"]:
            self.crawl_tree.insert(
                "",
                "end",
                values=(
                    "Low Crawl",
                    row["url"],
                    row["hits"],
                    "Trang Audit chưa xuất hiện hoặc chỉ có 1 hit Googlebot",
                ),
            )
        for number, evidence in (
            (1, f"{report['googlebot_hits']} Googlebot hits"),
            (2, f"Efficiency {report['crawl_efficiency']}%"),
            (7, f"{report['waste_hits']} waste hits"),
            (8, f"{len(report['low_crawl_urls'])} low-crawl URLs"),
            (9, json.dumps(report["by_device"], ensure_ascii=False)),
        ):
            self._mark_master(number, "Hoàn thành", evidence)
        self._save_state()
        self._render_roadmap()

    def _fetch_gsc(self):
        if not self.gsc_credential_path.get().strip() or not self.gsc_property.get().strip():
            messagebox.showwarning(
                "Thiếu cấu hình GSC",
                "Chọn Service Account JSON và nhập property trong API & Kết nối.",
            )
            return
        threading.Thread(target=self._gsc_worker, daemon=True).start()

    def _gsc_worker(self):
        try:
            client = SearchConsoleClient(self.gsc_credential_path.get())
            end = date.today() - timedelta(days=2)
            start = end - timedelta(days=89)
            rows = client.search_analytics(
                self.gsc_property.get(), start, end, ("date", "page", "query")
            )
            sitemaps = client.list_sitemaps(self.gsc_property.get())
            self.pro_events.put(("gsc-done", rows, sitemaps, start, end))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "Google Search Console")))

    def _render_gsc(self):
        if not hasattr(self, "gsc_tree"):
            return
        self._clear_tree(self.gsc_tree)
        for row in self.gsc_rows[:25000]:
            self.gsc_tree.insert(
                "",
                "end",
                values=(
                    row.get("date", ""),
                    row.get("page", ""),
                    row.get("query", ""),
                    row.get("clicks", 0),
                    row.get("impressions", 0),
                    f"{parse_number(row.get('ctr', 0)) * 100:.2f}%",
                    f"{parse_number(row.get('position', 0)):.1f}",
                ),
            )
        clicks = sum(parse_number(row.get("clicks", 0)) for row in self.gsc_rows)
        impressions = sum(
            parse_number(row.get("impressions", 0)) for row in self.gsc_rows
        )
        self.gsc_summary.configure(
            text=(
                f"{len(self.gsc_rows):,} rows • {clicks:,.0f} clicks • "
                f"{impressions:,.0f} impressions • {len(self.gsc_sitemaps)} sitemap GSC"
            )
        )

    def _inspect_gsc_url(self):
        url = normalize_url(self.gsc_inspect_url.get())
        if not url:
            messagebox.showwarning("Thiếu URL", "Nhập URL cần kiểm tra.")
            return
        threading.Thread(target=self._gsc_inspect_worker, args=(url,), daemon=True).start()

    def _gsc_inspect_worker(self, url):
        try:
            client = SearchConsoleClient(self.gsc_credential_path.get())
            result = client.inspect_url(self.gsc_property.get(), url)
            self.pro_events.put(("gsc-inspect", url, result))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "URL Inspection")))

    def _export_gsc(self):
        if not self.gsc_rows:
            messagebox.showinfo("Chưa có dữ liệu", "Lấy dữ liệu GSC trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="gsc-90-days-v43.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            export_csv(path, self.gsc_rows)

    def _import_performance(self):
        super()._import_performance()
        if self.performance_rows:
            self.gsc_rows = self.performance_rows
            self._render_gsc()
            self._render_decay()
            self._save_state()

    def _import_backlinks(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV/TSV", "*.csv *.tsv"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        try:
            self.backlink_rows = BacklinkAnalyzer.import_csv(path)
            self.backlink_summary = BacklinkAnalyzer.summarize(self.backlink_rows)
        except Exception as exc:
            error = explain_exception(exc, "Backlink Import")
            messagebox.showerror(error.title, error.user_message)
            return
        self._render_backlinks()
        self._render_roadmap()
        self._save_state()

    def _render_backlinks(self):
        if not hasattr(self, "backlink_tree"):
            return
        self._clear_tree(self.backlink_tree)
        for row in self.backlink_rows:
            self.backlink_tree.insert(
                "",
                "end",
                values=(
                    row["source"],
                    row["domain"],
                    row["target"],
                    row["anchor"],
                    row["authority"],
                    "Yes" if row["follow"] else "No",
                    row["risk"],
                ),
            )
        summary = self.backlink_summary or BacklinkAnalyzer.summarize(self.backlink_rows)
        self.backlink_summary_label.configure(
            text=(
                f"{summary.get('backlinks', 0)} links • "
                f"{summary.get('referring_domains', 0)} domains • "
                f"{summary.get('dofollow_percent', 0)}% dofollow • "
                f"{summary.get('high_risk', 0)} rủi ro cao"
            )
        )

    def _export_backlinks(self):
        if not self.backlink_rows:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="backlinks-normalized-v43.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            export_csv(path, self.backlink_rows)

    def _render_decay(self):
        source = self.gsc_rows or self.performance_rows
        self.decay_rows = analyze_content_decay(source)
        if not hasattr(self, "decay_tree"):
            return
        self._clear_tree(self.decay_tree)
        for row in self.decay_rows:
            self.decay_tree.insert(
                "",
                "end",
                values=(
                    row["page"],
                    row["previous_clicks"],
                    row["current_clicks"],
                    f"{row['click_change_percent']}%",
                    f"{row['impression_change_percent']}%",
                    row["status"],
                ),
            )
        self._render_roadmap()

    def _start_content_gap(self):
        keyword = clean_text(self.gap_keyword.get())
        own_url = normalize_url(self.gap_own_url.get())
        if not keyword or not own_url:
            messagebox.showwarning("Thiếu dữ liệu", "Nhập keyword và URL trang của bạn.")
            return
        threading.Thread(
            target=self._content_gap_worker, args=(keyword, own_url), daemon=True
        ).start()

    def _content_gap_worker(self, keyword, own_url):
        try:
            researcher = DirectGoogleResearcher()
            result = researcher.research(
                keyword,
                self.country.get(),
                self.language.get(),
                callback=lambda text, value: self.pro_events.put(
                    ("pro-status", text, value)
                ),
            )
            own_headings, _, _ = researcher.extract_page(own_url)
            report = analyze_content_gap(keyword, own_url, result, own_headings)
            self.pro_events.put(("content-gap-done", report))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "Content Gap")))

    def _start_competitor_rank(self):
        if not self.keyword_rows:
            messagebox.showwarning("Thiếu từ khóa", "Tạo Keyword Map trước.")
            return
        own_host = urlparse(
            self.current_project["website"] if self.current_project else self.website.get()
        ).netloc
        domains = [own_host]
        for value in self.competitor_domains.get().split(","):
            value = clean_text(value)
            if not value:
                continue
            parsed = urlparse(value if "://" in value else "//" + value)
            domains.append(parsed.netloc or parsed.path)
        domains = list(
            dict.fromkeys(value.lower().removeprefix("www.") for value in domains if value)
        )
        threading.Thread(
            target=self._competitor_worker, args=(domains,), daemon=True
        ).start()

    def _competitor_worker(self, domains):
        try:
            researcher = DirectGoogleResearcher()
            new_rows = []
            keywords = self.keyword_rows[:50]
            for index, keyword_row in enumerate(keywords):
                payload = researcher.search(
                    keyword_row["keyword"],
                    self.country.get(),
                    self.language.get(),
                    limit=20,
                )
                for domain in domains:
                    match = next(
                        (
                            item
                            for item in payload["results"]
                            if urlparse(item["link"]).netloc.removeprefix("www.")
                            == domain
                            or urlparse(item["link"]).netloc.removeprefix("www.").endswith(
                                "." + domain
                            )
                        ),
                        None,
                    )
                    new_rows.append(
                        {
                            "checked_at": utc_now(),
                            "keyword": keyword_row["keyword"],
                            "domain": domain,
                            "position": match["position"] if match else ">20",
                            "link": match["link"] if match else "",
                        }
                    )
                self.pro_events.put(
                    (
                        "pro-status",
                        f"Đã kiểm tra {index + 1}/{len(keywords)} keyword",
                        round((index + 1) / max(1, len(keywords)) * 100),
                    )
                )
            self.pro_events.put(("competitors-done", new_rows))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "Competitor Tracking")))

    def _render_competitors(self):
        if not hasattr(self, "competitor_tree"):
            return
        self._clear_tree(self.competitor_tree)
        for row in self.rank_history[-5000:]:
            self.competitor_tree.insert(
                "",
                "end",
                values=(
                    row.get("checked_at", ""),
                    row.get("keyword", ""),
                    row.get("domain", ""),
                    row.get("position", ""),
                    row.get("link", ""),
                ),
            )
        self.competitor_sov = competitor_share_of_voice(self.rank_history)
        if self.competitor_sov:
            self.sov_label.configure(
                text="Share of Voice: "
                + " • ".join(
                    f"{row['domain']} {row['share_of_voice']}%"
                    for row in self.competitor_sov[:5]
                )
            )

    def _render_roadmap(self):
        self.roadmap_rows = build_roadmap(
            self.fix_items,
            self.decay_rows,
            self.backlink_summary,
            self.gsc_rows,
        )
        if not hasattr(self, "roadmap_tree"):
            return
        self._clear_tree(self.roadmap_tree)
        for row in self.roadmap_rows:
            self.roadmap_tree.insert(
                "",
                "end",
                values=(
                    row["phase_days"],
                    row["workstream"],
                    row["priority"],
                    row["action"],
                    row["url"],
                    row["success_metric"],
                    row["status"],
                ),
            )

    def _create_schedule(self):
        if not self.current_project:
            messagebox.showwarning("Chưa chọn dự án", "Chọn/lưu dự án trước.")
            return
        try:
            result = WindowsAuditScheduler().create(
                self.current_project["id"],
                self.schedule_frequency.get(),
                self.schedule_time.get(),
                self.max_pages.get(),
            )
        except Exception as exc:
            error = explain_exception(exc, "Scheduled Audit")
            messagebox.showerror(error.title, error.user_message)
            return
        self.store.save_project_state(
            self.current_project["id"],
            "schedule",
            {
                **result,
                "frequency": self.schedule_frequency.get(),
                "time": self.schedule_time.get(),
                "updated_at": utc_now(),
            },
        )
        messagebox.showinfo(
            "Đã tạo lịch",
            f"{result['task_name']}\n{self.schedule_frequency.get()} lúc {self.schedule_time.get()}",
        )

    def _delete_schedule(self):
        if not self.current_project:
            return
        if not messagebox.askyesno(
            "Xóa lịch Audit",
            f"Xóa lịch tự động của dự án {self.current_project['name']}?",
        ):
            return
        try:
            WindowsAuditScheduler().delete(self.current_project["id"])
        except Exception as exc:
            error = explain_exception(exc, "Scheduled Audit")
            messagebox.showerror(error.title, error.user_message)
            return
        messagebox.showinfo("Scheduled Audit", "Đã xóa lịch.")

    def _refresh_alerts(self):
        if not hasattr(self, "alert_text"):
            return
        if self.current_project:
            self.latest_alerts = self.store.load_project_state(
                self.current_project["id"], "latest-alerts", {}
            ) or {}
        alerts = self.latest_alerts.get("new_issues", [])
        lines = [
            f"Lần kiểm tra: {self.latest_alerts.get('created_at', 'Chưa có')}",
            f"Snapshot: {self.latest_alerts.get('snapshot', '')}",
            f"Lỗi mới: {len(alerts)}",
            "",
        ]
        lines.extend(
            f"! {row.get('url', '')} - {row.get('issue', '')}" for row in alerts[:200]
        )
        if not alerts:
            lines.append("Không có lỗi mới hoặc Scheduled Audit chưa chạy.")
        self._set_text(self.alert_text, "\n".join(lines))

    def _report_data(self):
        self._render_link_map()
        self._render_decay()
        self._render_roadmap()
        return report_payload(
            project=self.current_project
            or {"name": "SEO Project", "website": self.website.get()},
            pages=self.pages,
            fixes=self.fix_items,
            site_files=self.site_files,
            link_map=self.link_map_report,
            log_report=self.log_report,
            gsc_rows=self.gsc_rows,
            pagespeed=self.latest_pagespeed,
            keyword_rows=self.keyword_rows,
            backlinks=self.backlink_rows,
            backlink_summary=self.backlink_summary,
            decay_rows=self.decay_rows,
            rank_rows=self.rank_history,
            roadmap=self.roadmap_rows,
            master_checks=self.master_checks,
            alerts=self.latest_alerts,
        )

    def _export_pdf_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile="seo-report-v43-30-60-90.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        try:
            export_pdf(path, self._report_data())
        except Exception as exc:
            error = explain_exception(exc, "Xuất PDF")
            messagebox.showerror(error.title, error.user_message)
            return
        messagebox.showinfo("Báo cáo PDF", f"Đã xuất:\n{path}")

    def _export_excel_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile="seo-report-v43-full.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_excel(path, self._report_data())
        except Exception as exc:
            error = explain_exception(exc, "Xuất Excel")
            messagebox.showerror(error.title, error.user_message)
            return
        messagebox.showinfo("Báo cáo Excel", f"Đã xuất:\n{path}")

    def _wp_client(self):
        return WordPressProClient(
            self.wp_site.get(), self.wp_user.get(), self.wp_password.get()
        )

    def _wp_preview(self):
        try:
            post_id = int(self.wp_post_id.get())
        except ValueError:
            messagebox.showwarning("Post ID", "Nhập Post ID là số nguyên.")
            return
        threading.Thread(target=self._wp_preview_worker, args=(post_id,), daemon=True).start()

    def _wp_preview_worker(self, post_id):
        try:
            post = self._wp_client().get_post(post_id)
            revisions = self._wp_client().list_revisions(post_id)
            self.pro_events.put(("wp-preview", post, revisions))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "WordPress Preview")))

    def _wp_rollback(self):
        try:
            post_id = int(self.wp_post_id.get())
            revision_id = (
                int(self.wp_revision_id.get())
                if self.wp_revision_id.get().strip()
                else None
            )
        except ValueError:
            messagebox.showwarning("Post/Revision ID", "ID phải là số nguyên.")
            return
        target = f"revision {revision_id}" if revision_id else "revision mới nhất"
        if not messagebox.askyesno(
            "Xác nhận WordPress Rollback",
            f"Khôi phục Post {post_id} về {target}?\n\n"
            "Thao tác này sẽ cập nhật nội dung bài viết trên WordPress.",
        ):
            return
        threading.Thread(
            target=self._wp_rollback_worker, args=(post_id, revision_id), daemon=True
        ).start()

    def _wp_rollback_worker(self, post_id, revision_id):
        try:
            result = self._wp_client().rollback(post_id, revision_id)
            self.pro_events.put(("wp-rollback", result))
        except Exception as exc:
            self.pro_events.put(("pro-error", explain_exception(exc, "WordPress Rollback")))

    def _test_all_apis(self):
        threading.Thread(target=self._api_test_worker, daemon=True).start()

    def _api_test_worker(self):
        results = []
        try:
            count = len(DirectGoogleResearcher().search("seo", limit=10)["results"])
            results.append(("Top 5 Direct", "OK", f"Đọc được {count} kết quả"))
        except Exception as exc:
            error = explain_exception(exc, "Top 5 Direct")
            results.append(("Top 5 Direct", "LỖI", error.user_message))

        url = normalize_url(self.psi_url.get() or self.website.get())
        if url:
            try:
                from seo_v4_core import PageSpeedClient

                value = PageSpeedClient(self.pagespeed_key.get()).analyze(url, "mobile")
                results.append(
                    ("PageSpeed", "OK", f"Performance {value['performance']}/100")
                )
            except Exception as exc:
                error = explain_exception(exc, "PageSpeed")
                results.append(("PageSpeed", "LỖI", error.user_message))
        else:
            results.append(("PageSpeed", "BỎ QUA", "Chưa có URL website"))

        if self.gsc_credential_path.get().strip():
            try:
                sites = SearchConsoleClient(
                    self.gsc_credential_path.get()
                ).list_sites()
                results.append(("Search Console", "OK", f"{len(sites)} property"))
            except Exception as exc:
                error = explain_exception(exc, "Search Console")
                results.append(("Search Console", "LỖI", error.user_message))
        else:
            results.append(("Search Console", "BỎ QUA", "Chưa chọn Service Account JSON"))

        if (
            self.wp_site.get().strip()
            and self.wp_user.get().strip()
            and self.wp_password.get().strip()
        ):
            try:
                name = self._wp_client().test()
                results.append(("WordPress", "OK", name))
            except Exception as exc:
                error = explain_exception(exc, "WordPress")
                results.append(("WordPress", "LỖI", error.user_message))
        else:
            results.append(("WordPress", "BỎ QUA", "Chưa nhập đủ thông tin"))
        self.pro_events.put(("api-tests", results))

    def _poll_pro_events(self):
        try:
            while True:
                event = self.pro_events.get_nowait()
                kind = event[0]
                if kind == "pro-error":
                    error = event[1]
                    messagebox.showerror(error.title, error.user_message)
                    self.status.set(error.title)
                    self.progress.set(0)
                elif kind == "pro-status":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "gsc-done":
                    self.gsc_rows, self.gsc_sitemaps = event[1], event[2]
                    self._render_gsc()
                    self._render_decay()
                    self._save_state()
                    self.status.set(
                        f"Đã lấy GSC {event[3]} đến {event[4]}: {len(self.gsc_rows)} rows."
                    )
                    self.progress.set(100)
                elif kind == "gsc-inspect":
                    result = event[2]
                    index = result.get("indexStatusResult", {})
                    messagebox.showinfo(
                        "URL Inspection",
                        "\n".join(
                            [
                                event[1],
                                f"Verdict: {index.get('verdict', '')}",
                                f"Coverage: {index.get('coverageState', '')}",
                                f"Robots: {index.get('robotsTxtState', '')}",
                                f"Indexing: {index.get('indexingState', '')}",
                                f"Last crawl: {index.get('lastCrawlTime', '')}",
                                f"Google canonical: {index.get('googleCanonical', '')}",
                            ]
                        ),
                    )
                elif kind == "content-gap-done":
                    self.content_gap_report = event[1]
                    self._clear_tree(self.gap_tree)
                    for row in self.content_gap_report["gaps"]:
                        self.gap_tree.insert(
                            "",
                            "end",
                            values=(row["priority"], row["topic"], row["coverage"]),
                        )
                    self.status.set(
                        f"Content Gap: {len(self.content_gap_report['gaps'])} chủ đề còn thiếu."
                    )
                    self.progress.set(100)
                elif kind == "competitors-done":
                    self.rank_history.extend(event[1])
                    self._render_competitors()
                    self._save_state()
                    self.status.set("Đã cập nhật Rank Tracking và Share of Voice.")
                    self.progress.set(100)
                elif kind == "wp-preview":
                    post, revisions = event[1], event[2]
                    title = (post.get("title") or {}).get("raw") or (
                        post.get("title") or {}
                    ).get("rendered", "")
                    content = (post.get("content") or {}).get("raw") or (
                        post.get("content") or {}
                    ).get("rendered", "")
                    lines = [
                        f"POST ID: {post.get('id')}",
                        f"TITLE: {title}",
                        f"STATUS: {post.get('status')}",
                        f"MODIFIED: {post.get('modified')}",
                        f"REVISIONS: {len(revisions)}",
                        "Revision gần nhất: "
                        + ", ".join(str(row.get("id")) for row in revisions[:10]),
                        "",
                        "NỘI DUNG HIỆN TẠI",
                        content,
                    ]
                    self._set_text(self.wp_preview_text, "\n".join(lines))
                elif kind == "wp-rollback":
                    result = event[1]
                    messagebox.showinfo(
                        "WordPress Rollback",
                        f"Đã khôi phục revision {result['restored_revision']}.\n"
                        f"Post ID: {result['post'].get('id')}",
                    )
                    self._wp_preview()
                elif kind == "api-tests":
                    lines = [
                        f"[{state}] {service}\n{detail}\n"
                        for service, state, detail in event[1]
                    ]
                    self._set_text(self.api_diagnostic_text, "\n".join(lines))
                    self.status.set("Đã kiểm tra tất cả kết nối.")
        except queue.Empty:
            pass
        self.after(120, self._poll_pro_events)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scheduled-audit")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--store-root")
    return parser.parse_known_args(argv)[0]


def main(argv=None):
    args = parse_args(argv)
    if args.scheduled_audit:
        try:
            result = run_scheduled_audit(
                args.scheduled_audit,
                max_pages=max(1, min(500, args.max_pages)),
                store_root=args.store_root,
            )
            return 0 if result else 1
        except Exception as exc:
            error = explain_exception(exc, "Scheduled Audit")
            try:
                log_path = Path(os.getenv("TEMP") or ".") / "seo-ai-studio-v43-scheduled.log"
                log_path.write_text(
                    f"{utc_now()} | {error.title} | {error.user_message}\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
            return 1
    AppV43().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
