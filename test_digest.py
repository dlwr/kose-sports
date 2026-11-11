import unittest

import digest


def news(title, url, image=None):
    return {"source": "山梨日日新聞", "title": title, "url": url, "published": "2026-11-11T19:05:00+09:00", "image": image}


def post(no, text):
    return {"no": no, "published": "2026-11-11T20:00:00+09:00", "text": text, "url": f"https://example.com/{no}"}


COLLECTED = {
    "news": [news("外国人２選手が練習参加", "https://s/1"), news("作戦ボード寄贈", "https://s/2", "https://img/2.jpg")],
    "videos": [],
    "notes": [],
    "boards": {"kofu5ch": [post(245, "監督そのままか")], "ra": [post(309, "ベンカリファ甲府か")], "cho": [post(906573, "藤枝戦")]},
    "club": {"record": "3勝3分10敗", "rank": 20, "league": "明治安田Ｊ２リーグ", "next": None, "players": ["後藤陽翔"]},
    "failures": [],
}
EMPTY = {**COLLECTED, "news": [], "boards": {"kofu5ch": [], "ra": [], "cho": []}}


def topic(sources, **extra):
    return {"headline": "見出し", "body": "本文", "sources": sources, **extra}


def raw(**parts):
    return {"top": topic(["N1"]), "briefs": [], "rumors": [], "boards": [], **parts}


class BuildPromptTest(unittest.TestCase):
    def setUp(self):
        self.user, self.index = digest.build_prompt(COLLECTED, "2026-11-12")

    def test_news_gets_numbered_id(self):
        self.assertIn("[N2] 作戦ボード寄贈", self.user)

    def test_each_board_has_its_own_prefix(self):
        self.assertEqual([k for k in self.index if k[0] != "N"], ["K1", "R1", "C1"])

    def test_board_post_text_is_in_prompt(self):
        self.assertIn("[R1] ベンカリファ甲府か", self.user)

    def test_index_keeps_url(self):
        self.assertEqual(self.index["N2"]["url"], "https://s/2")

    def test_board_post_is_labelled_by_board_and_number(self):
        self.assertEqual(self.index["R1"]["title"], "らスレ 309")

    def test_roster_is_in_prompt(self):
        self.assertIn("後藤陽翔", self.user)


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


class MakeDigestTest(unittest.TestCase):
    def test_closed_when_nothing_was_collected(self):
        self.assertTrue(digest.make_digest(EMPTY, "2026-11-12", llm=None)["closed"])

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
