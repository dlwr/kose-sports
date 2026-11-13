import unittest

import digest


def news(title, url, image=None):
    return {"source": "山梨日日新聞", "title": title, "url": url, "published": "2026-11-11T19:05:00+09:00", "image": image}


def post(no, text):
    return {"no": no, "published": "2026-11-11T20:00:00+09:00", "text": text, "url": f"https://example.com/{no}"}


def read(title, url, source="甲府サポ"):
    return {
        "source": source,
        "title": title,
        "url": url,
        "published": "2026-11-10T19:05:00+09:00",
        "image": "https://img/" + title,
        "excerpt": title + "の抜粋",
    }


COLLECTED = {
    "news": [news("外国人２選手が練習参加", "https://s/1"), news("作戦ボード寄贈", "https://s/2", "https://img/2.jpg")],
    "videos": [],
    "reads": [read("仙台戦の感想", "https://n/1"), read("藤枝戦の展望", "https://n/2"), read("組織論", "https://n/3")],
    "boards": {"kofu5ch": [post(245, "監督そのままか")], "ra": [post(309, "ベンカリファ甲府か")], "cho": [post(906573, "藤枝戦")]},
    "club": {"record": "3勝3分10敗", "rank": 20, "league": "明治安田Ｊ２リーグ", "next": None, "players": ["後藤陽翔"]},
    "failures": [],
}
EMPTY = {**COLLECTED, "news": [], "reads": [], "boards": {"kofu5ch": [], "ra": [], "cho": []}}
EARLIER = [
    {
        "date": "2026-11-11",
        "digest": {
            "top": {"headline": "練習に新顔", "body": "外国人2選手が練習に参加した。", "links": []},
            "briefs": [],
            "rumors": [{"headline": "内藤に移籍話", "body": "調査が届いたとの見方。", "confidence": 2, "links": []}],
            "boards": [{"headline": "重い空気", "body": "降格への不安。", "board": "超掲示板", "links": []}],
            "reads": [{"headline": "静寂の10分", "body": "仙台戦を振り返る。", "links": [{"source": "農林1965号"}]}],
        },
    }
]


def topic(sources, **extra):
    return {"headline": "見出し", "body": "本文", "sources": sources, **extra}


def raw(**parts):
    blank = {"second": topic([]), "briefs": [], "rumors": [], "boards": [], "reads": [], "editorial": ""}
    return {"top": topic(["N1"]), **blank, **parts}


class BuildPromptTest(unittest.TestCase):
    def setUp(self):
        self.user, self.index = digest.build_prompt(COLLECTED, "2026-11-12")

    def test_news_gets_numbered_id(self):
        self.assertIn("[N2] 作戦ボード寄贈", self.user)

    def test_each_board_has_its_own_prefix(self):
        self.assertEqual([k for k in self.index if k[0] not in "NB"], ["K1", "R1", "C1"])

    def test_board_post_text_is_in_prompt(self):
        self.assertIn("[R1] ベンカリファ甲府か", self.user)

    def test_index_keeps_url(self):
        self.assertEqual(self.index["N2"]["url"], "https://s/2")

    def test_board_post_is_labelled_by_board_and_number(self):
        self.assertEqual(self.index["R1"]["title"], "らスレ 309")

    def test_roster_is_in_prompt(self):
        self.assertIn("後藤陽翔", self.user)

    def test_news_with_image_is_marked(self):
        self.assertIn("[N2] 作戦ボード寄贈（山梨日日新聞 2026-11-11T19:05・写真あり）", self.user)

    def test_news_without_image_is_not_marked(self):
        self.assertIn("[N1] 外国人２選手が練習参加（山梨日日新聞 2026-11-11T19:05）", self.user)

    def test_read_gets_its_own_prefix(self):
        self.assertIn("[B2] 藤枝戦の展望（甲府サポ 2026-11-10・写真あり）", self.user)

    def test_read_excerpt_is_in_prompt(self):
        self.assertIn("藤枝戦の展望の抜粋", self.user)

    def test_index_keeps_read_image(self):
        self.assertEqual(self.index["B1"]["image"], "https://img/仙台戦の感想")

    def test_no_earlier_section_without_earlier_issues(self):
        self.assertNotIn("既報", self.user)


class EarlierIssuesTest(unittest.TestCase):
    def setUp(self):
        self.user, _ = digest.build_prompt(COLLECTED, "2026-11-12", EARLIER)

    def test_earlier_issue_is_dated(self):
        self.assertIn("2026-11-11 号", self.user)

    def test_earlier_top_is_in_prompt(self):
        self.assertIn("一面: 練習に新顔 ／ 外国人2選手が練習に参加した。", self.user)

    def test_earlier_rumor_keeps_confidence(self):
        self.assertIn("噂（確度2）: 内藤に移籍話", self.user)

    def test_earlier_board_keeps_board_name(self):
        self.assertIn("掲示板（超掲示板）: 重い空気", self.user)

    def test_earlier_read_keeps_writer(self):
        self.assertIn("読み物（農林1965号）: 静寂の10分", self.user)


class ValidateTest(unittest.TestCase):
    def setUp(self):
        _, self.index = digest.build_prompt(COLLECTED, "2026-11-12")

    def test_sources_become_links(self):
        out = digest.validate(raw(), self.index)
        self.assertEqual(out["top"]["links"], [{"title": "外国人２選手が練習参加", "url": "https://s/1", "source": "山梨日日新聞"}])

    def test_unknown_source_is_dropped(self):
        out = digest.validate(raw(top=topic(["N1", "N9"])), self.index)
        self.assertEqual(len(out["top"]["links"]), 1)

    def test_top_without_valid_source_is_removed(self):
        self.assertIsNone(digest.validate(raw(top=topic(["N9"])), self.index)["top"])

    def test_brief_without_valid_source_is_removed(self):
        out = digest.validate(raw(briefs=[topic([]), topic(["N2"])]), self.index)
        self.assertEqual(len(out["briefs"]), 1)

    def test_image_comes_from_first_source_that_has_one(self):
        out = digest.validate(raw(top=topic(["N1", "N2"])), self.index)
        self.assertEqual(out["top"]["image"], "https://img/2.jpg")

    def test_image_is_none_when_no_source_has_one(self):
        self.assertIsNone(digest.validate(raw(), self.index)["top"]["image"])

    def test_repeated_source_gives_one_link(self):
        out = digest.validate(raw(top=topic(["N1", "N1"])), self.index)
        self.assertEqual(len(out["top"]["links"]), 1)

    def test_links_are_capped(self):
        index = {f"N{i}": {"title": str(i), "url": f"https://s/{i}", "source": "s", "image": None} for i in range(9)}
        out = digest.validate(raw(top=topic(list(index))), index)
        self.assertEqual(len(out["top"]["links"]), 5)

    def test_rumor_keeps_confidence(self):
        out = digest.validate(raw(rumors=[topic(["R1"], origin="らスレ", confidence=1)]), self.index)
        self.assertEqual(out["rumors"][0]["confidence"], 1)

    def test_rumors_are_sorted_by_confidence(self):
        rumors = [topic(["R1"], origin="a", confidence=c) for c in (1, 4, 2)]
        out = digest.validate(raw(rumors=rumors), self.index)
        self.assertEqual([r["confidence"] for r in out["rumors"]], [4, 2, 1])

    def test_board_summary_keeps_board_name(self):
        out = digest.validate(raw(boards=[topic(["C1"], board="超掲示板")]), self.index)
        self.assertEqual(out["boards"][0]["board"], "超掲示板")

    def test_top_backed_only_by_board_posts_is_removed(self):
        self.assertIsNone(digest.validate(raw(top=topic(["C1", "K1"])), self.index)["top"])

    def test_top_can_be_a_read(self):
        out = digest.validate(raw(top=topic(["B1"])), self.index)
        self.assertEqual(out["top"]["image"], "https://img/仙台戦の感想")

    def test_second_needs_news(self):
        self.assertIsNone(digest.validate(raw(second=topic(["B1", "C1"])), self.index)["second"])

    def test_second_backed_by_news_is_kept(self):
        self.assertEqual(digest.validate(raw(second=topic(["N1", "C1"])), self.index)["second"]["headline"], "見出し")

    def test_brief_backed_only_by_board_posts_is_removed(self):
        out = digest.validate(raw(briefs=[topic(["C1"]), topic(["N2", "C1"])]), self.index)
        self.assertEqual(len(out["briefs"]), 1)

    def test_news_beyond_link_cap_still_backs_a_brief(self):
        index = {**{f"K{i}": self.index["K1"] for i in range(5)}, "N1": self.index["N1"]}
        self.assertEqual(len(digest.validate(raw(briefs=[topic(list(index))]), index)["briefs"]), 1)

    def test_read_needs_read_source(self):
        self.assertEqual(digest.validate(raw(reads=[topic(["N1"])]), self.index)["reads"], [])

    def test_reads_are_capped(self):
        reads = [topic(["B1"]), topic(["B2"]), topic(["B3"])]
        self.assertEqual(len(digest.validate(raw(reads=reads), self.index)["reads"]), 2)

    def test_read_used_as_top_is_not_repeated(self):
        out = digest.validate(raw(top=topic(["B1"]), reads=[topic(["B1"]), topic(["B2"])]), self.index)
        self.assertEqual([r["links"][0]["url"] for r in out["reads"]], ["https://n/2"])

    def test_read_as_top_counts_toward_cap(self):
        out = digest.validate(raw(top=topic(["B1"]), reads=[topic(["B2"]), topic(["B3"])]), self.index)
        self.assertEqual(len(out["reads"]), 1)

    def test_editorial_is_trimmed(self):
        self.assertEqual(digest.validate(raw(editorial=" 今日も最下位。\n"), self.index)["editorial"], "今日も最下位。")


class MakeDigestTest(unittest.TestCase):
    def test_closed_when_nothing_was_collected(self):
        self.assertTrue(digest.make_digest(EMPTY, "2026-11-12", llm=None)["closed"])

    def test_issue_with_only_reads_is_not_closed(self):
        only_reads = {**EMPTY, "reads": COLLECTED["reads"]}
        self.assertFalse(digest.make_digest(only_reads, "2026-11-12", lambda system, user: raw(top=topic(["B1"])))["closed"])

    def test_earlier_issues_reach_the_llm(self):
        seen = []
        digest.make_digest(COLLECTED, "2026-11-12", lambda system, user: seen.append(user) or raw(), EARLIER)
        self.assertIn("練習に新顔", seen[0])

    def test_llm_is_not_called_when_closed(self):
        def llm(system, user):
            raise AssertionError("called")

        digest.make_digest(EMPTY, "2026-11-12", llm)

    def test_llm_output_is_validated(self):
        out = digest.make_digest(COLLECTED, "2026-11-12", lambda system, user: raw(top=topic(["N9"])))
        self.assertIsNone(out["top"])

    def test_llm_failure_falls_back_to_links_only(self):
        def llm(system, user):
            raise RuntimeError("down")

        self.assertTrue(digest.make_digest(COLLECTED, "2026-11-12", llm)["links_only"])

    def test_normal_digest_is_not_links_only(self):
        self.assertFalse(digest.make_digest(COLLECTED, "2026-11-12", lambda system, user: raw())["links_only"])


if __name__ == "__main__":
    unittest.main()
