"""SEO intelligence, index diagnostics, audit comparison and backup for V4.8.

The module keeps paid-search metrics, first-party Search Console signals and
SEO estimates explicitly separated:

* Google Ads Keyword Planner is an optional source for real search-volume,
  monthly trend, CPC and *Ads* competition.
* Search Console impressions remain first-party site performance data.
* Opportunity 2.0 is a transparent internal prioritisation score.
* SERP weakness is an estimate and is never labelled as authoritative SEO KD.
"""

from __future__ import annotations

import hashlib
import csv
import json
import math
import re
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from seo_v4_core import clean_text, normalize_url, utc_now
from seo_v43_core import FriendlyError, parse_number
from seo_v44_keywords import ascii_key, classify_intent, cluster_label
from seo_v47_keywords import ProjectStoreV47


VERSION = "4.8.0"
GUIDE_FILE = "Huong_Dan_Chi_Tiet_SEO_AI_Studio_V48.pdf"
UPDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/tommydau1995-afk/SEO-Tool/"
    "main/update_manifest_v48.json"
)
GOOGLE_ADS_API_VERSION = "v25"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_ENDPOINT = "https://googleads.googleapis.com"


def _customer_id(value) -> str:
    return re.sub(r"\D", "", clean_text(value))


def load_google_ads_config(path_or_payload) -> dict:
    """Load and validate the minimal OAuth + Google Ads configuration."""

    if isinstance(path_or_payload, (str, Path)):
        path = Path(path_or_payload)
        if not path.exists():
            raise FriendlyError(
                "Không tìm thấy cấu hình Google Ads",
                f"File {path} không tồn tại.",
                "Chọn đúng file JSON cấu hình Keyword Planner.",
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FriendlyError(
                "Cấu hình Google Ads không hợp lệ",
                "File cấu hình không phải JSON hợp lệ.",
                "Tạo lại file từ mẫu trong Trung tâm kết nối.",
            ) from exc
    else:
        payload = dict(path_or_payload or {})

    aliases = {
        "developer_token": ("developer_token", "developerToken"),
        "client_id": ("client_id", "clientId"),
        "client_secret": ("client_secret", "clientSecret"),
        "refresh_token": ("refresh_token", "refreshToken"),
        "customer_id": ("customer_id", "customerId"),
        "login_customer_id": ("login_customer_id", "loginCustomerId"),
        "api_version": ("api_version", "apiVersion"),
    }
    result = {}
    for target, candidates in aliases.items():
        result[target] = next(
            (clean_text(payload.get(name)) for name in candidates if payload.get(name)),
            "",
        )
    result["customer_id"] = _customer_id(result["customer_id"])
    result["login_customer_id"] = _customer_id(result["login_customer_id"])
    result["api_version"] = result["api_version"] or GOOGLE_ADS_API_VERSION
    required = (
        "developer_token",
        "client_id",
        "client_secret",
        "refresh_token",
        "customer_id",
    )
    missing = [name for name in required if not result.get(name)]
    if missing:
        raise FriendlyError(
            "Thiếu cấu hình Google Ads",
            "Thiếu trường: " + ", ".join(missing),
            "Mở file mẫu, điền đủ OAuth, developer token và customer ID.",
        )
    return result


def google_ads_config_template() -> dict:
    return {
        "developer_token": "",
        "client_id": "",
        "client_secret": "",
        "refresh_token": "",
        "customer_id": "",
        "login_customer_id": "",
        "api_version": GOOGLE_ADS_API_VERSION,
        "_oauth_scope": "https://www.googleapis.com/auth/adwords",
        "_note": (
            "Ads competition is not SEO Keyword Difficulty. "
            "Do not share this file because it contains secrets."
        ),
    }


def import_keyword_planner_file(path) -> list[dict]:
    """Read Google Ads/Keyword Planner CSV or XLSX exports with tolerant headers."""

    path = Path(path)
    if not path.exists():
        raise ValueError("Không tìm thấy file Keyword Planner.")
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Thiếu openpyxl để đọc Excel.") from exc
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        workbook.close()
        if not rows:
            return []
        headers = [clean_text(value) for value in rows[0]]
        raw_rows = [dict(zip(headers, values)) for values in rows[1:]]
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            raw_rows = list(csv.DictReader(handle, dialect=dialect))

    def value(row, aliases):
        normalized = {ascii_key(key): item for key, item in row.items()}
        for alias in aliases:
            key = ascii_key(alias)
            if key in normalized:
                return normalized[key]
        return ""

    result = []
    for raw in raw_rows:
        keyword = clean_text(
            value(raw, ("keyword", "từ khóa", "search term", "keyword text"))
        )
        if not keyword:
            continue
        result.append(
            {
                "keyword": keyword,
                "volume": int(
                    parse_number(
                        value(
                            raw,
                            (
                                "avg monthly searches",
                                "average monthly searches",
                                "search volume",
                                "volume",
                                "lượt tìm kiếm trung bình hàng tháng",
                            ),
                        )
                    )
                ),
                "ads_competition": clean_text(
                    value(raw, ("competition", "mức độ cạnh tranh"))
                ),
                "ads_competition_index": int(
                    parse_number(
                        value(
                            raw,
                            (
                                "competition indexed value",
                                "competition index",
                                "chỉ số cạnh tranh",
                            ),
                        )
                    )
                ),
                "cpc_low": parse_number(
                    value(
                        raw,
                        (
                            "top of page bid low range",
                            "low top of page bid",
                            "giá thầu đầu trang phạm vi thấp",
                        ),
                    )
                ),
                "cpc_high": parse_number(
                    value(
                        raw,
                        (
                            "top of page bid high range",
                            "high top of page bid",
                            "giá thầu đầu trang phạm vi cao",
                        ),
                    )
                ),
                "metrics_source": "Google Ads Keyword Planner import",
            }
        )
    return result


class GoogleAdsKeywordPlannerClient:
    """Small REST client for Keyword Planner historical metrics and ideas."""

    def __init__(self, config, timeout=45, session=None):
        self.config = load_google_ads_config(config)
        self.timeout = max(10, int(timeout))
        self.http = session or requests.Session()
        self._access_token = ""
        self._expires_at = 0.0

    def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        try:
            response = self.http.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": self.config["client_id"],
                    "client_secret": self.config["client_secret"],
                    "refresh_token": self.config["refresh_token"],
                    "grant_type": "refresh_token",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise FriendlyError(
                "Google Ads OAuth thất bại",
                clean_text(exc) or "Không lấy được access token.",
                "Kiểm tra client ID, client secret, refresh token và kết nối Internet.",
            ) from exc
        token = clean_text(payload.get("access_token"))
        if not token:
            raise FriendlyError(
                "Google Ads OAuth thiếu token",
                "Google không trả access_token.",
                "Tạo lại refresh token đúng Google Ads scope.",
            )
        self._access_token = token
        self._expires_at = time.time() + int(payload.get("expires_in") or 3600)
        return token

    def _headers(self):
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "developer-token": self.config["developer_token"],
            "Content-Type": "application/json",
        }
        if self.config.get("login_customer_id"):
            headers["login-customer-id"] = self.config["login_customer_id"]
        return headers

    def _post(self, method: str, payload: dict) -> dict:
        version = re.sub(r"[^a-zA-Z0-9]", "", self.config["api_version"])
        url = (
            f"{GOOGLE_ADS_ENDPOINT}/{version}/customers/"
            f"{self.config['customer_id']}:{method}"
        )
        try:
            response = self.http.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                detail = clean_text(response.text)[:900]
                raise FriendlyError(
                    f"Google Ads API HTTP {response.status_code}",
                    detail or "Google Ads từ chối yêu cầu.",
                    (
                        "Kiểm tra developer token, quyền tài khoản, customer ID, "
                        "quota và phiên bản API."
                    ),
                )
            return response.json()
        except FriendlyError:
            raise
        except requests.Timeout as exc:
            raise FriendlyError(
                "Google Ads API quá thời gian",
                "Keyword Planner không phản hồi trong thời gian cho phép.",
                "Giảm số keyword rồi thử lại.",
            ) from exc
        except (requests.RequestException, ValueError) as exc:
            raise FriendlyError(
                "Không đọc được Google Ads",
                clean_text(exc) or "Phản hồi Keyword Planner không hợp lệ.",
                "Kiểm tra Internet và cấu hình Google Ads.",
            ) from exc

    @staticmethod
    def _money(micros) -> float:
        return round(parse_number(micros) / 1_000_000, 2)

    @classmethod
    def parse_historical_metrics(cls, payload: dict) -> list[dict]:
        rows = []
        for item in payload.get("results", []) or ():
            metrics = item.get("keywordMetrics") or {}
            monthly = [
                {
                    "year": value.get("year", ""),
                    "month": value.get("month", ""),
                    "searches": int(parse_number(value.get("monthlySearches", 0))),
                }
                for value in metrics.get("monthlySearchVolumes", []) or ()
            ]
            rows.append(
                {
                    "keyword": clean_text(item.get("text")),
                    "volume": int(parse_number(metrics.get("avgMonthlySearches", 0))),
                    "ads_competition": clean_text(metrics.get("competition")),
                    "ads_competition_index": int(
                        parse_number(metrics.get("competitionIndex", 0))
                    ),
                    "cpc_low": cls._money(
                        metrics.get("lowTopOfPageBidMicros", 0)
                    ),
                    "cpc_high": cls._money(
                        metrics.get("highTopOfPageBidMicros", 0)
                    ),
                    "monthly_searches": monthly,
                    "metrics_source": "Google Ads Keyword Planner",
                }
            )
        return [row for row in rows if row["keyword"]]

    def historical_metrics(
        self,
        keywords,
        language_constant="1000",
        geo_target_constant="2704",
    ) -> list[dict]:
        keywords = list(
            dict.fromkeys(
                clean_text(keyword)
                for keyword in keywords or ()
                if clean_text(keyword)
            )
        )[:1000]
        if not keywords:
            return []
        payload = {
            "keywords": keywords,
            "language": f"languageConstants/{_customer_id(language_constant)}",
            "geoTargetConstants": [
                f"geoTargetConstants/{_customer_id(geo_target_constant)}"
            ],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
        }
        return self.parse_historical_metrics(
            self._post("generateKeywordHistoricalMetrics", payload)
        )


def merge_keyword_metrics(discovery_rows, metric_rows, updated_at=None) -> list[dict]:
    """Merge real Keyword Planner metrics without converting Ads competition to KD."""

    metric_map = {
        ascii_key(row.get("keyword")): row
        for row in metric_rows or ()
        if ascii_key(row.get("keyword"))
    }
    timestamp = updated_at or utc_now()
    result = []
    for source in discovery_rows or ():
        row = dict(source)
        metric = metric_map.get(ascii_key(row.get("keyword")))
        if metric:
            row.update(
                {
                    "volume": int(parse_number(metric.get("volume", 0))),
                    "ads_competition": clean_text(metric.get("ads_competition")),
                    "ads_competition_index": int(
                        parse_number(metric.get("ads_competition_index", 0))
                    ),
                    "cpc_low": parse_number(metric.get("cpc_low", 0)),
                    "cpc_high": parse_number(metric.get("cpc_high", 0)),
                    "monthly_searches": metric.get("monthly_searches") or [],
                    "metrics_source": (
                        clean_text(metric.get("metrics_source"))
                        or "Google Ads Keyword Planner"
                    ),
                    "metrics_updated_at": timestamp,
                    "metrics_status": "Có Volume/CPC thật • Ads competition ≠ SEO KD",
                    "data_confidence": "Cao",
                }
            )
        else:
            row.setdefault("metrics_status", "Chưa có Volume/KD thật")
            row.setdefault("data_confidence", "Trung bình")
        result.append(row)
    return recalculate_opportunities(result)


def opportunity_score_v2(row: dict) -> tuple[int, str]:
    """Return a transparent 0-100 prioritisation score."""

    score = 12.0
    reasons = []
    sources = {
        clean_text(value)
        for value in clean_text(row.get("source")).split(" + ")
        if clean_text(value)
    }
    score += min(12, len(sources) * 4)
    if len(sources) >= 2:
        reasons.append("nhiều nguồn")

    volume = max(0.0, parse_number(row.get("volume", 0)))
    if volume:
        score += min(24, math.log10(volume + 1) * 7)
        reasons.append(f"Volume {volume:,.0f}")

    impressions = max(0.0, parse_number(row.get("gsc_impressions", 0)))
    clicks = max(0.0, parse_number(row.get("gsc_clicks", 0)))
    position = max(0.0, parse_number(row.get("gsc_position", 0)))
    if impressions:
        score += min(18, math.log10(impressions + 1) * 5)
        reasons.append(f"GSC {impressions:,.0f} impression")
        if 5 <= position <= 30:
            score += 10
            reasons.append(f"vị trí {position:.1f}")
        if impressions >= 50 and clicks / impressions < 0.02:
            score += 5

    intent = clean_text(row.get("intent")) or classify_intent(row.get("keyword", ""))
    if intent == "Transactional":
        score += 9
        reasons.append("intent giao dịch")
    elif intent == "Commercial":
        score += 7
        reasons.append("intent thương mại")
    elif intent == "Informational":
        score += 4

    business_value = max(1, min(5, int(parse_number(row.get("business_value", 3)))))
    score += (business_value - 1) * 2
    if business_value >= 4:
        reasons.append(f"giá trị KD {business_value}/5")

    ads_competition = int(parse_number(row.get("ads_competition_index", 0)))
    if ads_competition >= 60:
        score += 4
        reasons.append("tín hiệu quảng cáo cao")

    serp_weakness = max(0, min(100, parse_number(row.get("serp_weakness", 0))))
    if serp_weakness:
        score += serp_weakness * 0.12
        reasons.append(f"SERP weakness {serp_weakness:.0f}")

    if not clean_text(row.get("landing_page")):
        score += 5
        reasons.append("thiếu Landing Page")
    else:
        score += 3

    words = len(clean_text(row.get("keyword")).split())
    if 3 <= words <= 8:
        score += 5

    return min(100, int(round(score))), "; ".join(reasons[:5]) or "Tín hiệu ban đầu"


def recalculate_opportunities(rows) -> list[dict]:
    result = []
    for source in rows or ():
        row = dict(source)
        row["intent"] = clean_text(row.get("intent")) or classify_intent(
            row.get("keyword", "")
        )
        row["cluster"] = clean_text(row.get("cluster")) or cluster_label(
            row.get("keyword", ""), "Balanced"
        )
        row["opportunity"], row["opportunity_reason"] = opportunity_score_v2(row)
        row.setdefault("business_value", 3)
        row.setdefault("data_confidence", "Cao" if row.get("volume") else "Trung bình")
        result.append(row)
    result.sort(
        key=lambda row: (
            -int(parse_number(row.get("opportunity", 0))),
            -parse_number(row.get("volume", 0)),
            -parse_number(row.get("gsc_impressions", 0)),
            ascii_key(row.get("keyword")),
        )
    )
    return result


def estimate_serp_weakness(keyword, sources) -> dict:
    """Estimate how beatable a SERP looks from accessible Top-result signals.

    This is intentionally an estimate. It does not use backlink authority and
    therefore must not be presented as an authoritative SEO KD metric.
    """

    keyword_key = ascii_key(keyword)
    keyword_tokens = set(keyword_key.split())
    sources = list(sources or ())
    valid = [source for source in sources if clean_text(
        source.get("link") if isinstance(source, dict) else getattr(source, "link", "")
    )]
    score = 10.0
    reasons = []
    if len(valid) < 5:
        score += (5 - len(valid)) * 7
        reasons.append(f"chỉ đọc được {len(valid)}/5 kết quả")

    heading_counts = []
    exact_titles = 0
    weak_domains = 0
    domains = set()
    current_year = datetime.now(timezone.utc).year
    stale_mentions = 0
    for source in valid:
        get = (
            (lambda name: source.get(name, ""))
            if isinstance(source, dict)
            else (lambda name: getattr(source, name, ""))
        )
        title = clean_text(get("title"))
        snippet = clean_text(get("snippet"))
        link = clean_text(get("link"))
        headings = list(get("headings") or ())
        heading_counts.append(len(headings))
        title_tokens = set(ascii_key(title).split())
        if keyword_tokens and len(keyword_tokens & title_tokens) / len(keyword_tokens) >= 0.8:
            exact_titles += 1
        domain = urlparse(link).netloc.lower().removeprefix("www.")
        if domain:
            domains.add(domain)
        if any(token in domain for token in ("facebook.", "youtube.", "reddit.", "quora.")):
            weak_domains += 1
        years = [
            int(value)
            for value in re.findall(r"\b20\d{2}\b", f"{title} {snippet}")
        ]
        if years and max(years) <= current_year - 3:
            stale_mentions += 1

    average_headings = (
        sum(heading_counts) / len(heading_counts) if heading_counts else 0
    )
    if average_headings < 6:
        score += 22
        reasons.append(f"outline mỏng ({average_headings:.1f} heading)")
    elif average_headings < 10:
        score += 10
        reasons.append("outline chưa sâu")
    if exact_titles <= 2:
        score += 14
        reasons.append("ít Title phủ sát keyword")
    if weak_domains:
        score += min(15, weak_domains * 5)
        reasons.append(f"{weak_domains} nguồn cộng đồng/video")
    if stale_mentions:
        score += min(12, stale_mentions * 4)
        reasons.append(f"{stale_mentions} kết quả có tín hiệu cũ")
    if len(domains) <= 3 and len(valid) >= 4:
        score -= 8
        reasons.append("SERP tập trung ít domain")
    score = max(0, min(100, int(round(score))))
    return {
        "score": score,
        "label": "Dễ hơn" if score >= 70 else "Trung bình" if score >= 40 else "Khó hơn",
        "reason": "; ".join(reasons[:5]) or "Top kết quả có tín hiệu tương đối đầy đủ",
        "source_count": len(valid),
        "average_headings": round(average_headings, 1),
        "authority_note": "Không có backlink authority; đây không phải SEO KD chính xác.",
    }


def detect_keyword_cannibalization(
    gsc_rows, min_impressions=20, min_pages=2
) -> list[dict]:
    grouped = defaultdict(lambda: defaultdict(lambda: {"clicks": 0.0, "impressions": 0.0}))
    for raw in gsc_rows or ():
        query = clean_text(raw.get("query"))
        page = normalize_url(raw.get("page"))
        if not query or not page:
            continue
        grouped[ascii_key(query)][page]["query"] = query
        grouped[ascii_key(query)][page]["clicks"] += max(
            0, parse_number(raw.get("clicks", 0))
        )
        grouped[ascii_key(query)][page]["impressions"] += max(
            0, parse_number(raw.get("impressions", 0))
        )

    result = []
    for pages in grouped.values():
        eligible = [
            (url, values)
            for url, values in pages.items()
            if values["impressions"] >= min_impressions
        ]
        if len(eligible) < min_pages:
            continue
        eligible.sort(key=lambda item: item[1]["impressions"], reverse=True)
        total = sum(item[1]["impressions"] for item in eligible)
        top_share = eligible[0][1]["impressions"] / max(1, total)
        severity = "P0" if total >= 1000 and top_share < 0.75 else "P1"
        result.append(
            {
                "keyword": eligible[0][1]["query"],
                "pages": len(eligible),
                "total_impressions": round(total, 1),
                "primary_url": eligible[0][0],
                "competing_urls": [url for url, _ in eligible[1:]],
                "top_share": round(top_share * 100, 1),
                "priority": severity,
                "recommendation": (
                    "Chọn một URL chính; gộp nội dung hoặc đổi intent, title, "
                    "internal link và canonical của các URL cạnh tranh."
                ),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            0 if row["priority"] == "P0" else 1,
            -row["total_impressions"],
        ),
    )


def build_content_gaps(discovery_rows) -> list[dict]:
    grouped = defaultdict(list)
    for row in discovery_rows or ():
        if clean_text(row.get("landing_page")):
            continue
        grouped[clean_text(row.get("cluster")) or "Chưa phân nhóm"].append(row)
    result = []
    for cluster, rows in grouped.items():
        ordered = sorted(
            rows,
            key=lambda row: (
                -parse_number(row.get("opportunity", 0)),
                -parse_number(row.get("volume", 0)),
            ),
        )
        result.append(
            {
                "cluster": cluster,
                "keywords": len(rows),
                "primary_keyword": clean_text(ordered[0].get("keyword")),
                "max_opportunity": int(
                    parse_number(ordered[0].get("opportunity", 0))
                ),
                "total_volume": int(
                    sum(parse_number(row.get("volume", 0)) for row in rows)
                ),
                "priority": (
                    "P0"
                    if parse_number(ordered[0].get("opportunity", 0)) >= 80
                    else "P1"
                    if parse_number(ordered[0].get("opportunity", 0)) >= 60
                    else "P2"
                ),
                "recommendation": (
                    "Tạo Landing Page hoặc Content Brief cho cluster này và "
                    "liên kết từ Hub Page phù hợp."
                ),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            0 if row["priority"] == "P0" else 1 if row["priority"] == "P1" else 2,
            -row["max_opportunity"],
            -row["total_volume"],
        ),
    )


def gsc_data_quality(row_count, row_limit=25000) -> dict:
    row_count = max(0, int(row_count or 0))
    row_limit = max(1, int(row_limit or 25000))
    if not row_count:
        status = "Chưa có dữ liệu"
        confidence = "Thấp"
    elif row_count >= row_limit:
        status = f"Đã chạm giới hạn {row_limit:,} dòng/lần lấy"
        confidence = "Trung bình"
    else:
        status = "Dữ liệu top rows; API không bảo đảm trả toàn bộ truy vấn"
        confidence = "Trung bình"
    return {
        "rows": row_count,
        "row_limit": row_limit,
        "status": status,
        "confidence": confidence,
        "source": "Google Search Console Search Analytics",
        "checked_at": utc_now(),
    }


def inspect_live_url(url, timeout=25, session=None) -> dict:
    url = normalize_url(url)
    if not url:
        raise FriendlyError(
            "URL live không hợp lệ",
            "Không nhận diện được URL cần kiểm tra.",
            "Nhập URL đầy đủ, ví dụ https://example.com/page.",
        )
    http = session or requests.Session()
    http.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Googlebot/2.1; "
                "+http://www.google.com/bot.html) SEOAIStudio/4.8"
            ),
            "Accept-Language": "vi,en-US;q=0.8,en;q=0.7",
        }
    )
    started = time.perf_counter()
    try:
        response = http.get(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise FriendlyError(
            "Không tải được URL live",
            clean_text(exc),
            "Kiểm tra Internet, DNS, firewall/CDN và URL.",
        ) from exc
    elapsed = int((time.perf_counter() - started) * 1000)
    html = response.text if "html" in response.headers.get("Content-Type", "").lower() else ""
    soup = BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")
    robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    robots_meta = clean_text(robots.get("content", "") if robots else "")
    x_robots = clean_text(response.headers.get("X-Robots-Tag", ""))
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical = (
        normalize_url(urljoin(response.url, canonical_tag.get("href", "")))
        if canonical_tag
        else ""
    )
    h1 = soup.find("h1")
    title = clean_text(soup.title.get_text(" ") if soup.title else "")
    text = clean_text(soup.get_text(" ")) if html else ""

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots_allowed = None
    robots_error = ""
    try:
        robots_response = http.get(robots_url, timeout=min(timeout, 12))
        if robots_response.ok:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(robots_response.text.splitlines())
            robots_allowed = parser.can_fetch("Googlebot", url)
        else:
            robots_error = f"HTTP {robots_response.status_code}"
    except requests.RequestException as exc:
        robots_error = clean_text(exc)[:180]

    directives = (robots_meta + " " + x_robots).lower()
    indexable = (
        response.status_code == 200
        and "noindex" not in directives
        and robots_allowed is not False
    )
    return {
        "url": url,
        "final_url": normalize_url(response.url) or response.url,
        "status": response.status_code,
        "redirects": len(response.history),
        "response_ms": elapsed,
        "content_type": clean_text(response.headers.get("Content-Type", "")),
        "title": title,
        "h1": clean_text(h1.get_text(" ") if h1 else ""),
        "robots_meta": robots_meta,
        "x_robots_tag": x_robots,
        "robots_allowed_googlebot": robots_allowed,
        "robots_error": robots_error,
        "canonical": canonical,
        "indexable_live": indexable,
        "content_chars": len(text),
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "checked_at": utc_now(),
    }


def compare_indexed_and_live(inspection_result, live: dict) -> dict:
    index = (inspection_result or {}).get("indexStatusResult") or {}
    issues = []
    if int(parse_number(live.get("status", 0))) != 200:
        issues.append(f"Live HTTP {live.get('status')}")
    if live.get("robots_allowed_googlebot") is False:
        issues.append("robots.txt đang chặn Googlebot live")
    if not live.get("indexable_live"):
        issues.append("URL live hiện không indexable")
    verdict = clean_text(index.get("verdict"))
    if verdict and verdict.upper() not in ("PASS", "NEUTRAL"):
        issues.append(f"Google Index verdict: {verdict}")
    coverage = clean_text(index.get("coverageState"))
    if coverage and "indexed" not in coverage.lower():
        issues.append(f"Coverage: {coverage}")
    google_canonical = normalize_url(index.get("googleCanonical", ""))
    live_canonical = normalize_url(live.get("canonical", ""))
    if google_canonical and live_canonical and google_canonical != live_canonical:
        issues.append("Google canonical khác canonical live")
    indexed_url = normalize_url(index.get("indexingState", ""))
    return {
        "status": "Có vấn đề" if issues else "Ổn",
        "issues": issues,
        "indexed": {
            "verdict": verdict,
            "coverage": coverage,
            "robots": clean_text(index.get("robotsTxtState")),
            "indexing": clean_text(index.get("indexingState")),
            "last_crawl": clean_text(index.get("lastCrawlTime")),
            "google_canonical": google_canonical,
            "user_canonical": normalize_url(index.get("userCanonical", "")),
            "source_note": (
                "Đây là phiên bản đang nằm trong Google Index, không phải Live Test."
            ),
        },
        "live": live,
        "checked_at": utc_now(),
    }


def snapshot_metrics(snapshot: dict) -> dict:
    pages = snapshot.get("pages", []) or []
    issue_count = sum(len(page.get("issues", []) or []) for page in pages)
    scores = [parse_number(page.get("score", 0)) for page in pages]
    return {
        "created_at": clean_text(snapshot.get("created_at")),
        "pages": len(pages),
        "avg_score": round(sum(scores) / max(1, len(scores)), 1),
        "issues": issue_count,
        "indexable": sum(page.get("indexable") == "Yes" for page in pages),
        "errors_4xx_5xx": sum(
            int(parse_number(page.get("status", 0))) >= 400 for page in pages
        ),
        "orphans": sum(int(page.get("inlinks", 0)) == 0 for page in pages[1:]),
        "dead_ends": sum(bool(page.get("dead_end")) for page in pages),
    }


def compare_audit_snapshots(previous: dict, current: dict) -> dict:
    def issue_keys(snapshot):
        return {
            (clean_text(page.get("url")), clean_text(issue))
            for page in snapshot.get("pages", []) or ()
            for issue in page.get("issues", []) or ()
            if clean_text(issue)
        }

    old_keys = issue_keys(previous)
    new_keys = issue_keys(current)
    before = snapshot_metrics(previous)
    after = snapshot_metrics(current)
    deltas = {
        key: round(after[key] - before[key], 1)
        for key in (
            "pages",
            "avg_score",
            "issues",
            "indexable",
            "errors_4xx_5xx",
            "orphans",
            "dead_ends",
        )
    }
    resolved = sorted(old_keys - new_keys)
    new = sorted(new_keys - old_keys)
    remaining = sorted(old_keys & new_keys)
    status = (
        "Cải thiện"
        if (
            (len(resolved) > len(new) and deltas["avg_score"] >= 0)
            or (deltas["avg_score"] > 0 and len(new) <= len(resolved))
        )
        else "Suy giảm"
        if len(new) > len(resolved) or deltas["avg_score"] < 0
        else "Ổn định"
    )
    return {
        "status": status,
        "before": before,
        "after": after,
        "deltas": deltas,
        "resolved": resolved,
        "new": new,
        "remaining": remaining,
    }


class ProjectStoreV48(ProjectStoreV47):
    SETTINGS_FILE = "settings-v48.json"
    RECOVERY_FILE = "recovery-v48.json"

    def save_snapshot(self, project, pages, site_files, keyword_map=None, fixes=None):
        path = super().save_snapshot(
            project, pages, site_files, keyword_map=keyword_map, fixes=fixes
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["version"] = VERSION
        self._atomic_json(path, payload)
        return path

    def export_project_bundle(self, project_id, target) -> Path:
        project = next(
            (item for item in self.list_projects() if item.get("id") == project_id),
            None,
        )
        if not project:
            raise ValueError("Không tìm thấy dự án cần sao lưu.")
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "project.json",
                json.dumps(
                    {
                        "format": "SEO-AI-Studio-V48-Project",
                        "exported_at": utc_now(),
                        "project": project,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            project_dir = self.root / project_id
            if project_dir.exists():
                for path in project_dir.rglob("*"):
                    if path.is_file():
                        archive.write(path, Path("data") / path.relative_to(project_dir))
        return target

    def import_project_bundle(self, source) -> dict:
        source = Path(source)
        if not source.exists():
            raise ValueError("Không tìm thấy file sao lưu.")
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if "project.json" not in names:
                raise ValueError("File sao lưu thiếu project.json.")
            if any(
                Path(name).is_absolute() or ".." in Path(name).parts for name in names
            ):
                raise ValueError("File sao lưu chứa đường dẫn không an toàn.")
            metadata = json.loads(archive.read("project.json").decode("utf-8"))
            if metadata.get("format") != "SEO-AI-Studio-V48-Project":
                raise ValueError("Định dạng sao lưu không được hỗ trợ.")
            original = metadata.get("project") or {}
            project = self.upsert_project(
                original.get("name") or "Dự án khôi phục",
                original.get("website"),
            )
            target = self.root / project["id"]
            for name in names:
                path = Path(name)
                if not path.parts or path.parts[0] != "data" or name.endswith("/"):
                    continue
                relative = Path(*path.parts[1:])
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))
        return project


def onboarding_statuses_v48(
    project,
    pages,
    keyword_rows,
    discovery_rows,
    gsc_rows,
    pagespeed,
    wordpress_ok,
    google_ads_connected=False,
):
    def status(condition, error=False):
        return "Có lỗi" if error else "Đã kết nối" if condition else "Chưa thiết lập"

    return [
        {"step": 1, "name": "Tạo dự án", "status": status(bool(project))},
        {
            "step": 2,
            "name": "Nhập website",
            "status": status(bool(normalize_url((project or {}).get("website", "")))),
        },
        {"step": 3, "name": "Quốc gia & ngôn ngữ", "status": "Đã kết nối"},
        {"step": 4, "name": "Kiểm tra website", "status": status(bool(pages))},
        {"step": 5, "name": "Google Search Console", "status": status(bool(gsc_rows))},
        {
            "step": 6,
            "name": "PageSpeed/CrUX",
            "status": status(
                bool(pagespeed),
                bool(pagespeed.get("error")) if pagespeed else False,
            ),
        },
        {"step": 7, "name": "WordPress", "status": status(bool(wordpress_ok))},
        {
            "step": 8,
            "name": "Tìm bộ từ khóa",
            "status": status(bool(discovery_rows or keyword_rows)),
        },
        {
            "step": 9,
            "name": "Keyword Planner (tùy chọn)",
            "status": status(bool(google_ads_connected)),
        },
        {"step": 10, "name": "Full SEO Audit", "status": status(bool(pages))},
    ]
