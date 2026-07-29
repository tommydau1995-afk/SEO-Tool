"""SEO AI Studio V4.6 - guided complete SEO workflow."""

from __future__ import annotations

import argparse
import json
import queue
import threading
import time
import webbrowser
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse
import tkinter as tk

from app_v44 import AppV44
from seo_v4_core import (
    PageSpeedClient,
    SiteAuditor,
    build_fix_queue,
    clean_text,
    compare_snapshots,
    export_csv,
    normalize_url,
)
from seo_v43_core import (
    SearchConsoleClient,
    explain_exception,
    run_scheduled_audit,
)
from seo_v46_core import (
    GUIDE_FILE,
    VERSION,
    CredentialVault,
    CruxClient,
    ProjectStoreV46,
    SmartGoogleResearcher,
    UpdateChecker,
    build_content_briefs,
    build_detailed_issues,
    demo_payload,
    detailed_issue_rows,
    extract_urls,
    onboarding_statuses,
    support_information,
)


class SetupWizard(tk.Toplevel):
    """Seven-step first-run wizard for non-technical users."""

    STEP_NAMES = (
        "Tạo dự án",
        "Nhập website",
        "Quốc gia & ngôn ngữ",
        "Kiểm tra website",
        "Kết nối dữ liệu",
        "Import Semrush",
        "Full SEO Audit",
    )

    def __init__(self, app: "AppV46"):
        super().__init__(app)
        self.app = app
        self.title("Thiết lập SEO AI Studio V4.6")
        self.geometry("830x560")
        self.minsize(760, 520)
        self.transient(app)
        self.grab_set()
        self.index = 0
        self.project_name = tk.StringVar(
            value=app.project_name.get() or "Dự án SEO mới"
        )
        self.website = tk.StringVar(
            value=app.project_url.get() or app.website.get()
        )
        self.country = tk.StringVar(value=app.country.get() or "vn")
        self.language = tk.StringVar(value=app.language.get() or "vi")
        self.semrush_path = tk.StringVar()
        self.run_audit = tk.BooleanVar(value=True)
        self.frames: list[ttk.Frame] = []
        self._build()
        self._show(0)

    def _build(self):
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill="both", expand=True)
        left = ttk.LabelFrame(shell, text="7 bước thiết lập", padding=10)
        left.pack(side="left", fill="y", padx=(0, 12))
        self.step_labels = []
        for number, name in enumerate(self.STEP_NAMES, 1):
            label = ttk.Label(left, text=f"{number}. {name}", width=25)
            label.pack(anchor="w", pady=7)
            self.step_labels.append(label)

        self.body = ttk.Frame(shell)
        self.body.pack(side="left", fill="both", expand=True)
        self._project_step()
        self._website_step()
        self._market_step()
        self._check_step()
        self._connections_step()
        self._semrush_step()
        self._audit_step()

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        self.back_btn = ttk.Button(buttons, text="Quay lại", command=self._back)
        self.back_btn.pack(side="left")
        ttk.Button(buttons, text="Bỏ qua hướng dẫn", command=self._skip).pack(
            side="left", padx=7
        )
        self.next_btn = ttk.Button(
            buttons, text="Tiếp theo", style="Accent.TButton", command=self._next
        )
        self.next_btn.pack(side="right")

    def _page(self, title: str, description: str) -> ttk.Frame:
        frame = ttk.Frame(self.body, padding=10)
        ttk.Label(frame, text=title, style="Head.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text=description,
            wraplength=540,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(5, 18))
        self.frames.append(frame)
        return frame

    def _project_step(self):
        frame = self._page(
            "Bước 1 - Tạo dự án",
            "Mỗi website nên có một dự án riêng để lưu lịch sử Audit, keyword và báo cáo.",
        )
        ttk.Label(frame, text="Tên dự án:").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.project_name, width=55).pack(
            fill="x", pady=(5, 0)
        )

    def _website_step(self):
        frame = self._page(
            "Bước 2 - Nhập website",
            "Nhập URL đầy đủ. Tool sẽ chuẩn hóa HTTP/HTTPS và dùng URL này cho Audit.",
        )
        ttk.Label(frame, text="Website:").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.website, width=65).pack(
            fill="x", pady=(5, 0)
        )
        ttk.Label(
            frame,
            text="Ví dụ: https://example.com/",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=6)

    def _market_step(self):
        frame = self._page(
            "Bước 3 - Quốc gia và ngôn ngữ",
            "Thiết lập này được dùng cho nghiên cứu Top 5 và theo dõi thứ hạng.",
        )
        form = ttk.Frame(frame)
        form.pack(anchor="w")
        ttk.Label(form, text="Quốc gia:").grid(row=0, column=0, sticky="e", pady=5)
        ttk.Entry(form, textvariable=self.country, width=12).grid(
            row=0, column=1, padx=8
        )
        ttk.Label(form, text="Ngôn ngữ:").grid(row=1, column=0, sticky="e", pady=5)
        ttk.Entry(form, textvariable=self.language, width=12).grid(
            row=1, column=1, padx=8
        )

    def _check_step(self):
        frame = self._page(
            "Bước 4 - Kiểm tra website",
            "Tool sẽ kiểm tra định dạng URL ngay bây giờ. Crawl đầy đủ được thực hiện ở bước cuối.",
        )
        ttk.Label(
            frame,
            text="✓ URL hợp lệ sẽ hiển thị trạng thái Đã kết nối.\n"
            "✓ Crawl kiểm tra HTTP, Title, Meta, H1, Canonical, Link và Sitemap.",
            wraplength=530,
        ).pack(anchor="w")

    def _connections_step(self):
        frame = self._page(
            "Bước 5 - Kết nối dữ liệu",
            "GSC, PageSpeed/CrUX và WordPress là tùy chọn. Bạn có thể thiết lập sau trong Trung tâm kết nối.",
        )
        lines = (
            "• GSC: chọn Service Account JSON và nhập property.\n"
            "• PageSpeed/CrUX: nhập Google API Key nếu chạy thường xuyên.\n"
            "• WordPress: dùng Username và Application Password.\n"
            "• Mật khẩu có thể lưu trong Windows Credential Manager."
        )
        ttk.Label(frame, text=lines, wraplength=540).pack(anchor="w")
        ttk.Button(
            frame,
            text="Mở Trung tâm kết nối sau khi hoàn tất",
            command=lambda: self.app.status.set(
                "Hoàn tất Wizard rồi mở Trung tâm kết nối."
            ),
        ).pack(anchor="w", pady=14)

    def _semrush_step(self):
        frame = self._page(
            "Bước 6 - Import Semrush",
            "Có thể bỏ qua. Tool hỗ trợ CSV, TSV và Excel chứa Keyword, Volume và KD.",
        )
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.semrush_path).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Chọn file", command=self._browse_semrush).pack(
            side="left", padx=7
        )

    def _audit_step(self):
        frame = self._page(
            "Bước 7 - Full SEO Audit",
            "Sau khi lưu dự án, tool có thể tự Crawl, kiểm tra Technical SEO, Link Map, PageSpeed, GSC và tạo Roadmap.",
        )
        ttk.Checkbutton(
            frame,
            text="Chạy Full SEO Audit ngay sau khi hoàn tất",
            variable=self.run_audit,
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="Nếu website lớn, hãy bắt đầu với 100 URL rồi tăng dần.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=8)

    def _browse_semrush(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                ("Semrush", "*.csv *.tsv *.xlsx *.xlsm"),
                ("Tất cả", "*.*"),
            ],
        )
        if path:
            self.semrush_path.set(path)

    def _show(self, index):
        self.index = max(0, min(len(self.frames) - 1, index))
        for frame in self.frames:
            frame.pack_forget()
        self.frames[self.index].pack(fill="both", expand=True)
        for number, label in enumerate(self.step_labels):
            label.configure(
                foreground="#1769C2" if number == self.index else "#334155"
            )
        self.back_btn.configure(state="normal" if self.index else "disabled")
        self.next_btn.configure(
            text="Hoàn tất" if self.index == len(self.frames) - 1 else "Tiếp theo"
        )

    def _back(self):
        self._show(self.index - 1)

    def _next(self):
        if self.index == 0 and not clean_text(self.project_name.get()):
            messagebox.showwarning("Thiếu tên", "Hãy nhập tên dự án.", parent=self)
            return
        if self.index in (1, 3) and not normalize_url(self.website.get()):
            messagebox.showwarning(
                "URL chưa hợp lệ",
                "Nhập URL dạng https://tenmien.com/",
                parent=self,
            )
            return
        if self.index < len(self.frames) - 1:
            self._show(self.index + 1)
            return
        self._finish()

    def _finish(self):
        app = self.app
        try:
            project = app.store.upsert_project(
                self.project_name.get(), self.website.get()
            )
        except ValueError as exc:
            messagebox.showwarning("Thiếu thông tin", str(exc), parent=self)
            return
        app.country.set(clean_text(self.country.get()) or "vn")
        app.language.set(clean_text(self.language.get()) or "vi")
        app._refresh_projects(project["id"])
        app._select_project()
        app._save_app_settings(first_run_complete=True)
        semrush = clean_text(self.semrush_path.get())
        should_run = bool(self.run_audit.get())
        self.grab_release()
        self.destroy()
        if semrush:
            app._import_keyword_path(semrush)
        app._refresh_onboarding()
        if should_run:
            app.after(250, app._start_full_audit)

    def _skip(self):
        self.app._save_app_settings(first_run_complete=True)
        self.grab_release()
        self.destroy()


class AppV46(AppV44):
    WORKSPACES = (
        "Tổng quan",
        "Nghiên cứu",
        "Audit",
        "Kế hoạch & Thực thi",
        "Theo dõi",
    )

    def __init__(self):
        self.v46_events = queue.Queue()
        self.operation_name = ""
        self.operation_started = 0.0
        self.last_retry = None
        self.full_audit_running = False
        self.content_briefs = []
        self.wordpress_ok = False
        self.last_support_info = ""
        super().__init__()
        self.store = ProjectStoreV46()
        self.vault = CredentialVault()
        self._refresh_projects()
        self.title(f"SEO AI Studio V{VERSION} - Complete Guided Workflow")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_app_settings()
        self.after(150, self._poll_v46_events)
        self.after(500, self._offer_recovery)
        self.after(800, self._offer_first_run)
        self.after(1000, self._tick_elapsed)

    def _style(self):
        super()._style()
        style = ttk.Style(self)
        style.configure("Workspace.TNotebook.Tab", padding=(13, 8))
        style.configure("Success.TLabel", foreground="#2E7D32")
        style.configure("Warning.TLabel", foreground="#B45309")
        style.configure("Danger.TLabel", foreground="#C62828")

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 10))
        frame.pack(fill="x")
        ttk.Label(frame, text="SEO AI Studio V4.6", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            frame,
            text="Easy Workflow • Full Audit • Content Brief • CrUX • Recovery",
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

    def _tabs(self):
        self.workspace_tabs = ttk.Notebook(self, style="Workspace.TNotebook")
        self.workspace_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.workspace_frames = {}
        self.workspace_notebooks = {}

        def workspace(title):
            frame = ttk.Frame(self.workspace_tabs, padding=5)
            notebook = ttk.Notebook(frame)
            notebook.pack(fill="both", expand=True)
            self.workspace_tabs.add(frame, text=title)
            self.workspace_frames[title] = frame
            self.workspace_notebooks[title] = notebook
            self.tabs = notebook

        workspace("Tổng quan")
        self._easy_start_tab()
        self._dashboard_tab()
        self._projects_tab()

        workspace("Nghiên cứu")
        self._keyword_tab()
        self._serp_writer_tab()

        workspace("Audit")
        self._audit_tab()
        self._crawl_index_tab()
        self._performance_tab()
        self._link_map_tab()
        self._gsc_tab()

        workspace("Kế hoạch & Thực thi")
        self._fix_queue_tab()
        self._workflow_tab()
        self._master_tab()

        workspace("Theo dõi")
        self._automation_tab()
        self._growth_tab()
        self._integrations_tab()

        self.tabs = self.workspace_tabs
        self.after_idle(self._apply_mode)

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
            text="Một dự án - Một nút Full SEO Audit - Một danh sách việc cần làm",
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
            ("Import Semrush", self._import_keywords),
            ("Trung tâm kết nối", lambda: self._open_workspace("Theo dõi", "API & Kết nối")),
            ("Tạo Content Brief", lambda: self._open_workspace("Kế hoạch & Thực thi", "Content Workflow")),
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
            "Tool sẽ tự Crawl, tạo Internal Link Map, kiểm tra PageSpeed/CrUX, "
            "lấy GSC khi đã kết nối, tạo Fix Queue và Roadmap 30/60/90.",
        )
        self._refresh_onboarding()

    def _fix_queue_tab(self):
        frame = self._tab("Fix Queue chi tiết")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(bar, text="Đánh dấu Đã sửa", command=self._mark_fix_done).pack(
            side="left"
        )
        ttk.Button(bar, text="Đưa về Cần sửa", command=self._mark_fix_open).pack(
            side="left", padx=7
        )
        ttk.Button(bar, text="Xuất CSV", command=self._export_fixes).pack(
            side="left"
        )
        ttk.Label(
            bar,
            text="Mỗi lỗi gồm nguyên nhân, cách sửa, độ khó và tác động dự kiến.",
            foreground="#555",
        ).pack(side="right")
        self.fix_tree = self._tree(
            frame,
            (
                "priority",
                "issue",
                "url",
                "why",
                "recommendation",
                "difficulty",
                "impact",
                "status",
            ),
            (
                "Ưu tiên",
                "Lỗi",
                "URL",
                "Vì sao quan trọng",
                "Cách sửa",
                "Độ khó",
                "Tác động",
                "Trạng thái",
            ),
            (65, 170, 330, 310, 410, 80, 80, 100),
        )

    def _workflow_tab(self):
        frame = self._tab("Content Workflow")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Button(
            bar,
            text="Tạo Content Brief từ Cluster",
            style="Accent.TButton",
            command=self._create_content_briefs,
        ).pack(side="left")
        ttk.Button(
            bar, text="Đưa sang Top 5", command=self._brief_to_top5
        ).pack(side="left", padx=7)
        ttk.Button(
            bar, text="Đưa Brief sang Outline", command=self._brief_to_outline
        ).pack(side="left")
        ttk.Button(
            bar, text="Kiểm tra Landing Page", command=self._recheck_landing_page
        ).pack(side="left", padx=7)
        pane = ttk.Panedwindow(frame, orient="horizontal")
        pane.pack(fill="both", expand=True, pady=(10, 0))
        left = ttk.LabelFrame(pane, text="Cluster → Landing Page → Brief", padding=8)
        right = ttk.LabelFrame(pane, text="Content Brief chi tiết", padding=8)
        pane.add(left, weight=2)
        pane.add(right, weight=3)
        self.content_brief_tree = self._tree(
            left,
            ("cluster", "primary", "intent", "volume", "kd", "landing", "status"),
            (
                "Cluster",
                "Primary Keyword",
                "Intent",
                "Volume",
                "KD",
                "Landing Page",
                "Trạng thái",
            ),
            (180, 230, 110, 80, 70, 330, 100),
        )
        self.content_brief_tree.bind(
            "<<TreeviewSelect>>", lambda _event: self._show_selected_brief()
        )
        self.content_brief_text = tk.Text(
            right, wrap="word", font=("Segoe UI", 10)
        )
        self.content_brief_text.pack(fill="both", expand=True)
        self._set_text(
            self.content_brief_text,
            "Import Semrush và nhấn Tạo Content Brief từ Cluster.",
        )

    def _apply_mode(self):
        if not hasattr(self, "workspace_tabs"):
            return
        mode = self.mode_var.get() if hasattr(self, "mode_var") else "Easy"
        for title in self.WORKSPACES:
            frame = self.workspace_frames[title]
            try:
                self.workspace_tabs.hide(frame)
            except tk.TclError:
                pass
        visible = self.WORKSPACES if mode == "Pro" else ("Tổng quan",)
        for title in visible:
            self.workspace_tabs.add(self.workspace_frames[title], text=title)
        if "Tổng quan" in visible:
            self.workspace_tabs.select(self.workspace_frames["Tổng quan"])
        if hasattr(self, "status"):
            self.status.set(
                "Easy Mode: làm theo từng bước."
                if mode == "Easy"
                else "Pro Mode: đã hiển thị toàn bộ chức năng."
            )
        self._save_app_settings()

    def _open_workspace(self, workspace: str, tab_title: str | None = None):
        if workspace != "Tổng quan" and self.mode_var.get() != "Pro":
            self.mode_var.set("Pro")
        frame = self.workspace_frames.get(workspace)
        if frame:
            self.workspace_tabs.select(frame)
        if tab_title:
            notebook = self.workspace_notebooks.get(workspace)
            if notebook:
                for tab_id in notebook.tabs():
                    if notebook.tab(tab_id, "text") == tab_title:
                        notebook.select(tab_id)
                        break

    def _open_wizard(self):
        SetupWizard(self)

    def _offer_first_run(self):
        settings = self.store.load_app_settings()
        if not settings.get("first_run_complete") and not self.store.list_projects():
            self._open_wizard()

    def _save_app_settings(self, first_run_complete=None):
        if not hasattr(self, "store") or not isinstance(self.store, ProjectStoreV46):
            return
        settings = self.store.load_app_settings()
        settings.update(
            {
                "mode": self.mode_var.get() if hasattr(self, "mode_var") else "Easy",
                "last_project_id": (self.current_project or {}).get("id", ""),
                "country": self.country.get() if hasattr(self, "country") else "vn",
                "language": self.language.get() if hasattr(self, "language") else "vi",
            }
        )
        if first_run_complete is not None:
            settings["first_run_complete"] = bool(first_run_complete)
        self.store.save_app_settings(settings)

    def _load_app_settings(self):
        settings = self.store.load_app_settings()
        self.country.set(settings.get("country") or "vn")
        self.language.set(settings.get("language") or "vi")
        self.mode_var.set(settings.get("mode") or "Easy")
        project_id = settings.get("last_project_id")
        if project_id:
            self._refresh_projects(project_id)
            self._select_project()
        self._refresh_onboarding()

    def _offer_recovery(self):
        recovery = self.store.load_recovery()
        if not recovery.get("running"):
            return
        operation = recovery.get("operation") or "công việc trước"
        if not messagebox.askyesno(
            "Khôi phục dữ liệu",
            f"Phiên trước dừng khi đang chạy: {operation}.\n"
            "Khôi phục dự án, đầu vào và keyword đã lưu?",
        ):
            self.store.clear_recovery()
            return
        payload = recovery.get("payload") or {}
        project_id = payload.get("project_id")
        if project_id:
            self._refresh_projects(project_id)
            self._select_project()
        if payload.get("website"):
            self.website.set(payload["website"])
        if payload.get("keyword_rows"):
            self.keyword_rows = payload["keyword_rows"]
            self._render_keywords()
        self.status.set(f"Đã khôi phục dữ liệu từ thao tác {operation}.")
        self.store.clear_recovery()
        self._refresh_onboarding()

    def _recovery_payload(self):
        return {
            "project_id": (self.current_project or {}).get("id", ""),
            "website": self.website.get(),
            "keyword_rows": self.keyword_rows,
        }

    def _begin_operation(self, name: str, retry=None):
        self.operation_name = clean_text(name)
        self.operation_started = time.monotonic()
        self.last_retry = retry
        self.cancel_btn.configure(state="normal")
        self.retry_btn.configure(state="disabled")
        self.status.set(f"Đang chạy: {self.operation_name}")
        self.store.begin_recovery(self.operation_name, self._recovery_payload())

    def _end_operation(self, success=True):
        if success:
            self.store.clear_recovery()
            self.last_retry = None
            self.retry_btn.configure(state="disabled")
        else:
            self.retry_btn.configure(
                state="normal" if callable(self.last_retry) else "disabled"
            )
        self.operation_name = ""
        self.operation_started = 0.0
        self.cancel_btn.configure(state="disabled")
        self.elapsed_var.set("")

    def _tick_elapsed(self):
        if self.operation_started:
            seconds = max(0, int(time.monotonic() - self.operation_started))
            self.elapsed_var.set(
                f"{self.operation_name} • {seconds // 60:02d}:{seconds % 60:02d}"
            )
        self.after(1000, self._tick_elapsed)

    def _cancel_current_operation(self):
        self.stop_event.set()
        self.full_audit_running = False
        self.status.set("Đã yêu cầu hủy. Tool sẽ dừng ở bước an toàn gần nhất.")
        self._end_operation(success=False)

    def _retry_last(self):
        retry = self.last_retry
        if callable(retry):
            self.retry_btn.configure(state="disabled")
            retry()

    def _require_project(self, action: str) -> bool:
        if self.current_project:
            return True
        self._show_smart_error(
            "Chưa chọn dự án",
            f"Không thể {action} khi chưa có dự án.",
            "Mở Thiết lập từng bước hoặc tải dữ liệu Demo.",
            retry=self._open_wizard,
        )
        return False

    def _start_audit(self):
        if not self._require_project("chạy Website Audit"):
            return
        if not normalize_url(self.website.get()):
            self._show_smart_error(
                "URL chưa hợp lệ",
                "Website đang trống hoặc sai định dạng.",
                "Nhập URL dạng https://tenmien.com/ rồi thử lại.",
            )
            return
        self._begin_operation("Website Audit", retry=self._start_audit)
        super()._start_audit()

    def _start_serp_research(self):
        if not self._require_project("phân tích Top 5"):
            return
        if not clean_text(self.serp_keyword.get()):
            self._show_smart_error(
                "Thiếu keyword",
                "Chưa nhập từ khóa cần phân tích.",
                "Nhập keyword ở đầu màn hình Top 5.",
            )
            return
        self._begin_operation("Top 5 Google", retry=self._start_serp_research)
        super()._start_serp_research()

    def _serp_worker(self, keyword, manual_urls=None):
        try:
            result = SmartGoogleResearcher().research(
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
            self.events.put(("smart-error", explain_exception(exc, "Top 5 Direct")))

    def _serp_writer_tab(self):
        super()._serp_writer_tab()
        # The current tab is the newly-created Top 5 frame.
        notebook = self.workspace_notebooks.get("Nghiên cứu")
        if not notebook:
            return
        tab_id = notebook.tabs()[-1]
        frame = self.nametowidget(tab_id)
        tools = ttk.Frame(frame)
        tools.pack(fill="x", before=frame.winfo_children()[1], pady=(0, 7))
        ttk.Button(
            tools, text="Mở Google", command=self._open_google_search
        ).pack(side="left")
        ttk.Button(
            tools,
            text="Dán URL từ clipboard",
            style="Accent.TButton",
            command=self._paste_manual_urls,
        ).pack(side="left", padx=7)
        ttk.Label(
            tools,
            text="Khi Google yêu cầu CAPTCHA/Consent, hãy dùng hai nút này.",
            style="Muted.TLabel",
        ).pack(side="left")

    def _open_google_search(self):
        keyword = clean_text(self.serp_keyword.get())
        if not keyword:
            self._show_smart_error(
                "Thiếu keyword",
                "Chưa có từ khóa để mở Google.",
                "Nhập keyword rồi nhấn Mở Google.",
            )
            return
        webbrowser.open(
            SmartGoogleResearcher.google_search_url(
                keyword, self.country.get(), self.language.get()
            )
        )
        self.status.set("Đã mở Google. Sao chép tối đa 5 URL kết quả tự nhiên.")

    def _paste_manual_urls(self):
        try:
            value = self.clipboard_get()
        except tk.TclError:
            value = ""
        urls = extract_urls(value, limit=5)
        if not urls:
            self._show_smart_error(
                "Clipboard chưa có URL",
                "Không tìm thấy liên kết HTTP/HTTPS trong clipboard.",
                "Sao chép 5 URL kết quả Google rồi nhấn lại.",
            )
            return
        self.manual_serp_urls.delete("1.0", "end")
        self.manual_serp_urls.insert("1.0", "\n".join(urls))
        self.status.set(f"Đã dán {len(urls)} URL thủ công.")

    def _import_keywords(self):
        if not self._require_project("import Semrush"):
            return
        path = filedialog.askopenfilename(
            filetypes=[
                ("Semrush", "*.csv *.tsv *.xlsx *.xlsm"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xlsm"),
                ("Tất cả", "*.*"),
            ]
        )
        if path:
            self._import_keyword_path(path)

    def _import_keyword_path(self, path):
        from seo_v44_keywords import SemrushKeywordImporter

        try:
            detail = self.cluster_detail.get() if hasattr(self, "cluster_detail") else "Balanced"
            rows, summary = SemrushKeywordImporter().read(path, detail)
            if not rows:
                raise ValueError("File không có keyword hợp lệ.")
            existing = list(self.keyword_rows)
            self.keyword_rows = existing + rows
            self.keyword_rows = self._deduplicate_current()
            self.keyword_import_summary = summary
            self._render_keywords()
            self._create_content_briefs(silent=True)
            self._save_state()
            self._refresh_onboarding()
            self.status.set(f"Đã import {len(rows)} keyword từ {Path(path).name}.")
        except Exception as exc:
            error = explain_exception(exc, "Import Semrush")
            self._show_smart_error(error.title, error.message, error.hint)

    def _run_pagespeed(self):
        if not self._require_project("chạy PageSpeed/CrUX"):
            return
        url = normalize_url(self.psi_url.get() or self.website.get())
        if not url:
            self._show_smart_error(
                "URL PageSpeed chưa hợp lệ",
                "Không có URL để phân tích.",
                "Chọn dự án hoặc nhập URL hợp lệ.",
            )
            return
        self._begin_operation("PageSpeed & CrUX", retry=self._run_pagespeed)
        threading.Thread(
            target=self._pagespeed_worker,
            args=(url, self.psi_strategy.get()),
            daemon=True,
        ).start()

    def _pagespeed_worker(self, url, strategy):
        try:
            result = PageSpeedClient(self.pagespeed_key.get()).analyze(url, strategy)
            if self.pagespeed_key.get().strip():
                try:
                    result["crux"] = CruxClient(
                        self.pagespeed_key.get()
                    ).query(url, "PHONE" if strategy == "mobile" else "DESKTOP")
                except Exception as exc:
                    result["crux_error"] = clean_text(exc)
            self.events.put(("pagespeed-done", result))
        except Exception as exc:
            self.events.put(
                ("smart-error", explain_exception(exc, "PageSpeed/CrUX"))
            )

    def _finish_pagespeed(self, result):
        self.latest_pagespeed = result
        crux = result.get("crux") or {}
        lines = [
            "DỮ LIỆU PHÒNG THỬ NGHIỆM - LIGHTHOUSE",
            f"URL: {result.get('url', '')}",
            f"Thiết bị mô phỏng: {result.get('strategy', '')}",
            f"Performance: {result.get('performance')}/100",
            f"SEO: {result.get('seo')}/100",
            f"Accessibility: {result.get('accessibility')}/100",
            f"Best Practices: {result.get('best_practices')}/100",
            f"Lab LCP: {result.get('lcp_ms')} ms",
            f"Lab CLS: {result.get('cls')}",
            f"Lab TTFB: {result.get('ttfb_ms')} ms",
            "",
            "DỮ LIỆU NGƯỜI DÙNG THỰC - CRUX",
        ]
        if crux and not crux.get("unavailable"):
            lines.extend(
                [
                    f"Nguồn: {crux.get('source', 'Chrome UX Report')}",
                    f"Field LCP p75: {crux.get('lcp_ms')} ms",
                    f"Field INP p75: {crux.get('inp_ms')} ms",
                    f"Field CLS p75: {crux.get('cls')}",
                    f"Field TTFB p75: {crux.get('ttfb_ms')} ms",
                ]
            )
        else:
            lines.append(
                crux.get("message")
                or result.get("crux_error")
                or "Chưa có API Key hoặc URL chưa đủ dữ liệu CrUX."
            )
        lines.extend(["", "CƠ HỘI TỐI ƯU"])
        lines.extend(
            f"- {item.get('title')}: {item.get('display')}"
            for item in result.get("opportunities", [])
        )
        self._set_text(self.performance_text, "\n".join(lines))
        for number in range(51, 79):
            self._mark_master(number, "Đang làm", f"PageSpeed {result.get('strategy')}")
        self._mark_master(
            51, "Hoàn thành", f"Performance {result.get('performance')}/100"
        )
        self._save_state()
        self._refresh_onboarding()

    def _start_full_audit(self):
        if not self._require_project("chạy Full SEO Audit"):
            return
        url = normalize_url(self.website.get() or self.current_project["website"])
        if not url:
            self._show_smart_error(
                "URL chưa hợp lệ",
                "Dự án chưa có website hợp lệ.",
                "Cập nhật website trong Projects & History.",
            )
            return
        if self.full_audit_running:
            return
        self.full_audit_running = True
        self.stop_event = threading.Event()
        self.full_audit_btn.configure(state="disabled")
        self.progress.set(0)
        self._begin_operation("Full SEO Audit", retry=self._start_full_audit)
        threading.Thread(
            target=self._full_audit_worker,
            args=(url, max(1, min(500, int(self.max_pages.get())))),
            daemon=True,
        ).start()

    def _full_audit_worker(self, url, limit):
        warnings = []
        try:
            self.v46_events.put(("full-progress", "1/6 Đang crawl website", 5))
            auditor = SiteAuditor()
            pages = auditor.crawl(
                url,
                limit,
                callback=lambda current, count, total: self.v46_events.put(
                    (
                        "full-progress",
                        f"1/6 Crawl {count}/{total}: {current}",
                        5 + min(40, int(count / max(1, total) * 40)),
                    )
                ),
                stop=self.stop_event,
            )
            if self.stop_event.is_set():
                self.v46_events.put(("full-cancelled",))
                return
            graph = getattr(auditor, "last_graph", {})
            sitemap_urls = getattr(auditor, "last_sitemap_urls", set())
            orphans = getattr(auditor, "last_orphans", [])
            files = auditor.site_files(url)

            self.v46_events.put(
                ("full-progress", "2/6 Đang chạy Lighthouse/PageSpeed", 50)
            )
            pagespeed = None
            try:
                pagespeed = PageSpeedClient(self.pagespeed_key.get()).analyze(
                    url, "mobile"
                )
                if self.pagespeed_key.get().strip():
                    try:
                        pagespeed["crux"] = CruxClient(
                            self.pagespeed_key.get()
                        ).query(url, "PHONE")
                    except Exception as exc:
                        pagespeed["crux_error"] = clean_text(exc)
            except Exception as exc:
                warnings.append("PageSpeed: " + clean_text(exc))

            self.v46_events.put(
                ("full-progress", "3/6 Đang lấy Google Search Console", 66)
            )
            gsc_rows, gsc_sitemaps = [], []
            if (
                self.gsc_credential_path.get().strip()
                and self.gsc_property.get().strip()
            ):
                try:
                    client = SearchConsoleClient(self.gsc_credential_path.get())
                    end = date.today() - timedelta(days=2)
                    start = end - timedelta(days=89)
                    gsc_rows = client.search_analytics(
                        self.gsc_property.get(),
                        start,
                        end,
                        ("date", "page", "query"),
                    )
                    gsc_sitemaps = client.list_sitemaps(self.gsc_property.get())
                except Exception as exc:
                    warnings.append("Search Console: " + clean_text(exc))
            else:
                warnings.append("Search Console: chưa kết nối, đã bỏ qua.")

            self.v46_events.put(
                ("full-progress", "4/6 Đang tạo Internal Link Map", 76)
            )
            self.v46_events.put(
                ("full-progress", "5/6 Đang tạo Fix Queue và Roadmap", 86)
            )
            result = {
                "pages": pages,
                "files": files,
                "orphans": orphans,
                "graph": graph,
                "sitemap_urls": sitemap_urls,
                "pagespeed": pagespeed,
                "gsc_rows": gsc_rows,
                "gsc_sitemaps": gsc_sitemaps,
                "warnings": warnings,
            }
            self.v46_events.put(
                ("full-progress", "6/6 Đang hoàn thiện báo cáo", 95)
            )
            self.v46_events.put(("full-done", result))
        except Exception as exc:
            self.v46_events.put(
                ("full-error", explain_exception(exc, "Full SEO Audit"))
            )

    def _finish_full_audit(self, result):
        snapshots_before = (
            self.store.list_snapshots(self.current_project["id"])
            if self.current_project
            else []
        )
        self.internal_graph = result["graph"]
        self.sitemap_urls = set(result["sitemap_urls"])
        self._finish_audit(result["pages"], result["files"], result["orphans"])
        if result.get("pagespeed"):
            self._finish_pagespeed(result["pagespeed"])
        if result.get("gsc_rows"):
            self.gsc_rows = result["gsc_rows"]
            self.gsc_sitemaps = result["gsc_sitemaps"]
            self._render_gsc()
            self._render_decay()
        self._render_fixes()
        self._create_content_briefs(silent=True)
        self._render_roadmap()
        snapshots_after = (
            self.store.list_snapshots(self.current_project["id"])
            if self.current_project
            else []
        )
        validation = ""
        if snapshots_before and snapshots_after:
            try:
                previous = self.store.load_snapshot(snapshots_before[0])
                current = self.store.load_snapshot(snapshots_after[0])
                comparison = compare_snapshots(previous, current)
                validation = (
                    f"\nSo với lần trước: {len(comparison['resolved'])} lỗi đã sửa, "
                    f"{len(comparison['new'])} lỗi mới, "
                    f"{len(comparison['remaining'])} lỗi còn lại."
                )
            except Exception:
                validation = ""
        score = (
            round(sum(page.score for page in self.pages) / len(self.pages))
            if self.pages
            else 0
        )
        summary = [
            "FULL SEO AUDIT HOÀN TẤT",
            f"SEO Score: {score}/100",
            f"Trang đã crawl: {len(self.pages)}",
            f"Lỗi cần xử lý: {len(self.fix_items)}",
            f"P0: {sum(item.priority == 'P0' for item in self.fix_items)}",
            f"Orphan Page: {len(self.link_map_report.get('orphans', []))}",
            f"Dead-end: {len(self.link_map_report.get('dead_ends', []))}",
            f"Keyword: {len(self.keyword_rows)}",
            f"Content Brief: {len(self.content_briefs)}",
            validation,
            "",
            "CẢNH BÁO/BƯỚC ĐÃ BỎ QUA",
            *[f"- {warning}" for warning in result.get("warnings", [])],
            "",
            "HÀNH ĐỘNG TIẾP THEO",
            "1. Xử lý P0 trong Fix Queue chi tiết.",
            "2. Mapping Cluster vào Landing Page.",
            "3. Tạo Content Brief và phân tích Top 5.",
            "4. Audit lại để xác thực lỗi đã sửa.",
        ]
        self._set_text(self.full_audit_text, "\n".join(summary))
        self.full_audit_running = False
        self.full_audit_btn.configure(state="normal")
        self.progress.set(100)
        self.status.set(f"Full SEO Audit hoàn tất: {len(self.pages)} trang.")
        self._save_state()
        self._refresh_onboarding()
        self._end_operation(success=True)

    def _render_fixes(self):
        if not hasattr(self, "fix_tree"):
            return
        self._clear_tree(self.fix_tree)
        for index, issue in enumerate(build_detailed_issues(self.fix_items)):
            self.fix_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    issue.priority,
                    issue.issue,
                    issue.url,
                    issue.why_it_matters,
                    issue.recommendation,
                    issue.difficulty,
                    issue.expected_impact,
                    issue.status,
                ),
            )

    def _export_fixes(self):
        if not self.fix_items:
            messagebox.showinfo("Chưa có lỗi", "Chạy Website Audit trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="fix-queue-chi-tiet-v46.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            export_csv(path, detailed_issue_rows(self.fix_items))

    def _create_content_briefs(self, silent=False):
        self.content_briefs = build_content_briefs(self.keyword_rows)
        self._render_content_briefs()
        if self.current_project:
            self.store.save_project_state(
                self.current_project["id"], "content-briefs", self.content_briefs
            )
        if not silent:
            if self.content_briefs:
                self.status.set(
                    f"Đã tạo {len(self.content_briefs)} Content Brief từ Cluster."
                )
            else:
                messagebox.showinfo(
                    "Chưa có Cluster", "Import Semrush hoặc thêm keyword trước."
                )

    def _render_content_briefs(self):
        if not hasattr(self, "content_brief_tree"):
            return
        self._clear_tree(self.content_brief_tree)
        for index, brief in enumerate(self.content_briefs):
            self.content_brief_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    brief["cluster"],
                    brief["primary_keyword"],
                    brief["intent"],
                    brief["total_volume"],
                    brief["average_kd"],
                    brief["landing_page"],
                    brief["status"],
                ),
            )

    def _selected_brief(self):
        selection = self.content_brief_tree.selection()
        if not selection:
            return None
        index = int(selection[0])
        return self.content_briefs[index] if index < len(self.content_briefs) else None

    def _show_selected_brief(self):
        brief = self._selected_brief()
        if not brief:
            return
        lines = [
            f"CLUSTER: {brief['cluster']}",
            f"PRIMARY KEYWORD: {brief['primary_keyword']}",
            f"SEARCH INTENT: {brief['intent']}",
            f"ĐỊNH DẠNG: {brief['content_format']}",
            f"TITLE GỢI Ý: {brief['suggested_title']}",
            f"LANDING PAGE: {brief['landing_page'] or 'Chưa mapping'}",
            f"TOTAL VOLUME: {brief['total_volume']} | AVG KD: {brief['average_kd']}",
            "",
            "SECONDARY KEYWORDS",
            *[f"- {value}" for value in brief["secondary_keywords"]],
            "",
            "OUTLINE GỢI Ý",
            *[f"H2. {value}" for value in brief["headings"]],
            "",
            "CÂU HỎI CẦN TRẢ LỜI",
            *[f"- {value}" for value in brief["questions"]],
            "",
            "QUY TRÌNH",
            "Top 5 → Content Gap → Hoàn thiện Outline → WordPress Draft → Recheck.",
        ]
        self._set_text(self.content_brief_text, "\n".join(lines))

    def _brief_to_top5(self):
        brief = self._selected_brief()
        if not brief:
            messagebox.showinfo("Chưa chọn Brief", "Chọn một Cluster trước.")
            return
        self.serp_keyword.set(brief["primary_keyword"])
        self._open_workspace("Nghiên cứu", "Top 5 Direct")
        self.status.set("Đã chuyển Primary Keyword sang Top 5.")

    def _brief_to_outline(self):
        brief = self._selected_brief()
        if not brief:
            messagebox.showinfo("Chưa chọn Brief", "Chọn một Cluster trước.")
            return
        outline = [
            brief["suggested_title"],
            "",
            *[f"H2: {heading}" for heading in brief["headings"]],
            "",
            "Secondary Keywords:",
            ", ".join(brief["secondary_keywords"]),
            "",
            "Questions:",
            *[f"- {question}" for question in brief["questions"]],
        ]
        self._set_text(self.outline_text, "\n".join(outline))
        self._open_workspace("Nghiên cứu", "Top 5 Direct")
        self.status.set("Đã đưa Content Brief sang vùng Outline.")

    def _recheck_landing_page(self):
        brief = self._selected_brief()
        if not brief or not normalize_url(brief.get("landing_page")):
            self._show_smart_error(
                "Chưa có Landing Page",
                "Content Brief chưa được mapping URL hợp lệ.",
                "Sửa Landing Page trong Keyword Intelligence rồi tạo lại Brief.",
            )
            return
        url = normalize_url(brief["landing_page"])
        threading.Thread(
            target=self._recheck_worker, args=(url,), daemon=True
        ).start()
        self._begin_operation("Recheck Landing Page", retry=self._recheck_landing_page)

    def _recheck_worker(self, url):
        try:
            host = urlparse(url).netloc.lower()
            page, _links = SiteAuditor().analyze_page(url, host)
            self.v46_events.put(("recheck-done", page))
        except Exception as exc:
            self.v46_events.put(
                ("full-error", explain_exception(exc, "Recheck Landing Page"))
            )

    def _load_demo(self):
        payload = demo_payload()
        project = self.store.upsert_project(
            payload["project"]["name"], payload["project"]["website"]
        )
        self._refresh_projects(project["id"])
        self._select_project()
        self.internal_graph = payload["graph"]
        self.sitemap_urls = payload["sitemap_urls"]
        self.keyword_rows = payload["keywords"]
        self.gsc_rows = payload["gsc_rows"]
        self.latest_pagespeed = payload["pagespeed"]
        self._finish_audit(
            payload["pages"],
            payload["site_files"],
            sorted(payload["sitemap_urls"] - set(payload["graph"])),
        )
        self._finish_pagespeed(payload["pagespeed"])
        self._render_keywords()
        self._render_gsc()
        self._render_decay()
        self._create_content_briefs(silent=True)
        self._save_state()
        self._save_app_settings(first_run_complete=True)
        self._refresh_onboarding()
        self.status.set("Đã tải dữ liệu Demo. Bạn có thể thử toàn bộ chức năng.")

    def _refresh_onboarding(self):
        if not hasattr(self, "onboarding_tree"):
            return
        rows = onboarding_statuses(
            self.current_project,
            self.pages,
            self.keyword_rows,
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
                else "Thiết lập đã hoàn tất. Hãy xử lý Fix Queue và theo dõi kết quả."
            )
        )

    def _select_project(self, event=None):
        super()._select_project(event)
        if self.current_project and hasattr(self, "vault"):
            self._load_secrets(silent=True)
        self._refresh_onboarding()
        self._save_app_settings()

    def _load_project_state(self):
        super()._load_project_state()
        if not self.current_project:
            return
        self.content_briefs = self.store.load_project_state(
            self.current_project["id"], "content-briefs", []
        ) or []
        self._render_content_briefs()
        self._refresh_onboarding()

    def _save_state(self):
        super()._save_state()
        if self.current_project:
            self.store.save_project_state(
                self.current_project["id"], "content-briefs", self.content_briefs
            )

    def _integrations_tab(self):
        super()._integrations_tab()
        notebook = self.workspace_notebooks.get("Theo dõi")
        if not notebook:
            return
        tab_id = notebook.tabs()[-1]
        frame = self.nametowidget(tab_id)
        vault = ttk.LabelFrame(
            frame, text="Windows Credential Manager", padding=10
        )
        vault.pack(fill="x", pady=(10, 0))
        ttk.Label(
            vault,
            text=(
                "Lưu PageSpeed/CrUX API Key và WordPress Application Password "
                "trong kho bí mật của Windows; không ghi vào project hoặc báo cáo."
            ),
            wraplength=1050,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            vault, text="Lưu bí mật an toàn", command=self._save_secrets
        ).pack(side="right", padx=5)
        ttk.Button(
            vault, text="Tải bí mật đã lưu", command=self._load_secrets
        ).pack(side="right", padx=5)
        ttk.Label(
            frame,
            text=(
                "WordPress: trong wp-admin mở Users → Profile → Application Passwords, "
                "tạo mật khẩu riêng cho SEO AI Studio rồi nhấn Kiểm tra WordPress."
            ),
            wraplength=1100,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=8)

    def _save_secrets(self):
        if not self._require_project("lưu thông tin kết nối"):
            return
        try:
            if self.pagespeed_key.get().strip():
                self.vault.save(
                    self.current_project["id"], "pagespeed_key", self.pagespeed_key.get()
                )
            if self.wp_password.get().strip():
                self.vault.save(
                    self.current_project["id"], "wp_password", self.wp_password.get()
                )
            messagebox.showinfo(
                "Đã lưu an toàn",
                "Bí mật đã được lưu trong Windows Credential Manager.",
            )
        except Exception as exc:
            error = explain_exception(exc, "Credential Manager")
            self._show_smart_error(error.title, error.message, error.hint)

    def _load_secrets(self, silent=False):
        if not self.current_project or not hasattr(self, "vault"):
            return
        page_key = self.vault.load(self.current_project["id"], "pagespeed_key")
        wp_password = self.vault.load(self.current_project["id"], "wp_password")
        if page_key:
            self.pagespeed_key.set(page_key)
        if wp_password:
            self.wp_password.set(wp_password)
        if not silent:
            messagebox.showinfo(
                "Kho bí mật",
                "Đã tải thông tin kết nối đã lưu cho dự án này."
                if page_key or wp_password
                else "Dự án chưa có bí mật đã lưu.",
            )

    def _test_wordpress(self):
        try:
            from seo_v43_core import WordPressProClient

            name = WordPressProClient(
                self.wp_site.get(), self.wp_user.get(), self.wp_password.get()
            ).test()
            self.wordpress_ok = True
            self._refresh_onboarding()
            messagebox.showinfo("WordPress", f"Kết nối thành công: {name}")
        except Exception as exc:
            self.wordpress_ok = False
            error = explain_exception(exc, "WordPress")
            self._show_smart_error(error.title, error.message, error.hint)

    def _check_updates(self):
        self.status.set("Đang kiểm tra phiên bản mới…")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            self.v46_events.put(("update-result", UpdateChecker().check(VERSION)))
        except Exception as exc:
            self.v46_events.put(
                ("full-error", explain_exception(exc, "Kiểm tra cập nhật"))
            )

    def _show_update(self, result):
        window = tk.Toplevel(self)
        window.title("Cập nhật SEO AI Studio")
        window.geometry("560x300")
        window.transient(self)
        body = ttk.Frame(window, padding=16)
        body.pack(fill="both", expand=True)
        title = (
            f"Có phiên bản mới {result['latest']}"
            if result["update_available"]
            else f"Bạn đang dùng bản mới nhất {result['current']}"
        )
        ttk.Label(body, text=title, style="Head.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            text=result.get("notes") or "Không có ghi chú phát hành.",
            wraplength=500,
        ).pack(anchor="w", pady=12)
        buttons = ttk.Frame(body)
        buttons.pack(side="bottom", fill="x")
        if result.get("download_url"):
            ttk.Button(
                buttons,
                text="Mở trang tải bộ cài mới",
                style="Accent.TButton",
                command=lambda: webbrowser.open(result["download_url"]),
            ).pack(side="left")
        ttk.Button(buttons, text="Đóng", command=window.destroy).pack(side="right")

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
                "Cài lại bộ Setup V4.6 đầy đủ.",
            )
            return
        webbrowser.open(path.as_uri())

    def _show_smart_error(
        self, title, message, hint="", details="", retry=None
    ):
        self.last_retry = retry or self.last_retry
        self.last_support_info = details or support_information(
            message, self.operation_name
        )
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("690x430")
        window.minsize(620, 390)
        window.transient(self)
        body = ttk.Frame(window, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=title, style="Head.TLabel").pack(anchor="w")
        cause = ttk.LabelFrame(body, text="Nguyên nhân", padding=10)
        cause.pack(fill="x", pady=(12, 8))
        ttk.Label(cause, text=message, wraplength=620).pack(anchor="w")
        fix = ttk.LabelFrame(body, text="Cách xử lý", padding=10)
        fix.pack(fill="x")
        ttk.Label(
            fix,
            text=hint or "Kiểm tra đầu vào và thử lại.",
            wraplength=620,
        ).pack(anchor="w")
        detail_box = ttk.LabelFrame(body, text="Thông tin hỗ trợ", padding=8)
        detail_box.pack(fill="both", expand=True, pady=8)
        text = tk.Text(detail_box, height=6, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.last_support_info)
        text.configure(state="disabled")
        buttons = ttk.Frame(body)
        buttons.pack(fill="x")

        def copy_info():
            self.clipboard_clear()
            self.clipboard_append(self.last_support_info)
            self.status.set("Đã sao chép thông tin hỗ trợ.")

        ttk.Button(buttons, text="Sao chép thông tin", command=copy_info).pack(
            side="left"
        )
        if callable(self.last_retry):
            def run_retry():
                callback = self.last_retry
                window.destroy()
                callback()

            ttk.Button(
                buttons,
                text="Thử lại",
                style="Accent.TButton",
                command=run_retry,
            ).pack(side="left", padx=7)
        ttk.Button(buttons, text="Đóng", command=window.destroy).pack(side="right")

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
                    self._refresh_onboarding()
                    self._end_operation(success=True)
                elif kind == "serp-progress":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "serp-done":
                    self._finish_serp(event[1])
                    self._end_operation(success=True)
                elif kind == "pagespeed-done":
                    self._finish_pagespeed(event[1])
                    self.progress.set(100)
                    self.status.set("Đã hoàn tất PageSpeed và CrUX.")
                    self._end_operation(success=True)
                elif kind == "ranks-done":
                    self._detect_cannibalization()
                    self._render_keywords()
                    self._save_state()
                    self.status.set("Đã kiểm tra thứ hạng.")
                elif kind == "status":
                    self.status.set(event[1])
                elif kind == "smart-error":
                    error = event[1]
                    self.audit_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.serp_btn.configure(state="normal")
                    self._end_operation(success=False)
                    self._show_smart_error(
                        error.title, error.message, error.hint, retry=self.last_retry
                    )
                elif kind == "error":
                    self.audit_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.serp_btn.configure(state="normal")
                    self._end_operation(success=False)
                    self._show_smart_error(
                        event[1],
                        event[2],
                        "Kiểm tra đầu vào, kết nối rồi nhấn Thử lại.",
                        retry=self.last_retry,
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _poll_pro_events(self):
        try:
            while True:
                event = self.pro_events.get_nowait()
                kind = event[0]
                if kind == "pro-error":
                    error = event[1]
                    self._show_smart_error(
                        error.title, error.message, error.hint, retry=self.last_retry
                    )
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
                    self._refresh_onboarding()
                    self.status.set(
                        f"Đã lấy GSC {event[3]} đến {event[4]}: {len(self.gsc_rows)} rows."
                    )
                    self.progress.set(100)
                elif kind == "gsc-inspect":
                    index = event[2].get("indexStatusResult", {})
                    messagebox.showinfo(
                        "URL Inspection - dữ liệu trong chỉ mục",
                        "\n".join(
                            [
                                event[1],
                                "",
                                "Lưu ý: đây là trạng thái của phiên bản đang nằm trong "
                                "Google Index, không phải kiểm tra trực tiếp URL hiện tại.",
                                "",
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
                    self._set_text(
                        self.wp_preview_text,
                        "\n".join(
                            [
                                f"POST ID: {post.get('id')}",
                                f"TITLE: {title}",
                                f"STATUS: {post.get('status')}",
                                f"MODIFIED: {post.get('modified')}",
                                f"REVISIONS: {len(revisions)}",
                                "",
                                "NỘI DUNG HIỆN TẠI",
                                content,
                            ]
                        ),
                    )
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

    def _poll_v46_events(self):
        try:
            while True:
                event = self.v46_events.get_nowait()
                kind = event[0]
                if kind == "full-progress":
                    self.status.set(event[1])
                    self.progress.set(event[2])
                elif kind == "full-done":
                    self._finish_full_audit(event[1])
                elif kind == "full-cancelled":
                    self.full_audit_running = False
                    self.full_audit_btn.configure(state="normal")
                    self.status.set("Full SEO Audit đã được hủy.")
                    self._end_operation(success=False)
                elif kind == "full-error":
                    error = event[1]
                    self.full_audit_running = False
                    self.full_audit_btn.configure(state="normal")
                    self._end_operation(success=False)
                    self._show_smart_error(
                        error.title, error.message, error.hint, retry=self.last_retry
                    )
                elif kind == "update-result":
                    self._show_update(event[1])
                    self.status.set("Đã kiểm tra cập nhật.")
                elif kind == "recheck-done":
                    page = event[1]
                    self._end_operation(success=True)
                    self._show_smart_error(
                        "Kết quả Recheck Landing Page",
                        f"SEO Score: {page.score}/100 | HTTP {page.status}",
                        (
                            "Không còn lỗi."
                            if not page.issues
                            else "Cần xử lý: " + " | ".join(page.issues)
                        ),
                        details=support_information(
                            f"{page.url} - {page.issue_text or 'Tốt'}",
                            "Recheck Landing Page",
                        ),
                    )
        except queue.Empty:
            pass
        self.after(150, self._poll_v46_events)

    def _on_close(self):
        self._save_app_settings()
        if not self.operation_name:
            self.store.clear_recovery()
        self.destroy()


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
    app = AppV46()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
