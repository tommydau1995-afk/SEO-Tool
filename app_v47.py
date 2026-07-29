"""SEO AI Studio V4.7 - built-in Keyword Discovery without Semrush."""

from __future__ import annotations

import argparse
import queue
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from app_v44 import AppV44
from app_v46 import AppV46, SetupWizard
from seo_v4_core import clean_text, normalize_url
from seo_v43_core import explain_exception, run_scheduled_audit
from seo_v44_keywords import deduplicate_keywords
from seo_v46_core import UpdateChecker
from seo_v47_keywords import (
    DISCOVERY_LEVELS,
    GUIDE_FILE,
    UPDATE_MANIFEST_URL,
    VERSION,
    GoogleSuggestClient,
    ProjectStoreV47,
    aggregate_gsc_queries,
    discovery_summary,
    discovery_to_keyword_rows,
    export_discovery_csv,
    export_discovery_workbook,
    merge_keyword_candidates,
    onboarding_statuses_v47,
    split_seed_keywords,
    website_keyword_candidates,
)


class SetupWizardV47(SetupWizard):
    STEP_NAMES = (
        "Tạo dự án",
        "Nhập website",
        "Quốc gia & ngôn ngữ",
        "Kiểm tra website",
        "Kết nối dữ liệu",
        "Tìm bộ từ khóa",
        "Full SEO Audit",
    )

    def __init__(self, app: "AppV47"):
        self.seed_keywords = tk.StringVar()
        super().__init__(app)
        self.title("Thiết lập SEO AI Studio V4.7")

    def _semrush_step(self):
        frame = self._page(
            "Bước 6 - Tìm bộ từ khóa",
            "Nhập tối đa 10 từ khóa gốc. Sau khi hoàn tất, tool có thể mở rộng bằng "
            "Google Suggest, GSC và nội dung website mà không cần Semrush.",
        )
        ttk.Label(frame, text="Từ khóa gốc (phân cách bằng dấu phẩy):").pack(
            anchor="w"
        )
        ttk.Entry(frame, textvariable=self.seed_keywords, width=65).pack(
            fill="x", pady=(5, 0)
        )
        ttk.Label(
            frame,
            text="Ví dụ: nội thất cao cấp, thiết kế nội thất, thi công nội thất",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=6)

    def _finish(self):
        seeds = clean_text(self.seed_keywords.get())
        app = self.app
        super()._finish()
        if seeds and hasattr(app, "discovery_seed_text"):
            app.discovery_seed_text.delete("1.0", "end")
            app.discovery_seed_text.insert("1.0", seeds)
            app.after(350, lambda: app._open_workspace("Nghiên cứu", "Tìm bộ từ khóa"))


class AppV47(AppV46):
    def __init__(self):
        self.discovery_events = queue.Queue()
        self.discovery_cancel_event = threading.Event()
        self.discovery_running = False
        self.keyword_discovery_rows: list[dict] = []
        super().__init__()
        self.store = ProjectStoreV47()
        self._refresh_projects()
        self.title(f"SEO AI Studio V{VERSION} - Keyword Discovery")
        self._load_app_settings()
        self.after(130, self._poll_discovery_events)

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 10))
        frame.pack(fill="x")
        ttk.Label(frame, text="SEO AI Studio V4.7", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            frame,
            text="Keyword Discovery • GSC Opportunities • Intent • Cluster • Full SEO",
            foreground="#1769C2",
        ).pack(side="left", padx=16)
        ttk.Button(
            frame, text="Hướng dẫn chi tiết", command=self._open_guide
        ).pack(side="right", padx=(7, 0))
        ttk.Button(
            frame, text="Kiểm tra cập nhật", command=self._check_updates
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
        frame = self._tab("Bắt đầu")
        hero = ttk.LabelFrame(frame, text="Quy trình SEO dành cho người mới", padding=12)
        hero.pack(fill="x")
        left = ttk.Frame(hero)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(
            left,
            text="Tìm bộ từ khóa - Full SEO Audit - Nhận danh sách việc cần làm",
            style="Hero.TLabel",
        ).pack(anchor="w")
        self.next_action_label = ttk.Label(
            left,
            text="Bước tiếp theo: tạo hoặc chọn dự án.",
            style="Muted.TLabel",
        )
        self.next_action_label.pack(anchor="w", pady=(4, 0))
        self.full_audit_btn = ttk.Button(
            hero,
            text="Chạy Full SEO Audit",
            style="Accent.TButton",
            command=self._start_full_audit,
        )
        self.full_audit_btn.pack(side="right", padx=(8, 0))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=10)
        for text, command in (
            ("Thiết lập từng bước", self._open_wizard),
            ("Tải dữ liệu Demo", self._load_demo),
            (
                "Tìm bộ từ khóa",
                lambda: self._open_workspace("Nghiên cứu", "Tìm bộ từ khóa"),
            ),
            (
                "Trung tâm kết nối",
                lambda: self._open_workspace("Theo dõi", "API & Kết nối"),
            ),
            (
                "Tạo Content Brief",
                lambda: self._open_workspace(
                    "Kế hoạch & Thực thi", "Content Workflow"
                ),
            ),
        ):
            ttk.Button(actions, text=text, command=command).pack(
                side="left", padx=(0, 7)
            )

        body = ttk.Panedwindow(frame, orient="horizontal")
        body.pack(fill="both", expand=True)
        left_box = ttk.LabelFrame(body, text="Trạng thái thiết lập", padding=8)
        right_box = ttk.LabelFrame(body, text="Kết quả Full Audit", padding=8)
        body.add(left_box, weight=2)
        body.add(right_box, weight=3)
        self.onboarding_tree = self._tree(
            left_box,
            ("step", "name", "status"),
            ("Bước", "Hạng mục", "Trạng thái"),
            (55, 300, 130),
        )
        self.full_audit_text = tk.Text(
            right_box, wrap="word", font=("Segoe UI", 10), relief="flat"
        )
        self.full_audit_text.pack(fill="both", expand=True)
        self._set_text(
            self.full_audit_text,
            "Chưa chạy Full SEO Audit.\n\n"
            "Bạn có thể tìm bộ từ khóa trước hoặc chạy Audit trước. Tool sẽ dùng dữ "
            "liệu website và GSC để làm giàu danh sách keyword khi có sẵn.",
        )
        self._refresh_onboarding()

    def _keyword_tab(self):
        self._keyword_discovery_tab()
        AppV44._keyword_tab(self)

    def _keyword_discovery_tab(self):
        frame = self._tab("Tìm bộ từ khóa")
        hero = ttk.LabelFrame(
            frame, text="Keyword Discovery không cần Semrush", padding=10
        )
        hero.pack(fill="x")
        left = ttk.Frame(hero)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(
            left,
            text="Google Suggest + Search Console + chủ đề trên website",
            style="Hero.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            left,
            text=(
                "Tool tự loại trùng, phân Search Intent, tạo Cluster, gợi ý Landing "
                "Page và chấm điểm Cơ hội. Không tự bịa Volume hoặc KD."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        self.discovery_start_btn = ttk.Button(
            hero,
            text="Tìm bộ từ khóa",
            style="Accent.TButton",
            command=self._start_keyword_discovery,
        )
        self.discovery_start_btn.pack(side="right", padx=(8, 0))

        input_box = ttk.LabelFrame(frame, text="1. Đầu vào", padding=8)
        input_box.pack(fill="x", pady=(8, 0))
        ttk.Label(input_box, text="Từ khóa gốc (tối đa 10):").grid(
            row=0, column=0, sticky="nw", padx=(0, 6)
        )
        self.discovery_seed_text = tk.Text(input_box, height=3, width=62, wrap="word")
        self.discovery_seed_text.grid(
            row=0, column=1, rowspan=2, sticky="ew", padx=(0, 8)
        )
        options = ttk.Frame(input_box)
        options.grid(row=0, column=2, rowspan=2, sticky="nw")
        self.discovery_level = tk.StringVar(value="Cân bằng")
        self.discovery_limit = tk.IntVar(value=500)
        self.discovery_use_google = tk.BooleanVar(value=True)
        self.discovery_use_gsc = tk.BooleanVar(value=True)
        self.discovery_use_website = tk.BooleanVar(value=True)
        ttk.Label(options, text="Mức mở rộng:").grid(row=0, column=0, sticky="e")
        ttk.Combobox(
            options,
            textvariable=self.discovery_level,
            values=tuple(DISCOVERY_LEVELS),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, padx=5)
        ttk.Label(options, text="Tối đa:").grid(row=0, column=2, sticky="e")
        ttk.Spinbox(
            options, from_=50, to=2000, increment=50, textvariable=self.discovery_limit, width=8
        ).grid(row=0, column=3, padx=5)
        ttk.Checkbutton(
            options, text="Google Suggest", variable=self.discovery_use_google
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            options, text="Google Search Console", variable=self.discovery_use_gsc
        ).grid(row=1, column=2, columnspan=2, sticky="w")
        ttk.Checkbutton(
            options, text="Website đã crawl", variable=self.discovery_use_website
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        input_box.columnconfigure(1, weight=1)
        ttk.Label(
            input_box,
            text=(
                "Nhanh: ít request • Cân bằng: phù hợp mặc định • Sâu: nhiều biến thể, "
                "có thể bị Google giới hạn tạm thời."
            ),
            style="Muted.TLabel",
        ).grid(row=2, column=1, sticky="w", pady=(4, 0))

        cards = ttk.Frame(frame)
        cards.pack(fill="x", pady=(8, 4))
        self.discovery_metric_keywords = self._small_metric(cards, "0", "Keywords")
        self.discovery_metric_clusters = self._small_metric(cards, "0", "Clusters")
        self.discovery_metric_high = self._small_metric(cards, "0", "Cơ hội ≥70")
        self.discovery_metric_gsc = self._small_metric(cards, "0", "Có dữ liệu GSC")
        self.discovery_metric_mapped = self._small_metric(cards, "0", "Có Landing Page")

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(3, 5))
        ttk.Button(
            actions, text="Chọn Cơ hội ≥70", command=self._select_high_opportunity
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Đưa dòng chọn sang Keyword Intelligence",
            command=self._add_selected_discovery,
        ).pack(side="left", padx=6)
        ttk.Button(
            actions,
            text="Tạo Content Brief từ Cơ hội ≥70",
            command=self._high_opportunity_to_briefs,
        ).pack(side="left")
        ttk.Button(
            actions, text="Xuất Excel", command=self._export_discovery_xlsx
        ).pack(side="right")
        ttk.Button(
            actions, text="Xuất CSV", command=self._export_discovery_csv
        ).pack(side="right", padx=6)

        self.discovery_tree = self._tree(
            frame,
            (
                "keyword",
                "opportunity",
                "intent",
                "cluster",
                "source",
                "impressions",
                "clicks",
                "position",
                "landing_page",
                "metrics",
            ),
            (
                "Keyword",
                "Cơ hội",
                "Search Intent",
                "Cluster",
                "Nguồn",
                "GSC Impressions",
                "Clicks",
                "Position",
                "Landing Page gợi ý",
                "Volume/KD",
            ),
            (260, 70, 125, 170, 220, 115, 75, 75, 340, 170),
        )
        self.discovery_tree.configure(selectmode="extended")
        self.discovery_note = ttk.Label(
            frame,
            text=(
                "Cơ hội là điểm ưu tiên nội bộ 0-100, không phải Keyword Difficulty. "
                "GSC Impressions không phải Search Volume."
            ),
            style="Muted.TLabel",
        )
        self.discovery_note.pack(anchor="w", pady=(5, 0))

    def _start_keyword_discovery(self):
        if not self._require_project("tìm bộ từ khóa"):
            return
        seeds = split_seed_keywords(self.discovery_seed_text.get("1.0", "end"))
        sources = (
            self.discovery_use_google.get(),
            self.discovery_use_gsc.get(),
            self.discovery_use_website.get(),
        )
        if not any(sources):
            self._show_smart_error(
                "Chưa chọn nguồn dữ liệu",
                "Phải bật ít nhất một nguồn Google Suggest, GSC hoặc Website.",
                "Chọn nguồn phù hợp rồi chạy lại.",
                retry=self._start_keyword_discovery,
            )
            return
        if self.discovery_use_google.get() and not seeds:
            self._show_smart_error(
                "Thiếu từ khóa gốc",
                "Google Suggest cần ít nhất một từ khóa gốc.",
                "Nhập 1-10 từ khóa, mỗi dòng một từ hoặc phân cách bằng dấu phẩy.",
                retry=self._start_keyword_discovery,
            )
            return
        try:
            limit = max(50, min(2000, int(self.discovery_limit.get())))
        except (TypeError, ValueError):
            limit = 500
            self.discovery_limit.set(limit)
        config = {
            "use_google": bool(self.discovery_use_google.get()),
            "use_gsc": bool(self.discovery_use_gsc.get()),
            "use_website": bool(self.discovery_use_website.get()),
            "country": clean_text(self.country.get()) or "vn",
            "language": clean_text(self.language.get()) or "vi",
            "level": self.discovery_level.get(),
            "cluster_detail": (
                self.cluster_detail.get()
                if hasattr(self, "cluster_detail")
                else "Balanced"
            ),
        }
        self.discovery_cancel_event.clear()
        self.discovery_running = True
        self.discovery_start_btn.configure(state="disabled")
        self._begin_operation("Tìm bộ từ khóa", self._start_keyword_discovery)
        threading.Thread(
            target=self._keyword_discovery_worker,
            args=(seeds, limit, config, list(self.gsc_rows), list(self.pages)),
            daemon=True,
        ).start()

    def _keyword_discovery_worker(self, seeds, limit, config, gsc_source, pages):
        try:
            suggest_rows = []
            if config["use_google"]:
                client = GoogleSuggestClient()

                def progress(query, current, total):
                    percent = min(65, int(current / max(1, total) * 65))
                    self.discovery_events.put(
                        ("progress", f"Google Suggest: {query}", percent)
                    )

                suggest_rows = client.expand(
                    seeds,
                    country=config["country"],
                    language=config["language"],
                    level=config["level"],
                    max_keywords=limit,
                    progress=progress,
                    cancelled=self.discovery_cancel_event.is_set,
                )
            if self.discovery_cancel_event.is_set():
                self.discovery_events.put(("cancelled",))
                return
            self.discovery_events.put(("progress", "Đang tổng hợp dữ liệu GSC…", 72))
            gsc_rows = (
                aggregate_gsc_queries(gsc_source)
                if config["use_gsc"]
                else []
            )
            self.discovery_events.put(("progress", "Đang đọc chủ đề website…", 80))
            website_rows = (
                website_keyword_candidates(pages)
                if config["use_website"]
                else []
            )
            result = merge_keyword_candidates(
                suggest_rows=suggest_rows,
                gsc_rows=gsc_rows,
                website_rows=website_rows,
                pages=pages,
                cluster_detail=config["cluster_detail"],
                limit=limit,
            )
            if not result:
                raise ValueError(
                    "Không tìm thấy keyword. Hãy nhập seed khác, lấy GSC hoặc chạy Website Audit."
                )
            self.discovery_events.put(("done", result))
        except Exception as exc:
            self.discovery_events.put(
                ("error", explain_exception(exc, "Keyword Discovery"))
            )

    def _poll_discovery_events(self):
        try:
            while True:
                event = self.discovery_events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "done":
                    self.keyword_discovery_rows = event[1]
                    self.discovery_running = False
                    self.discovery_start_btn.configure(state="normal")
                    self.progress.set(100)
                    self._render_discovery()
                    self._save_state()
                    self._refresh_onboarding()
                    self.status.set(
                        f"Đã tìm {len(self.keyword_discovery_rows):,} keyword."
                    )
                    self._end_operation(success=True)
                elif kind == "cancelled":
                    self.discovery_running = False
                    self.discovery_start_btn.configure(state="normal")
                    self.status.set("Đã hủy tìm bộ từ khóa.")
                    self._end_operation(success=False)
                elif kind == "error":
                    self.discovery_running = False
                    self.discovery_start_btn.configure(state="normal")
                    error = event[1]
                    self._end_operation(success=False)
                    self._show_smart_error(
                        error.title,
                        error.message,
                        error.hint,
                        retry=self._start_keyword_discovery,
                    )
        except queue.Empty:
            pass
        self.after(130, self._poll_discovery_events)

    def _render_discovery(self):
        if not hasattr(self, "discovery_tree"):
            return
        self._clear_tree(self.discovery_tree)
        for index, row in enumerate(self.keyword_discovery_rows):
            self.discovery_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row.get("keyword", ""),
                    row.get("opportunity", 0),
                    row.get("intent", ""),
                    row.get("cluster", ""),
                    row.get("source", ""),
                    f"{float(row.get('gsc_impressions') or 0):,.0f}",
                    f"{float(row.get('gsc_clicks') or 0):,.0f}",
                    f"{float(row.get('gsc_position') or 0):.1f}"
                    if row.get("gsc_position")
                    else "",
                    row.get("landing_page", "") or "Đề xuất tạo mới",
                    row.get("metrics_status", ""),
                ),
            )
        summary = discovery_summary(self.keyword_discovery_rows)
        self.discovery_metric_keywords.configure(text=f"{summary['keywords']:,}")
        self.discovery_metric_clusters.configure(text=f"{summary['clusters']:,}")
        self.discovery_metric_high.configure(text=f"{summary['high_opportunity']:,}")
        self.discovery_metric_gsc.configure(text=f"{summary['gsc_keywords']:,}")
        self.discovery_metric_mapped.configure(text=f"{summary['mapped']:,}")

    def _select_high_opportunity(self):
        self.discovery_tree.selection_remove(self.discovery_tree.selection())
        for index, row in enumerate(self.keyword_discovery_rows):
            if int(row.get("opportunity", 0)) >= 70:
                self.discovery_tree.selection_add(str(index))

    def _selected_discovery_rows(self):
        rows = []
        for item in self.discovery_tree.selection():
            try:
                rows.append(self.keyword_discovery_rows[int(item)])
            except (ValueError, IndexError):
                continue
        return rows

    def _add_selected_discovery(self, silent=False):
        selected = self._selected_discovery_rows()
        if not selected:
            if not silent:
                messagebox.showinfo(
                    "Chưa chọn keyword",
                    "Chọn một hoặc nhiều dòng cần đưa sang Keyword Intelligence.",
                )
            return 0
        converted = discovery_to_keyword_rows(selected)
        before = len(self.keyword_rows)
        self.keyword_rows = deduplicate_keywords([*self.keyword_rows, *converted])
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()
        self._refresh_onboarding()
        added = max(0, len(self.keyword_rows) - before)
        if not silent:
            messagebox.showinfo(
                "Đã chuyển keyword",
                f"Đã xử lý {len(selected):,} dòng; thêm mới {added:,} keyword.\n"
                "Volume/KD để trống vì chưa có nguồn metrics thật.",
            )
            self._open_workspace("Nghiên cứu", "Keyword Intelligence")
        return added

    def _high_opportunity_to_briefs(self):
        self._select_high_opportunity()
        selected = self._selected_discovery_rows()
        if not selected:
            messagebox.showinfo(
                "Chưa có Cơ hội cao",
                "Chưa có keyword đạt điểm Cơ hội từ 70 trở lên.",
            )
            return
        self._add_selected_discovery(silent=True)
        self._create_content_briefs(silent=True)
        self._open_workspace("Kế hoạch & Thực thi", "Content Workflow")
        messagebox.showinfo(
            "Đã tạo Content Brief",
            f"Đã chuyển {len(selected):,} keyword Cơ hội cao và tạo "
            f"{len(self.content_briefs):,} Content Brief.",
        )

    def _export_discovery_csv(self):
        if not self.keyword_discovery_rows:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy tìm bộ từ khóa trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="keyword-discovery-v47.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            export_discovery_csv(path, self.keyword_discovery_rows)
            messagebox.showinfo("Đã xuất CSV", path)

    def _export_discovery_xlsx(self):
        if not self.keyword_discovery_rows:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy tìm bộ từ khóa trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile="keyword-discovery-v47.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_discovery_workbook(path, self.keyword_discovery_rows)
        except Exception as exc:
            error = explain_exception(exc, "Xuất Keyword Discovery Excel")
            self._show_smart_error(error.title, error.message, error.hint)
            return
        messagebox.showinfo("Đã xuất Excel", path)

    def _open_wizard(self):
        SetupWizardV47(self)

    def _refresh_onboarding(self):
        if not hasattr(self, "onboarding_tree"):
            return
        rows = onboarding_statuses_v47(
            self.current_project,
            self.pages,
            self.keyword_rows,
            self.keyword_discovery_rows,
            self.gsc_rows,
            self.latest_pagespeed,
            self.wordpress_ok,
        )
        self._clear_tree(self.onboarding_tree)
        for row in rows:
            self.onboarding_tree.insert(
                "", "end", values=(row["step"], row["name"], row["status"])
            )
        pending = next(
            (row["name"] for row in rows if row["status"] != "Đã kết nối"), None
        )
        self.next_action_label.configure(
            text=(
                f"Bước tiếp theo: {pending}."
                if pending
                else "Thiết lập hoàn tất. Hãy xử lý Fix Queue và theo dõi kết quả."
            )
        )

    def _load_project_state(self):
        super()._load_project_state()
        if not self.current_project:
            return
        self.keyword_discovery_rows = self.store.load_project_state(
            self.current_project["id"], "keyword-discovery-v47", []
        ) or []
        self._render_discovery()
        self._refresh_onboarding()

    def _save_state(self):
        super()._save_state()
        if self.current_project:
            self.store.save_project_state(
                self.current_project["id"],
                "keyword-discovery-v47",
                self.keyword_discovery_rows,
            )

    def _load_demo(self):
        super()._load_demo()
        self.keyword_discovery_rows = merge_keyword_candidates(
            gsc_rows=aggregate_gsc_queries(self.gsc_rows),
            website_rows=website_keyword_candidates(self.pages),
            pages=self.pages,
            limit=100,
        )
        self._render_discovery()
        self._save_state()
        self._refresh_onboarding()

    def _cancel_current_operation(self):
        if self.discovery_running:
            self.discovery_cancel_event.set()
            self.status.set(
                "Đã yêu cầu hủy tìm keyword. Tool sẽ dừng sau request hiện tại."
            )
            return
        super()._cancel_current_operation()

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
                "Cài lại bộ Setup V4.7 đầy đủ.",
            )
            return
        webbrowser.open(path.as_uri())

    def _on_close(self):
        self.discovery_cancel_event.set()
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
    app = AppV47()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
