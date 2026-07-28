"""Professional and growth features for SEO AI Studio V4.3.

The module extends the stable V4 crawler instead of duplicating it.  Network
clients deliberately expose small, testable methods and return plain Python
data so the desktop UI, scheduled runner and report exporters share one model.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Callable, Iterable
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from seo_v4_core import (
    USER_AGENT,
    ProjectStore,
    SerpResearchResult,
    SerpResearcher,
    SerpSource,
    ServerLogAnalyzer,
    SiteAuditor,
    WordPressClient,
    build_fix_queue,
    clean_text,
    normalize_url,
    utc_now,
)


VERSION = "4.3.0"
GOOGLE_SEARCH_URL = "https://www.google.com/search"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


class ProjectStoreV43(ProjectStore):
    """Project store compatible with V4 data while stamping V4.3 snapshots."""

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
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path


class FriendlyError(RuntimeError):
    """An actionable error safe to show directly in the desktop app."""

    def __init__(self, title: str, message: str, hint: str = ""):
        self.title = clean_text(title)
        self.message = clean_text(message)
        self.hint = clean_text(hint)
        super().__init__(self.user_message)

    @property
    def user_message(self):
        return self.message + (f"\n\nCách xử lý: {self.hint}" if self.hint else "")


def explain_exception(exc: Exception, service: str = "Dịch vụ") -> FriendlyError:
    """Translate common HTTP/API failures into concise Vietnamese guidance."""

    if isinstance(exc, FriendlyError):
        return exc
    if isinstance(exc, requests.Timeout):
        return FriendlyError(
            f"{service}: quá thời gian",
            "Máy chủ không phản hồi trong thời gian cho phép.",
            "Kiểm tra Internet, firewall/CDN rồi thử lại với ít URL hơn.",
        )
    if isinstance(exc, requests.ConnectionError):
        return FriendlyError(
            f"{service}: lỗi kết nối",
            "Không thể kết nối tới máy chủ.",
            "Kiểm tra Internet, DNS, proxy và chứng chỉ HTTPS.",
        )
    if isinstance(exc, requests.HTTPError):
        response = exc.response
        status = response.status_code if response is not None else 0
        hints = {
            400: "Kiểm tra URL, property và tham số đã nhập.",
            401: "Thông tin xác thực hết hạn hoặc không hợp lệ.",
            403: "Tài khoản chưa được cấp quyền hoặc API chưa được bật.",
            404: "Endpoint, property, post hoặc URL không tồn tại.",
            429: "Đã vượt hạn mức. Chờ một lúc rồi chạy lại với tốc độ thấp hơn.",
        }
        hint = hints.get(status, "Kiểm tra trạng thái dịch vụ và thử lại sau.")
        return FriendlyError(
            f"{service}: HTTP {status or 'không xác định'}",
            f"Máy chủ từ chối yêu cầu ({status or 'không rõ mã lỗi'}).",
            hint,
        )
    text = clean_text(exc)
    lowered = text.lower()
    if "captcha" in lowered or "unusual traffic" in lowered:
        return FriendlyError(
            f"{service}: Google yêu cầu xác minh",
            "Google không trả kết quả tìm kiếm thông thường cho yêu cầu này.",
            "Dán 5 URL kết quả vào chế độ thủ công hoặc thử lại sau.",
        )
    if "json" in lowered or "decode" in lowered:
        return FriendlyError(
            f"{service}: dữ liệu không hợp lệ",
            "Phản hồi không đúng định dạng JSON mong đợi.",
            "Kiểm tra endpoint/API key và xem dịch vụ có đang trả trang lỗi hay không.",
        )
    return FriendlyError(
        f"{service}: không hoàn tất",
        text or "Đã xảy ra lỗi chưa xác định.",
        "Kiểm tra cấu hình đầu vào rồi thử lại.",
    )


class DirectGoogleResearcher:
    """Top results and rank research without SerpApi or another paid API.

    Google HTML is intentionally treated as a best-effort source.  The manual
    URL fallback remains available because automated search responses can be
    rate-limited or replaced with consent/CAPTCHA pages.
    """

    def __init__(self, timeout=25, user_agent=USER_AGENT):
        self.timeout = timeout
        self.http = requests.Session()
        self.http.headers.update(
            {
                "User-Agent": user_agent.split(" SEOAIStudio/", 1)[0],
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.7,en;q=0.6",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    @staticmethod
    def _result_href(raw: str) -> str:
        raw = clean_text(raw)
        if raw.startswith("/url?"):
            query = parse_qs(urlparse(raw).query)
            raw = (query.get("q") or query.get("url") or [""])[0]
        if not raw.startswith(("http://", "https://")):
            return ""
        host = urlparse(raw).netloc.lower()
        if host.endswith("google.com") or ".google." in host:
            return ""
        return normalize_url(raw)

    @classmethod
    def parse_search_html(cls, html: str, limit=10) -> dict:
        soup = BeautifulSoup(html or "", "html.parser")
        plain = clean_text(soup.get_text(" ")).lower()
        blocked_tokens = (
            "our systems have detected unusual traffic",
            "unusual traffic from your computer network",
            "không phải là rô-bốt",
            "captcha",
        )
        if any(token in plain for token in blocked_tokens):
            raise FriendlyError(
                "Google yêu cầu xác minh",
                "Google đã trả trang CAPTCHA/unusual traffic.",
                "Dùng 5 URL thủ công hoặc chờ rồi thử lại.",
            )

        results = []
        seen = set()
        for heading in soup.select("h3"):
            anchor = heading.find_parent("a")
            if not anchor:
                continue
            link = cls._result_href(anchor.get("href", ""))
            if not link or link in seen:
                continue
            seen.add(link)
            container = heading.find_parent(["div", "article"])
            snippet = ""
            if container:
                candidates = [
                    clean_text(node.get_text(" "))
                    for node in container.select("div, span")
                    if len(clean_text(node.get_text(" "))) >= 45
                ]
                snippet = min(candidates, key=len) if candidates else ""
            results.append(
                {
                    "position": len(results) + 1,
                    "title": clean_text(heading.get_text(" ")),
                    "link": link,
                    "snippet": snippet[:500],
                }
            )
            if len(results) >= limit:
                break

        questions = []
        for node in soup.select("[data-q], [jsname]"):
            candidate = clean_text(node.get("data-q") or node.get_text(" "))
            if (
                candidate.endswith("?")
                and 6 <= len(candidate) <= 180
                and candidate not in questions
            ):
                questions.append(candidate)
            if len(questions) >= 8:
                break

        ai_text = ""
        selectors = (
            '[data-attrid*="AIOverview"]',
            '[data-attrid*="ai_overview"]',
            "[data-mcpr]",
        )
        for selector in selectors:
            node = soup.select_one(selector)
            candidate = clean_text(node.get_text(" ") if node else "")
            if len(candidate) >= 80:
                ai_text = candidate[:3500]
                break
        return {"results": results, "questions": questions, "ai_overview": ai_text}

    def search(self, keyword: str, gl="vn", hl="vi", limit=10) -> dict:
        keyword = clean_text(keyword)
        if not keyword:
            raise ValueError("Hãy nhập từ khóa cần nghiên cứu.")
        try:
            response = self.http.get(
                GOOGLE_SEARCH_URL,
                params={
                    "q": keyword,
                    "num": max(10, min(20, int(limit))),
                    "hl": clean_text(hl) or "vi",
                    "gl": clean_text(gl) or "vn",
                    "pws": "0",
                    "filter": "0",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = self.parse_search_html(response.text, limit=limit)
        except Exception as exc:
            raise explain_exception(exc, "Google Search") from exc
        if not payload["results"]:
            raise FriendlyError(
                "Không đọc được Top Google",
                "Google đã trả HTML nhưng không có cấu trúc kết quả có thể đọc.",
                "Dán 5 URL vào ô URL thủ công rồi chạy lại.",
            )
        return payload

    def research(
        self,
        keyword,
        gl="vn",
        hl="vi",
        manual_urls: Iterable[str] | None = None,
        callback: Callable[[str, int], None] | None = None,
    ):
        keyword = clean_text(keyword)
        callback = callback or (lambda *_: None)
        manual = []
        for value in manual_urls or []:
            target = normalize_url(value)
            if target and target not in manual:
                manual.append(target)
        callback("Đang lấy Top 5 trực tiếp từ Google…", 8)
        if manual:
            sources = [
                SerpSource(position=i + 1, title=f"Nguồn thủ công {i + 1}", link=url)
                for i, url in enumerate(manual[:5])
            ]
            search = {"questions": [], "ai_overview": ""}
        else:
            search = self.search(keyword, gl, hl, limit=10)
            sources = [
                SerpSource(
                    position=item["position"],
                    title=item["title"],
                    link=item["link"],
                    snippet=item["snippet"],
                )
                for item in search["results"][:5]
            ]

        callback("Đang crawl H1-H3 và ảnh của 5 nguồn…", 25)
        images = []
        for index, source in enumerate(sources):
            try:
                headings, image, page_title = self.extract_page(source.link)
                source.headings = headings
                if page_title and source.title.startswith("Nguồn thủ công"):
                    source.title = page_title
                source.fetch_status = (
                    f"Đã lấy {len(headings)} heading"
                    if headings
                    else "Không tìm thấy heading"
                )
                if image and image not in {row["original"] for row in images}:
                    images.append(
                        {
                            "position": len(images) + 1,
                            "title": source.title,
                            "original": image,
                            "source": source.link,
                        }
                    )
            except Exception as exc:
                source.fetch_status = "Không đọc được: " + clean_text(exc)[:100]
            callback(
                f"Đã đọc {index + 1}/{len(sources)} nguồn…",
                25 + round((index + 1) / max(1, len(sources)) * 50),
            )
        callback("Đang hợp nhất outline và content gap…", 88)
        outline = SerpResearcher.merge_outline(
            keyword,
            sources,
            search.get("ai_overview", ""),
            search.get("questions", []),
            images[:4],
        )
        if not search.get("ai_overview"):
            outline += (
                "\n\nGHI CHÚ AI OVERVIEW\n"
                "- Google không cung cấp AI Overview ổn định trong chế độ trực tiếp.\n"
                "- Outline vẫn được tổng hợp từ H1-H3 của 5 kết quả đầu.\n"
            )
        callback("Hoàn tất Top 5 không cần SerpApi.", 100)
        return SerpResearchResult(
            keyword=keyword,
            searched_at=utc_now(),
            sources=sources,
            ai_overview=search.get("ai_overview", ""),
            related_questions=search.get("questions", []),
            images=images[:4],
            outline=outline,
        )

    def extract_page(self, url):
        response = self.http.get(url, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        headings = []
        for node in soup.find_all(["h1", "h2", "h3"]):
            value = clean_text(node.get_text(" "))
            if value:
                headings.append(f"{node.name.upper()}: {value}")
        image_node = (
            soup.find("meta", property="og:image")
            or soup.find("meta", attrs={"name": "twitter:image"})
        )
        image = ""
        if image_node:
            image = urljoin(response.url, clean_text(image_node.get("content", "")))
        title = clean_text(soup.title.get_text(" ") if soup.title else "")
        return headings[:120], image, title

    def rank(self, keyword, domain, gl="vn", hl="vi", limit=20):
        target_host = urlparse(normalize_url(domain)).netloc.lower().removeprefix("www.")
        payload = self.search(keyword, gl, hl, limit=limit)
        for item in payload["results"]:
            host = urlparse(item["link"]).netloc.lower().removeprefix("www.")
            if host == target_host or host.endswith("." + target_host):
                return {
                    "position": item["position"],
                    "link": item["link"],
                    "title": item["title"],
                    "checked_at": utc_now(),
                }
        return {"position": ">20", "link": "", "title": "", "checked_at": utc_now()}


class SearchConsoleClient:
    """Read-only Search Console client using a service account JSON file."""

    def __init__(self, credential_path: str, timeout=60):
        path = Path(clean_text(credential_path))
        if not path.exists():
            raise FriendlyError(
                "Thiếu Service Account JSON",
                "Không tìm thấy file xác thực Google Search Console.",
                "Chọn file JSON và cấp email service account quyền đọc property GSC.",
            )
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise FriendlyError(
                "Thiếu thư viện Google",
                "Bản chạy hiện tại chưa có Google API Client.",
                "Cài lại SEO AI Studio V4.3 bằng bộ cài đầy đủ.",
            ) from exc
        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(path), scopes=[GSC_SCOPE]
            )
            self.service = build(
                "searchconsole",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception as exc:
            raise explain_exception(exc, "Google Search Console") from exc
        self.credential_path = str(path)
        self.timeout = timeout

    def list_sites(self):
        try:
            return self.service.sites().list().execute().get("siteEntry", [])
        except Exception as exc:
            raise explain_exception(exc, "Google Search Console") from exc

    def search_analytics(
        self,
        site_url,
        start_date,
        end_date,
        dimensions=("date", "page", "query"),
        row_limit=25000,
    ):
        site_url = clean_text(site_url)
        if not site_url:
            raise ValueError("Hãy nhập property GSC, ví dụ sc-domain:example.com.")
        body = {
            "startDate": str(start_date),
            "endDate": str(end_date),
            "dimensions": list(dimensions),
            "rowLimit": max(1, min(25000, int(row_limit))),
            "dataState": "final",
        }
        try:
            payload = (
                self.service.searchanalytics()
                .query(siteUrl=site_url, body=body)
                .execute()
            )
        except Exception as exc:
            raise explain_exception(exc, "Google Search Console") from exc
        rows = []
        for raw in payload.get("rows", []):
            keys = raw.get("keys", [])
            row = {
                dimension: keys[index] if index < len(keys) else ""
                for index, dimension in enumerate(dimensions)
            }
            row.update(
                {
                    "clicks": raw.get("clicks", 0),
                    "impressions": raw.get("impressions", 0),
                    "ctr": raw.get("ctr", 0),
                    "position": raw.get("position", 0),
                }
            )
            rows.append(row)
        return rows

    def list_sitemaps(self, site_url):
        try:
            return (
                self.service.sitemaps()
                .list(siteUrl=clean_text(site_url))
                .execute()
                .get("sitemap", [])
            )
        except Exception as exc:
            raise explain_exception(exc, "Google Search Console") from exc

    def inspect_url(self, site_url, inspection_url, language_code="vi-VN"):
        body = {
            "inspectionUrl": normalize_url(inspection_url),
            "siteUrl": clean_text(site_url),
            "languageCode": language_code,
        }
        try:
            return (
                self.service.urlInspection()
                .index()
                .inspect(body=body)
                .execute()
                .get("inspectionResult", {})
            )
        except Exception as exc:
            raise explain_exception(exc, "URL Inspection") from exc


def build_link_map(pages, graph, sitemap_urls=()):
    page_by_url = {page.url: page for page in pages}
    edges = []
    incoming = Counter()
    for source, targets in (graph or {}).items():
        source_page = page_by_url.get(source)
        for target in sorted(set(targets)):
            incoming[target] += 1
            target_page = page_by_url.get(target)
            edges.append(
                {
                    "source": source,
                    "source_depth": getattr(source_page, "depth", ""),
                    "target": target,
                    "target_depth": getattr(target_page, "depth", ""),
                    "target_inlinks": getattr(target_page, "inlinks", incoming[target]),
                    "target_status": getattr(target_page, "status", "Chưa crawl"),
                }
            )
    crawled = set(page_by_url)
    sitemap = {normalize_url(value) for value in sitemap_urls if normalize_url(value)}
    orphans = sorted(sitemap - crawled)
    dead_ends = sorted(page.url for page in pages if page.dead_end)
    deep_pages = sorted(page.url for page in pages if page.depth > 3)
    weak_pages = sorted(
        page.url for page in pages if page.depth > 0 and page.inlinks <= 1
    )
    return {
        "edges": edges,
        "crawled_urls": len(crawled),
        "sitemap_urls": len(sitemap),
        "sitemap_coverage": round(len(crawled & sitemap) / len(sitemap) * 100, 1)
        if sitemap
        else 0,
        "orphans": orphans,
        "dead_ends": dead_ends,
        "deep_pages": deep_pages,
        "weak_pages": weak_pages,
    }


class AdvancedServerLogAnalyzer(ServerLogAnalyzer):
    """V4 log parser with corrected path matching and crawl efficiency KPIs."""

    def analyze(self, path, known_urls=None):
        report = super().analyze(path, known_urls)
        known_urls = [normalize_url(url) for url in (known_urls or []) if normalize_url(url)]
        by_path = {row["url"]: row["hits"] for row in report.get("top_urls", [])}
        low_crawl = []
        for url in known_urls:
            parsed = urlparse(url)
            route = parsed.path or "/"
            if parsed.query:
                route += "?" + parsed.query
            hits = by_path.get(route, 0)
            if hits <= 1:
                low_crawl.append({"url": url, "hits": hits})
        report["low_crawl_urls"] = low_crawl
        waste_hits = sum(row["hits"] for row in report.get("waste_urls", []))
        total = report.get("googlebot_hits", 0)
        report["waste_hits"] = waste_hits
        report["useful_hits"] = max(0, total - waste_hits)
        report["crawl_efficiency"] = (
            round((total - waste_hits) / total * 100, 1) if total else 0
        )
        device = report.get("by_device", {})
        smartphone = device.get("Smartphone", 0)
        desktop = device.get("Desktop", 0)
        report["mobile_share"] = round(smartphone / total * 100, 1) if total else 0
        report["desktop_share"] = round(desktop / total * 100, 1) if total else 0
        statuses = report.get("by_status", {})
        report["error_hits"] = sum(
            count for status, count in statuses.items() if int(status) >= 400
        )
        return report


def _first_value(row, names, default=""):
    normalized = {clean_text(key).lower(): value for key, value in row.items()}
    for name in names:
        if clean_text(name).lower() in normalized:
            return normalized[clean_text(name).lower()]
    return default


class BacklinkAnalyzer:
    SOURCE_KEYS = (
        "source",
        "source url",
        "referring page",
        "referring url",
        "url from",
        "backlink",
    )
    TARGET_KEYS = ("target", "target url", "destination", "url to", "landing page")
    ANCHOR_KEYS = ("anchor", "anchor text", "text")
    DOMAIN_RATING_KEYS = ("dr", "da", "domain rating", "domain authority", "authority")
    FOLLOW_KEYS = ("follow", "dofollow", "link type", "type")
    TRAFFIC_KEYS = ("traffic", "organic traffic", "ref traffic")

    @classmethod
    def import_csv(cls, path):
        rows = []
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            for raw in csv.DictReader(handle, dialect=dialect):
                source = normalize_url(_first_value(raw, cls.SOURCE_KEYS))
                if not source:
                    continue
                target = normalize_url(_first_value(raw, cls.TARGET_KEYS))
                anchor = clean_text(_first_value(raw, cls.ANCHOR_KEYS))
                authority_raw = clean_text(_first_value(raw, cls.DOMAIN_RATING_KEYS, "0"))
                traffic_raw = clean_text(_first_value(raw, cls.TRAFFIC_KEYS, "0"))
                try:
                    authority = float(re.sub(r"[^\d.]", "", authority_raw) or 0)
                except ValueError:
                    authority = 0
                try:
                    traffic = float(re.sub(r"[^\d.]", "", traffic_raw) or 0)
                except ValueError:
                    traffic = 0
                follow_value = clean_text(_first_value(raw, cls.FOLLOW_KEYS, "follow")).lower()
                follow = not any(token in follow_value for token in ("nofollow", "ugc", "sponsored", "false", "0"))
                domain = urlparse(source).netloc.lower().removeprefix("www.")
                rows.append(
                    {
                        "source": source,
                        "domain": domain,
                        "target": target,
                        "anchor": anchor,
                        "authority": authority,
                        "traffic": traffic,
                        "follow": follow,
                        "risk": cls.risk_level(source, anchor, authority),
                    }
                )
        return rows

    @staticmethod
    def risk_level(source, anchor, authority):
        host = urlparse(source).netloc.lower()
        spam_tokens = ("casino", "bet", "porn", "viagra", "loan", "crypto-airdrop")
        suspicious_tlds = (".xyz", ".top", ".click", ".work", ".gq")
        if any(token in (host + " " + anchor.lower()) for token in spam_tokens):
            return "Cao"
        if host.endswith(suspicious_tlds) and authority < 10:
            return "Cao"
        if authority < 5:
            return "Trung bình"
        return "Thấp"

    @staticmethod
    def summarize(rows):
        rows = list(rows)
        domains = {row["domain"] for row in rows}
        follow = sum(bool(row.get("follow")) for row in rows)
        risky = sum(row.get("risk") == "Cao" for row in rows)
        anchors = Counter(row.get("anchor") or "(trống)" for row in rows)
        authorities = [float(row.get("authority", 0)) for row in rows]
        return {
            "backlinks": len(rows),
            "referring_domains": len(domains),
            "dofollow_percent": round(follow / len(rows) * 100, 1) if rows else 0,
            "high_risk": risky,
            "median_authority": round(median(authorities), 1) if authorities else 0,
            "top_anchors": anchors.most_common(10),
        }


def parse_number(value):
    text = clean_text(value).replace(",", "").replace("%", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def parse_iso_date(value):
    text = clean_text(value)[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def analyze_content_decay(rows, reference_date=None, window_days=30):
    """Compare the latest window with the directly preceding window per URL."""

    reference_date = reference_date or date.today()
    current_start = reference_date - timedelta(days=window_days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)
    grouped = defaultdict(
        lambda: {"current_clicks": 0.0, "previous_clicks": 0.0,
                 "current_impressions": 0.0, "previous_impressions": 0.0}
    )
    for row in rows:
        page = normalize_url(
            _first_value(row, ("page", "url", "landing page", "trang"))
        )
        row_date = parse_iso_date(_first_value(row, ("date", "ngày")))
        if not page or not row_date:
            continue
        clicks = parse_number(_first_value(row, ("clicks", "organic clicks", "lượt nhấp")))
        impressions = parse_number(
            _first_value(row, ("impressions", "lượt hiển thị"))
        )
        bucket = grouped[page]
        if current_start <= row_date <= reference_date:
            bucket["current_clicks"] += clicks
            bucket["current_impressions"] += impressions
        elif previous_start <= row_date <= previous_end:
            bucket["previous_clicks"] += clicks
            bucket["previous_impressions"] += impressions
    results = []
    for page, values in grouped.items():
        previous = values["previous_clicks"]
        current = values["current_clicks"]
        click_change = (
            round((current - previous) / previous * 100, 1)
            if previous
            else (100.0 if current else 0.0)
        )
        prev_imp = values["previous_impressions"]
        cur_imp = values["current_impressions"]
        impression_change = (
            round((cur_imp - prev_imp) / prev_imp * 100, 1)
            if prev_imp
            else (100.0 if cur_imp else 0.0)
        )
        if click_change <= -30 or impression_change <= -35:
            status = "Decay nặng"
        elif click_change <= -15 or impression_change <= -20:
            status = "Cần làm mới"
        elif click_change > 15:
            status = "Tăng trưởng"
        else:
            status = "Ổn định"
        results.append(
            {
                "page": page,
                **values,
                "click_change_percent": click_change,
                "impression_change_percent": impression_change,
                "status": status,
            }
        )
    order = {"Decay nặng": 0, "Cần làm mới": 1, "Ổn định": 2, "Tăng trưởng": 3}
    return sorted(
        results,
        key=lambda row: (order.get(row["status"], 9), row["click_change_percent"]),
    )


def analyze_content_gap(keyword, own_url, serp_result, own_headings=None):
    own_headings = own_headings or []
    own_keys = {SerpResearcher._heading_key(value) for value in own_headings}
    frequency = Counter()
    examples = {}
    for source in serp_result.sources:
        for heading in source.headings:
            key = SerpResearcher._heading_key(heading)
            if not key:
                continue
            frequency[key] += 1
            examples.setdefault(key, clean_text(re.sub(r"^H[1-6]:\s*", "", heading)))
    gaps = [
        {
            "topic": examples[key],
            "competitor_count": count,
            "coverage": f"{count}/{max(1, len(serp_result.sources))}",
            "priority": "P0" if count >= 4 else ("P1" if count >= 2 else "P2"),
        }
        for key, count in frequency.most_common()
        if key not in own_keys
    ]
    return {
        "keyword": clean_text(keyword),
        "own_url": normalize_url(own_url),
        "gaps": gaps[:100],
        "own_heading_count": len(own_headings),
        "competitor_heading_count": sum(len(source.headings) for source in serp_result.sources),
    }


def competitor_share_of_voice(rank_rows):
    """Calculate visibility using a simple top-20 reciprocal position model."""

    scores = defaultdict(float)
    keywords = set()
    for row in rank_rows:
        keyword = clean_text(row.get("keyword"))
        domain = clean_text(row.get("domain"))
        keywords.add(keyword)
        raw_position = row.get("position")
        try:
            position = int(raw_position)
        except (TypeError, ValueError):
            position = 100
        scores[domain] += max(0, 21 - position) / 20
    total = sum(scores.values())
    return [
        {
            "domain": domain,
            "visibility_score": round(score, 2),
            "share_of_voice": round(score / total * 100, 1) if total else 0,
            "keywords": len(keywords),
        }
        for domain, score in sorted(scores.items(), key=lambda item: -item[1])
    ]


def build_roadmap(fixes=(), decay_rows=(), backlink_summary=None, gsc_rows=()):
    items = []
    for fix in fixes:
        priority = getattr(fix, "priority", fix.get("priority", "P2") if isinstance(fix, dict) else "P2")
        issue = getattr(fix, "issue", fix.get("issue", "") if isinstance(fix, dict) else "")
        url = getattr(fix, "url", fix.get("url", "") if isinstance(fix, dict) else "")
        recommendation = getattr(
            fix,
            "recommendation",
            fix.get("recommendation", "") if isinstance(fix, dict) else "",
        )
        phase = 30 if priority == "P0" else (60 if priority == "P1" else 90)
        items.append(
            {
                "phase_days": phase,
                "workstream": "Technical SEO",
                "priority": priority,
                "action": issue,
                "url": url,
                "success_metric": recommendation,
                "status": getattr(fix, "status", "Cần làm"),
            }
        )
    for row in decay_rows:
        if row.get("status") not in ("Decay nặng", "Cần làm mới"):
            continue
        phase = 30 if row["status"] == "Decay nặng" else 60
        items.append(
            {
                "phase_days": phase,
                "workstream": "Content SEO",
                "priority": "P0" if phase == 30 else "P1",
                "action": f"Làm mới nội dung ({row['click_change_percent']}% clicks)",
                "url": row["page"],
                "success_metric": "Khôi phục clicks/impressions so với kỳ trước",
                "status": "Cần làm",
            }
        )
    if backlink_summary and backlink_summary.get("high_risk"):
        items.append(
            {
                "phase_days": 60,
                "workstream": "Authority",
                "priority": "P1",
                "action": f"Rà soát {backlink_summary['high_risk']} backlink rủi ro cao",
                "url": "",
                "success_metric": "Hoàn tất đánh giá thủ công và ghi nhận quyết định",
                "status": "Cần làm",
            }
        )
    if gsc_rows:
        items.append(
            {
                "phase_days": 90,
                "workstream": "Measurement",
                "priority": "P2",
                "action": "Đánh giá KPI GSC 90 ngày",
                "url": "",
                "success_metric": "Tăng clicks, impressions và landing pages có traffic",
                "status": "Theo dõi",
            }
        )
    return sorted(items, key=lambda row: (row["phase_days"], row["priority"], row["url"]))


class WordPressProClient(WordPressClient):
    def _request(self, method, path, **kwargs):
        try:
            response = requests.request(
                method,
                self._endpoint(path),
                auth=(self.username, self.app_password),
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise explain_exception(exc, "WordPress") from exc

    def get_post(self, post_id):
        return self._request("GET", f"posts/{int(post_id)}", params={"context": "edit"})

    def list_revisions(self, post_id):
        return self._request(
            "GET", f"posts/{int(post_id)}/revisions", params={"context": "edit", "per_page": 100}
        )

    def get_revision(self, post_id, revision_id):
        return self._request(
            "GET",
            f"posts/{int(post_id)}/revisions/{int(revision_id)}",
            params={"context": "edit"},
        )

    def update_post(self, post_id, title, content, status=None):
        payload = {"title": clean_text(title), "content": content}
        if status:
            payload["status"] = status
        return self._request("POST", f"posts/{int(post_id)}", json=payload)

    def rollback(self, post_id, revision_id=None):
        revisions = self.list_revisions(post_id)
        if not revisions:
            raise FriendlyError(
                "Không có revision",
                "WordPress không trả revision nào cho bài viết này.",
                "Bật revisions trong WordPress hoặc chọn bài viết khác.",
            )
        revision = (
            self.get_revision(post_id, revision_id)
            if revision_id
            else revisions[0]
        )
        title = (revision.get("title") or {}).get("raw") or (revision.get("title") or {}).get("rendered", "")
        content = (revision.get("content") or {}).get("raw") or (revision.get("content") or {}).get("rendered", "")
        updated = self.update_post(post_id, title, content)
        return {
            "post": updated,
            "restored_revision": revision.get("id"),
            "restored_modified": revision.get("modified"),
        }


class WindowsAuditScheduler:
    def __init__(self, executable=None):
        self.executable = str(
            executable
            or (sys.executable if getattr(sys, "frozen", False) else Path(sys.argv[0]).resolve())
        )

    @staticmethod
    def task_name(project_id):
        return f"SEO AI Studio V4.3 - {clean_text(project_id)}"

    def create(self, project_id, frequency="DAILY", start_time="02:00", max_pages=100):
        if os.name != "nt":
            raise FriendlyError(
                "Scheduled Audit chỉ tạo trên Windows",
                "Task Scheduler không khả dụng trên hệ điều hành hiện tại.",
                "Cài bộ Setup V4.3 trên Windows rồi tạo lịch từ ứng dụng.",
            )
        frequency = clean_text(frequency).upper()
        if frequency not in ("DAILY", "WEEKLY"):
            raise ValueError("Tần suất phải là DAILY hoặc WEEKLY.")
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clean_text(start_time)):
            raise ValueError("Giờ chạy phải có định dạng HH:MM.")
        run = (
            f'"{self.executable}" --scheduled-audit {clean_text(project_id)} '
            f"--max-pages {max(1, min(500, int(max_pages)))}"
        )
        command = [
            "schtasks.exe",
            "/Create",
            "/TN",
            self.task_name(project_id),
            "/TR",
            run,
            "/SC",
            frequency,
            "/ST",
            clean_text(start_time),
            "/F",
        ]
        if frequency == "WEEKLY":
            command.extend(["/D", "MON"])
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise FriendlyError(
                "Không tạo được lịch Audit",
                clean_text(result.stderr or result.stdout),
                "Mở ứng dụng bằng tài khoản có quyền tạo Task Scheduler và thử lại.",
            )
        return {"task_name": self.task_name(project_id), "command": run}

    def delete(self, project_id):
        if os.name != "nt":
            raise FriendlyError(
                "Scheduled Audit chỉ quản lý trên Windows",
                "Không thể xóa Task Scheduler ở hệ điều hành hiện tại.",
            )
        result = subprocess.run(
            ["schtasks.exe", "/Delete", "/TN", self.task_name(project_id), "/F"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise FriendlyError(
                "Không xóa được lịch Audit",
                clean_text(result.stderr or result.stdout),
            )
        return True


def run_scheduled_audit(project_id, max_pages=100, store_root=None):
    store = ProjectStoreV43(store_root)
    project = next(
        (item for item in store.list_projects() if item.get("id") == project_id),
        None,
    )
    if not project:
        raise ValueError(f"Không tìm thấy project ID {project_id}.")
    auditor = SiteAuditor()
    pages = auditor.crawl(project["website"], max_pages)
    site_files = auditor.site_files(project["website"])
    fixes = build_fix_queue(pages)
    before = store.list_snapshots(project_id)
    snapshot = store.save_snapshot(project, pages, site_files, fixes=fixes)
    alerts = []
    if before:
        previous = store.load_snapshot(before[0])
        current = store.load_snapshot(snapshot)
        old = {
            (page.get("url", ""), issue)
            for page in previous.get("pages", [])
            for issue in page.get("issues", [])
        }
        new = {
            (page.get("url", ""), issue)
            for page in current.get("pages", [])
            for issue in page.get("issues", [])
        }
        alerts = [
            {"url": url, "issue": issue, "detected_at": utc_now()}
            for url, issue in sorted(new - old)
        ]
    store.save_project_state(
        project_id,
        "latest-alerts",
        {
            "created_at": utc_now(),
            "snapshot": snapshot.name,
            "new_issues": alerts,
            "count": len(alerts),
        },
    )
    return {"snapshot": str(snapshot), "new_issues": alerts, "pages": len(pages)}


def dashboard_kpis(pages=(), fixes=(), gsc_rows=(), log_report=None, decay_rows=(), backlinks=()):
    score = round(sum(page.score for page in pages) / len(pages)) if pages else 0
    p0 = sum(
        getattr(item, "priority", item.get("priority") if isinstance(item, dict) else "") == "P0"
        and getattr(item, "status", item.get("status") if isinstance(item, dict) else "") != "Đã sửa"
        for item in fixes
    )
    clicks = round(sum(parse_number(row.get("clicks")) for row in gsc_rows), 1)
    impressions = round(sum(parse_number(row.get("impressions")) for row in gsc_rows), 1)
    return {
        "seo_score": score,
        "pages": len(pages),
        "p0_open": p0,
        "gsc_clicks": clicks,
        "gsc_impressions": impressions,
        "crawl_efficiency": (log_report or {}).get("crawl_efficiency", 0),
        "decay_pages": sum(
            row.get("status") in ("Decay nặng", "Cần làm mới") for row in decay_rows
        ),
        "backlinks": len(backlinks),
    }
