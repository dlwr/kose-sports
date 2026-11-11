import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import build
from collect import JST

NOW = datetime(2026, 11, 12, 6, 0, tzinfo=JST)
CLUB = {"record": None, "rank": None, "league": None, "next": None, "players": ["後藤陽翔"]}


def news(url):
    return {"source": "s", "title": url, "url": url, "published": "2026-11-11T10:00:00+09:00", "image": None}


def collected(*urls):
    return {
        "news": [news(u) for u in urls],
        "videos": [],
        "notes": [],
        "boards": {"kofu5ch": [], "ra": [], "cho": []},
        "club": CLUB,
        "failures": [],
    }


def stored(day, *urls):
    digest = {"closed": True, "links_only": False, "top": None, "briefs": [], "rumors": [], "boards": []}
    return {"date": day, "club": CLUB, "digest": digest, "news": [news(u) for u in urls], "videos": [], "notes": [], "failures": []}


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data, self.dist = self.root / "data", self.root / "dist"
        self.data.mkdir()

    def save(self, issue):
        (self.data / f"{issue['date']}.json").write_text(json.dumps(issue, ensure_ascii=False))

    def publish(self, *urls, llm=None):
        return build.publish(NOW, self.data, lambda now: collected(*urls), llm)

    def test_issue_is_saved_under_its_date(self):
        self.publish("https://a")
        self.assertTrue((self.data / "2026-11-12.json").exists())

    def test_news_already_published_is_dropped(self):
        self.save(stored("2026-11-11", "https://a"))
        self.assertEqual([n["url"] for n in self.publish("https://a", "https://b")["news"]], ["https://b"])

    def test_rerun_on_same_day_keeps_its_own_news(self):
        self.save(stored("2026-11-12", "https://a"))
        self.assertEqual([n["url"] for n in self.publish("https://a")["news"]], ["https://a"])

    def test_roster_is_not_stored(self):
        self.assertNotIn("players", self.publish("https://a")["club"])

    def test_llm_failure_is_listed_in_failures(self):
        def llm(system, user):
            raise RuntimeError("down")

        self.assertEqual(self.publish("https://a", llm=llm)["failures"], ["要約"])

    def test_site_has_a_page_per_issue(self):
        self.save(stored("2026-11-11"))
        self.save(stored("2026-11-12"))
        build.build_site(self.data, self.dist)
        self.assertTrue((self.dist / "2026-11-11.html").exists())

    def test_index_is_latest_issue(self):
        for day in ("2026-11-10", "2026-11-12", "2026-11-11"):
            self.save(stored(day))
        build.build_site(self.data, self.dist)
        self.assertIn("小瀬スポーツ 2026-11-12", (self.dist / "index.html").read_text())

    def test_pages_link_to_neighbours(self):
        for day in ("2026-11-10", "2026-11-11", "2026-11-12"):
            self.save(stored(day))
        build.build_site(self.data, self.dist)
        page = (self.dist / "2026-11-11.html").read_text()
        self.assertTrue('href="2026-11-10.html"' in page and 'href="2026-11-12.html"' in page)

    def test_custom_domain_file(self):
        self.save(stored("2026-11-12"))
        build.build_site(self.data, self.dist)
        self.assertEqual((self.dist / "CNAME").read_text().strip(), "kose-sports.yuta25.com")

    def test_crawlers_are_disallowed(self):
        self.save(stored("2026-11-12"))
        build.build_site(self.data, self.dist)
        self.assertIn("Disallow: /", (self.dist / "robots.txt").read_text())


if __name__ == "__main__":
    unittest.main()
