"""Core services for SEO AI Studio V4.6.

V4.6 keeps the proven V4/V4.3/V4.4 engines and adds the product layer needed
for a guided, recoverable SEO workflow: stronger direct Google parsing,
first-run state, safe credential storage, CrUX field data, update checks,
detailed issue records and cluster-based content briefs.
"""

from __future__ import annotations

import json
import platform
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from seo_v4_core import FixItem, PageResult, clean_text, normalize_url, utc_now
from seo_v43_core import DirectGoogleResearcher, FriendlyError
from seo_v44_keywords import ProjectStoreV44, cluster_summary


VERSION = "4.6.0"
GUIDE_FILE = "Huong_Dan_Chi_Tiet_SEO_AI_Studio_V46.pdf"
UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/tommydau1995-afk/SEO-Tool/"
    "main/update_manifest_v46.json"
)


def version_tuple(value: str) -> tuple[int, ...]:
    values = [int(item) for item in re.findall(r"\d+", clean_text(value))]
    return tuple(values or [0])


def extract_urls(value: str, limit: int = 5) -> list[str]:
    """Extract and normalize the first unique HTTP URLs from clipboard text."""

    found: list[str] = []
    for raw in re.findall(r"https?://[^\s<>\"]+", value or "", flags=re.I):
        target = normalize_url(raw.rstrip(".,);]"))
        if target and target not in found:
            found.append(target)
        if len(found) >= max(1, limit):
            break
    return found


class SmartGoogleResearcher(DirectGoogleResearcher):
    """Best-effort Google parser with consent/challenge detection and fallbacks."""

    BLOCKED_TOKENS = (
        "our systems have detected unusual traffic",
        "unusual traffic from your computer network",
        "automated queries",
        "verify you are human",
        "xác minh bạn là người",
        "không phải là rô-bốt",
        "captcha",
    )
    CONSENT_TOKENS = (
        "before you continue to google",
        "trước khi bạn tiếp tục đến google",
        "chấp nhận tất cả",
        "accept all",
        "consent.google.com",
        "choose what data",
    )

    @staticmethod
    def google_search_url(keyword: str, gl: str = "vn", hl: str = "vi") -> str:
        return (
            "https://www.google.com/search?"
            f"q={quote_plus(clean_text(keyword))}&gl={quote_plus(clean_text(gl) or 'vn')}"
            f"&hl={quote_plus(clean_text(hl) or 'vi')}&pws=0&filter=0"
        )

    @classmethod
    def _challenge_type(cls, soup: BeautifulSoup, html: str) -> str:
        plain = clean_text(soup.get_text(" ")).lower()
        raw = (html or "").lower()
        if any(token in plain or token in raw for token in cls.BLOCKED_TOKENS):
            return "captcha"
        if any(token in plain or token in raw for token in cls.CONSENT_TOKENS):
            return "consent"
        if soup.select_one("form[action*='consent']"):
            return "consent"
        if soup.select_one("form[action*='sorry']"):
            return "captcha"
        return ""

    @classmethod
    def parse_search_html(cls, html: str, limit: int = 10) -> dict:
        soup = BeautifulSoup(html or "", "html.parser")
        challenge = cls._challenge_type(soup, html)
        if challenge == "captcha":
            raise FriendlyError(
                "Google yêu cầu xác minh",
                "Google đã trả trang CAPTCHA hoặc chặn truy vấn tự động.",
                "Mở Google bằng nút trong tool, tìm từ khóa rồi dán 5 URL kết quả tự nhiên.",
            )
        if challenge == "consent":
            raise FriendlyError(
                "Google yêu cầu đồng ý quyền riêng tư",
                "Google đã trả trang Consent thay cho kết quả tìm kiếm.",
                "Hoàn tất Consent trong trình duyệt rồi dùng nút Dán URL từ clipboard.",
            )

        base = super().parse_search_html(html, limit=limit)
        results = list(base["results"])
        seen = {row["link"] for row in results}

        # Google commonly moves headings/anchors between these containers.
        containers = soup.select(
            "div.MjjYud, div.g, div[data-snhf], div[data-header-feature], article"
        )
        for container in containers:
            heading = container.select_one("h3, [role='heading'][aria-level='3']")
            anchor = (
                heading.find_parent("a") if heading else None
            ) or container.select_one("a[href]")
            if not anchor:
                continue
            link = cls._result_href(anchor.get("href", ""))
            title = clean_text(
                heading.get_text(" ") if heading else anchor.get_text(" ")
            )
            if not link or link in seen or len(title) < 3:
                continue
            snippet_node = container.select_one(
                "[data-sncf], .VwiC3b, .yXK7lf, [data-content-feature='1']"
            )
            results.append(
                {
                    "position": len(results) + 1,
                    "title": title[:300],
                    "link": link,
                    "snippet": clean_text(
                        snippet_node.get_text(" ") if snippet_node else ""
                    )[:500],
                }
            )
            seen.add(link)
            if len(results) >= limit:
                break

        # Last-resort parser: any external anchor carrying an H3/heading.
        if len(results) < limit:
            for anchor in soup.select("a[href]"):
                heading = anchor.select_one("h3, [role='heading']")
                if not heading:
                    continue
                link = cls._result_href(anchor.get("href", ""))
                if not link or link in seen:
                    continue
                title = clean_text(heading.get_text(" "))
                if len(title) < 3:
                    continue
                results.append(
                    {
                        "position": len(results) + 1,
                        "title": title[:300],
                        "link": link,
                        "snippet": "",
                    }
                )
                seen.add(link)
                if len(results) >= limit:
                    break

        return {
            "results": results[:limit],
            "questions": base["questions"],
            "ai_overview": base["ai_overview"],
        }

    @staticmethod
    def explain_empty_html(html: str) -> FriendlyError:
        soup = BeautifulSoup(html or "", "html.parser")
        text = clean_text(soup.get_text(" "))
        if not text:
            message = "Google trả về trang trống hoặc nội dung chỉ tải bằng JavaScript."
        else:
            message = (
                "Google trả HTML nhưng không có kết quả tự nhiên mà tool có thể nhận dạng."
            )
        return FriendlyError(
            "Không đọc được Top Google",
            message,
            "Nhấn Mở Google, sao chép 5 URL tự nhiên rồi dùng Dán URL từ clipboard.",
        )

    def search(self, keyword: str, gl: str = "vn", hl: str = "vi", limit: int = 10):
        keyword = clean_text(keyword)
        if not keyword:
            raise FriendlyError(
                "Thiếu keyword",
                "Chưa có từ khóa để nghiên cứu Top 5.",
                "Nhập một keyword rồi chạy lại.",
            )
        try:
            response = self.http.get(
                "https://www.google.com/search",
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
        except FriendlyError:
            raise
        except requests.Timeout as exc:
            raise FriendlyError(
                "Google quá thời gian",
                "Google không phản hồi trong thời gian cho phép.",
                "Kiểm tra Internet rồi nhấn Thử lại hoặc dùng 5 URL thủ công.",
            ) from exc
        except requests.RequestException as exc:
            raise FriendlyError(
                "Không kết nối được Google",
                clean_text(exc) or "Yêu cầu Google thất bại.",
                "Kiểm tra Internet, proxy/firewall rồi thử lại.",
            ) from exc
        if not payload["results"]:
            raise self.explain_empty_html(response.text)
        return payload


class ProjectStoreV46(ProjectStoreV44):
    SETTINGS_FILE = "settings-v46.json"
    RECOVERY_FILE = "recovery-v46.json"

    def save_snapshot(self, project, pages, site_files, keyword_map=None, fixes=None):
        path = super().save_snapshot(
            project, pages, site_files, keyword_map=keyword_map, fixes=fixes
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["version"] = VERSION
        self._atomic_json(path, payload)
        return path

    @staticmethod
    def _atomic_json(path: Path, payload) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp.replace(path)
        return path

    def load_app_settings(self) -> dict:
        path = self.root / self.SETTINGS_FILE
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_app_settings(self, payload: dict) -> Path:
        return self._atomic_json(self.root / self.SETTINGS_FILE, payload)

    def begin_recovery(self, operation: str, payload: dict | None = None) -> Path:
        value = {
            "running": True,
            "operation": clean_text(operation),
            "updated_at": utc_now(),
            "payload": payload or {},
        }
        return self._atomic_json(self.root / self.RECOVERY_FILE, value)

    def checkpoint_recovery(self, operation: str, payload: dict | None = None) -> Path:
        return self.begin_recovery(operation, payload)

    def load_recovery(self) -> dict:
        path = self.root / self.RECOVERY_FILE
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def clear_recovery(self) -> None:
        self._atomic_json(
            self.root / self.RECOVERY_FILE,
            {"running": False, "updated_at": utc_now()},
        )


class CredentialVault:
    """Store secrets in the operating-system credential backend when available."""

    SERVICE = "SEO AI Studio V4.6"

    def __init__(self):
        try:
            import keyring

            self.keyring = keyring
        except Exception:
            self.keyring = None

    @property
    def available(self) -> bool:
        return self.keyring is not None

    @staticmethod
    def _name(project_id: str, field: str) -> str:
        return f"{clean_text(project_id)}:{clean_text(field)}"

    def save(self, project_id: str, field: str, value: str) -> None:
        if not self.available:
            raise FriendlyError(
                "Kho bí mật chưa khả dụng",
                "Windows Credential Manager không thể được mở trong bản chạy này.",
                "Cài lại bản đầy đủ V4.6 hoặc chỉ nhập mật khẩu cho phiên hiện tại.",
            )
        self.keyring.set_password(
            self.SERVICE, self._name(project_id, field), clean_text(value)
        )

    def load(self, project_id: str, field: str) -> str:
        if not self.available:
            return ""
        return (
            self.keyring.get_password(
                self.SERVICE, self._name(project_id, field)
            )
            or ""
        )

    def delete(self, project_id: str, field: str) -> None:
        if not self.available:
            return
        try:
            self.keyring.delete_password(
                self.SERVICE, self._name(project_id, field)
            )
        except Exception:
            pass


class UpdateChecker:
    def __init__(self, manifest_url: str = UPDATE_MANIFEST_URL, timeout: int = 15):
        self.manifest_url = manifest_url
        self.timeout = timeout

    def check(self, current_version: str = VERSION) -> dict:
        response = requests.get(
            self.manifest_url,
            headers={"User-Agent": f"SEOAIStudio/{VERSION}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        latest = clean_text(payload.get("version"))
        if not latest:
            raise FriendlyError(
                "Manifest cập nhật không hợp lệ",
                "Máy chủ không trả phiên bản mới nhất.",
                "Thử lại sau hoặc mở trang GitHub của dự án.",
            )
        return {
            "current": current_version,
            "latest": latest,
            "update_available": version_tuple(latest) > version_tuple(current_version),
            "download_url": clean_text(payload.get("download_url")),
            "notes": clean_text(payload.get("notes")),
        }


class CruxClient:
    """Chrome UX Report field data client, separate from Lighthouse lab data."""

    ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
    METRICS = (
        "largest_contentful_paint",
        "interaction_to_next_paint",
        "cumulative_layout_shift",
        "experimental_time_to_first_byte",
    )

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = clean_text(api_key)
        self.timeout = timeout

    @staticmethod
    def _p75(metric: dict):
        value = (metric or {}).get("percentiles", {}).get("p75")
        return value if isinstance(value, (int, float)) else None

    @classmethod
    def parse_record(cls, payload: dict) -> dict:
        record = payload.get("record", {})
        metrics = record.get("metrics", {})
        return {
            "source": "Chrome UX Report (Field Data - 28 ngày)",
            "collection_period": record.get("collectionPeriod", {}),
            "form_factor": record.get("key", {}).get("formFactor", ""),
            "lcp_ms": cls._p75(metrics.get("largest_contentful_paint", {})),
            "inp_ms": cls._p75(metrics.get("interaction_to_next_paint", {})),
            "cls": cls._p75(metrics.get("cumulative_layout_shift", {})),
            "ttfb_ms": cls._p75(
                metrics.get("experimental_time_to_first_byte", {})
            ),
        }

    def query(self, url: str, form_factor: str = "PHONE") -> dict:
        if not self.api_key:
            raise FriendlyError(
                "CrUX cần API Key",
                "Chưa có Google API Key để lấy dữ liệu người dùng thực.",
                "Nhập PageSpeed/CrUX API Key trong Trung tâm kết nối.",
            )
        target = normalize_url(url)
        response = requests.post(
            self.ENDPOINT,
            params={"key": self.api_key},
            json={
                "url": target,
                "formFactor": clean_text(form_factor).upper() or "PHONE",
                "metrics": list(self.METRICS),
            },
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "source": "Chrome UX Report",
                "unavailable": True,
                "message": "URL chưa đủ dữ liệu người dùng thực trong CrUX.",
            }
        response.raise_for_status()
        return self.parse_record(response.json())


@dataclass
class DetailedIssue:
    priority: str
    issue: str
    url: str
    why_it_matters: str
    recommendation: str
    difficulty: str
    expected_impact: str
    status: str


ISSUE_DETAILS = {
    "HTTP": (
        "Googlebot và người dùng không thể truy cập nội dung ổn định.",
        "Trung bình",
        "Cao",
    ),
    "Title": (
        "Title ảnh hưởng trực tiếp đến khả năng hiểu chủ đề và tỷ lệ nhấp.",
        "Dễ",
        "Cao",
    ),
    "Meta": (
        "Meta Description tốt giúp trình bày kết quả tìm kiếm rõ hơn.",
        "Dễ",
        "Trung bình",
    ),
    "H1": (
        "H1 giúp xác định chủ đề chính và cấu trúc nội dung.",
        "Dễ",
        "Trung bình",
    ),
    "Canonical": (
        "Canonical sai có thể hợp nhất tín hiệu vào URL không mong muốn.",
        "Trung bình",
        "Cao",
    ),
    "Noindex": (
        "Trang noindex không thể xuất hiện trong chỉ mục Google.",
        "Dễ",
        "Cao",
    ),
    "Internal Link": (
        "Internal link giúp khám phá URL và phân phối sức mạnh liên kết.",
        "Trung bình",
        "Cao",
    ),
    "Nội dung mỏng": (
        "Nội dung thiếu chiều sâu khó đáp ứng đầy đủ Search Intent.",
        "Khó",
        "Cao",
    ),
    "Phản hồi chậm": (
        "Phản hồi chậm làm giảm trải nghiệm và hiệu quả crawl.",
        "Khó",
        "Cao",
    ),
    "ALT": (
        "ALT giúp khả năng truy cập và tìm kiếm hình ảnh.",
        "Dễ",
        "Thấp",
    ),
    "Schema": (
        "Structured Data giúp máy tìm kiếm hiểu entity và nội dung.",
        "Trung bình",
        "Trung bình",
    ),
}


def _issue_detail(issue: str, priority: str):
    lowered = clean_text(issue).lower()
    for token, detail in ISSUE_DETAILS.items():
        if token.lower() in lowered:
            return detail
    impact = "Cao" if priority == "P0" else "Trung bình" if priority == "P1" else "Thấp"
    return (
        "Lỗi này có thể ảnh hưởng đến khả năng crawl, index hoặc trải nghiệm.",
        "Trung bình",
        impact,
    )


def build_detailed_issues(fixes: Iterable[FixItem]) -> list[DetailedIssue]:
    rows: list[DetailedIssue] = []
    for fix in fixes:
        why, difficulty, impact = _issue_detail(fix.issue, fix.priority)
        rows.append(
            DetailedIssue(
                priority=fix.priority,
                issue=fix.issue,
                url=fix.url,
                why_it_matters=why,
                recommendation=fix.recommendation,
                difficulty=difficulty,
                expected_impact=impact,
                status=fix.status,
            )
        )
    return rows


def build_content_briefs(keyword_rows: Iterable[dict]) -> list[dict]:
    rows = list(keyword_rows)
    summaries = cluster_summary(rows)
    by_cluster: dict[str, list[dict]] = {}
    for row in rows:
        by_cluster.setdefault(clean_text(row.get("cluster")) or "Chưa phân nhóm", []).append(
            row
        )
    briefs = []
    for summary in summaries:
        cluster = summary["cluster"]
        members = sorted(
            by_cluster.get(cluster, []),
            key=lambda item: (-int(item.get("volume") or 0), item.get("keyword", "")),
        )
        primary = summary["primary_keyword"]
        intent = summary["dominant_intent"]
        secondary = [
            clean_text(row.get("keyword"))
            for row in members
            if clean_text(row.get("keyword")) != primary
        ][:12]
        format_name = {
            "Informational": "Bài hướng dẫn chuyên sâu",
            "Commercial": "Trang so sánh/đánh giá",
            "Transactional": "Landing Page chuyển đổi",
            "Navigational": "Trang thương hiệu/danh mục",
        }.get(intent, "Bài viết chuyên sâu")
        headings = [
            f"{primary.title()} là gì?",
            f"Lợi ích và trường hợp nên chọn {primary}",
            f"Tiêu chí đánh giá {primary}",
            f"Quy trình triển khai {primary}",
            f"Câu hỏi thường gặp về {primary}",
        ]
        briefs.append(
            {
                "cluster": cluster,
                "primary_keyword": primary,
                "secondary_keywords": secondary,
                "intent": intent,
                "content_format": format_name,
                "suggested_title": f"{primary.title()}: Hướng dẫn đầy đủ và thực tế",
                "landing_page": summary.get("landing_page")
                or next(
                    (
                        clean_text(row.get("landing_page") or row.get("url"))
                        for row in members
                        if clean_text(row.get("landing_page") or row.get("url"))
                    ),
                    "",
                ),
                "total_volume": summary["total_volume"],
                "average_kd": summary.get(
                    "average_kd", summary.get("avg_difficulty", 0)
                ),
                "headings": headings,
                "questions": [
                    f"{primary} phù hợp với ai?",
                    f"Chi phí triển khai {primary} là bao nhiêu?",
                    f"Làm thế nào để đánh giá hiệu quả {primary}?",
                ],
                "status": "Chưa viết",
            }
        )
    return briefs


def onboarding_statuses(
    project=None,
    pages=(),
    keyword_rows=(),
    gsc_rows=(),
    pagespeed=None,
    wordpress_ok=False,
) -> list[dict]:
    website = clean_text((project or {}).get("website"))
    checks = [
        ("Tạo dự án", bool(project)),
        ("Nhập website", bool(normalize_url(website))),
        ("Chọn quốc gia và ngôn ngữ", bool(project)),
        ("Kiểm tra website", bool(list(pages))),
        ("Kết nối Google Search Console", bool(list(gsc_rows))),
        ("Chạy PageSpeed/CrUX", bool(pagespeed)),
        ("Kết nối WordPress", bool(wordpress_ok)),
        ("Import Semrush", bool(list(keyword_rows))),
        ("Chạy Full SEO Audit", bool(list(pages))),
    ]
    return [
        {
            "step": index,
            "name": name,
            "status": "Đã kết nối" if done else "Chưa thiết lập",
        }
        for index, (name, done) in enumerate(checks, 1)
    ]


def demo_payload() -> dict:
    pages = [
        PageResult(
            score=92,
            status=200,
            url="https://example.com/",
            final_url="https://example.com/",
            title="Nội thất cao cấp cho không gian hiện đại",
            title_len=39,
            meta="Thiết kế và thi công nội thất cao cấp.",
            meta_len=42,
            h1="Nội thất cao cấp",
            h1_count=1,
            h2_count=5,
            words=1250,
            images=8,
            missing_alt=1,
            internal_links=6,
            external_links=1,
            canonical="https://example.com/",
            indexable="Yes",
            response_ms=420,
            schema_count=1,
            og_title="Nội thất cao cấp",
            issues=["1 ảnh thiếu ALT"],
            depth=0,
            inlinks=4,
            dead_end=False,
        ),
        PageResult(
            score=68,
            status=200,
            url="https://example.com/thiet-ke-biet-thu",
            final_url="https://example.com/thiet-ke-biet-thu",
            title="Thiết kế biệt thự",
            title_len=17,
            meta="",
            meta_len=0,
            h1="Thiết kế biệt thự",
            h1_count=1,
            h2_count=2,
            words=410,
            images=5,
            missing_alt=2,
            internal_links=0,
            external_links=0,
            canonical="",
            indexable="Yes",
            response_ms=1280,
            schema_count=0,
            og_title="",
            issues=[
                "Thiếu Meta Description",
                "Thiếu Canonical",
                "Nội dung mỏng",
                "Thiếu Internal Link",
            ],
            depth=3,
            inlinks=1,
            dead_end=True,
        ),
    ]
    keywords = [
        {
            "keyword": "nội thất cao cấp",
            "volume": 2400,
            "difficulty": 55.0,
            "intent": "Commercial",
            "cluster": "nội thất cao cấp",
            "landing_page": "https://example.com/",
            "priority": "P1",
            "source": "Demo",
            "cpc": 1.2,
            "position": 8,
            "trend": "",
            "competition": "",
            "results": 0,
            "rank": 8,
            "status": "Mapped",
        },
        {
            "keyword": "thiết kế nội thất biệt thự",
            "volume": 1300,
            "difficulty": 48.0,
            "intent": "Transactional",
            "cluster": "nội thất cao cấp",
            "landing_page": "https://example.com/thiet-ke-biet-thu",
            "priority": "P1",
            "source": "Demo",
            "cpc": 1.6,
            "position": 15,
            "trend": "",
            "competition": "",
            "results": 0,
            "rank": 15,
            "status": "Mapped",
        },
        {
            "keyword": "phong cách nội thất hiện đại",
            "volume": 900,
            "difficulty": 39.0,
            "intent": "Informational",
            "cluster": "phong cách nội thất",
            "landing_page": "",
            "priority": "P2",
            "source": "Demo",
            "cpc": 0.8,
            "position": "",
            "trend": "",
            "competition": "",
            "results": 0,
            "rank": "",
            "status": "Unmapped",
        },
    ]
    gsc = [
        {
            "date": utc_now()[:10],
            "query": "nội thất cao cấp",
            "page": "https://example.com/",
            "clicks": 124,
            "impressions": 2100,
            "ctr": 0.059,
            "position": 8.1,
        }
    ]
    pagespeed = {
        "url": "https://example.com/",
        "strategy": "mobile",
        "performance": 78,
        "seo": 95,
        "accessibility": 91,
        "best_practices": 92,
        "lcp_ms": 2800,
        "inp_ms": None,
        "cls": 0.08,
        "ttfb_ms": 620,
        "fcp_ms": 1400,
        "opportunities": [
            {"title": "Tối ưu hình ảnh", "display": "Tiết kiệm 420 KiB"}
        ],
        "crux": {
            "source": "Chrome UX Report (Demo)",
            "lcp_ms": 2500,
            "inp_ms": 180,
            "cls": 0.06,
            "ttfb_ms": 540,
        },
    }
    return {
        "project": {
            "name": "Demo Nội thất Cao cấp",
            "website": "https://example.com/",
        },
        "pages": pages,
        "keywords": keywords,
        "gsc_rows": gsc,
        "pagespeed": pagespeed,
        "site_files": {
            "robots.txt": {"status": 200, "url": "https://example.com/robots.txt"},
            "sitemap.xml": {"status": 200, "url": "https://example.com/sitemap.xml"},
        },
        "graph": {
            "https://example.com/": ["https://example.com/thiet-ke-biet-thu"],
            "https://example.com/thiet-ke-biet-thu": [],
        },
        "sitemap_urls": {
            "https://example.com/",
            "https://example.com/thiet-ke-biet-thu",
            "https://example.com/orphan",
        },
    }


def support_information(error: Exception | str, operation: str = "") -> str:
    return "\n".join(
        [
            f"SEO AI Studio: {VERSION}",
            f"Hệ điều hành: {platform.platform()}",
            f"Thao tác: {clean_text(operation) or 'Không xác định'}",
            f"Thời điểm: {utc_now()}",
            f"Lỗi: {clean_text(error)}",
            "Lưu ý: thông tin hỗ trợ không bao gồm API key hoặc mật khẩu.",
        ]
    )


def detailed_issue_rows(fixes: Iterable[FixItem]) -> list[dict]:
    return [asdict(item) for item in build_detailed_issues(fixes)]
