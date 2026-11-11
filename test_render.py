import unittest

import render


def topic(headline="見出し", **extra):
    return {
        "headline": headline,
        "body": "一段落目\n二段落目",
        "links": [{"title": "元記事", "url": "https://example.com/a", "source": "山梨日日新聞"}],
        "image": None,
        **extra,
    }


def issue(**parts):
    digest = {"closed": False, "links_only": False, "top": topic("トップ見出し"), "briefs": [], "rumors": [], "boards": []}
    digest.update(parts.pop("digest", {}))
    base = {
        "date": "2026-11-12",
        "club": {
            "record": "3勝3分10敗",
            "rank": 20,
            "league": "明治安田Ｊ２リーグ",
            "next": {"date": "2026-11-14", "round": "第17節", "time": "14:00", "opponent": "藤枝ＭＹＦＣ", "home": False, "venue": "藤枝サ"},
        },
        "digest": digest,
        "news": [],
        "videos": [],
        "notes": [],
        "failures": [],
    }
    return {**base, **parts}


def html(prev=None, next=None, **parts):
    return render.render_issue(issue(**parts), prev, next)


class RenderTest(unittest.TestCase):
    def test_page_is_not_indexed(self):
        self.assertIn('<meta name="robots" content="noindex', html())

    def test_date_in_masthead(self):
        self.assertIn("2026年11月12日（木）", html())

    def test_countdown_to_next_match(self):
        self.assertIn("あと2日", html())

    def test_match_day(self):
        self.assertIn("本日キックオフ", html(date="2026-11-14"))

    def test_rank(self):
        self.assertIn("20位", html())

    def test_club_block_is_omitted_without_data(self):
        club = {"record": None, "rank": None, "league": None, "next": None}
        self.assertNotIn("None", html(club=club))

    def test_top_headline(self):
        self.assertIn("トップ見出し", html())

    def test_body_paragraphs_are_split(self):
        self.assertIn("<p>一段落目</p><p>二段落目</p>", html(digest={"briefs": [topic()]}))

    def test_top_without_image_puts_body_beside_headline(self):
        self.assertIn('<div class="top-side"><p>一段落目</p><p>二段落目</p></div>', html())

    def test_scraped_text_is_escaped(self):
        page = html(digest={"top": topic("<script>alert(1)</script>")})
        self.assertNotIn("<script>alert(1)", page)

    def test_non_http_link_is_dropped(self):
        bad = topic(links=[{"title": "x", "url": "javascript:alert(1)", "source": "s"}])
        self.assertNotIn("javascript:", html(digest={"top": bad}))

    def test_image_is_hotlinked_without_referrer(self):
        page = html(digest={"top": topic(image="https://img/a.jpg")})
        self.assertIn('<img src="https://img/a.jpg" alt="" referrerpolicy="no-referrer"', page)

    def test_rumor_meter_has_text(self):
        rumor = topic("FW獲得か", origin="らスレ", confidence=2)
        self.assertIn("確度 2/5", html(digest={"rumors": [rumor]}))

    def test_unconfirmed_rumor_is_labelled(self):
        rumor = topic("FW獲得か", origin="らスレ", confidence=2)
        self.assertIn("未確認", html(digest={"rumors": [rumor]}))

    def test_official_rumor_is_not_labelled_unconfirmed(self):
        rumor = topic("FW獲得", origin="クラブ公式", confidence=5)
        self.assertNotIn("未確認", html(digest={"rumors": [rumor]}))

    def test_rumor_origin(self):
        rumor = topic("FW獲得か", origin="らスレの書き込み", confidence=1)
        self.assertIn("らスレの書き込み", html(digest={"rumors": [rumor]}))

    def test_news_comes_before_rumors_in_season(self):
        page = html(digest={"briefs": [topic("短信A")], "rumors": [topic("噂B", origin="o", confidence=1)]})
        self.assertLess(page.index("短信A"), page.index("噂B"))

    def test_rumors_come_first_off_season(self):
        club = {"record": None, "rank": None, "league": None, "next": None}
        page = html(club=club, digest={"briefs": [topic("短信A")], "rumors": [topic("噂B", origin="o", confidence=1)]})
        self.assertLess(page.index("噂B"), page.index("短信A"))

    def test_board_name(self):
        self.assertIn("超掲示板", html(digest={"boards": [topic("荒れ模様", board="超掲示板")]}))

    def test_empty_section_has_no_heading(self):
        self.assertNotIn("サポーターの note", html())

    def test_notes_section(self):
        note = {"source": "甲府サポ", "title": "観戦記", "url": "https://note.com/x", "published": "2026-11-11T19:00:00+09:00", "image": None}
        self.assertIn("観戦記", html(notes=[note]))

    def test_closed_issue(self):
        self.assertIn("本日休刊", html(digest={"closed": True, "top": None}))

    def test_links_only_issue_lists_news(self):
        item = {"source": "山梨日日新聞", "title": "練習参加", "url": "https://s/1", "published": "2026-11-11T16:41:00+09:00", "image": None}
        page = html(news=[item], digest={"links_only": True, "top": None})
        self.assertIn('<a href="https://s/1" target="_blank" rel="noopener">練習参加</a>', page)

    def test_failures_are_noted(self):
        self.assertIn("本日は 5ch、note を取得できませんでした", html(failures=["5ch", "note"]))

    def test_llm_failure_is_noted(self):
        self.assertIn("要約を作れなかった", html(digest={"links_only": True, "top": None}))

    def test_pager_stays_in_same_tab(self):
        self.assertIn('<a href="2026-11-11.html">', html(prev="2026-11-11"))

    def test_previous_issue_link(self):
        self.assertIn('href="2026-11-11.html"', html(prev="2026-11-11"))

    def test_next_issue_link(self):
        self.assertIn('href="2026-11-13.html"', html(next="2026-11-13"))


if __name__ == "__main__":
    unittest.main()
