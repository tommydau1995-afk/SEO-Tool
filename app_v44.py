"""SEO AI Studio V4.4 - beginner-friendly Keyword Intelligence."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from app_v43 import AppV43
from seo_v4_core import clean_text, normalize_url, utc_now
from seo_v43_core import DirectGoogleResearcher, explain_exception, run_scheduled_audit
from seo_v44_keywords import (
    INTENT_COLORS,
    VERSION,
    ProjectStoreV44,
    SemrushKeywordImporter,
    classify_intent,
    cluster_label,
    cluster_summary,
    export_keyword_workbook,
    keyword_kpis,
    normalize_keyword_row,
    rebuild_keyword_intelligence,
)


GUIDE_FILE = "Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf"


class AppV44(AppV43):
    def __init__(self):
        self.keyword_import_summary = {}
        super().__init__()
        self.store = ProjectStoreV44()
        self._refresh_projects()
        self.title(f"SEO AI Studio V{VERSION} - Keyword Intelligence")

    def _style(self):
        super()._style()
        style = ttk.Style(self)
        style.configure("Keyword.Treeview", rowheight=31, font=("Segoe UI", 9))
        style.configure(
            "Keyword.Treeview.Heading", font=("Segoe UI", 9, "bold")
        )
        style.configure("Hero.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("SmallMetric.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Muted.TLabel", foreground="#5C6B7A")

    def _header(self):
        frame = ttk.Frame(self, padding=(15, 12))
        frame.pack(fill="x")
        ttk.Label(
            frame, text="SEO AI Studio V4.4", style="Title.TLabel"
        ).pack(side="left")
        ttk.Label(
            frame,
            text="Semrush Import • Search Intent • Keyword Clusters • Complete SEO",
            foreground="#1769c2",
        ).pack(side="left", padx=16)
        ttk.Button(frame, text="Hướng dẫn người mới", command=self._open_guide).pack(
            side="right", padx=(8, 0)
        )
        self.project_badge = ttk.Label(frame, text="Chưa chọn dự án")
        self.project_badge.pack(side="right")

    def _footer(self):
        frame = ttk.Frame(self, padding=(12, 6))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status).pack(side="left")
        ttk.Progressbar(
            frame, variable=self.progress, maximum=100, length=250
        ).pack(side="right", padx=(8, 0))
        ttk.Label(frame, text=f"V{VERSION}").pack(side="right")

    def _keyword_tab(self):
        frame = self._tab("Keyword Intelligence")
        hero = ttk.LabelFrame(
            frame,
            text="Semrush Keyword Intelligence",
            padding=(12, 8),
        )
        hero.pack(fill="x")
        left = ttk.Frame(hero)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(
            left,
            text="Import Keyword + Volume + KD, tự nhận Search Intent và phân nhóm chủ đề",
            style="Hero.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            left,
            text=(
                "Hỗ trợ Semrush CSV/TSV/XLSX. Intent và Cluster là gợi ý tự động, "
                "có thể chỉnh sửa trước khi lập Content Plan."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Button(
            hero,
            text="Import file Semrush",
            style="Accent.TButton",
            command=self._import_keywords,
        ).pack(side="right", padx=(8, 0))

        cards = ttk.Frame(frame)
        cards.pack(fill="x", pady=(10, 4))
        self.kw_metric_count = self._small_metric(cards, "0", "Keywords")
        self.kw_metric_volume = self._small_metric(cards, "0", "Total Volume")
        self.kw_metric_kd = self._small_metric(cards, "0", "KD trung bình")
        self.kw_metric_clusters = self._small_metric(cards, "0", "Clusters")
        self.kw_metric_mapped = self._small_metric(cards, "0", "Đã map URL")

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(4, 0))
        self.kw_keyword = tk.StringVar()
        self.kw_volume = tk.StringVar()
        self.kw_difficulty = tk.StringVar()
        self.kw_url = tk.StringVar()
        self.kw_intent = tk.StringVar(value="Informational")
        self.kw_priority = tk.StringVar(value="P1")
        ttk.Label(actions, text="Keyword:").grid(row=0, column=0, sticky="e")
        ttk.Entry(actions, textvariable=self.kw_keyword, width=27).grid(
            row=0, column=1, padx=4
        )
        ttk.Label(actions, text="Volume:").grid(row=0, column=2, sticky="e")
        ttk.Entry(actions, textvariable=self.kw_volume, width=10).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(actions, text="KD %:").grid(row=0, column=4, sticky="e")
        ttk.Entry(actions, textvariable=self.kw_difficulty, width=8).grid(
            row=0, column=5, padx=4
        )
        ttk.Label(actions, text="Landing Page:").grid(row=0, column=6, sticky="e")
        ttk.Entry(actions, textvariable=self.kw_url, width=31).grid(
            row=0, column=7, padx=4, sticky="ew"
        )
        ttk.Button(actions, text="Thêm", command=self._add_keyword).grid(
            row=0, column=8, padx=4
        )
        ttk.Button(actions, text="Sửa dòng chọn", command=self._edit_keyword).grid(
            row=0, column=9, padx=4
        )
        ttk.Button(actions, text="Xóa dòng chọn", command=self._delete_keywords).grid(
            row=0, column=10, padx=4
        )
        actions.columnconfigure(7, weight=1)

        filters = ttk.Frame(frame)
        filters.pack(fill="x", pady=(8, 0))
        self.kw_filter_text = tk.StringVar()
        self.kw_filter_intent = tk.StringVar(value="Tất cả")
        self.kw_filter_cluster = tk.StringVar(value="Tất cả")
        self.kw_filter_volume = tk.StringVar(value="0")
        self.cluster_detail = tk.StringVar(value="Balanced")
        ttk.Label(filters, text="Tìm:").pack(side="left")
        search_entry = ttk.Entry(filters, textvariable=self.kw_filter_text, width=25)
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<KeyRelease>", lambda _event: self._render_keywords())
        ttk.Label(filters, text="Intent:").pack(side="left", padx=(8, 0))
        intent_box = ttk.Combobox(
            filters,
            textvariable=self.kw_filter_intent,
            values=(
                "Tất cả",
                "Informational",
                "Commercial",
                "Transactional",
                "Navigational",
            ),
            state="readonly",
            width=16,
        )
        intent_box.pack(side="left", padx=4)
        intent_box.bind("<<ComboboxSelected>>", lambda _event: self._render_keywords())
        ttk.Label(filters, text="Cluster:").pack(side="left", padx=(8, 0))
        self.cluster_filter_box = ttk.Combobox(
            filters,
            textvariable=self.kw_filter_cluster,
            values=("Tất cả",),
            state="readonly",
            width=24,
        )
        self.cluster_filter_box.pack(side="left", padx=4)
        self.cluster_filter_box.bind(
            "<<ComboboxSelected>>", lambda _event: self._render_keywords()
        )
        ttk.Label(filters, text="Volume từ:").pack(side="left", padx=(8, 0))
        volume_entry = ttk.Entry(
            filters, textvariable=self.kw_filter_volume, width=9
        )
        volume_entry.pack(side="left", padx=4)
        volume_entry.bind("<KeyRelease>", lambda _event: self._render_keywords())
        ttk.Label(filters, text="Độ chi tiết nhóm:").pack(
            side="left", padx=(10, 0)
        )
        ttk.Combobox(
            filters,
            textvariable=self.cluster_detail,
            values=("Broad", "Balanced", "Tight"),
            state="readonly",
            width=10,
        ).pack(side="left", padx=4)
        ttk.Button(
            filters, text="Phân loại lại", command=self._rebuild_keywords
        ).pack(side="left", padx=4)
        ttk.Button(
            filters, text="Kiểm tra Rank", command=self._check_ranks
        ).pack(side="right")
        ttk.Button(
            filters, text="Xuất Excel", command=self._export_keywords
        ).pack(side="right", padx=5)
        ttk.Button(
            filters, text="Xuất CSV", command=self._export_keyword_csv
        ).pack(side="right")

        pane = ttk.Panedwindow(frame, orient="vertical")
        pane.pack(fill="both", expand=True, pady=(7, 0))
        keyword_box = ttk.LabelFrame(pane, text="Danh sách Keyword", padding=6)
        cluster_box = ttk.LabelFrame(
            pane, text="Tóm tắt Cluster và Primary Keyword", padding=6
        )
        pane.add(keyword_box, weight=3)
        pane.add(cluster_box, weight=1)
        self.keyword_tree = self._tree(
            keyword_box,
            (
                "keyword",
                "volume",
                "difficulty",
                "intent",
                "cluster",
                "url",
                "cpc",
                "priority",
                "rank",
                "status",
            ),
            (
                "Keyword",
                "Volume",
                "KD %",
                "Search Intent",
                "Cluster",
                "Landing Page",
                "CPC",
                "Ưu tiên",
                "Rank",
                "Trạng thái",
            ),
            (260, 85, 70, 130, 180, 330, 70, 70, 70, 165),
        )
        self.keyword_tree.configure(style="Keyword.Treeview")
        for intent, color in INTENT_COLORS.items():
            self.keyword_tree.tag_configure(intent, background=color)
        self.keyword_tree.bind("<Double-1>", lambda _event: self._edit_keyword())

        self.cluster_tree = self._tree(
            cluster_box,
            (
                "cluster",
                "keywords",
                "volume",
                "kd",
                "intent",
                "primary",
                "url",
            ),
            (
                "Cluster",
                "Số key",
                "Total Volume",
                "Avg. KD",
                "Intent chính",
                "Primary Keyword",
                "Landing Page",
            ),
            (230, 75, 110, 85, 130, 320, 390),
        )
        self.import_note = ttk.Label(
            frame,
            text="Chưa import Semrush.",
            style="Muted.TLabel",
        )
        self.import_note.pack(anchor="w", pady=(5, 0))

    def _small_metric(self, parent, value, label):
        card = ttk.LabelFrame(parent, text=label, padding=(12, 6))
        card.pack(side="left", fill="x", expand=True, padx=(0, 7))
        widget = ttk.Label(card, text=value, style="SmallMetric.TLabel")
        widget.pack()
        return widget

    def _add_keyword(self):
        keyword = clean_text(self.kw_keyword.get())
        if not keyword:
            messagebox.showwarning("Thiếu keyword", "Nhập keyword cần thêm.")
            return
        row = normalize_keyword_row(
            {
                "keyword": keyword,
                "volume": self.kw_volume.get(),
                "difficulty": self.kw_difficulty.get(),
                "url": self.kw_url.get(),
                "intent": classify_intent(keyword),
                "cluster": cluster_label(keyword, self.cluster_detail.get()),
                "source": "Manual",
            },
            source="Manual",
            cluster_detail=self.cluster_detail.get(),
        )
        self.keyword_rows.append(row)
        self.kw_keyword.set("")
        self.kw_volume.set("")
        self.kw_difficulty.set("")
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()

    def _import_keywords(self):
        path = filedialog.askopenfilename(
            title="Chọn file export từ Semrush",
            filetypes=[
                ("Semrush CSV/XLSX", "*.csv *.tsv *.xlsx *.xlsm"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xlsm"),
                ("Tất cả", "*.*"),
            ],
        )
        if not path:
            return
        try:
            imported, summary = SemrushKeywordImporter().read(
                path, self.cluster_detail.get()
            )
        except Exception as exc:
            error = explain_exception(exc, "Semrush Import")
            messagebox.showerror(error.title, error.user_message)
            return
        if not imported:
            messagebox.showwarning(
                "Không có keyword", "File không chứa dòng keyword hợp lệ."
            )
            return
        replace = messagebox.askyesno(
            "Cách nhập dữ liệu",
            f"Đã đọc {len(imported):,} keyword.\n\n"
            "Chọn Yes để THAY THẾ danh sách hiện tại.\n"
            "Chọn No để GỘP với dữ liệu đang có.",
        )
        if replace:
            self.keyword_rows = imported
        else:
            self.keyword_rows.extend(imported)
            self.keyword_rows = self._deduplicate_current()
        self.keyword_import_summary = summary
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()
        detected = summary["detected"]
        self.import_note.configure(
            text=(
                f"Semrush: {summary['file']} • {summary['keywords_imported']:,} keyword • "
                f"bỏ {summary['duplicates_removed']:,} trùng • "
                f"cột: Keyword={detected['keyword'] or 'thiếu'}, "
                f"Volume={detected['volume'] or 'không có'}, "
                f"KD={detected['difficulty'] or 'không có'}, "
                f"Intent={detected['intent'] or 'tool tự phân loại'}"
            )
        )
        messagebox.showinfo(
            "Import Semrush hoàn tất",
            f"Keyword: {summary['keywords_imported']:,}\n"
            f"Trùng đã loại: {summary['duplicates_removed']:,}\n"
            f"Clusters: {len(cluster_summary(self.keyword_rows)):,}\n\n"
            "Hãy kiểm tra Search Intent, Cluster và map Landing Page trước khi "
            "xuất Content Plan.",
        )

    def _deduplicate_current(self):
        from seo_v44_keywords import deduplicate_keywords

        return deduplicate_keywords(
            [
                normalize_keyword_row(
                    row,
                    source=clean_text(row.get("source")) or "Manual",
                    cluster_detail=self.cluster_detail.get(),
                )
                for row in self.keyword_rows
            ]
        )

    def _detect_cannibalization(self):
        mapping = {}
        for index, row in enumerate(self.keyword_rows):
            keyword = clean_text(row.get("keyword")).lower()
            url = normalize_url(row.get("url"))
            if keyword and url:
                mapping.setdefault(keyword, set()).add(url)
        for index, row in enumerate(self.keyword_rows):
            keyword = clean_text(row.get("keyword")).lower()
            url = normalize_url(row.get("url"))
            if not url:
                row["status"] = "Chưa map Landing Page"
            elif len(mapping.get(keyword, set())) > 1:
                row["status"] = "Cannibalization"
            else:
                row["status"] = "Mapped"

    def _filtered_keywords(self):
        query = clean_text(self.kw_filter_text.get()).lower()
        intent = self.kw_filter_intent.get()
        cluster = self.kw_filter_cluster.get()
        try:
            min_volume = float(clean_text(self.kw_filter_volume.get()) or 0)
        except ValueError:
            min_volume = 0
        rows = []
        for index, row in enumerate(self.keyword_rows):
            if query and query not in clean_text(row.get("keyword")).lower():
                continue
            if intent != "Tất cả" and row.get("intent") != intent:
                continue
            if cluster != "Tất cả" and row.get("cluster") != cluster:
                continue
            try:
                volume = float(row.get("volume") or 0)
            except (TypeError, ValueError):
                volume = 0
            if volume < min_volume:
                continue
            rows.append((index, row))
        return rows

    def _render_keywords(self):
        if not hasattr(self, "keyword_tree"):
            return
        self.keyword_rows = [
            normalize_keyword_row(
                row,
                source=clean_text(row.get("source")) or "Manual",
                cluster_detail=self.cluster_detail.get(),
            )
            for row in self.keyword_rows
            if clean_text(row.get("keyword"))
        ]
        clusters = sorted(
            {clean_text(row.get("cluster")) for row in self.keyword_rows if row.get("cluster")}
        )
        self.cluster_filter_box["values"] = ["Tất cả"] + clusters
        if self.kw_filter_cluster.get() not in self.cluster_filter_box["values"]:
            self.kw_filter_cluster.set("Tất cả")
        self._clear_tree(self.keyword_tree)
        for index, row in self._filtered_keywords():
            self.keyword_tree.insert(
                "",
                "end",
                iid=str(index),
                tags=(row.get("intent", ""),),
                values=(
                    row.get("keyword", ""),
                    f"{float(row.get('volume') or 0):,.0f}",
                    f"{float(row.get('difficulty') or 0):.1f}",
                    row.get("intent", ""),
                    row.get("cluster", ""),
                    row.get("url", ""),
                    f"{float(row.get('cpc') or 0):,.2f}",
                    row.get("priority", ""),
                    row.get("rank", ""),
                    row.get("status", ""),
                ),
            )
        kpis = keyword_kpis(self.keyword_rows)
        self.kw_metric_count.configure(text=f"{kpis['keywords']:,}")
        self.kw_metric_volume.configure(text=f"{kpis['total_volume']:,}")
        self.kw_metric_kd.configure(text=f"{kpis['average_difficulty']:.1f}")
        self.kw_metric_clusters.configure(text=f"{kpis['clusters']:,}")
        self.kw_metric_mapped.configure(text=f"{kpis['mapped']:,}")
        self._render_cluster_summary()

    def _render_cluster_summary(self):
        if not hasattr(self, "cluster_tree"):
            return
        self._clear_tree(self.cluster_tree)
        for row in cluster_summary(self.keyword_rows):
            self.cluster_tree.insert(
                "",
                "end",
                values=(
                    row["cluster"],
                    row["keywords"],
                    f"{row['total_volume']:,}",
                    row["avg_difficulty"],
                    row["dominant_intent"],
                    row["primary_keyword"],
                    row["landing_page"],
                ),
            )

    def _rebuild_keywords(self):
        if not self.keyword_rows:
            return
        if not messagebox.askyesno(
            "Phân loại lại",
            "Tool sẽ tính lại Search Intent và Cluster cho toàn bộ keyword.\n"
            "Các chỉnh sửa Intent/Cluster thủ công hiện tại sẽ bị thay thế. Tiếp tục?",
        ):
            return
        self.keyword_rows = rebuild_keyword_intelligence(
            self.keyword_rows, self.cluster_detail.get()
        )
        self._detect_cannibalization()
        self._render_keywords()
        self._save_state()
        self.status.set(
            f"Đã phân loại lại {len(self.keyword_rows):,} keyword ở mức "
            f"{self.cluster_detail.get()}."
        )

    def _edit_keyword(self):
        selected = self.keyword_tree.selection()
        if not selected:
            messagebox.showinfo("Chưa chọn", "Chọn một keyword cần sửa.")
            return
        index = int(selected[0])
        row = self.keyword_rows[index]
        window = tk.Toplevel(self)
        window.title("Chỉnh sửa Keyword")
        window.geometry("720x430")
        window.transient(self)
        window.grab_set()
        values = {
            key: tk.StringVar(value=str(row.get(key, "")))
            for key in (
                "keyword",
                "volume",
                "difficulty",
                "intent",
                "cluster",
                "url",
                "cpc",
                "priority",
            )
        }
        form = ttk.Frame(window, padding=16)
        form.pack(fill="both", expand=True)
        labels = (
            ("keyword", "Keyword"),
            ("volume", "Volume"),
            ("difficulty", "KD %"),
            ("intent", "Search Intent"),
            ("cluster", "Cluster"),
            ("url", "Landing Page"),
            ("cpc", "CPC"),
            ("priority", "Ưu tiên"),
        )
        for row_index, (key, label) in enumerate(labels):
            ttk.Label(form, text=label + ":").grid(
                row=row_index, column=0, sticky="e", padx=6, pady=6
            )
            if key == "intent":
                widget = ttk.Combobox(
                    form,
                    textvariable=values[key],
                    values=tuple(INTENT_COLORS),
                    state="readonly",
                )
            elif key == "priority":
                widget = ttk.Combobox(
                    form,
                    textvariable=values[key],
                    values=("P0", "P1", "P2"),
                    state="readonly",
                )
            else:
                widget = ttk.Entry(form, textvariable=values[key])
            widget.grid(row=row_index, column=1, sticky="ew", padx=6, pady=6)
        form.columnconfigure(1, weight=1)

        def save():
            updated = dict(row)
            for key, variable in values.items():
                updated[key] = variable.get()
            self.keyword_rows[index] = normalize_keyword_row(
                updated,
                source=clean_text(updated.get("source")) or "Manual",
                cluster_detail=self.cluster_detail.get(),
            )
            self._detect_cannibalization()
            self._render_keywords()
            self._save_state()
            window.destroy()

        ttk.Button(
            form, text="Lưu thay đổi", style="Accent.TButton", command=save
        ).grid(row=len(labels), column=1, sticky="e", pady=10)

    def _delete_keywords(self):
        selected = self.keyword_tree.selection()
        if not selected:
            return
        if not messagebox.askyesno(
            "Xóa keyword", f"Xóa {len(selected)} keyword đã chọn?"
        ):
            return
        indices = sorted((int(item) for item in selected), reverse=True)
        for index in indices:
            if 0 <= index < len(self.keyword_rows):
                self.keyword_rows.pop(index)
        self._render_keywords()
        self._save_state()

    def _export_keywords(self):
        if not self.keyword_rows:
            messagebox.showinfo("Chưa có dữ liệu", "Import hoặc thêm keyword trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile="keyword-intelligence-v44.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_keyword_workbook(path, self.keyword_rows)
        except Exception as exc:
            error = explain_exception(exc, "Xuất Keyword Excel")
            messagebox.showerror(error.title, error.user_message)
            return
        messagebox.showinfo("Đã xuất Excel", path)

    def _export_keyword_csv(self):
        if not self.keyword_rows:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="keyword-intelligence-v44.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        fields = [
            "keyword",
            "volume",
            "difficulty",
            "intent",
            "cluster",
            "url",
            "cpc",
            "competition",
            "results",
            "trend",
            "priority",
            "rank",
            "status",
            "source",
        ]
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.keyword_rows)

    def _rank_worker(self):
        try:
            researcher = DirectGoogleResearcher()
            mapped = [row for row in self.keyword_rows if normalize_url(row.get("url"))]
            if not mapped:
                raise ValueError(
                    "Chưa có keyword nào được map Landing Page để kiểm tra Rank."
                )
            for index, row in enumerate(mapped):
                result = researcher.rank(
                    row["keyword"],
                    row["url"],
                    self.country.get(),
                    self.language.get(),
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
                self.events.put(("status", f"Rank {index + 1}/{len(mapped)}"))
            self.events.put(("ranks-done",))
        except Exception as exc:
            error = explain_exception(exc, "Rank Tracking")
            self.events.put(("error", error.title, error.user_message))

    def _open_guide(self):
        candidates = [
            Path(sys.executable).resolve().parent / GUIDE_FILE,
            Path(__file__).resolve().parent / "output" / "pdf" / GUIDE_FILE,
            Path.cwd() / "output" / "pdf" / GUIDE_FILE,
        ]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if not path:
            messagebox.showinfo(
                "Chưa tìm thấy hướng dẫn",
                f"File {GUIDE_FILE} chưa có cạnh ứng dụng.\n"
                "Hãy cài bằng SEO_AI_Studio_V44_Setup.exe hoặc tải file hướng dẫn riêng.",
            )
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("Không mở được PDF", str(exc))


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
                log_path = (
                    Path(os.getenv("TEMP") or ".")
                    / "seo-ai-studio-v44-scheduled.log"
                )
                log_path.write_text(
                    f"{utc_now()} | {error.title} | {error.user_message}\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
            return 1
    AppV44().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
