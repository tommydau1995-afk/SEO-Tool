import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from generate_user_guide_v46 import generate
from seo_v4_core import FixItem
from seo_v43_core import FriendlyError
from seo_v46_core import (
    CruxClient,
    ProjectStoreV46,
    SmartGoogleResearcher,
    build_content_briefs,
    build_detailed_issues,
    demo_payload,
    extract_urls,
    onboarding_statuses,
    support_information,
    version_tuple,
)


class SmartGoogleTests(unittest.TestCase):
    def test_parses_newer_google_containers(self):
        html = """
        <html><body>
          <div class="MjjYud">
            <div class="yuRUbf">
              <a href="https://one.example/article">
                <div role="heading" aria-level="3">Kết quả mới</div>
              </a>
            </div>
            <div class="VwiC3b">Đoạn mô tả kết quả Google mới.</div>
          </div>
          <article>
            <a href="/url?q=https%3A%2F%2Ftwo.example%2Fpage">
              <h3>Kết quả thứ hai</h3>
            </a>
          </article>
        </body></html>
        """
        result = SmartGoogleResearcher.parse_search_html(html)
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["results"][0]["link"], "https://two.example/page")
        self.assertEqual(result["results"][1]["link"], "https://one.example/article")

    def test_detects_vietnamese_consent(self):
        html = """
        <html><body><form action="https://consent.google.com/save">
        Trước khi bạn tiếp tục đến Google - Chấp nhận tất cả
        </form></body></html>
        """
        with self.assertRaises(FriendlyError) as context:
            SmartGoogleResearcher.parse_search_html(html)
        self.assertIn("Consent", context.exception.message)

    def test_search_url_contains_locale(self):
        url = SmartGoogleResearcher.google_search_url("nội thất cao cấp", "vn", "vi")
        self.assertIn("gl=vn", url)
        self.assertIn("hl=vi", url)
        self.assertIn("n%E1%BB%99i", url)

    def test_extracts_unique_clipboard_urls(self):
        value = (
            "https://one.example/a\n"
            "https://one.example/a\n"
            "Kết quả: https://two.example/b), và https://three.example/c."
        )
        self.assertEqual(
            extract_urls(value),
            [
                "https://one.example/a",
                "https://two.example/b",
                "https://three.example/c",
            ],
        )


class RecoveryAndWorkflowTests(unittest.TestCase):
    def test_project_store_recovery_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStoreV46(temp)
            store.begin_recovery(
                "Full SEO Audit",
                {"project_id": "abc", "keyword_rows": [{"keyword": "seo"}]},
            )
            saved = store.load_recovery()
            self.assertTrue(saved["running"])
            self.assertEqual(saved["operation"], "Full SEO Audit")
            self.assertEqual(saved["payload"]["project_id"], "abc")
            store.clear_recovery()
            self.assertFalse(store.load_recovery()["running"])

    def test_app_settings_are_atomic_json(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStoreV46(temp)
            store.save_app_settings({"mode": "Easy", "first_run_complete": True})
            path = Path(temp) / "settings-v46.json"
            self.assertEqual(json.loads(path.read_text())["mode"], "Easy")
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_detailed_issue_has_all_requested_fields(self):
        fixes = [
            FixItem(
                priority="P0",
                issue="HTTP 500",
                url="https://example.com/error",
                recommendation="Sửa máy chủ.",
            )
        ]
        row = build_detailed_issues(fixes)[0]
        self.assertEqual(row.expected_impact, "Cao")
        self.assertTrue(row.why_it_matters)
        self.assertTrue(row.difficulty)
        self.assertEqual(row.status, "Cần sửa")

    def test_content_briefs_follow_cluster_mapping(self):
        rows = [
            {
                "keyword": "nội thất cao cấp",
                "volume": 2000,
                "difficulty": 50,
                "intent": "Commercial",
                "cluster": "nội thất cao cấp",
                "landing_page": "https://example.com/noi-that",
            },
            {
                "keyword": "mẫu nội thất cao cấp",
                "volume": 800,
                "difficulty": 35,
                "intent": "Commercial",
                "cluster": "nội thất cao cấp",
                "landing_page": "https://example.com/noi-that",
            },
        ]
        brief = build_content_briefs(rows)[0]
        self.assertEqual(brief["primary_keyword"], "nội thất cao cấp")
        self.assertEqual(brief["total_volume"], 2800)
        self.assertEqual(brief["intent"], "Commercial")
        self.assertEqual(brief["landing_page"], "https://example.com/noi-that")
        self.assertIn("mẫu nội thất cao cấp", brief["secondary_keywords"])

    def test_onboarding_has_explicit_statuses(self):
        payload = demo_payload()
        rows = onboarding_statuses(
            payload["project"],
            payload["pages"],
            payload["keywords"],
            payload["gsc_rows"],
            payload["pagespeed"],
            True,
        )
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row["status"] == "Đã kết nối" for row in rows))

    def test_demo_payload_is_offline_and_complete(self):
        payload = demo_payload()
        self.assertEqual(len(payload["pages"]), 2)
        self.assertGreaterEqual(len(payload["keywords"]), 3)
        self.assertTrue(payload["graph"])
        self.assertIn("crux", payload["pagespeed"])


class TechnicalIntegrationTests(unittest.TestCase):
    def test_crux_parser_keeps_field_metrics_separate(self):
        payload = {
            "record": {
                "key": {"formFactor": "PHONE"},
                "collectionPeriod": {"firstDate": {"year": 2026}},
                "metrics": {
                    "largest_contentful_paint": {"percentiles": {"p75": 2500}},
                    "interaction_to_next_paint": {"percentiles": {"p75": 180}},
                    "cumulative_layout_shift": {"percentiles": {"p75": 0.08}},
                    "experimental_time_to_first_byte": {
                        "percentiles": {"p75": 600}
                    },
                },
            }
        }
        result = CruxClient.parse_record(payload)
        self.assertIn("Field Data", result["source"])
        self.assertEqual(result["lcp_ms"], 2500)
        self.assertEqual(result["inp_ms"], 180)

    def test_versions_compare_numerically(self):
        self.assertGreater(version_tuple("4.10.0"), version_tuple("4.6.0"))
        self.assertEqual(version_tuple("V4.6"), (4, 6))

    def test_support_info_does_not_include_secrets_label(self):
        text = support_information("HTTP 403", "Search Console")
        self.assertIn("4.6.0", text)
        self.assertIn("Search Console", text)
        self.assertIn("không bao gồm API key", text)

    def test_detailed_guide_has_all_tool_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            path = generate(Path(temp) / "guide.pdf")
            reader = PdfReader(path)
            self.assertEqual(len(reader.pages), 28)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            for token in (
                "Easy Mode",
                "Full SEO Audit",
                "Content Workflow",
                "CrUX",
                "Google Search Console",
                "WordPress",
                "Fix Queue",
            ):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
