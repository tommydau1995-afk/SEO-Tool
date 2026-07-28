import tempfile
import unittest
from pathlib import Path

from seo_v4_checks import build_master_checks
from seo_v4_core import (
    PageResult,
    ProjectStore,
    SerpResearcher,
    ServerLogAnalyzer,
    build_fix_queue,
    compare_snapshots,
    normalize_url,
)


class V4CoreTests(unittest.TestCase):
    def test_master_checklist_has_exactly_150_items(self):
        checks = build_master_checks()
        self.assertEqual(len(checks), 150)
        self.assertEqual(checks[0].id, 1)
        self.assertEqual(checks[-1].id, 150)

    def test_url_normalization(self):
        self.assertEqual(normalize_url("example.com/a/"), "https://example.com/a")

    def test_outline_merges_ai_overview_questions_and_sources(self):
        source = type(
            "Source",
            (),
            {
                "headings": ["H2: Khái niệm", "H2: Quy trình", "H3: Chuẩn bị"],
                "position": 1,
                "title": "Nguồn A",
                "link": "https://example.com/a",
                "fetch_status": "Đã lấy 3 heading",
            },
        )()
        value = SerpResearcher.merge_outline(
            "dịch vụ seo",
            [source],
            "SEO giúp website tăng khả năng hiển thị.",
            ["SEO là gì?"],
            [{"title": "SEO", "original": "https://example.com/seo.jpg"}],
        )
        self.assertIn("CONTENT BRIEF TỔNG HỢP TOP 5 + AI OVERVIEW", value)
        self.assertIn("H2: Câu hỏi thường gặp", value)
        self.assertIn("https://example.com/seo.jpg", value)

    def test_log_analyzer_splits_mobile_and_desktop(self):
        rows = [
            '1.1.1.1 - - [28/Jul/2026:10:00:00 +0700] "GET /a HTTP/1.1" 200 100 "-" "Googlebot/2.1 (+http://www.google.com/bot.html)"',
            '1.1.1.2 - - [28/Jul/2026:10:01:00 +0700] "GET /search?q=x HTTP/1.1" 404 10 "-" "Mozilla/5.0 (Linux; Android) Googlebot/2.1 Mobile"',
            '1.1.1.3 - - [28/Jul/2026:10:02:00 +0700] "GET /human HTTP/1.1" 200 10 "-" "Chrome"',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            path.write_text("\n".join(rows), encoding="utf-8")
            report = ServerLogAnalyzer().analyze(path)
        self.assertEqual(report["googlebot_hits"], 2)
        self.assertEqual(report["by_device"]["Desktop"], 1)
        self.assertEqual(report["by_device"]["Smartphone"], 1)
        self.assertTrue(report["waste_urls"])

    def test_fix_queue_and_validation(self):
        page = PageResult(
            score=50,
            status=200,
            url="https://example.com",
            final_url="https://example.com",
            title="",
            title_len=0,
            meta="",
            meta_len=0,
            h1="",
            h1_count=0,
            h2_count=0,
            words=100,
            images=0,
            missing_alt=0,
            internal_links=0,
            external_links=0,
            canonical="",
            indexable="Yes",
            response_ms=100,
            schema_count=0,
            og_title="",
            issues=["Thiếu Title", "Thiếu Meta"],
        )
        fixes = build_fix_queue([page])
        self.assertEqual(fixes[0].priority, "P0")
        comparison = compare_snapshots(
            {"pages": [{"url": page.url, "issues": page.issues}]},
            {"pages": [{"url": page.url, "issues": ["Thiếu Meta"]}]},
        )
        self.assertEqual(comparison["resolved"], [(page.url, "Thiếu Title")])

    def test_project_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(directory)
            project = store.upsert_project("Demo", "example.com")
            store.save_project_state(project["id"], "keyword-map", [{"keyword": "seo"}])
            result = store.load_project_state(project["id"], "keyword-map", [])
        self.assertEqual(result[0]["keyword"], "seo")


if __name__ == "__main__":
    unittest.main()
