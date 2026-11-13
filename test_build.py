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


def read(url):
    return {**news(url), "excerpt": "抜粋"}


def answer(top=(), reads=()):
    def topic(sources):
        return {"headline": "見出し", "body": "本文", "sources": list(sources)}

    blank = {"second": topic([]), "briefs": [], "rumors": [], "boards": [], "editorial": ""}
    return lambda system, user: {"top": topic(top), "reads": [topic([r]) for r in reads], **blank}


def collected(*urls, videos=(), reads=()):
    return {
        "news": [news(u) for u in urls],
        "videos": [news(u) for u in videos],
        "reads": [read(u) for u in reads],
        "boards": {"kofu5ch": [], "ra": [], "cho": []},
        "club": CLUB,
        "failures": [],
    }


def stored(day, *urls, videos=(), **extra):
    digest = {"closed": True, "links_only": False, "top": None, "briefs": [], "rumors": [], "boards": []}
    base = {"date": day, "club": CLUB, "digest": digest, "news": [news(u) for u in urls], "notes": [], "failures": []}
    return {**base, "videos": [news(u) for u in videos], **extra}


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data, self.dist = self.root / "data", self.root / "dist"
        self.data.mkdir()

    def save(self, issue):
        (self.data / f"{issue['date']}.json").write_text(json.dumps(issue, ensure_ascii=False))

    def publish(self, *urls, llm=None, **more):
        self.since = []
        return build.publish(NOW, self.data, lambda now, since: self.since.append(since) or collected(*urls, **more), llm)

    def test_issue_is_saved_under_its_date(self):
        self.publish("https://a")
        self.assertTrue((self.data / "2026-11-12.json").exists())

    def test_news_already_published_is_dropped(self):
        self.save(stored("2026-11-11", "https://a"))
        self.assertEqual([n["url"] for n in self.publish("https://a", "https://b")["news"]], ["https://b"])

    def test_rerun_on_same_day_keeps_its_own_news(self):
        self.save(stored("2026-11-12", "https://a"))
        self.assertEqual([n["url"] for n in self.publish("https://a")["news"]], ["https://a"])

    def test_video_already_published_is_dropped(self):
        self.save(stored("2026-11-11", videos=["https://v/1"]))
        self.assertEqual([v["url"] for v in self.publish(videos=["https://v/1", "https://v/2"])["videos"]], ["https://v/2"])

    def test_collection_time_is_stored(self):
        self.assertEqual(self.publish("https://a")["collected_at"], "2026-11-12T06:00:00+09:00")

    def test_collector_gets_previous_collection_time(self):
        self.save(stored("2026-11-10", collected_at="2026-11-10T06:05:00+09:00"))
        self.save(stored("2026-11-11", collected_at="2026-11-11T10:35:00+09:00"))
        self.publish("https://a")
        self.assertEqual(self.since, ["2026-11-11T10:35:00+09:00"])

    def test_collector_gets_no_time_on_first_issue(self):
        self.publish("https://a")
        self.assertEqual(self.since, [None])

    def featured(self, day, key, url):
        link = {"title": "t", "url": url, "source": "s"}
        topic = {"headline": "h", "body": "b", "links": [link], "image": None}
        issue = stored(day)
        issue["digest"][key] = [topic] if key == "reads" else topic
        self.save(issue)

    def offered_reads(self, *urls):
        prompts = []
        self.publish(reads=urls, llm=lambda system, user: prompts.append(user) or answer()(system, user))
        return [u for u in urls if u in prompts[0]]

    def test_read_featured_in_an_old_issue_is_not_offered_again(self):
        self.featured("2026-11-06", "reads", "https://n/1")
        self.assertEqual(self.offered_reads("https://n/1", "https://n/2"), ["https://n/2"])

    def test_read_used_as_top_is_not_offered_again(self):
        self.featured("2026-11-11", "top", "https://n/1")
        self.assertEqual(self.offered_reads("https://n/1", "https://n/2"), ["https://n/2"])

    def test_chosen_read_is_stored_in_digest(self):
        issue = self.publish(reads=["https://n/1", "https://n/2"], llm=answer(reads=["B2"]))
        self.assertEqual(issue["digest"]["reads"][0]["links"][0]["url"], "https://n/2")

    def test_earlier_issue_is_shown_to_the_llm(self):
        self.save(stored("2026-11-11"))
        prompts = []
        self.publish("https://a", llm=lambda system, user: prompts.append(user) or answer()(system, user))
        self.assertIn("2026-11-11 号", prompts[0])

    def test_only_recent_issues_are_shown_to_the_llm(self):
        for day in ("2026-11-08", "2026-11-09", "2026-11-10", "2026-11-11"):
            self.save(stored(day))
        prompts = []
        self.publish("https://a", llm=lambda system, user: prompts.append(user) or answer()(system, user))
        self.assertNotIn("2026-11-08 号", prompts[0])

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
