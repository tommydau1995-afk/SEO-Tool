"""SEO AI Studio V4.8 - SEO Intelligence and live index diagnostics."""

from __future__ import annotations

import argparse
import json
import queue
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from app_v47 import AppV47, SetupWizardV47
from seo_v4_core import clean_text, normalize_url
from seo_v43_core import SearchConsoleClient, explain_exception, run_scheduled_audit
from seo_v46_core import UpdateChecker
from seo_v48_intelligence import (
    GUIDE_FILE,
    UPDATE_MANIFEST_URL,
    VERSION,
    GoogleAdsKeywordPlannerClient,
    ProjectStoreV48,
    build_content_gaps,
    compare_audit_snapshots,
    compare_indexed_and_live,
    detect_keyword_cannibalization,
    estimate_serp_weakness,
    google_ads_config_template,
    gsc_data_quality,
    import_keyword_planner_file,
    inspect_live_url,
    merge_keyword_metrics,
    onboarding_statuses_v48,
    recalculate_opportunities,
)


class SetupWizardV48(SetupWizardV47):
    def __init__(self, app: "AppV48"):
        super().__init__(app)
        self.title("Thiết lập SEO AI Studio V4.8")


class AppV48(AppV47):
    def __init__(self):
        self.v48_events = queue.Queue()
        self.google_ads_connected = False
        self.cannibalization_rows: list[dict] = []
        self.content_gap_v48_rows: list[dict] = []
        self.index_debug_report: dict = {}
        self.audit_comparison_report: dict = {}
        self.keyword_metrics_running = False
        self.index_debug_running = False
        self.v48_cancel_event = threading.Event()
        super().__init__()
        self.store = ProjectStoreV48()
        self._refresh_projects()
        self.title(f"SEO AI Studio V{VERSION} - SEO Intelligence")
        self._load_app_settings()
        self.bind_all("<Control-k>", self._open_command_palette)
        self.bind_all("<Control-K>", self._open_command_palette)
        self.after(140, self._poll_v48_events)

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 10))
        frame.pack(fill="x")
        ttk.Label(frame, text="SEO AI Studio V4.8", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            frame,
            text=(
                "Keyword Planner • Opportunity 2.0 • Cannibalization • "
                "Index Debugger • Audit Diff"
            ),
            foreground="#1769C2",
        ).pack(side="left", padx=16)
        ttk.Button(
            frame, text="Hướng dẫn chi tiết", command=self._open_guide
        ).pack(side="right", padx=(7, 0))
        ttk.Button(
            frame, text="Kiểm tra cập nhật", command=self._check_updates
        ).pack(side="right", padx=(7, 0))
        ttk.Button(
            frame, text="Tìm chức năng (Ctrl+K)", command=self._open_command_palette
        ).pack(side="right", padx=(7, 0))
        self.project_badge = ttk.Label(frame, text="Chưa chọn dự án")
        self.project_badge.pack(side="right", padx=10)
        self.mode_var = tk.StringVar(value="Easy")
        ttk.Combobox(
            frame,
            textvariable=self.mode_var,
            values=("Easy", "Pro"),
            state="readonly",
            width=8,
        ).pack(side="right")
        self.mode_var.trace_add("write", lambda *_: self._apply_mode())
        ttk.Label(frame, text="Chế độ:").pack(side="right", padx=(10, 4))

    def _footer(self):
        frame = ttk.Frame(self, padding=(12, 6))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status).pack(side="left")
        self.elapsed_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.elapsed_var, style="Muted.TLabel").pack(
            side="left", padx=12
        )
        self.retry_btn = ttk.Button(
            frame, text="Chạy lại", state="disabled", command=self._retry_last
        )
        self.retry_btn.pack(side="right", padx=(5, 0))
        self.cancel_btn = ttk.Button(
            frame,
            text="Hủy",
            state="disabled",
            command=self._cancel_current_operation,
        )
        self.cancel_btn.pack(side="right", padx=(5, 0))
        ttk.Progressbar(
            frame, variable=self.progress, maximum=100, length=260
        ).pack(side="right", padx=(8, 0))
        ttk.Label(frame, text=f"V{VERSION}").pack(side="right")

    def _easy_start_tab(self):
        super()._easy_start_tab()
        actions = ttk.Frame(self.nametowidget(self.workspace_notebooks["Tổng quan"].tabs()[0]))
        actions.pack(fill="x", pady=(4, 0))
        ttk.Button(
            actions,
            text="SEO Intelligence",
            command=lambda: self._open_workspace("Nghiên cứu", "SEO Intelligence"),
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Index Debugger",
            command=lambda: self._open_workspace("Audit", "Index Debugger"),
        ).pack(side="left", padx=7)
        ttk.Button(
            actions,
            text="So sánh Audit",
            command=lambda: self._open_workspace("Audit", "So sánh Audit"),
        ).pack(side="left")

    def _keyword_tab(self):
        super()._keyword_tab()
        self._seo_intelligence_tab()

    def _crawl_index_tab(self):
        super()._crawl_index_tab()
        self._index_debugger_tab()
        self._audit_comparison_tab()

    def _seo_intelligence_tab(self):
        frame = self._tab("SEO Intelligence")
        top = ttk.LabelFrame(
            frame,
            text="Keyword Planner tùy chọn + Opportunity 2.0",
            padding=10,
        )
        top.pack(fill="x")
        ttk.Label(
            top,
            text=(
                "Volume/CPC chỉ lấy từ Google Ads hoặc file import thật. "
                "Ads Competition không phải SEO Keyword Difficulty."
            ),
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=8, sticky="w")
        self.google_ads_config_path = tk.StringVar()
        self.google_ads_language_id = tk.StringVar(value="1040")
        self.google_ads_geo_id = tk.StringVar(value="2704")
        ttk.Label(top, text="Google Ads JSON:").grid(
            row=1, column=0, sticky="e", pady=(8, 0)
        )
        ttk.Entry(top, textvariable=self.google_ads_config_path, width=52).grid(
            row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=(8, 0)
        )
        ttk.Button(top, text="Chọn", command=self._choose_google_ads_config).grid(
            row=1, column=4, pady=(8, 0)
        )
        ttk.Button(top, text="Tạo file mẫu", command=self._create_google_ads_template).grid(
            row=1, column=5, padx=5, pady=(8, 0)
        )
        ttk.Button(top, text="Kiểm tra", command=self._test_google_ads).grid(
            row=1, column=6, pady=(8, 0)
        )
        ttk.Label(top, text="Language ID:").grid(row=2, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.google_ads_language_id, width=9).grid(
            row=2, column=1, sticky="w", padx=5
        )
        ttk.Label(top, text="Geo ID:").grid(row=2, column=2, sticky="e")
        ttk.Entry(top, textvariable=self.google_ads_geo_id, width=9).grid(
            row=2, column=3, sticky="w", padx=5
        )
        ttk.Button(
            top,
            text="Lấy Volume/CPC cho bộ từ khóa",
            style="Accent.TButton",
            command=self._start_keyword_metrics,
        ).grid(row=2, column=4, columnspan=2, sticky="w")
        ttk.Button(
            top, text="Import Keyword Planner", command=self._import_keyword_planner
        ).grid(row=2, column=6, padx=5)
        top.columnconfigure(3, weight=1)

        quality = ttk.Frame(frame)
        quality.pack(fill="x", pady=(7, 4))
        self.v48_metric_keywords = self._small_metric(quality, "0", "Keywords")
        self.v48_metric_volume = self._small_metric(quality, "0", "Có Volume")
        self.v48_metric_cannibal = self._small_metric(quality, "0", "Cannibalization")
        self.v48_metric_gaps = self._small_metric(quality, "0", "Content Gap")
        self.v48_metric_high = self._small_metric(quality, "0", "Cơ hội ≥80")
        self.gsc_quality_label = ttk.Label(
            frame,
            text="GSC: chưa có dữ liệu.",
            style="Muted.TLabel",
        )
        self.gsc_quality_label.pack(anchor="w", pady=(0, 4))

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(
            actions,
            text="Tính lại Opportunity 2.0",
            command=self._recalculate_v48,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Phát hiện Cannibalization",
            command=self._refresh_cannibalization,
        ).pack(side="left", padx=6)
        ttk.Button(
            actions,
            text="Tạo Content Gap",
            command=self._refresh_content_gaps,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Ước tính SERP Weakness từ Top 5",
            command=self._apply_serp_weakness,
        ).pack(side="left", padx=6)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, pady=(6, 0))
        keyword_frame = ttk.Frame(notebook, padding=5)
        cannibal_frame = ttk.Frame(notebook, padding=5)
        gap_frame = ttk.Frame(notebook, padding=5)
        notebook.add(keyword_frame, text="Keyword Opportunity")
        notebook.add(cannibal_frame, text="Cannibalization")
        notebook.add(gap_frame, text="Content Gap")

        self.v48_keyword_tree = self._tree(
            keyword_frame,
            (
                "keyword",
                "opportunity",
                "volume",
                "ads_comp",
                "cpc",
                "gsc",
                "intent",
                "landing",
                "confidence",
                "provenance",
            ),
            (
                "Keyword",
                "Cơ hội 2.0",
                "Volume",
                "Ads Competition",
                "CPC thấp-cao",
                "GSC Impressions",
                "Intent",
                "Landing Page",
                "Tin cậy",
                "Nguồn metrics / ngày",
            ),
            (260, 90, 90, 125, 120, 115, 115, 360, 80, 260),
        )
        self.v48_cannibal_tree = self._tree(
            cannibal_frame,
            (
                "priority",
                "keyword",
                "pages",
                "impressions",
                "share",
                "primary",
                "competing",
                "recommendation",
            ),
            (
                "Ưu tiên",
                "Keyword",
                "Số URL",
                "Impressions",
                "Top share",
                "URL chính",
                "URL cạnh tranh",
                "Cách xử lý",
            ),
            (70, 240, 70, 100, 90, 320, 420, 420),
        )
        self.v48_gap_tree = self._tree(
            gap_frame,
            (
                "priority",
                "cluster",
                "keywords",
                "primary",
                "opportunity",
                "volume",
                "recommendation",
            ),
            (
                "Ưu tiên",
                "Cluster",
                "Keywords",
                "Primary Keyword",
                "Cơ hội",
                "Volume",
                "Đề xuất",
            ),
            (70, 220, 85, 280, 80, 90, 450),
        )

    def _index_debugger_tab(self):
        frame = self._tab("Index Debugger")
        hero = ttk.LabelFrame(
            frame,
            text="So sánh Google Index với URL live hiện tại",
            padding=10,
        )
        hero.pack(fill="x")
        ttk.Label(
            hero,
            text=(
                "URL Inspection phản ánh phiên bản trong Google Index. "
                "Tool tải URL live riêng để kiểm tra HTTP, robots, canonical và nội dung."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w")
        row = ttk.Frame(hero)
        row.pack(fill="x", pady=(8, 0))
        self.index_debug_url = tk.StringVar()
        ttk.Entry(row, textvariable=self.index_debug_url).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            row,
            text="Kiểm tra Index + Live",
            style="Accent.TButton",
            command=self._start_index_debugger,
        ).pack(side="left", padx=7)
        ttk.Button(
            row, text="Chỉ kiểm tra Live", command=lambda: self._start_index_debugger(True)
        ).pack(side="left")
        pane = ttk.Panedwindow(frame, orient="horizontal")
        pane.pack(fill="both", expand=True, pady=(8, 0))
        left = ttk.LabelFrame(pane, text="Kết quả", padding=8)
        right = ttk.LabelFrame(pane, text="Vấn đề và hướng xử lý", padding=8)
        pane.add(left, weight=3)
        pane.add(right, weight=2)
        self.index_debug_text = tk.Text(left, wrap="word", font=("Segoe UI", 10))
        self.index_debug_text.pack(fill="both", expand=True)
        self.index_issue_tree = self._tree(
            right,
            ("issue", "action"),
            ("Vấn đề", "Hướng xử lý"),
            (310, 430),
        )
        self._set_text(
            self.index_debug_text,
            "Nhập URL rồi chọn Kiểm tra. Kết quả luôn ghi rõ nguồn Index hay Live.",
        )

    def _audit_comparison_tab(self):
        frame = self._tab("So sánh Audit")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(
            bar,
            text="So sánh 2 lần Audit gần nhất",
            style="Accent.TButton",
            command=self._compare_latest_audits,
        ).pack(side="left")
        ttk.Button(bar, text="Sao lưu dự án", command=self._export_project_backup).pack(
            side="left", padx=7
        )
        ttk.Button(
            bar, text="Khôi phục dự án", command=self._import_project_backup
        ).pack(side="left")
        self.audit_compare_summary = tk.Text(
            frame, height=10, wrap="word", font=("Segoe UI", 10)
        )
        self.audit_compare_summary.pack(fill="x", pady=(8, 6))
        self.audit_diff_tree = self._tree(
            frame,
            ("type", "url", "issue"),
            ("Thay đổi", "URL", "Lỗi"),
            (110, 470, 520),
        )
        self._set_text(
            self.audit_compare_summary,
            "Cần ít nhất hai snapshot Audit để xem lỗi mới, đã sửa và tái phát.",
        )

    def _choose_google_ads_config(self):
        path = filedialog.askopenfilename(
            filetypes=[("Google Ads JSON", "*.json"), ("Tất cả", "*.*")]
        )
        if path:
            self.google_ads_config_path.set(path)

    def _create_google_ads_template(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="google_ads_keyword_planner_config.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(google_ads_config_template(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.google_ads_config_path.set(path)
        messagebox.showinfo(
            "Đã tạo file mẫu",
            "Điền thông tin Google Ads OAuth vào file. Không chia sẻ file này.",
        )

    def _test_google_ads(self):
        if not self._require_project("kiểm tra Google Ads"):
            return
        seed = (
            self.keyword_discovery_rows[0].get("keyword")
            if self.keyword_discovery_rows
            else "seo"
        )
        self._start_keyword_metrics(test_keyword=seed)

    def _start_keyword_metrics(self, test_keyword=None):
        if not self._require_project("lấy Keyword Planner"):
            return
        path = clean_text(self.google_ads_config_path.get())
        if not path:
            self._show_smart_error(
                "Chưa chọn Google Ads JSON",
                "Keyword Planner cần file cấu hình OAuth.",
                "Nhấn Tạo file mẫu, điền thông tin rồi chọn file.",
                retry=self._start_keyword_metrics,
            )
            return
        keywords = (
            [test_keyword]
            if test_keyword
            else [
                row.get("keyword")
                for row in self.keyword_discovery_rows
                if row.get("keyword")
            ][:1000]
        )
        if not keywords:
            self._show_smart_error(
                "Chưa có bộ từ khóa",
                "Không có keyword để lấy metrics.",
                "Chạy Tìm bộ từ khóa trước.",
            )
            return
        self.keyword_metrics_running = True
        self.v48_cancel_event.clear()
        self._begin_operation(
            "Google Ads Keyword Planner",
            retry=lambda: self._start_keyword_metrics(test_keyword),
        )
        threading.Thread(
            target=self._keyword_metrics_worker,
            args=(path, keywords, bool(test_keyword)),
            daemon=True,
        ).start()

    def _keyword_metrics_worker(self, path, keywords, test_only):
        try:
            self.v48_events.put(("progress", "Đang xác thực Google Ads OAuth…", 15))
            client = GoogleAdsKeywordPlannerClient(path)
            self.v48_events.put(("progress", "Đang lấy Volume/CPC thật…", 55))
            metrics = client.historical_metrics(
                keywords,
                language_constant=self.google_ads_language_id.get(),
                geo_target_constant=self.google_ads_geo_id.get(),
            )
            if self.v48_cancel_event.is_set():
                self.v48_events.put(("cancelled",))
                return
            self.v48_events.put(("metrics-done", metrics, test_only))
        except Exception as exc:
            self.v48_events.put(
                ("error", explain_exception(exc, "Google Ads Keyword Planner"))
            )

    def _import_keyword_planner(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Keyword Planner", "*.csv *.tsv *.xlsx *.xlsm"),
                ("Tất cả", "*.*"),
            ]
        )
        if not path:
            return
        try:
            metrics = import_keyword_planner_file(path)
            if not metrics:
                raise ValueError("Không nhận diện được keyword trong file.")
            self.keyword_discovery_rows = merge_keyword_metrics(
                self.keyword_discovery_rows, metrics
            )
            self.google_ads_connected = True
            self._render_discovery()
            self._render_v48_intelligence()
            self._save_state()
            self._refresh_onboarding()
            messagebox.showinfo(
                "Đã import Keyword Planner",
                f"Đã đọc {len(metrics):,} dòng metrics thật.",
            )
        except Exception as exc:
            error = explain_exception(exc, "Import Keyword Planner")
            self._show_smart_error(error.title, error.message, error.hint)

    def _recalculate_v48(self):
        self.keyword_discovery_rows = recalculate_opportunities(
            self.keyword_discovery_rows
        )
        self._render_discovery()
        self._render_v48_intelligence()
        self._save_state()
        self.status.set("Đã tính lại Opportunity 2.0.")

    def _refresh_cannibalization(self):
        self.cannibalization_rows = detect_keyword_cannibalization(self.gsc_rows)
        self._render_v48_intelligence()
        self._save_state()
        self.status.set(
            f"Đã phát hiện {len(self.cannibalization_rows):,} nhóm cannibalization."
        )

    def _refresh_content_gaps(self):
        self.content_gap_v48_rows = build_content_gaps(
            self.keyword_discovery_rows
        )
        self._render_v48_intelligence()
        self._save_state()
        self.status.set(
            f"Đã tạo {len(self.content_gap_v48_rows):,} Content Gap cluster."
        )

    def _apply_serp_weakness(self):
        result = getattr(self, "serp_result", None)
        if not result:
            messagebox.showinfo(
                "Chưa có Top 5",
                "Phân tích Top 5 Direct trước, sau đó chạy ước tính SERP Weakness.",
            )
            return
        estimate = estimate_serp_weakness(result.keyword, result.sources)
        key = clean_text(result.keyword)
        matched = 0
        for row in self.keyword_discovery_rows:
            if row.get("keyword", "").casefold() == key.casefold():
                row["serp_weakness"] = estimate["score"]
                row["serp_weakness_reason"] = estimate["reason"]
                matched += 1
        if matched:
            self.keyword_discovery_rows = recalculate_opportunities(
                self.keyword_discovery_rows
            )
            self._render_discovery()
            self._render_v48_intelligence()
            self._save_state()
        messagebox.showinfo(
            "SERP Weakness ước tính",
            (
                f"{result.keyword}: {estimate['score']}/100 - {estimate['label']}\n"
                f"{estimate['reason']}\n\n{estimate['authority_note']}\n"
                f"Đã cập nhật {matched} dòng Keyword Discovery."
            ),
        )

    def _render_v48_intelligence(self):
        if not hasattr(self, "v48_keyword_tree"):
            return
        self._clear_tree(self.v48_keyword_tree)
        for index, row in enumerate(self.keyword_discovery_rows):
            self.v48_keyword_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row.get("keyword", ""),
                    row.get("opportunity", 0),
                    f"{int(row.get('volume') or 0):,}" if row.get("volume") else "",
                    (
                        f"{row.get('ads_competition', '')} "
                        f"({int(row.get('ads_competition_index') or 0)})"
                    ).strip(),
                    (
                        f"{float(row.get('cpc_low') or 0):,.2f}-"
                        f"{float(row.get('cpc_high') or 0):,.2f}"
                        if row.get("cpc_low") or row.get("cpc_high")
                        else ""
                    ),
                    f"{float(row.get('gsc_impressions') or 0):,.0f}",
                    row.get("intent", ""),
                    row.get("landing_page", "") or "Đề xuất tạo mới",
                    row.get("data_confidence", "Trung bình"),
                    (
                        f"{row.get('metrics_source', '')} • "
                        f"{row.get('metrics_updated_at', '')}"
                    ).strip(" •"),
                ),
            )
        self._clear_tree(self.v48_cannibal_tree)
        for row in self.cannibalization_rows:
            self.v48_cannibal_tree.insert(
                "",
                "end",
                values=(
                    row["priority"],
                    row["keyword"],
                    row["pages"],
                    f"{row['total_impressions']:,.0f}",
                    f"{row['top_share']:.1f}%",
                    row["primary_url"],
                    "\n".join(row["competing_urls"]),
                    row["recommendation"],
                ),
            )
        self._clear_tree(self.v48_gap_tree)
        for row in self.content_gap_v48_rows:
            self.v48_gap_tree.insert(
                "",
                "end",
                values=(
                    row["priority"],
                    row["cluster"],
                    row["keywords"],
                    row["primary_keyword"],
                    row["max_opportunity"],
                    f"{row['total_volume']:,}",
                    row["recommendation"],
                ),
            )
        rows = self.keyword_discovery_rows
        self.v48_metric_keywords.configure(text=f"{len(rows):,}")
        self.v48_metric_volume.configure(
            text=f"{sum(bool(row.get('volume')) for row in rows):,}"
        )
        self.v48_metric_cannibal.configure(
            text=f"{len(self.cannibalization_rows):,}"
        )
        self.v48_metric_gaps.configure(text=f"{len(self.content_gap_v48_rows):,}")
        self.v48_metric_high.configure(
            text=f"{sum(int(row.get('opportunity') or 0) >= 80 for row in rows):,}"
        )
        quality = gsc_data_quality(len(self.gsc_rows))
        self.gsc_quality_label.configure(
            text=f"GSC • {quality['status']} • Tin cậy: {quality['confidence']}"
        )

    def _start_index_debugger(self, live_only=False):
        if not self._require_project("kiểm tra Index"):
            return
        url = normalize_url(
            self.index_debug_url.get()
            or self.gsc_inspect_url.get()
            or self.current_project.get("website")
        )
        if not url:
            self._show_smart_error(
                "URL chưa hợp lệ",
                "Không nhận diện được URL cần kiểm tra.",
                "Nhập URL đầy đủ rồi chạy lại.",
            )
            return
        self.index_debug_url.set(url)
        self.index_debug_running = True
        self.v48_cancel_event.clear()
        self._begin_operation(
            "Index Debugger",
            retry=lambda: self._start_index_debugger(live_only),
        )
        threading.Thread(
            target=self._index_debug_worker,
            args=(url, live_only),
            daemon=True,
        ).start()

    def _index_debug_worker(self, url, live_only):
        try:
            self.v48_events.put(("progress", "Đang tải URL live…", 30))
            live = inspect_live_url(url)
            inspection = {}
            warning = ""
            if not live_only:
                credential = clean_text(self.gsc_credential_path.get())
                property_name = clean_text(self.gsc_property.get())
                if credential and property_name:
                    self.v48_events.put(
                        ("progress", "Đang đọc phiên bản trong Google Index…", 70)
                    )
                    inspection = SearchConsoleClient(credential).inspect_url(
                        property_name, url
                    )
                else:
                    warning = (
                        "Search Console chưa kết nối; chỉ có kết quả live. "
                        "Kết nối GSC để so sánh phiên bản trong Google Index."
                    )
            report = compare_indexed_and_live(inspection, live)
            report["warning"] = warning
            if self.v48_cancel_event.is_set():
                self.v48_events.put(("cancelled",))
                return
            self.v48_events.put(("index-done", report))
        except Exception as exc:
            self.v48_events.put(("error", explain_exception(exc, "Index Debugger")))

    def _render_index_debugger(self):
        if not hasattr(self, "index_debug_text") or not self.index_debug_report:
            return
        report = self.index_debug_report
        indexed = report.get("indexed", {})
        live = report.get("live", {})
        lines = [
            "INDEX DEBUGGER V4.8",
            f"Kết luận: {report.get('status', '')}",
            "",
            "A. GOOGLE INDEX - KHÔNG PHẢI LIVE TEST",
            indexed.get("source_note", ""),
            f"Verdict: {indexed.get('verdict', '') or 'Chưa lấy'}",
            f"Coverage: {indexed.get('coverage', '') or 'Chưa lấy'}",
            f"Robots: {indexed.get('robots', '') or 'Chưa lấy'}",
            f"Indexing: {indexed.get('indexing', '') or 'Chưa lấy'}",
            f"Last crawl: {indexed.get('last_crawl', '') or 'Chưa lấy'}",
            f"Google canonical: {indexed.get('google_canonical', '') or 'Chưa lấy'}",
            "",
            "B. URL LIVE HIỆN TẠI",
            f"URL: {live.get('url', '')}",
            f"Final URL: {live.get('final_url', '')}",
            f"HTTP: {live.get('status', '')} • Redirects: {live.get('redirects', 0)}",
            f"Response: {live.get('response_ms', 0)} ms",
            f"Indexable live: {'Có' if live.get('indexable_live') else 'Không'}",
            f"robots.txt cho Googlebot: {live.get('robots_allowed_googlebot')}",
            f"Robots Meta: {live.get('robots_meta', '') or 'Không có'}",
            f"X-Robots-Tag: {live.get('x_robots_tag', '') or 'Không có'}",
            f"Canonical live: {live.get('canonical', '') or 'Thiếu'}",
            f"Title: {live.get('title', '') or 'Thiếu'}",
            f"H1: {live.get('h1', '') or 'Thiếu'}",
            f"Nội dung: {live.get('content_chars', 0):,} ký tự",
            "",
            report.get("warning", ""),
        ]
        self._set_text(self.index_debug_text, "\n".join(lines))
        self._clear_tree(self.index_issue_tree)
        issues = report.get("issues", [])
        for issue in issues:
            self.index_issue_tree.insert(
                "",
                "end",
                values=(
                    issue,
                    "Kiểm tra HTTP, robots, noindex, canonical và yêu cầu Google crawl lại sau khi sửa.",
                ),
            )
        if not issues:
            self.index_issue_tree.insert(
                "",
                "end",
                values=("Không phát hiện xung đột chính", "Tiếp tục theo dõi sau lần crawl mới."),
            )

    def _compare_latest_audits(self):
        if not self._require_project("so sánh Audit"):
            return
        snapshots = self.store.list_snapshots(self.current_project["id"])
        if len(snapshots) < 2:
            messagebox.showinfo(
                "Chưa đủ snapshot",
                "Cần chạy Full SEO Audit ít nhất hai lần.",
            )
            return
        previous = self.store.load_snapshot(snapshots[1])
        current = self.store.load_snapshot(snapshots[0])
        self.audit_comparison_report = compare_audit_snapshots(previous, current)
        self._render_audit_comparison()
        self._save_state()

    def _render_audit_comparison(self):
        if not hasattr(self, "audit_compare_summary") or not self.audit_comparison_report:
            return
        report = self.audit_comparison_report
        before, after, delta = report["before"], report["after"], report["deltas"]
        lines = [
            f"Kết luận: {report['status']}",
            f"Snapshot trước: {before.get('created_at', '')}",
            f"Snapshot mới: {after.get('created_at', '')}",
            "",
            f"SEO Score: {before['avg_score']} → {after['avg_score']} ({delta['avg_score']:+.1f})",
            f"Tổng lỗi: {before['issues']} → {after['issues']} ({delta['issues']:+.0f})",
            f"Lỗi đã sửa: {len(report['resolved'])}",
            f"Lỗi mới/tái phát: {len(report['new'])}",
            f"Lỗi còn lại: {len(report['remaining'])}",
            f"HTTP 4xx/5xx: {before['errors_4xx_5xx']} → {after['errors_4xx_5xx']}",
            f"Orphan: {before['orphans']} → {after['orphans']}",
            f"Dead-end: {before['dead_ends']} → {after['dead_ends']}",
        ]
        self._set_text(self.audit_compare_summary, "\n".join(lines))
        self._clear_tree(self.audit_diff_tree)
        for kind, rows in (
            ("Đã sửa", report["resolved"]),
            ("Lỗi mới", report["new"]),
            ("Còn lại", report["remaining"]),
        ):
            for url, issue in rows:
                self.audit_diff_tree.insert("", "end", values=(kind, url, issue))

    def _export_project_backup(self):
        if not self._require_project("sao lưu dự án"):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=f"{self.current_project['id']}-seo-v48-backup.zip",
            filetypes=[("SEO V4.8 Backup", "*.zip")],
        )
        if path:
            self.store.export_project_bundle(self.current_project["id"], path)
            messagebox.showinfo("Đã sao lưu dự án", path)

    def _import_project_backup(self):
        path = filedialog.askopenfilename(
            filetypes=[("SEO V4.8 Backup", "*.zip"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        try:
            project = self.store.import_project_bundle(path)
            self._refresh_projects(project["id"])
            self._select_project()
            messagebox.showinfo(
                "Đã khôi phục dự án",
                f"{project['name']}\n{project['website']}",
            )
        except Exception as exc:
            error = explain_exception(exc, "Khôi phục dự án")
            self._show_smart_error(error.title, error.message, error.hint)

    def _open_command_palette(self, event=None):
        commands = (
            ("Bắt đầu", "Tổng quan", "Bắt đầu"),
            ("Tìm bộ từ khóa", "Nghiên cứu", "Tìm bộ từ khóa"),
            ("SEO Intelligence", "Nghiên cứu", "SEO Intelligence"),
            ("Keyword Intelligence", "Nghiên cứu", "Keyword Intelligence"),
            ("Top 5 Direct", "Nghiên cứu", "Top 5 Direct"),
            ("Website Audit", "Audit", "Website Audit"),
            ("Index Debugger", "Audit", "Index Debugger"),
            ("So sánh Audit", "Audit", "So sánh Audit"),
            ("Fix Queue", "Kế hoạch & Thực thi", "Fix Queue chi tiết"),
            ("Content Workflow", "Kế hoạch & Thực thi", "Content Workflow"),
            ("API & Kết nối", "Theo dõi", "API & Kết nối"),
        )
        window = tk.Toplevel(self)
        window.title("Tìm chức năng")
        window.geometry("650x430")
        window.transient(self)
        body = ttk.Frame(window, padding=12)
        body.pack(fill="both", expand=True)
        query = tk.StringVar()
        entry = ttk.Entry(body, textvariable=query, font=("Segoe UI", 12))
        entry.pack(fill="x")
        tree = self._tree(
            body,
            ("name", "workspace", "tab"),
            ("Chức năng", "Khu vực", "Tab"),
            (220, 160, 220),
        )

        def render(*_):
            self._clear_tree(tree)
            key = clean_text(query.get()).lower()
            for index, command in enumerate(commands):
                if not key or key in " ".join(command).lower():
                    tree.insert("", "end", iid=str(index), values=command)

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            name, workspace, tab = tree.item(selected[0], "values")
            window.destroy()
            self._open_workspace(workspace, tab)
            self.status.set(f"Đã mở: {name}")

        query.trace_add("write", render)
        tree.bind("<Double-1>", open_selected)
        tree.bind("<Return>", open_selected)
        entry.bind("<Return>", lambda _event: (tree.selection_set(tree.get_children()[0]), open_selected()) if tree.get_children() else None)
        window.bind("<Escape>", lambda _event: window.destroy())
        render()
        entry.focus_set()

    def _render_discovery(self):
        super()._render_discovery()
        self._render_v48_intelligence()

    def _finish_full_audit(self, result):
        super()._finish_full_audit(result)
        self.keyword_discovery_rows = recalculate_opportunities(
            self.keyword_discovery_rows
        )
        self.cannibalization_rows = detect_keyword_cannibalization(self.gsc_rows)
        self.content_gap_v48_rows = build_content_gaps(self.keyword_discovery_rows)
        self._render_v48_intelligence()
        snapshots = (
            self.store.list_snapshots(self.current_project["id"])
            if self.current_project
            else []
        )
        if len(snapshots) >= 2:
            self.audit_comparison_report = compare_audit_snapshots(
                self.store.load_snapshot(snapshots[1]),
                self.store.load_snapshot(snapshots[0]),
            )
            self._render_audit_comparison()
        self._save_state()

    def _load_project_state(self):
        super()._load_project_state()
        if not self.current_project:
            return
        project_id = self.current_project["id"]
        self.cannibalization_rows = self.store.load_project_state(
            project_id, "cannibalization-v48", []
        ) or []
        self.content_gap_v48_rows = self.store.load_project_state(
            project_id, "content-gap-v48", []
        ) or []
        self.index_debug_report = self.store.load_project_state(
            project_id, "index-debug-v48", {}
        ) or {}
        self.audit_comparison_report = self.store.load_project_state(
            project_id, "audit-comparison-v48", {}
        ) or {}
        connection = self.store.load_project_state(
            project_id, "google-ads-settings-v48", {}
        ) or {}
        if hasattr(self, "google_ads_config_path"):
            self.google_ads_config_path.set(connection.get("config_path", ""))
            self.google_ads_language_id.set(connection.get("language_id", "1040"))
            self.google_ads_geo_id.set(connection.get("geo_id", "2704"))
        self.google_ads_connected = any(
            bool(row.get("metrics_source")) for row in self.keyword_discovery_rows
        )
        self._render_v48_intelligence()
        self._render_index_debugger()
        self._render_audit_comparison()
        self._refresh_onboarding()

    def _save_state(self):
        super()._save_state()
        if not self.current_project:
            return
        project_id = self.current_project["id"]
        self.store.save_project_state(
            project_id, "cannibalization-v48", self.cannibalization_rows
        )
        self.store.save_project_state(
            project_id, "content-gap-v48", self.content_gap_v48_rows
        )
        self.store.save_project_state(
            project_id, "index-debug-v48", self.index_debug_report
        )
        self.store.save_project_state(
            project_id, "audit-comparison-v48", self.audit_comparison_report
        )
        if hasattr(self, "google_ads_config_path"):
            self.store.save_project_state(
                project_id,
                "google-ads-settings-v48",
                {
                    "config_path": self.google_ads_config_path.get(),
                    "language_id": self.google_ads_language_id.get(),
                    "geo_id": self.google_ads_geo_id.get(),
                    "note": "Chỉ lưu đường dẫn; không lưu secret vào project.",
                },
            )

    def _refresh_onboarding(self):
        if not hasattr(self, "onboarding_tree"):
            return
        rows = onboarding_statuses_v48(
            self.current_project,
            self.pages,
            self.keyword_rows,
            self.keyword_discovery_rows,
            self.gsc_rows,
            self.latest_pagespeed,
            self.wordpress_ok,
            self.google_ads_connected,
        )
        self._clear_tree(self.onboarding_tree)
        for row in rows:
            self.onboarding_tree.insert(
                "", "end", values=(row["step"], row["name"], row["status"])
            )
        required_names = {
            "Tạo dự án",
            "Nhập website",
            "Quốc gia & ngôn ngữ",
            "Kiểm tra website",
            "Tìm bộ từ khóa",
            "Full SEO Audit",
        }
        pending = next(
            (
                row["name"]
                for row in rows
                if row["name"] in required_names and row["status"] != "Đã kết nối"
            ),
            None,
        )
        self.next_action_label.configure(
            text=(
                f"Bước tiếp theo: {pending}."
                if pending
                else "Quy trình chính đã sẵn sàng. Các kết nối còn lại là tùy chọn."
            )
        )

    def _poll_v48_events(self):
        try:
            while True:
                event = self.v48_events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "metrics-done":
                    metrics, test_only = event[1], event[2]
                    self.keyword_metrics_running = False
                    self.google_ads_connected = True
                    if not test_only:
                        self.keyword_discovery_rows = merge_keyword_metrics(
                            self.keyword_discovery_rows, metrics
                        )
                        self._refresh_content_gaps()
                    self._render_discovery()
                    self._render_v48_intelligence()
                    self._save_state()
                    self._refresh_onboarding()
                    self.progress.set(100)
                    self.status.set(
                        f"Keyword Planner hoàn tất: {len(metrics):,} keyword có dữ liệu."
                    )
                    self._end_operation(success=True)
                    if test_only:
                        messagebox.showinfo(
                            "Google Ads Keyword Planner",
                            (
                                f"Kết nối thành công; nhận {len(metrics)} dòng dữ liệu."
                                if metrics
                                else "Kết nối thành công nhưng keyword thử chưa có metrics."
                            ),
                        )
                elif kind == "index-done":
                    self.index_debug_running = False
                    self.index_debug_report = event[1]
                    self._render_index_debugger()
                    self._save_state()
                    self.progress.set(100)
                    self.status.set("Index Debugger đã hoàn tất.")
                    self._end_operation(success=True)
                elif kind == "error":
                    self.keyword_metrics_running = False
                    self.index_debug_running = False
                    error = event[1]
                    self._end_operation(success=False)
                    self._show_smart_error(
                        error.title,
                        error.message,
                        error.hint,
                        retry=self.last_retry,
                    )
                elif kind == "cancelled":
                    self.keyword_metrics_running = False
                    self.index_debug_running = False
                    self.status.set("Đã hủy thao tác V4.8.")
                    self._end_operation(success=False)
        except queue.Empty:
            pass
        self.after(140, self._poll_v48_events)

    def _cancel_current_operation(self):
        if self.keyword_metrics_running or self.index_debug_running:
            self.v48_cancel_event.set()
            self.status.set(
                "Đã yêu cầu hủy. Tool sẽ bỏ kết quả sau API request hiện tại."
            )
            return
        super()._cancel_current_operation()

    def _open_wizard(self):
        SetupWizardV48(self)

    def _update_worker(self):
        try:
            checker = UpdateChecker(manifest_url=UPDATE_MANIFEST_URL)
            self.v46_events.put(("update-result", checker.check(VERSION)))
        except Exception as exc:
            self.v46_events.put(
                ("full-error", explain_exception(exc, "Kiểm tra cập nhật"))
            )

    def _open_guide(self):
        candidates = [
            Path(__file__).resolve().parent / GUIDE_FILE,
            Path(__file__).resolve().parent / "output" / "pdf" / GUIDE_FILE,
            Path(getattr(__import__("sys"), "_MEIPASS", ".")) / GUIDE_FILE,
        ]
        path = next((item for item in candidates if item.exists()), None)
        if not path:
            self._show_smart_error(
                "Không tìm thấy hướng dẫn",
                f"Thiếu file {GUIDE_FILE}.",
                "Cài lại bộ Setup V4.8 đầy đủ.",
            )
            return
        webbrowser.open(path.as_uri())

    def _on_close(self):
        self.v48_cancel_event.set()
        self._save_state()
        super()._on_close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scheduled-audit")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--store-root")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.scheduled_audit:
        run_scheduled_audit(
            args.scheduled_audit,
            max_pages=args.max_pages,
            store_root=args.store_root,
        )
        return 0
    app = AppV48()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
