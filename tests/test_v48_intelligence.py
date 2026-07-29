import csv
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader
from generate_user_guide_v48 import generate
from seo_v4_core import PageResult
from seo_v43_core import FriendlyError
from seo_v48_intelligence import (
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
    load_google_ads_config,
    merge_keyword_metrics,
    onboarding_statuses_v48,
    opportunity_score_v2,
)


def config():
    return {
        "developer_token": "dev",
        "client_id": "client",
        "client_secret": "secret",
        "refresh_token": "refresh",
        "customer_id": "123-456-7890",
        "login_customer_id": "999-888-7777",
        "api_version": "v22",
    }


class FakeResponse:
    def __init__(self, payload=None, status=200, text="", url="https://example.com/page", headers=None, history=None):
        self.payload = payload or {}
        self.status_code = status
        self.text = text
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.history = history or []

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = RuntimeError(f"HTTP {self.status_code}")
            raise error


class FakeAdsSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if "oauth2.googleapis.com" in url:
            return FakeResponse({"access_token": "access", "expires_in": 3600})
        return FakeResponse(
            {
                "results": [
                    {
                        "text": "dịch vụ seo",
                        "keywordMetrics": {
                            "avgMonthlySearches": "1200",
                            "competition": "HIGH",
                            "competitionIndex": "74",
                            "lowTopOfPageBidMicros": "1500000",
                            "highTopOfPageBidMicros": "5500000",
                            "monthlySearchVolumes": [
                                {
                                    "year": "2026",
                                    "month": "JUNE",
                                    "monthlySearches": "1300",
                                }
                            ],
                        },
                    }
                ]
            }
        )


class FakeLiveSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, **kwargs):
        if url.endswith("/robots.txt"):
            return FakeResponse(
                status=200,
                text="User-agent: Googlebot\nAllow: /\n",
                url=url,
                headers={"Content-Type": "text/plain"},
            )
        html = """
        <html><head>
          <title>Dịch vụ SEO</title>
          <meta name="robots" content="index,follow">
          <link rel="canonical" href="https://example.com/page">
        </head><body><h1>Dịch vụ SEO tổng thể</h1><p>Nội dung kiểm tra live.</p></body></html>
        """
        return FakeResponse(
            status=200,
            text=html,
            url="https://example.com/page",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )


class GoogleAdsTests(unittest.TestCase):
    def test_config_normalizes_customer_ids_and_requires_secrets(self):
        value = load_google_ads_config(config())
        self.assertEqual(value["customer_id"], "1234567890")
        self.assertEqual(value["login_customer_id"], "9998887777")
        with self.assertRaises(FriendlyError):
            load_google_ads_config({"developer_token": "x"})

    def test_template_does_not_claim_ads_competition_is_kd(self):
        template = google_ads_config_template()
        self.assertIn("not SEO Keyword Difficulty", template["_note"])
        self.assertEqual(template["api_version"], "v25")

    def test_rest_client_parses_real_metrics_and_headers(self):
        session = FakeAdsSession()
        rows = GoogleAdsKeywordPlannerClient(
            config(), session=session
        ).historical_metrics(
            ["dịch vụ seo"], language_constant="1040", geo_target_constant="2704"
        )
        self.assertEqual(rows[0]["volume"], 1200)
        self.assertEqual(rows[0]["ads_competition_index"], 74)
        self.assertEqual(rows[0]["cpc_low"], 1.5)
        self.assertEqual(rows[0]["cpc_high"], 5.5)
        api_call = session.calls[1]
        self.assertIn("generateKeywordHistoricalMetrics", api_call[0])
        self.assertEqual(api_call[1]["headers"]["developer-token"], "dev")
        self.assertEqual(api_call[1]["headers"]["login-customer-id"], "9998887777")
        self.assertEqual(
            api_call[1]["json"]["language"], "languageConstants/1040"
        )

    def test_keyword_planner_csv_import(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "planner.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "Keyword",
                        "Avg. monthly searches",
                        "Competition",
                        "Competition (indexed value)",
                        "Top of page bid (low range)",
                        "Top of page bid (high range)",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "Keyword": "dịch vụ seo",
                        "Avg. monthly searches": "1,200",
                        "Competition": "High",
                        "Competition (indexed value)": "74",
                        "Top of page bid (low range)": "1.5",
                        "Top of page bid (high range)": "5.5",
                    }
                )
            rows = import_keyword_planner_file(path)
            self.assertEqual(rows[0]["keyword"], "dịch vụ seo")
            self.assertEqual(rows[0]["volume"], 1200)
            self.assertEqual(rows[0]["ads_competition_index"], 74)


class OpportunityTests(unittest.TestCase):
    def test_merge_keeps_ads_competition_separate_from_kd(self):
        rows = merge_keyword_metrics(
            [
                {
                    "keyword": "dịch vụ seo",
                    "source": "Google Suggest + Google Search Console",
                    "intent": "Transactional",
                    "gsc_impressions": 500,
                    "gsc_clicks": 5,
                    "gsc_position": 12,
                    "landing_page": "",
                }
            ],
            [
                {
                    "keyword": "Dịch vụ SEO",
                    "volume": 1200,
                    "ads_competition": "HIGH",
                    "ads_competition_index": 74,
                    "cpc_low": 1.5,
                    "cpc_high": 5.5,
                    "metrics_source": "Google Ads Keyword Planner",
                }
            ],
        )
        self.assertEqual(rows[0]["volume"], 1200)
        self.assertNotIn("difficulty", rows[0])
        self.assertIn("≠ SEO KD", rows[0]["metrics_status"])
        self.assertGreaterEqual(rows[0]["opportunity"], 80)

    def test_opportunity_v2_explains_inputs(self):
        score, reason = opportunity_score_v2(
            {
                "keyword": "dịch vụ seo tổng thể",
                "source": "Google Suggest + Google Search Console",
                "volume": 2000,
                "gsc_impressions": 1000,
                "gsc_clicks": 5,
                "gsc_position": 9,
                "intent": "Transactional",
                "business_value": 5,
                "ads_competition_index": 80,
                "serp_weakness": 60,
                "landing_page": "",
            }
        )
        self.assertGreaterEqual(score, 90)
        self.assertIn("Volume", reason)
        self.assertIn("GSC", reason)


class StrategyTests(unittest.TestCase):
    def test_serp_weakness_is_explicitly_not_authoritative_kd(self):
        estimate = estimate_serp_weakness(
            "dịch vụ seo",
            [
                {
                    "title": "Tìm dịch vụ marketing",
                    "link": "https://reddit.com/r/seo",
                    "snippet": "Bài viết 2021",
                    "headings": ["H1: Dịch vụ"],
                },
                {
                    "title": "SEO cho doanh nghiệp",
                    "link": "https://youtube.com/watch?v=1",
                    "snippet": "Video 2022",
                    "headings": [],
                },
            ],
        )
        self.assertGreaterEqual(estimate["score"], 70)
        self.assertIn("không phải SEO KD", estimate["authority_note"])

    def test_cannibalization_requires_multiple_pages(self):
        rows = detect_keyword_cannibalization(
            [
                {
                    "query": "dịch vụ seo",
                    "page": "https://example.com/a",
                    "impressions": 800,
                    "clicks": 10,
                },
                {
                    "query": "dịch vụ seo",
                    "page": "https://example.com/b",
                    "impressions": 600,
                    "clicks": 5,
                },
                {
                    "query": "seo local",
                    "page": "https://example.com/c",
                    "impressions": 500,
                    "clicks": 8,
                },
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["priority"], "P0")
        self.assertEqual(rows[0]["pages"], 2)

    def test_content_gap_groups_unmapped_clusters(self):
        gaps = build_content_gaps(
            [
                {
                    "keyword": "dịch vụ seo",
                    "cluster": "SEO",
                    "opportunity": 90,
                    "volume": 1200,
                    "landing_page": "",
                },
                {
                    "keyword": "báo giá seo",
                    "cluster": "SEO",
                    "opportunity": 82,
                    "volume": 500,
                    "landing_page": "",
                },
                {
                    "keyword": "seo là gì",
                    "cluster": "SEO",
                    "opportunity": 60,
                    "landing_page": "https://example.com/seo",
                },
            ]
        )
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["keywords"], 2)
        self.assertEqual(gaps[0]["total_volume"], 1700)
        self.assertEqual(gaps[0]["priority"], "P0")

    def test_gsc_quality_warns_at_row_limit(self):
        quality = gsc_data_quality(25000)
        self.assertIn("giới hạn", quality["status"])
        self.assertEqual(quality["confidence"], "Trung bình")


class IndexDebuggerTests(unittest.TestCase):
    def test_live_inspection_reads_robots_canonical_and_content(self):
        result = inspect_live_url(
            "https://example.com/page", session=FakeLiveSession()
        )
        self.assertEqual(result["status"], 200)
        self.assertTrue(result["indexable_live"])
        self.assertTrue(result["robots_allowed_googlebot"])
        self.assertEqual(result["canonical"], "https://example.com/page")
        self.assertEqual(result["title"], "Dịch vụ SEO")
        self.assertGreater(result["content_chars"], 10)

    def test_index_comparison_labels_index_as_not_live(self):
        report = compare_indexed_and_live(
            {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "googleCanonical": "https://example.com/other",
                    "userCanonical": "https://example.com/page",
                }
            },
            {
                "status": 200,
                "indexable_live": True,
                "robots_allowed_googlebot": True,
                "canonical": "https://example.com/page",
            },
        )
        self.assertIn("không phải Live Test", report["indexed"]["source_note"])
        self.assertIn(
            "Google canonical khác canonical live",
            report["issues"],
        )


class AuditAndBackupTests(unittest.TestCase):
    def test_audit_comparison_reports_resolved_new_and_score_delta(self):
        previous = {
            "created_at": "2026-07-01",
            "pages": [
                {
                    "url": "https://example.com/",
                    "score": 70,
                    "status": 200,
                    "indexable": "Yes",
                    "inlinks": 1,
                    "dead_end": False,
                    "issues": ["Thiếu Meta Description"],
                }
            ],
        }
        current = {
            "created_at": "2026-07-29",
            "pages": [
                {
                    "url": "https://example.com/",
                    "score": 90,
                    "status": 200,
                    "indexable": "Yes",
                    "inlinks": 1,
                    "dead_end": False,
                    "issues": ["Thiếu Schema"],
                }
            ],
        }
        report = compare_audit_snapshots(previous, current)
        self.assertEqual(report["status"], "Cải thiện")
        self.assertEqual(report["deltas"]["avg_score"], 20)
        self.assertEqual(len(report["resolved"]), 1)
        self.assertEqual(len(report["new"]), 1)

    def test_project_backup_roundtrip_preserves_state(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            source_store = ProjectStoreV48(first)
            project = source_store.upsert_project(
                "SEO Example", "https://example.com"
            )
            source_store.save_project_state(
                project["id"], "keyword-discovery-v47", [{"keyword": "seo"}]
            )
            bundle = source_store.export_project_bundle(
                project["id"], Path(first) / "backup.zip"
            )
            target_store = ProjectStoreV48(second)
            restored = target_store.import_project_bundle(bundle)
            state = target_store.load_project_state(
                restored["id"], "keyword-discovery-v47", []
            )
            self.assertEqual(state[0]["keyword"], "seo")

    def test_onboarding_marks_keyword_planner_optional_state(self):
        rows = onboarding_statuses_v48(
            {"website": "https://example.com"},
            [object()],
            [],
            [{"keyword": "seo"}],
            [{"query": "seo"}],
            {"lab": {"score": 80}},
            True,
            True,
        )
        planner = next(
            row for row in rows if row["name"] == "Keyword Planner (tùy chọn)"
        )
        self.assertEqual(planner["status"], "Đã kết nối")

    def test_v48_guide_covers_every_new_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            path = generate(Path(temp) / "guide-v48.pdf")
            reader = PdfReader(path)
            self.assertGreaterEqual(len(reader.pages), 33)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            for token in (
                "Keyword Planner",
                "Opportunity 2.0",
                "SERP Weakness",
                "Cannibalization",
                "Content Gap",
                "Index Debugger",
                "Google Index",
                "URL live",
                "So sánh Audit",
                "Sao lưu dự án",
                "Ctrl+K",
            ):
                self.assertIn(token, text)

    def test_v48_packaging_targets_v48_executable(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / "installer_v48.iss").read_text(encoding="utf-8")
        workflow = (
            root / ".github" / "workflows" / "build-v48.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('Source: "dist\\{#MyAppExeName}"', installer)
        self.assertIn('Get-Item "dist\\SEO_AI_Studio_V48.exe"', workflow)
        self.assertNotIn('Source: "dist\\SEO_AI_Studio_V47.exe"', installer)


if __name__ == "__main__":
    unittest.main()
