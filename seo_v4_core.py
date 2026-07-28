import csv
import hashlib
import json
import os
import re
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


VERSION = "4.0.0"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/126 Safari/537.36 SEOAIStudio/4.0"
)
SERP_ENDPOINT = "https://serpapi.com/search.json"


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_url(value):
    value = clean_text(value)
    if value and not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    if not parsed.netloc:
        return ""
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(path=path, fragment="").geturl()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value):
    normalized = unicodedata.normalize("NFKD", clean_text(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def app_data_dir():
    root = os.getenv("APPDATA")
    if root:
        base = Path(root)
    else:
        base = Path.home() / ".seo-ai-studio-v4"
    target = base / "SEO AI Studio V4"
    target.mkdir(parents=True, exist_ok=True)
    return target


@dataclass
class PageResult:
    score: int
    status: int
    url: str
    final_url: str
    title: str
    title_len: int
    meta: str
    meta_len: int
    h1: str
    h1_count: int
    h2_count: int
    words: int
    images: int
    missing_alt: int
    internal_links: int
    external_links: int
    canonical: str
    indexable: str
    response_ms: int
    schema_count: int
    og_title: str
    issues: list[str] = field(default_factory=list)
    depth: int = 0
    inlinks: int = 0
    dead_end: bool = False

    @property
    def issue_text(self):
        return " | ".join(self.issues)


@dataclass
class FixItem:
    priority: str
    issue: str
    url: str
    recommendation: str
    status: str = "Cần sửa"


@dataclass
class SerpSource:
    position: int
    title: str
    link: str
    snippet: str = ""
    headings: list[str] = field(default_factory=list)
    fetch_status: str = "Chưa đọc"


@dataclass
class SerpResearchResult:
    keyword: str
    searched_at: str
    sources: list[SerpSource]
    ai_overview: str
    related_questions: list[str]
    images: list[dict]
    outline: str


class SiteAuditor:
    def __init__(self, timeout=15, user_agent=USER_AGENT):
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update(
            {"User-Agent": user_agent, "Accept-Language": "vi,en-US;q=0.8,en;q=0.7"}
        )

    def crawl(
        self,
        start_url: str,
        limit: int,
        callback: Callable[[str, int, int], None] | None = None,
        stop: threading.Event | None = None,
    ):
        start_url = normalize_url(start_url)
        if not start_url:
            raise ValueError("URL website không hợp lệ.")
        host = urlparse(start_url).netloc.lower()
        queue = deque([(start_url, 0)])
        seen = set()
        pages = []
        graph = {}
        stop = stop or threading.Event()
        callback = callback or (lambda *_: None)

        while queue and len(pages) < max(1, min(500, int(limit))) and not stop.is_set():
            current, depth = queue.popleft()
            current = urldefrag(current)[0]
            current = normalize_url(current)
            if not current or current in seen:
                continue
            seen.add(current)
            callback(current, len(pages), limit)
            page, links = self.analyze_page(current, host)
            page.depth = depth
            page.dead_end = page.internal_links == 0
            pages.append(page)
            graph[current] = links
            for link in links:
                queued_urls = {item[0] for item in queue}
                if link not in seen and link not in queued_urls:
                    queue.append((link, depth + 1))
        incoming = Counter(link for links in graph.values() for link in links)
        for page in pages:
            page.inlinks = incoming.get(page.url, 0)
        self.last_graph = graph
        try:
            self.last_sitemap_urls = set(self.sitemap_urls(start_url))
        except Exception:
            self.last_sitemap_urls = set()
        self.last_orphans = sorted(self.last_sitemap_urls - set(graph))
        return pages

    def analyze_page(self, url, site_host):
        started = time.perf_counter()
        links = []
        data = {
            "score": 0,
            "status": 0,
            "url": url,
            "final_url": url,
            "title": "",
            "title_len": 0,
            "meta": "",
            "meta_len": 0,
            "h1": "",
            "h1_count": 0,
            "h2_count": 0,
            "words": 0,
            "images": 0,
            "missing_alt": 0,
            "internal_links": 0,
            "external_links": 0,
            "canonical": "",
            "indexable": "Yes",
            "response_ms": 0,
            "schema_count": 0,
            "og_title": "",
            "issues": [],
        }
        try:
            response = self.http.get(url, timeout=self.timeout, allow_redirects=True)
            data["response_ms"] = int((time.perf_counter() - started) * 1000)
            data["status"] = response.status_code
            data["final_url"] = normalize_url(response.url) or response.url
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                data["issues"] = ["Không phải HTML"]
                data["score"] = 40 if response.ok else 0
                return PageResult(**data), links

            soup = BeautifulSoup(response.text, "html.parser")
            title = clean_text(soup.title.get_text(" ") if soup.title else "")
            data["title"] = title
            data["title_len"] = len(title)
            desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
            data["meta"] = clean_text(desc.get("content", "") if desc else "")
            data["meta_len"] = len(data["meta"])
            h1s = soup.find_all("h1")
            data["h1_count"] = len(h1s)
            data["h1"] = clean_text(h1s[0].get_text(" ") if h1s else "")
            data["h2_count"] = len(soup.find_all("h2"))
            canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
            data["canonical"] = (
                normalize_url(urljoin(response.url, canonical.get("href", "")))
                if canonical
                else ""
            )
            robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
            x_robots = response.headers.get("X-Robots-Tag", "")
            robots_value = " ".join(
                [robots.get("content", "") if robots else "", x_robots]
            ).lower()
            if "noindex" in robots_value:
                data["indexable"] = "No"
            og = soup.find("meta", property="og:title")
            data["og_title"] = clean_text(og.get("content", "") if og else "")
            data["schema_count"] = len(
                soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)})
            )
            images = soup.find_all("img")
            data["images"] = len(images)
            data["missing_alt"] = sum(
                1 for image in images if not clean_text(image.get("alt", ""))
            )

            for anchor in soup.find_all("a", href=True):
                raw = clean_text(anchor.get("href", ""))
                if not raw or raw.startswith(
                    ("#", "mailto:", "tel:", "javascript:", "data:")
                ):
                    continue
                target = normalize_url(urljoin(response.url, raw))
                parsed = urlparse(target)
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc.lower() == site_host:
                    data["internal_links"] += 1
                    links.append(target)
                else:
                    data["external_links"] += 1

            for tag in soup(["script", "style", "noscript", "svg", "template"]):
                tag.decompose()
            visible = clean_text(soup.get_text(" "))
            data["words"] = len(re.findall(r"\b[\wÀ-ỹ]+\b", visible))
            data["issues"] = self.detect_issues(data)
            data["score"] = max(0, 100 - self.penalty(data))
        except requests.RequestException as exc:
            data["response_ms"] = int((time.perf_counter() - started) * 1000)
            data["issues"] = ["Lỗi kết nối: " + clean_text(exc)[:150]]
        except Exception as exc:
            data["issues"] = ["Lỗi phân tích: " + clean_text(exc)[:150]]
        return PageResult(**data), links

    @staticmethod
    def detect_issues(data):
        issues = []
        status = data["status"]
        if status != 200:
            issues.append(f"HTTP {status}")
        if not data["title"]:
            issues.append("Thiếu Title")
        elif not 30 <= data["title_len"] <= 60:
            issues.append("Title chưa tối ưu")
        if not data["meta"]:
            issues.append("Thiếu Meta")
        elif not 120 <= data["meta_len"] <= 160:
            issues.append("Meta chưa tối ưu")
        if data["h1_count"] == 0:
            issues.append("Thiếu H1")
        elif data["h1_count"] > 1:
            issues.append("Nhiều H1")
        if not data["canonical"]:
            issues.append("Thiếu Canonical")
        if data["indexable"] == "No":
            issues.append("Noindex")
        if data["words"] < 300:
            issues.append("Nội dung mỏng")
        if data["missing_alt"]:
            issues.append(f"{data['missing_alt']} ảnh thiếu ALT")
        if data["internal_links"] == 0:
            issues.append("Thiếu Internal Link")
        if data["response_ms"] > 2000:
            issues.append("Phản hồi chậm")
        if data["schema_count"] == 0:
            issues.append("Thiếu Schema")
        if not data["og_title"]:
            issues.append("Thiếu Open Graph")
        return issues

    @staticmethod
    def penalty(data):
        points = 0
        for issue in data["issues"]:
            if issue.startswith("HTTP") or issue == "Noindex":
                points += 25
            elif issue in ("Thiếu Title", "Thiếu Meta", "Thiếu H1"):
                points += 15
            elif "ảnh thiếu ALT" in issue:
                points += min(12, data["missing_alt"] * 2)
            elif issue in ("Thiếu Canonical", "Nội dung mỏng"):
                points += 10
            else:
                points += 5
        return min(points, 100)

    def site_files(self, url):
        parsed = urlparse(normalize_url(url))
        root = f"{parsed.scheme}://{parsed.netloc}/"
        result = {}
        for name in ("robots.txt", "sitemap.xml"):
            try:
                response = self.http.get(urljoin(root, name), timeout=self.timeout)
                result[name] = {
                    "status": response.status_code,
                    "url": response.url,
                    "size": len(response.content),
                }
            except requests.RequestException:
                result[name] = {"status": 0, "url": urljoin(root, name), "size": 0}
        try:
            sitemap_urls = self.sitemap_urls(url)
            result["sitemap.xml"]["url_count"] = len(sitemap_urls)
        except Exception:
            result["sitemap.xml"]["url_count"] = 0
        return result

    def sitemap_urls(self, url, max_sitemaps=20, max_urls=5000):
        parsed = urlparse(normalize_url(url))
        first = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        queue = deque([first])
        seen_maps = set()
        urls = []
        while queue and len(seen_maps) < max_sitemaps and len(urls) < max_urls:
            sitemap = queue.popleft()
            if sitemap in seen_maps:
                continue
            seen_maps.add(sitemap)
            response = self.http.get(sitemap, timeout=self.timeout)
            if response.status_code != 200:
                continue
            root = ET.fromstring(response.content)
            root_name = root.tag.rsplit("}", 1)[-1].lower()
            locations = [
                clean_text(element.text)
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1].lower() == "loc"
            ]
            if root_name == "sitemapindex":
                for child in locations:
                    if child and child not in seen_maps:
                        queue.append(child)
            else:
                for location in locations:
                    target = normalize_url(location)
                    if target:
                        urls.append(target)
                        if len(urls) >= max_urls:
                            break
        return list(dict.fromkeys(urls))


ISSUE_GUIDE = {
    "HTTP": ("P0", "Sửa URL lỗi, redirect chain hoặc liên kết trỏ tới trang lỗi."),
    "Noindex": ("P0", "Kiểm tra robots meta/X-Robots-Tag và mở index nếu trang cần SEO."),
    "Thiếu Title": ("P0", "Viết Title duy nhất, đúng intent, dài khoảng 30–60 ký tự."),
    "Thiếu H1": ("P0", "Bổ sung đúng một H1 mô tả chủ đề chính của trang."),
    "Nhiều H1": ("P1", "Giữ một H1 chính; chuyển tiêu đề phụ thành H2/H3."),
    "Thiếu Meta": ("P1", "Viết Meta Description hấp dẫn, khoảng 120–160 ký tự."),
    "Title chưa tối ưu": ("P1", "Rút gọn hoặc mở rộng Title về khoảng 30–60 ký tự."),
    "Meta chưa tối ưu": ("P1", "Điều chỉnh Meta Description về khoảng 120–160 ký tự."),
    "Thiếu Canonical": ("P1", "Thêm canonical tự tham chiếu hoặc URL chuẩn phù hợp."),
    "Nội dung mỏng": ("P1", "Mở rộng nội dung theo intent và bổ sung thông tin hữu ích."),
    "Thiếu Internal Link": ("P1", "Thêm liên kết nội bộ có anchor mô tả tới trang liên quan."),
    "Phản hồi chậm": ("P1", "Tối ưu máy chủ, cache, ảnh, JavaScript và CSS quan trọng."),
    "ảnh thiếu ALT": ("P2", "Bổ sung ALT mô tả ngắn gọn cho ảnh có ý nghĩa."),
    "Thiếu Schema": ("P2", "Thêm JSON-LD phù hợp như Article, Product, FAQ hoặc LocalBusiness."),
    "Thiếu Open Graph": ("P2", "Thêm og:title, og:description và og:image."),
}


def build_fix_queue(pages: Iterable[PageResult]):
    fixes = []
    for page in pages:
        for issue in page.issues:
            key = next((name for name in ISSUE_GUIDE if name in issue), issue)
            priority, recommendation = ISSUE_GUIDE.get(
                key, ("P2", "Kiểm tra thủ công và xử lý theo mục tiêu SEO của trang.")
            )
            fixes.append(
                FixItem(
                    priority=priority,
                    issue=issue,
                    url=page.url,
                    recommendation=recommendation,
                )
            )
    order = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(fixes, key=lambda item: (order.get(item.priority, 9), item.url))


def audit_summary(pages, site_files):
    score = round(sum(page.score for page in pages) / len(pages)) if pages else 0
    counter = Counter(issue for page in pages for issue in page.issues)
    lines = [
        f"ĐIỂM SEO: {score}/100",
        f"Trang đã quét: {len(pages)}",
        f"Trang có lỗi: {sum(bool(page.issues) for page in pages)}",
        (
            "robots.txt: OK"
            if site_files.get("robots.txt", {}).get("status") == 200
            else "robots.txt: Lỗi/không tìm thấy"
        ),
        (
            "sitemap.xml: OK"
            if site_files.get("sitemap.xml", {}).get("status") == 200
            else "sitemap.xml: Lỗi/không tìm thấy"
        ),
        "",
        "LỖI PHỔ BIẾN",
    ]
    lines.extend(
        [f"- {name}: {count} trang" for name, count in counter.most_common(15)]
        or ["- Không phát hiện lỗi phổ biến."]
    )
    return score, "\n".join(lines)


class ProjectStore:
    def __init__(self, root=None):
        self.root = Path(root or app_data_dir())
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "projects.json"

    def _read_index(self):
        if not self.index_path.exists():
            return {"projects": []}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"projects": []}

    def _write_index(self, data):
        temp = self.index_path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.index_path)

    def list_projects(self):
        return self._read_index().get("projects", [])

    def upsert_project(self, name, website):
        name = clean_text(name)
        website = normalize_url(website)
        if not name or not website:
            raise ValueError("Tên dự án và website là bắt buộc.")
        data = self._read_index()
        project_id = hashlib.sha1(website.encode("utf-8")).hexdigest()[:12]
        now = utc_now()
        project = next(
            (item for item in data["projects"] if item["id"] == project_id), None
        )
        if project:
            project.update({"name": name, "website": website, "updated_at": now})
        else:
            project = {
                "id": project_id,
                "name": name,
                "website": website,
                "created_at": now,
                "updated_at": now,
            }
            data["projects"].append(project)
        self._write_index(data)
        (self.root / project_id).mkdir(exist_ok=True)
        return project

    def save_snapshot(self, project, pages, site_files, keyword_map=None, fixes=None):
        project_dir = self.root / project["id"]
        project_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        payload = {
            "version": VERSION,
            "project": project,
            "created_at": utc_now(),
            "site_files": site_files,
            "pages": [asdict(page) for page in pages],
            "keyword_map": keyword_map or [],
            "fixes": [asdict(item) for item in (fixes or [])],
        }
        path = project_dir / f"audit-{stamp}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_snapshots(self, project_id):
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        return sorted(project_dir.glob("audit-*.json"), reverse=True)

    @staticmethod
    def load_snapshot(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def save_project_state(self, project_id, name, payload):
        project_dir = self.root / project_id
        project_dir.mkdir(exist_ok=True)
        path = project_dir / f"{slugify(name)}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp.replace(path)
        return path

    def load_project_state(self, project_id, name, default=None):
        path = self.root / project_id / f"{slugify(name)}.json"
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default


def compare_snapshots(previous, current):
    def issue_keys(snapshot):
        return {
            (page.get("url", ""), issue)
            for page in snapshot.get("pages", [])
            for issue in page.get("issues", [])
        }

    old = issue_keys(previous)
    new = issue_keys(current)
    return {
        "resolved": sorted(old - new),
        "new": sorted(new - old),
        "remaining": sorted(old & new),
    }


class SerpResearcher:
    def __init__(self, api_key, timeout=25, user_agent=USER_AGENT):
        self.api_key = clean_text(api_key)
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update(
            {"User-Agent": user_agent, "Accept-Language": "vi,en-US;q=0.8,en;q=0.7"}
        )

    def _serp_request(self, **params):
        if not self.api_key:
            raise ValueError("Hãy nhập SerpApi Key trong tab Tích hợp.")
        params["api_key"] = self.api_key
        response = self.http.get(SERP_ENDPOINT, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(clean_text(payload["error"]))
        return payload

    def research(self, keyword, gl="vn", hl="vi", callback=None):
        keyword = clean_text(keyword)
        if not keyword:
            raise ValueError("Hãy nhập từ khóa cần nghiên cứu.")
        callback = callback or (lambda *_: None)
        callback("Đang lấy Google Top 5 và AI Overview…", 5)
        search = self._serp_request(
            engine="google",
            q=keyword,
            gl=gl or "vn",
            hl=hl or "vi",
            num=10,
        )
        organic = search.get("organic_results", [])[:5]
        sources = [
            SerpSource(
                position=int(item.get("position", index + 1)),
                title=clean_text(item.get("title")),
                link=clean_text(item.get("link")),
                snippet=clean_text(item.get("snippet")),
            )
            for index, item in enumerate(organic)
            if item.get("link")
        ]

        callback("Đang đọc outline H1–H3 của 5 kết quả…", 25)
        for index, source in enumerate(sources):
            try:
                source.headings = self.extract_headings(source.link)
                source.fetch_status = (
                    f"Đã lấy {len(source.headings)} heading"
                    if source.headings
                    else "Không tìm thấy heading"
                )
            except Exception as exc:
                source.fetch_status = "Không đọc được: " + clean_text(exc)[:80]
            callback(
                f"Đã đọc {index + 1}/{len(sources)} kết quả…",
                25 + int(((index + 1) / max(1, len(sources))) * 35),
            )

        ai_overview = self.extract_ai_overview(search)
        if not ai_overview:
            token = (search.get("ai_overview") or {}).get("page_token")
            if token:
                callback("Đang lấy nội dung AI Overview mở rộng…", 65)
                extra = self._serp_request(
                    engine="google_ai_overview", page_token=token
                )
                ai_overview = self.extract_ai_overview(extra)

        callback("Đang lấy 4 hình ảnh liên quan…", 72)
        images = self.fetch_images(keyword, gl, hl)
        questions = [
            clean_text(item.get("question"))
            for item in search.get("related_questions", [])
            if item.get("question")
        ][:8]
        callback("Đang hợp nhất thành outline đầy đủ…", 88)
        outline = self.merge_outline(keyword, sources, ai_overview, questions, images)
        callback("Hoàn tất SERP Research.", 100)
        return SerpResearchResult(
            keyword=keyword,
            searched_at=utc_now(),
            sources=sources,
            ai_overview=ai_overview,
            related_questions=questions,
            images=images,
            outline=outline,
        )

    def rank(self, keyword, domain, gl="vn", hl="vi"):
        domain = urlparse(normalize_url(domain)).netloc.lower()
        if not domain:
            raise ValueError("Domain theo dõi thứ hạng không hợp lệ.")
        payload = self._serp_request(
            engine="google", q=clean_text(keyword), gl=gl or "vn", hl=hl or "vi", num=100
        )
        for item in payload.get("organic_results", []):
            result_domain = urlparse(clean_text(item.get("link"))).netloc.lower()
            if result_domain == domain or result_domain.endswith("." + domain):
                return {
                    "keyword": clean_text(keyword),
                    "position": int(item.get("position", 0)),
                    "url": clean_text(item.get("link")),
                    "title": clean_text(item.get("title")),
                    "checked_at": utc_now(),
                }
        return {
            "keyword": clean_text(keyword),
            "position": ">100",
            "url": "",
            "title": "",
            "checked_at": utc_now(),
        }

    def extract_headings(self, url):
        response = self.http.get(url, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()
        if "text/html" not in response.headers.get("Content-Type", "").lower():
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        result = []
        for heading in soup.find_all(["h1", "h2", "h3"]):
            value = clean_text(heading.get_text(" "))
            if 3 <= len(value) <= 180:
                result.append(f"{heading.name.upper()}: {value}")
        return self._unique(result)[:40]

    def fetch_images(self, keyword, gl, hl):
        try:
            payload = self._serp_request(
                engine="google_images",
                q=keyword,
                gl=gl or "vn",
                hl=hl or "vi",
                ijn=0,
            )
        except Exception:
            return []
        images = []
        for item in payload.get("images_results", []):
            original = clean_text(item.get("original") or item.get("thumbnail"))
            if not original:
                continue
            images.append(
                {
                    "title": clean_text(item.get("title")),
                    "original": original,
                    "thumbnail": clean_text(item.get("thumbnail")),
                    "source": clean_text(item.get("source")),
                    "link": clean_text(item.get("link")),
                }
            )
            if len(images) == 4:
                break
        return images

    @classmethod
    def extract_ai_overview(cls, payload):
        block = payload.get("ai_overview") or payload.get("answer") or {}
        values = []

        def visit(node):
            if isinstance(node, str):
                value = clean_text(node)
                if len(value) >= 20 and not value.startswith(("http://", "https://")):
                    values.append(value)
            elif isinstance(node, list):
                for item in node:
                    visit(item)
            elif isinstance(node, dict):
                preferred = (
                    "text",
                    "snippet",
                    "title",
                    "question",
                    "answer",
                    "list",
                    "text_blocks",
                    "contents",
                )
                for key in preferred:
                    if key in node:
                        visit(node[key])

        visit(block)
        return "\n".join(cls._unique(values))

    @staticmethod
    def _heading_key(value):
        value = re.sub(r"^H[1-3]:\s*", "", clean_text(value), flags=re.I)
        value = unicodedata.normalize("NFKD", value).encode(
            "ascii", "ignore"
        ).decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    @classmethod
    def _unique(cls, values):
        seen = set()
        result = []
        for value in values:
            key = cls._heading_key(value)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(clean_text(value))
        return result

    @classmethod
    def merge_outline(cls, keyword, sources, ai_overview, questions, images):
        h2_candidates = []
        h3_candidates = []
        for source in sources:
            for heading in source.headings:
                if heading.startswith("H2:"):
                    h2_candidates.append(heading[3:].strip())
                elif heading.startswith("H3:"):
                    h3_candidates.append(heading[3:].strip())
        h2_candidates = cls._unique(h2_candidates)[:12]
        h3_candidates = cls._unique(h3_candidates)[:10]
        if not h2_candidates:
            h2_candidates = [
                f"{keyword} là gì?",
                f"Vì sao {keyword} quan trọng?",
                f"Quy trình {keyword} từng bước",
                "Các lỗi thường gặp và cách khắc phục",
                "Kinh nghiệm lựa chọn và tối ưu",
            ]

        lines = [
            "CONTENT BRIEF TỔNG HỢP TOP 5 + AI OVERVIEW",
            f"Từ khóa chính: {keyword}",
            f"Search intent đề xuất: {cls.infer_intent(keyword)}",
            f"SEO Title: {keyword.title()} — Hướng dẫn đầy đủ và dễ áp dụng",
            (
                "Meta Description: "
                f"Tìm hiểu {keyword}, quy trình thực hiện, tiêu chí lựa chọn, "
                "lỗi cần tránh và câu trả lời cho các thắc mắc phổ biến."
            ),
            f"URL Slug: /{slugify(keyword)}",
            "",
            f"H1: {keyword.title()} — Hướng dẫn toàn diện",
            "",
            "MỞ BÀI",
            "- Nêu vấn đề, đối tượng đọc và kết quả người đọc nhận được.",
        ]
        if ai_overview:
            lines.extend(
                [
                    "- Tích hợp và diễn giải lại các ý chính từ AI Overview:",
                    *[f"  • {item}" for item in ai_overview.splitlines()[:8]],
                ]
            )
        else:
            lines.append(
                "- Google không trả về AI Overview cho truy vấn này; dùng dữ liệu Top 5."
            )

        lines.extend(["", "DÀN Ý HỢP NHẤT"])
        for index, heading in enumerate(h2_candidates, 1):
            lines.append(f"H2.{index}: {heading}")
            if index <= len(h3_candidates):
                lines.append(f"  H3: {h3_candidates[index - 1]}")
            lines.append("  - Giải thích rõ, có ví dụ, dữ liệu hoặc checklist thực hành.")

        if questions:
            lines.extend(["", "H2: Câu hỏi thường gặp"])
            lines.extend(f"  H3: {question}" for question in cls._unique(questions)[:8])

        lines.extend(
            [
                "",
                "H2: Kết luận và hành động tiếp theo",
                "- Tóm tắt giá trị chính; đưa CTA phù hợp search intent.",
                "",
                "GỢI Ý HÌNH ẢNH (kiểm tra quyền sử dụng trước khi đăng)",
            ]
        )
        lines.extend(
            [
                f"- Ảnh {index}: {item.get('title') or keyword} — "
                f"{item.get('original')}"
                for index, item in enumerate(images, 1)
            ]
            or ["- Chưa lấy được hình ảnh từ Google Images."]
        )
        lines.extend(["", "NGUỒN TOP 5 ĐÃ PHÂN TÍCH"])
        lines.extend(
            f"{source.position}. {source.title}\n   {source.link}\n   {source.fetch_status}"
            for source in sources
        )
        lines.extend(
            [
                "",
                "CHECKLIST BÀI VIẾT",
                "- Viết nguyên bản; không sao chép câu chữ từ nguồn.",
                "- Phủ đủ intent, entity, câu hỏi và góc nhìn quan trọng.",
                "- Một H1; H2/H3 rõ ràng; bổ sung internal link hợp lý.",
                "- Ảnh có ALT mô tả; kiểm tra bản quyền và nguồn ảnh.",
                "- Kiểm chứng số liệu, ngày tháng và tuyên bố quan trọng trước khi xuất bản.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def infer_intent(keyword):
        value = keyword.lower()
        if any(word in value for word in ("mua", "giá", "ở đâu", "đặt", "dịch vụ")):
            return "Transactional"
        if any(word in value for word in ("tốt nhất", "review", "so sánh", "top ")):
            return "Commercial"
        if any(word in value for word in ("đăng nhập", "website", "trang chủ")):
            return "Navigational"
        return "Informational"


class WordPressClient:
    def __init__(self, site_url, username, app_password, timeout=25):
        self.site_url = normalize_url(site_url)
        self.username = clean_text(username)
        self.app_password = clean_text(app_password)
        self.timeout = timeout

    def _endpoint(self, path):
        return urljoin(self.site_url.rstrip("/") + "/", f"wp-json/wp/v2/{path}")

    def test(self):
        response = requests.get(
            self._endpoint("users/me"),
            auth=(self.username, self.app_password),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return clean_text(data.get("name") or data.get("slug") or self.username)

    def create_draft(self, title, content):
        response = requests.post(
            self._endpoint("posts"),
            auth=(self.username, self.app_password),
            json={"title": clean_text(title), "content": content, "status": "draft"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def import_performance_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = {clean_text(key).lower(): clean_text(value) for key, value in row.items()}
            rows.append(normalized)
    return rows


def export_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if not rows:
        raise ValueError("Không có dữ liệu để xuất.")
    if fieldnames is None:
        first = rows[0]
        fieldnames = list(first.keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


LOG_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<url>\S+)(?:\s+HTTP/[0-9.]+)?"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)


class ServerLogAnalyzer:
    WASTE_PATTERNS = re.compile(
        r"(\?|/search|/tag/|/author/|/filter|/sort|/page/\d+|"
        r"\.(?:css|js|jpg|jpeg|png|gif|svg|webp|avif|woff2?|ico)(?:\?|$))",
        re.I,
    )

    def analyze(self, path, known_urls=None):
        known_urls = {normalize_url(url) for url in (known_urls or []) if url}
        total_lines = 0
        googlebot_hits = []
        by_url = Counter()
        by_status = Counter()
        by_device = Counter()
        by_day = Counter()

        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                total_lines += 1
                match = LOG_PATTERN.search(line)
                if not match:
                    continue
                data = match.groupdict()
                agent = clean_text(data.get("agent"))
                if "googlebot" not in agent.lower():
                    continue
                raw_url = data["url"]
                parsed = urlparse(raw_url)
                path_value = parsed.path or "/"
                if parsed.query:
                    path_value += "?" + parsed.query
                status = int(data["status"])
                device = (
                    "Smartphone"
                    if re.search(r"mobile|smartphone|android", agent, re.I)
                    else "Desktop"
                )
                day = clean_text(data.get("time")).split(":", 1)[0]
                hit = {
                    "time": clean_text(data.get("time")),
                    "path": path_value,
                    "status": status,
                    "device": device,
                    "ip": data.get("ip", ""),
                    "waste": self.is_waste(path_value, status),
                }
                googlebot_hits.append(hit)
                by_url[path_value] += 1
                by_status[status] += 1
                by_device[device] += 1
                if day:
                    by_day[day] += 1

        waste = [
            {"url": url, "hits": count}
            for url, count in by_url.most_common()
            if self.is_waste(url, 200)
            or any(
                hit["path"] == url and hit["status"] >= 300 for hit in googlebot_hits
            )
        ]
        top_urls = [{"url": url, "hits": count} for url, count in by_url.most_common(50)]
        low_crawl = []
        if known_urls:
            path_counts = Counter()
            for url, count in by_url.items():
                path_counts[urlparse(url).path or "/"] += count
            for url in sorted(known_urls):
                count = path_counts[urlparse(url).path or "/"]
                if count <= 1:
                    low_crawl.append({"url": url, "hits": count})
        return {
            "total_lines": total_lines,
            "googlebot_hits": len(googlebot_hits),
            "by_status": dict(by_status),
            "by_device": dict(by_device),
            "by_day": dict(by_day),
            "top_urls": top_urls,
            "waste_urls": waste[:100],
            "low_crawl_urls": low_crawl[:200],
            "spoofing_note": (
                "Kết quả nhận diện theo User-Agent. Với quyết định bảo mật, "
                "hãy xác minh reverse DNS của Googlebot trên máy chủ."
            ),
        }

    def is_waste(self, url, status):
        return status >= 300 or bool(self.WASTE_PATTERNS.search(url))


class PageSpeedClient:
    ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, api_key="", timeout=60):
        self.api_key = clean_text(api_key)
        self.timeout = timeout

    def analyze(self, url, strategy="mobile"):
        params = {
            "url": normalize_url(url),
            "strategy": strategy,
            "category": ["performance", "seo", "accessibility", "best-practices"],
        }
        if self.api_key:
            params["key"] = self.api_key
        response = requests.get(self.ENDPOINT, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})
        loading = data.get("loadingExperience", {}).get("metrics", {})

        def score(name):
            value = categories.get(name, {}).get("score")
            return round(value * 100) if isinstance(value, (int, float)) else None

        def numeric(audit_id):
            value = audits.get(audit_id, {}).get("numericValue")
            return round(value, 2) if isinstance(value, (int, float)) else None

        return {
            "url": normalize_url(url),
            "strategy": strategy,
            "fetched_at": lighthouse.get("fetchTime") or utc_now(),
            "performance": score("performance"),
            "seo": score("seo"),
            "accessibility": score("accessibility"),
            "best_practices": score("best-practices"),
            "lcp_ms": numeric("largest-contentful-paint"),
            "inp_ms": self._field_metric(loading, "INTERACTION_TO_NEXT_PAINT"),
            "cls": numeric("cumulative-layout-shift"),
            "ttfb_ms": numeric("server-response-time"),
            "fcp_ms": numeric("first-contentful-paint"),
            "speed_index_ms": numeric("speed-index"),
            "opportunities": [
                {
                    "id": key,
                    "title": clean_text(value.get("title")),
                    "display": clean_text(value.get("displayValue")),
                    "score": value.get("score"),
                }
                for key, value in audits.items()
                if value.get("details", {}).get("type") == "opportunity"
                and value.get("score") is not None
                and value.get("score") < 0.9
            ][:20],
        }

    @staticmethod
    def _field_metric(metrics, name):
        value = metrics.get(name, {}).get("percentile")
        return round(value, 2) if isinstance(value, (int, float)) else None
