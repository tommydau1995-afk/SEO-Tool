import csv
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from collections import Counter, deque
from dataclasses import asdict, dataclass
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

VERSION = "3.0.0"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SEOAIStudio/3.0"


def resource_path(path):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), path)


def normalize_url(value):
    value = value.strip()
    if value and not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    return parsed._replace(fragment="").geturl().rstrip("/") if parsed.netloc else ""


def text(value):
    return re.sub(r"\s+", " ", value or "").strip()


@dataclass
class Page:
    score: int
    status: int
    url: str
    title: str
    title_len: int
    meta: str
    meta_len: int
    h1: str
    h1_count: int
    words: int
    images: int
    missing_alt: int
    internal_links: int
    external_links: int
    canonical: str
    indexable: str
    response_ms: int
    issues: str


class Auditor:
    def __init__(self, timeout=12, user_agent=UA):
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": user_agent})

    def crawl(self, start_url, limit, callback, stop):
        host = urlparse(start_url).netloc.lower()
        todo, seen, pages = deque([start_url]), set(), []
        while todo and len(pages) < limit and not stop.is_set():
            url = urldefrag(todo.popleft())[0].rstrip("/")
            if url in seen:
                continue
            seen.add(url)
            callback(url, len(pages), limit)
            page, links = self.page(url, host)
            pages.append(page)
            for link in links:
                if link not in seen and link not in todo:
                    todo.append(link)
        return pages

    def page(self, url, host):
        started, links = time.perf_counter(), []
        data = dict(
            score=0, status=0, url=url, title="", title_len=0, meta="",
            meta_len=0, h1="", h1_count=0, words=0, images=0,
            missing_alt=0, internal_links=0, external_links=0,
            canonical="", indexable="Yes", response_ms=0, issues="",
        )
        try:
            response = self.http.get(url, timeout=self.timeout, allow_redirects=True)
            data["response_ms"] = int((time.perf_counter() - started) * 1000)
            data["status"] = response.status_code
            if "text/html" not in response.headers.get("Content-Type", "").lower():
                data["issues"] = "Không phải HTML"
                data["score"] = 40 if response.ok else 0
                return Page(**data), links
            soup = BeautifulSoup(response.text, "html.parser")
            data["title"] = text(soup.title.get_text(" ") if soup.title else "")
            data["title_len"] = len(data["title"])
            desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
            data["meta"] = text(desc.get("content", "") if desc else "")
            data["meta_len"] = len(data["meta"])
            h1s = soup.find_all("h1")
            data["h1_count"] = len(h1s)
            data["h1"] = text(h1s[0].get_text(" ") if h1s else "")
            canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
            data["canonical"] = urljoin(response.url, canonical.get("href", "")) if canonical else ""
            robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
            if robots and "noindex" in robots.get("content", "").lower():
                data["indexable"] = "No"
            images = soup.find_all("img")
            data["images"] = len(images)
            data["missing_alt"] = sum(1 for image in images if not text(image.get("alt", "")))
            for anchor in soup.find_all("a", href=True):
                raw = anchor.get("href", "").strip()
                if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
                    continue
                target = urldefrag(urljoin(response.url, raw))[0].rstrip("/")
                parsed = urlparse(target)
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc.lower() == host:
                    data["internal_links"] += 1
                    links.append(target)
                else:
                    data["external_links"] += 1
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            data["words"] = len(re.findall(r"\b[\wÀ-ỹ]+\b", text(soup.get_text(" "))))
            issues = self.issues(data)
            data["issues"] = " | ".join(issues)
            data["score"] = max(0, 100 - self.penalty(data, issues))
        except requests.RequestException as exc:
            data["response_ms"] = int((time.perf_counter() - started) * 1000)
            data["issues"] = "Lỗi kết nối: " + text(str(exc))[:130]
        except Exception as exc:
            data["issues"] = "Lỗi phân tích: " + text(str(exc))[:130]
        return Page(**data), links

    @staticmethod
    def issues(d):
        found = []
        if d["status"] != 200:
            found.append(f"HTTP {d['status']}")
        if not d["title"]:
            found.append("Thiếu Title")
        elif not 30 <= d["title_len"] <= 60:
            found.append("Title chưa tối ưu")
        if not d["meta"]:
            found.append("Thiếu Meta")
        elif not 70 <= d["meta_len"] <= 160:
            found.append("Meta chưa tối ưu")
        if d["h1_count"] == 0:
            found.append("Thiếu H1")
        elif d["h1_count"] > 1:
            found.append("Nhiều H1")
        if not d["canonical"]:
            found.append("Thiếu Canonical")
        if d["indexable"] == "No":
            found.append("Noindex")
        if d["words"] < 300:
            found.append("Nội dung mỏng")
        if d["missing_alt"]:
            found.append(f"{d['missing_alt']} ảnh thiếu ALT")
        if d["response_ms"] > 2000:
            found.append("Phản hồi chậm")
        return found

    @staticmethod
    def penalty(data, issues):
        points = 0
        for issue in issues:
            if issue.startswith("HTTP") or issue == "Noindex":
                points += 25
            elif issue in ("Thiếu Title", "Thiếu Meta", "Thiếu H1"):
                points += 15
            elif "ảnh thiếu ALT" in issue:
                points += min(12, data["missing_alt"] * 2)
            else:
                points += 7
        return min(100, points)

    def site_files(self, url):
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}/"
        output = {}
        for name in ("robots.txt", "sitemap.xml"):
            try:
                output[name] = self.http.get(urljoin(root, name), timeout=self.timeout).status_code
            except requests.RequestException:
                output[name] = 0
        return output


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"SEO AI Studio V{VERSION}")
        try:
            self.iconbitmap(resource_path("assets/seo_ai_studio_icon.ico"))
        except tk.TclError:
            pass
        self.geometry("1280x780")
        self.minsize(1000, 650)
        self.results, self.events = [], queue.Queue()
        self.stop = threading.Event()
        self.url = tk.StringVar()
        self.max_pages = tk.IntVar(value=30)
        self.status = tk.StringVar(value="Sẵn sàng quét website.")
        self.progress = tk.DoubleVar(value=0)
        self._style()
        self._header()
        self._tabs()
        self._footer()
        self.after(100, self._poll)

    def _style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
        style.configure("Head.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Score.TLabel", font=("Segoe UI", 28, "bold"))
        style.configure("Treeview", rowheight=27)

    def _header(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="x")
        ttk.Label(frame, text="SEO AI Studio V3", style="Title.TLabel").pack(side="left")
        ttk.Label(frame, text="Real Website Auditor", foreground="#1769c2").pack(side="left", padx=14)

    def _tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._dashboard()
        self._audit()
        self._strategy()
        self._content_plan()
        self._writer()

    def _tab(self, name):
        frame = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(frame, text=name)
        return frame

    def _dashboard(self):
        frame = self._tab("Dashboard")
        ttk.Label(frame, text="Tổng quan SEO", style="Head.TLabel").pack(anchor="w")
        cards = ttk.Frame(frame)
        cards.pack(fill="x", pady=14)
        self.score_label = ttk.Label(cards, text="--/100", style="Score.TLabel")
        self.score_label.pack(side="left", padx=(0, 70))
        self.pages_label = ttk.Label(cards, text="Trang đã quét: 0", font=("Segoe UI", 13))
        self.pages_label.pack(side="left", padx=(0, 70))
        self.errors_label = ttk.Label(cards, text="Trang có lỗi: 0", font=("Segoe UI", 13))
        self.errors_label.pack(side="left")
        self.summary = tk.Text(frame, wrap="word", font=("Segoe UI", 10))
        self.summary.pack(fill="both", expand=True)
        self._put(self.summary, "Chưa có dữ liệu. Mở Website Audit để bắt đầu.")

    def _audit(self):
        frame = self._tab("Website Audit")
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        ttk.Label(bar, text="Website:").grid(row=0, column=0)
        ttk.Entry(bar, textvariable=self.url, width=55).grid(row=0, column=1, padx=7, sticky="ew")
        ttk.Label(bar, text="Tối đa:").grid(row=0, column=2)
        ttk.Spinbox(bar, from_=1, to=300, textvariable=self.max_pages, width=7).grid(row=0, column=3, padx=5)
        self.start_btn = ttk.Button(bar, text="Bắt đầu quét", command=self.start_audit)
        self.start_btn.grid(row=0, column=4, padx=5)
        self.stop_btn = ttk.Button(bar, text="Dừng", command=self.stop.set, state="disabled")
        self.stop_btn.grid(row=0, column=5, padx=5)
        ttk.Button(bar, text="Xuất CSV", command=self.export_audit).grid(row=0, column=6, padx=5)
        bar.columnconfigure(1, weight=1)
        ttk.Progressbar(frame, maximum=100, variable=self.progress).pack(fill="x", pady=10)
        columns = ("score", "status", "url", "title", "meta", "h1", "words", "alt", "ms", "index", "issues")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        labels = ("Điểm", "HTTP", "URL", "Title", "Meta", "H1", "Từ", "Thiếu ALT", "ms", "Index", "Lỗi")
        widths = (55, 55, 280, 55, 55, 45, 55, 70, 55, 55, 350)
        for key, label, width in zip(columns, labels, widths):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        y = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        x = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        y.pack(side="right", fill="y")
        x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def _strategy(self):
        frame = self._tab("SEO Strategy")
        ttk.Label(frame, text="Chiến lược dựa trên Audit", style="Head.TLabel").pack(anchor="w")
        self.strategy = tk.Text(frame, wrap="word", font=("Segoe UI", 10))
        self.strategy.pack(fill="both", expand=True, pady=10)
        self._put(self.strategy, "Hãy chạy Website Audit để tạo chiến lược.")

    def _content_plan(self):
        frame = self._tab("Content Plan")
        ttk.Label(frame, text="Tạo kế hoạch nội dung", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=10)
        self.keyword = tk.StringVar()
        ttk.Label(bar, text="Từ khóa chính:").pack(side="left")
        ttk.Entry(bar, textvariable=self.keyword, width=45).pack(side="left", padx=7)
        ttk.Button(bar, text="Tạo Content Plan", command=self.make_plan).pack(side="left")
        ttk.Button(bar, text="Xuất CSV", command=self.export_plan).pack(side="left", padx=7)
        columns = ("cluster", "keyword", "intent", "title", "funnel")
        self.plan = ttk.Treeview(frame, columns=columns, show="headings")
        for key, label, width in zip(columns, ("Cụm", "Từ khóa", "Intent", "Tiêu đề", "Funnel"), (130, 210, 110, 520, 80)):
            self.plan.heading(key, text=label)
            self.plan.column(key, width=width, anchor="w")
        self.plan.pack(fill="both", expand=True)

    def _writer(self):
        frame = self._tab("SEO Writer")
        ttk.Label(frame, text="Tạo dàn ý SEO cục bộ", style="Head.TLabel").pack(anchor="w")
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=10)
        self.topic = tk.StringVar()
        ttk.Label(bar, text="Chủ đề:").pack(side="left")
        ttk.Entry(bar, textvariable=self.topic, width=55).pack(side="left", padx=7)
        ttk.Button(bar, text="Tạo dàn ý", command=self.make_outline).pack(side="left")
        ttk.Button(bar, text="Sao chép", command=self.copy_outline).pack(side="left", padx=7)
        self.outline = tk.Text(frame, wrap="word", font=("Segoe UI", 10))
        self.outline.pack(fill="both", expand=True)

    def _footer(self):
        frame = ttk.Frame(self, padding=(12, 6))
        frame.pack(fill="x")
        ttk.Label(frame, textvariable=self.status).pack(side="left")
        ttk.Label(frame, text=f"V{VERSION} — không cần API key").pack(side="right")

    def start_audit(self):
        url = normalize_url(self.url.get())
        if not url:
            messagebox.showwarning("Thiếu URL", "Nhập website, ví dụ: example.com")
            return
        self.url.set(url)
        self.results, self.stop = [], threading.Event()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal", command=self.stop.set)
        threading.Thread(target=self._work, args=(url,), daemon=True).start()

    def _work(self, url):
        auditor = Auditor()
        limit = max(1, min(300, int(self.max_pages.get())))
        pages = auditor.crawl(
            url, limit,
            lambda current, count, total: self.events.put(("progress", current, count, total)),
            self.stop,
        )
        files = auditor.site_files(url)
        self.events.put(("done", pages, files))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, current, count, total = event
                    self.status.set("Đang quét: " + current)
                    self.progress.set(min(95, count / max(1, total) * 100))
                else:
                    self._finish(event[1], event[2])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, pages, files):
        self.results = pages
        for p in pages:
            self.tree.insert("", "end", values=(
                p.score, p.status, p.url, p.title_len, p.meta_len, p.h1_count,
                p.words, p.missing_alt, p.response_ms, p.indexable, p.issues or "Tốt",
            ))
        score = round(sum(p.score for p in pages) / len(pages)) if pages else 0
        errors = sum(bool(p.issues) for p in pages)
        self.score_label.configure(text=f"{score}/100")
        self.pages_label.configure(text=f"Trang đã quét: {len(pages)}")
        self.errors_label.configure(text=f"Trang có lỗi: {errors}")
        summary, strategy = self.report(pages, files, score)
        self._put(self.summary, summary)
        self._put(self.strategy, strategy)
        self.progress.set(100)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status.set(f"Hoàn tất: {len(pages)} trang — điểm {score}/100")
        self.tabs.select(0)

    @staticmethod
    def report(pages, files, score):
        counter = Counter()
        for page in pages:
            counter.update(page.issues.split(" | ") if page.issues else [])
        lines = [
            f"ĐIỂM SEO: {score}/100", f"Trang đã quét: {len(pages)}",
            f"robots.txt: {'OK' if files['robots.txt'] == 200 else 'Lỗi/không tìm thấy'}",
            f"sitemap.xml: {'OK' if files['sitemap.xml'] == 200 else 'Lỗi/không tìm thấy'}",
            "", "LỖI PHỔ BIẾN:",
        ]
        lines += [f"- {name}: {count} trang" for name, count in counter.most_common(12)] or ["- Không phát hiện lỗi phổ biến."]
        priorities = []
        if any(name.startswith("HTTP") or name == "Noindex" for name in counter):
            priorities.append("P0 — Sửa lỗi HTTP và indexability trước.")
        if counter["Thiếu Title"] or counter["Thiếu H1"]:
            priorities.append("P0 — Bổ sung Title và H1 duy nhất cho các trang bị thiếu.")
        if counter["Thiếu Meta"]:
            priorities.append("P1 — Viết Meta Description 120–160 ký tự.")
        if counter["Nội dung mỏng"]:
            priorities.append("P1 — Mở rộng các trang dưới 300 từ theo đúng search intent.")
        if sum(p.missing_alt for p in pages):
            priorities.append("P2 — Bổ sung ALT mô tả cho hình ảnh.")
        if files["robots.txt"] != 200 or files["sitemap.xml"] != 200:
            priorities.append("P1 — Hoàn thiện robots.txt và sitemap.xml.")
        if not priorities:
            priorities.append("P2 — Duy trì nội dung và internal link, đo lại mỗi tháng.")
        strategy = "\n".join([
            "CHIẾN LƯỢC ƯU TIÊN", "", *priorities, "",
            "LỘ TRÌNH 30 NGÀY",
            "Tuần 1: HTTP, index, Title, H1, Canonical.",
            "Tuần 2: Meta, nội dung mỏng, ảnh thiếu ALT.",
            "Tuần 3: Topic cluster và internal link.",
            "Tuần 4: Search Console, sitemap và Audit lại.",
        ])
        return "\n".join(lines), strategy

    def export_audit(self):
        if not self.results:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy chạy Audit trước.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="seo-audit-v3.csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(asdict(self.results[0]).keys()))
                writer.writeheader()
                writer.writerows(asdict(page) for page in self.results)
            messagebox.showinfo("Đã xuất", path)

    def make_plan(self):
        keyword = text(self.keyword.get())
        if not keyword:
            messagebox.showwarning("Thiếu từ khóa", "Hãy nhập từ khóa chính.")
            return
        for item in self.plan.get_children():
            self.plan.delete(item)
        data = [
            ("Kiến thức", f"{keyword} là gì", "Informational", f"{keyword.title()} là gì? Hướng dẫn đầy đủ", "TOFU"),
            ("Hướng dẫn", f"cách {keyword}", "Informational", f"Cách {keyword} hiệu quả từng bước", "TOFU"),
            ("So sánh", f"{keyword} tốt nhất", "Commercial", f"Top giải pháp {keyword} tốt nhất", "MOFU"),
            ("Chi phí", f"giá {keyword}", "Commercial", f"Chi phí {keyword}: Bảng giá và lựa chọn", "MOFU"),
            ("Đánh giá", f"review {keyword}", "Commercial", f"Review {keyword}: Ưu và nhược điểm", "MOFU"),
            ("Mua hàng", f"{keyword} ở đâu", "Transactional", f"{keyword} ở đâu uy tín?", "BOFU"),
            ("Vấn đề", f"lỗi {keyword}", "Informational", f"Lỗi {keyword} thường gặp và cách sửa", "TOFU"),
            ("Dịch vụ", f"dịch vụ {keyword}", "Transactional", f"Dịch vụ {keyword}: Quy trình và báo giá", "BOFU"),
        ]
        for row in data:
            self.plan.insert("", "end", values=row)

    def export_plan(self):
        rows = [self.plan.item(item, "values") for item in self.plan.get_children()]
        if not rows:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy tạo Content Plan trước.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="content-plan-v3.csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Cụm", "Từ khóa", "Intent", "Tiêu đề", "Funnel"])
                writer.writerows(rows)

    def make_outline(self):
        topic = text(self.topic.get())
        if not topic:
            messagebox.showwarning("Thiếu chủ đề", "Hãy nhập chủ đề.")
            return
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        value = f"""SEO TITLE\n{topic.title()}: Hướng dẫn chi tiết và dễ áp dụng\n\nMETA DESCRIPTION\nTìm hiểu {topic}, quy trình thực hiện, kinh nghiệm lựa chọn và các lỗi cần tránh.\n\nURL SLUG\n/{slug}\n\nH1: {topic.title()}: Hướng dẫn toàn diện\nH2: {topic.title()} là gì?\nH2: Vì sao {topic} quan trọng?\nH2: Quy trình {topic} từng bước\n  H3: Chuẩn bị\n  H3: Thực hiện\n  H3: Kiểm tra và tối ưu\nH2: Những lỗi thường gặp\nH2: Kinh nghiệm và tiêu chí lựa chọn\nH2: Chi phí và thời gian\nH2: Câu hỏi thường gặp\nH2: Kết luận và lời kêu gọi hành động\n\nCHECKLIST\n- Title 30–60 ký tự; Meta 120–160 ký tự.\n- Một H1; cấu trúc H2/H3 rõ ràng.\n- 3–5 internal link; ALT cho hình ảnh.\n- Bám đúng search intent và kiểm tra tính chính xác."""
        self._put(self.outline, value)

    def copy_outline(self):
        value = self.outline.get("1.0", "end").strip()
        if value:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.status.set("Đã sao chép dàn ý.")

    @staticmethod
    def _put(widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value)


if __name__ == "__main__":
    App().mainloop()
