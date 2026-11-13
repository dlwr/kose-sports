import unittest
from datetime import datetime, timedelta
from unittest import mock

import collect
from collect import JST

NOW = datetime(2026, 11, 12, 6, 0, tzinfo=JST)

GNEWS = """<rss><channel><title>x</title>
<item><title>甲府がDF獲得へ - スポーツ報知</title><link>https://news.google.com/rss/articles/AAA?oc=5</link>
<pubDate>Tue, 10 Nov 2026 05:04:50 GMT</pubDate><source url="https://hochi.news">スポーツ報知</source></item>
</channel></rss>"""

OFFICIAL = """<ul><li> <a class="newsList__item" href="/news/other/525715"> <div class="newsList__itemText">
<p class="top-news__day">2026.11.10 （火）</p> <p class="top-news__category -other"><span>その他</span></p>
<p class="top-news__information__detail">秋田戦のお知らせ</p> </div>
<div class="newsList__itemImage"> <img alt="PHOTO" src="https://cdn.www.ventforet.jp/images/photo_notfound.gif" /> </div> </a> </li>
<li> <a class="newsList__item" href="/news/team/525707"> <div class="newsList__itemText">
<p class="top-news__day">2026.11.9 （月）</p>
<p class="top-news__information__detail">新加入選手のお知らせ</p> </div>
<div class="newsList__itemImage"> <img alt="PHOTO" src="https://cdn.www.ventforet.jp/images/p.jpg" /> </div> </a> </li></ul>"""

GNEWS_SANNICHI = """<rss><channel>
<item><title>ＶＦ甲府 外国人２選手が練習参加 - sannichi.co.jp</title><link>https://news.google.com/rss/articles/S1?oc=5</link>
<pubDate>Wed, 11 Nov 2026 07:41:00 GMT</pubDate><source url="https://www.sannichi.co.jp">sannichi.co.jp</source></item>
<item><title>今朝の気温（11日午前6時） - sannichi.co.jp</title><link>https://news.google.com/rss/articles/S2?oc=5</link>
<pubDate>Wed, 11 Nov 2026 07:00:00 GMT</pubDate><source url="https://www.sannichi.co.jp">sannichi.co.jp</source></item>
</channel></rss>"""

REDIRECT_PAGE = '<c-wiz><div data-n-a-sg="SIG" data-n-a-ts="1794406190"></div></c-wiz>'
REDIRECT_ANSWER = (
    ")]}'\n\n"
    '[["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://www.sannichi.co.jp/article/1?g\\\\u003dco\\",1]",null,null,null,"generic"]]'
)
ARTICLE = '<html><head><meta property="og:image" content="https://cdn.sannichi.co.jp/img/a.jpg"></head></html>'

HOCHI = """<ul><li class="article-list__item"> <a href="/articles/20261109-OHT1T51310.html" class="article-list__unit">
<img src="data:image/gif;base64,R0" data-src="https://hochi.news/images/a.jpg" alt="x">
<h3 class="article-list__title">板野友美 ルビーにときめき</h3> <time class="article-list__date">2026年11月09日 20:03</time> </a> </li>
<li class="article-list__item"> <a href="/articles/20261110-OHT1T51001.html" class="article-list__unit">
<img src="data:image/gif;base64,R0" data-src="https://hochi.news/images/b.jpg" alt="x">
<h3 class="article-list__title">【甲府】渋谷監督「前を向く」</h3> <time class="article-list__date">2026年11月10日 08:30</time> </a> </li></ul>"""

YOUTUBE = """<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<entry><yt:videoId>abc123</yt:videoId><title>ハイライト</title><published>2026-11-10T09:00:00+00:00</published></entry></feed>"""

NOTE = """<rss xmlns:note="https://note.com" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>仙台戦の感想</title><media:thumbnail>https://assets.st-note.com/t.jpg</media:thumbnail>
<note:creatorName>甲府サポ</note:creatorName><pubDate>Wed, 11 Nov 2026 19:42:10 +0900</pubDate>
<link>https://note.com/a/n/n1</link>
<description><![CDATA[<p>仙台戦を振り返る。</p><a href="https://note.com/a/n/n1">続きをみる</a>]]></description></item></channel></rss>"""

BLOG_RSS = """<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>データで見るJ</title>
<item><title>J2下位はなぜ勝てないのか</title><link>https://blog.example/kofu</link>
<pubDate>Wed, 11 Nov 2026 16:20:04 +0000</pubDate><description>短い要約</description>
<content:encoded><![CDATA[<p>甲府の失点を数える。</p>]]></content:encoded></item>
<item><title>札幌の6連勝</title><link>https://blog.example/sapporo</link>
<pubDate>Wed, 11 Nov 2026 10:00:00 +0000</pubDate><description>札幌の話</description></item></channel></rss>"""

BLOG_RDF = """<rdf:RDF xmlns="http://purl.org/rss/1.0/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>小瀬日記</title></channel>
<item><title>ヴァンフォーレの藤枝戦</title><link>https://diary.example/1</link><description>行ってきた</description>
<dc:date>2026-11-09T06:00:00+09:00</dc:date></item></rdf:RDF>"""
BLOG_ARTICLE = '<html><head><meta property="og:image" content="https://blog.example/img/kofu.jpg"></head></html>'

SUBJECT = """1794368995.dat<>移籍・レンタル・戦力外「ら」スレ Part17978 (461)
1793848769.dat<>ヴァンフォーレ甲府 ☆ 遂にJ1復帰!!1076 (246)
1794142270.dat<>移籍・レンタル・戦力外「ら」スレ Part17977 (1002)
1793440097.dat<>移籍・レンタル・戦力外「ら」スレ Part17969 (73)
1787762532.dat<>ジェフユナイテッド千葉レディース (215)
"""


def post_5ch(no, date, body):
    return (
        f'<div id="{no}" data-date="NG" data-userid="ID:x" data-id="{no}" class="clear post"><div class="post-header">'
        f'<span class="postid">{no}</span><input type="hidden" name="date" value="{date}">'
        f'<span class="date">{date}</span><span class="uid">ID:x</span></div>'
        f'<div class="post-content"> {body} </div></div>'
    )


THREAD = post_5ch(1, "2026/11/10(火) 11:14:29.72", "監督交代の噂 <br> 本当か？") + post_5ch(
    2, "2026/11/11(水) 09:00:00.00", '<a href="../1">&gt;&gt;1</a> <br> ないだろ'
)

CHO = """<a name="906571" id="906571"></a><article class="post"> <header class="post__header">
<span class="post__user-name" style="color:#ffff00;">青赤</span>
<span class="post__date">2026/11/11 22:24</span> <span class="post__model">iOS18.7</span>
<div class="post__post-no">No.906571</div> </header> <div class="post__body"> <div> </div>
<a href="./?anc=906569#anc" class="res-anchor">&gt;&gt;906569</a><div class="anchor-frame"></div>引退したんだ！ </div>
<footer class="post__footer"> <a href="write.php?replay=906571">返信</a> </footer> </article>"""

SCHEDULE = """<p>明治安田Ｊ２リーグの成績</p><p>3勝3分10敗（20位）</p><h2>日程・結果</h2>
<div>2026/11/8 (日)</div><div>第16節</div><div>15:00</div><div>KO</div><div>ベガルタ仙台</div><div>仙台</div>
<div>5</div><div>試合終了</div><div>1</div><div>ヴァンフォーレ甲府</div><div>甲府</div><div>ユアスタ</div>
<div>2026/11/14 (土)</div><div>第17節</div><div>藤枝ＭＹＦＣ</div><div>藤枝</div><div>14:00</div>
<div>ヴァンフォーレ甲府</div><div>甲府</div><div>藤枝サ</div><div>藤枝総合運動公園サッカー場</div>
<div>2026/11/21 (土)</div><div>第18節</div><div>ヴァンフォーレ甲府</div><div>甲府</div><div>14:00</div>
<div>ヴァンラーレ八戸</div><div>八戸</div><div>ＪＩＴス</div><div>ＪＩＴ　リサイクルインク　スタジアム</div>"""

PLAYERS = """<a class="o-table__player-name-link" href="/player/1658991/">後藤 陽翔</a>
<a class="o-table__player-name-link" href="/player/1632238/">東 ジョン</a>"""


class ParseNewsTest(unittest.TestCase):
    def test_gnews_strips_source_suffix_from_title(self):
        self.assertEqual(collect.parse_gnews(GNEWS)[0]["title"], "甲府がDF獲得へ")

    def test_gnews_source(self):
        self.assertEqual(collect.parse_gnews(GNEWS)[0]["source"], "スポーツ報知")

    def test_gnews_published_in_jst(self):
        self.assertEqual(collect.parse_gnews(GNEWS)[0]["published"], "2026-11-10T14:04:50+09:00")

    def test_gnews_names_sannichi(self):
        self.assertEqual(collect.parse_gnews(GNEWS_SANNICHI)[0]["source"], "山梨日日新聞")

    def test_official_url_is_absolute(self):
        self.assertEqual(collect.parse_official(OFFICIAL)[0]["url"], "https://www.ventforet.jp/news/other/525715")

    def test_official_title(self):
        self.assertEqual(collect.parse_official(OFFICIAL)[0]["title"], "秋田戦のお知らせ")

    def test_official_date_only_counts_as_end_of_day(self):
        self.assertEqual(collect.parse_official(OFFICIAL)[0]["published"], "2026-11-10T23:59:00+09:00")

    def test_official_placeholder_image_is_dropped(self):
        self.assertIsNone(collect.parse_official(OFFICIAL)[0]["image"])

    def test_official_image(self):
        self.assertEqual(collect.parse_official(OFFICIAL)[1]["image"], "https://cdn.www.ventforet.jp/images/p.jpg")

    def test_hochi_keeps_only_kofu_titles(self):
        self.assertEqual([i["title"] for i in collect.parse_hochi(HOCHI)], ["【甲府】渋谷監督「前を向く」"])

    def test_hochi_image_comes_from_lazy_attribute(self):
        self.assertEqual(collect.parse_hochi(HOCHI)[0]["image"], "https://hochi.news/images/b.jpg")

    def test_hochi_published(self):
        self.assertEqual(collect.parse_hochi(HOCHI)[0]["published"], "2026-11-10T08:30:00+09:00")

    def test_youtube_url(self):
        self.assertEqual(collect.parse_youtube(YOUTUBE)[0]["url"], "https://www.youtube.com/watch?v=abc123")

    def test_youtube_image(self):
        self.assertEqual(collect.parse_youtube(YOUTUBE)[0]["image"], "https://i.ytimg.com/vi/abc123/mqdefault.jpg")

    def test_note_author(self):
        self.assertEqual(collect.parse_note(NOTE)[0]["source"], "甲府サポ")

    def test_note_image(self):
        self.assertEqual(collect.parse_note(NOTE)[0]["image"], "https://assets.st-note.com/t.jpg")

    def test_note_excerpt_is_plain_text(self):
        self.assertEqual(collect.parse_note(NOTE)[0]["excerpt"], "仙台戦を振り返る。 続きをみる")

    def test_excerpt_is_capped(self):
        long = NOTE.replace("仙台戦を振り返る。", "あ" * 1000)
        self.assertEqual(len(collect.parse_note(long)[0]["excerpt"]), collect.EXCERPT)

    def test_blog_source_is_blog_title(self):
        self.assertEqual(collect.parse_blog(BLOG_RSS)[0]["source"], "データで見るJ")

    def test_blog_posts_not_mentioning_kofu_are_dropped(self):
        self.assertEqual([i["url"] for i in collect.parse_blog(BLOG_RSS)], ["https://blog.example/kofu"])

    def test_blog_excerpt_comes_from_full_content(self):
        self.assertEqual(collect.parse_blog(BLOG_RSS)[0]["excerpt"], "甲府の失点を数える。")

    def test_blog_published_in_jst(self):
        self.assertEqual(collect.parse_blog(BLOG_RSS)[0]["published"], "2026-11-12T01:20:04+09:00")

    def test_rdf_blog_published(self):
        self.assertEqual(collect.parse_blog(BLOG_RDF)[0]["published"], "2026-11-09T06:00:00+09:00")

    def test_rdf_blog_excerpt_falls_back_to_description(self):
        self.assertEqual(collect.parse_blog(BLOG_RDF)[0]["excerpt"], "行ってきた")


class GnewsRedirectTest(unittest.TestCase):
    def test_request_carries_article_id_and_signature(self):
        self.assertIn("SIG", collect.gnews_request(REDIRECT_PAGE, "S1"))

    def test_request_is_none_without_signature(self):
        self.assertIsNone(collect.gnews_request("<html></html>", "S1"))

    def test_answer_gives_article_url(self):
        self.assertEqual(collect.parse_gnews_answer(REDIRECT_ANSWER), "https://www.sannichi.co.jp/article/1?g=co")

    def test_og_image(self):
        self.assertEqual(collect.parse_og_image(ARTICLE), "https://cdn.sannichi.co.jp/img/a.jpg")

    def test_og_image_with_content_first(self):
        html = '<meta content="https://x/a.jpg" property="og:image">'
        self.assertEqual(collect.parse_og_image(html), "https://x/a.jpg")

    def test_site_default_og_image_is_ignored(self):
        html = '<meta property="og:image" content="https://www.ventforet.jp/asset/img/og-image.png">'
        self.assertIsNone(collect.parse_og_image(html))

    def test_page_without_og_image(self):
        self.assertIsNone(collect.parse_og_image("<html></html>"))


class ParseBoardsTest(unittest.TestCase):
    def test_subject_finds_kofu_thread(self):
        self.assertEqual(collect.parse_subject(SUBJECT)["kofu5ch"], ["1793848769"])

    def test_subject_takes_two_newest_ra_threads(self):
        self.assertEqual(collect.parse_subject(SUBJECT)["ra"], ["1794368995", "1794142270"])

    def test_5ch_text_joins_lines(self):
        self.assertEqual(collect.parse_5ch(THREAD, "1793848769")[0]["text"], "監督交代の噂\n本当か？")

    def test_5ch_anchor_stays_readable(self):
        self.assertEqual(collect.parse_5ch(THREAD, "1793848769")[1]["text"], ">>1\nないだろ")

    def test_5ch_published(self):
        self.assertEqual(collect.parse_5ch(THREAD, "1793848769")[0]["published"], "2026-11-10T11:14:29+09:00")

    def test_5ch_url_points_at_post(self):
        self.assertEqual(
            collect.parse_5ch(THREAD, "1793848769")[1]["url"],
            "https://kizuna.5ch.io/test/read.cgi/soccer/1793848769/2",
        )

    def test_cho_text(self):
        self.assertEqual(collect.parse_cho(CHO)[0]["text"], ">>906569 引退したんだ！")

    def test_cho_published(self):
        self.assertEqual(collect.parse_cho(CHO)[0]["published"], "2026-11-11T22:24:00+09:00")

    def test_cho_url(self):
        self.assertEqual(collect.parse_cho(CHO)[0]["url"], "https://bm.best-hit.tv/ventforet/?anc=906571#anc")


class SelectRaTest(unittest.TestCase):
    POSTS = [
        {"no": 1, "text": "浦和がFW獲得らしい"},
        {"no": 2, "text": "それより鹿島"},
        {"no": 3, "text": ">>2\n甲府のボランチ狙ってるって"},
        {"no": 4, "text": "後藤陽翔に J1 から話"},
        {"no": 5, "text": "関係ない話"},
    ]

    def test_keeps_keyword_hits_and_their_anchor_targets(self):
        picked = collect.select_ra(self.POSTS, ["甲府", "後藤陽翔"])
        self.assertEqual([p["no"] for p in picked], [2, 3, 4])


class ParseClubTest(unittest.TestCase):
    def test_record(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["record"], "3勝3分10敗")

    def test_rank(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["rank"], 20)

    def test_league(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["league"], "明治安田Ｊ２リーグ")

    def test_next_match_is_first_fixture_from_today(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["next"]["date"], "2026-11-14")

    def test_next_match_opponent_when_away(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["next"]["opponent"], "藤枝ＭＹＦＣ")

    def test_next_match_is_away(self):
        self.assertFalse(collect.parse_schedule(SCHEDULE, NOW)["next"]["home"])

    def test_next_match_kickoff(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["next"]["time"], "14:00")

    def test_next_match_venue(self):
        self.assertEqual(collect.parse_schedule(SCHEDULE, NOW)["next"]["venue"], "藤枝総合運動公園サッカー場")

    def test_next_match_opponent_when_home(self):
        later = datetime(2026, 11, 15, 6, 0, tzinfo=JST)
        self.assertEqual(collect.parse_schedule(SCHEDULE, later)["next"]["opponent"], "ヴァンラーレ八戸")

    def test_no_fixture_left(self):
        later = datetime(2026, 12, 1, 6, 0, tzinfo=JST)
        self.assertIsNone(collect.parse_schedule(SCHEDULE, later)["next"])

    def test_players_drop_space(self):
        self.assertEqual(collect.parse_players(PLAYERS), ["後藤陽翔", "東ジョン"])


class CollectTest(unittest.TestCase):
    def fetch(self, url, encoding="utf-8", data=None):
        pages = {
            "rss/articles": REDIRECT_PAGE,
            "batchexecute": REDIRECT_ANSWER,
            "sannichi.co.jp/article": ARTICLE,
            "sannichi.co.jp": GNEWS_SANNICHI,
            "news.google.com": GNEWS,
            "ventforet.jp": globals()["OFFICIAL"],
            "hochi": HOCHI,
            "youtube": YOUTUBE,
            "note.com": NOTE,
            "blog.example/feed": BLOG_RSS,
            "blog.example": BLOG_ARTICLE,
            "subject.txt": SUBJECT,
            "read.cgi": THREAD,
            "best-hit": CHO,
            "/day/": SCHEDULE,
            "/player/": PLAYERS,
        }
        for key, body in pages.items():
            if key in url:
                if key in self.broken:
                    raise OSError("boom")
                return body
        raise AssertionError(url)

    def setUp(self):
        self.broken = set()
        feeds = mock.patch.object(collect, "BLOG_FEEDS", ["https://blog.example/feed"])
        feeds.start()
        self.addCleanup(feeds.stop)

    def run_collect(self, now=NOW, since=None):
        return collect.collect(now, self.fetch, sleep=lambda s: None, since=since)

    def reads(self, **kwargs):
        return {r["title"]: r for r in self.run_collect(**kwargs)["reads"]}

    def test_news_older_than_window_is_dropped(self):
        titles = [n["title"] for n in self.run_collect()["news"]]
        self.assertNotIn("甲府がDF獲得へ", titles)

    def test_news_inside_window_is_kept(self):
        titles = [n["title"] for n in self.run_collect()["news"]]
        self.assertIn("ＶＦ甲府 外国人２選手が練習参加", titles)

    def test_sannichi_items_about_other_topics_are_dropped(self):
        titles = [n["title"] for n in self.run_collect()["news"]]
        self.assertNotIn("今朝の気温（11日午前6時）", titles)

    def sannichi_item(self):
        return next(n for n in self.run_collect()["news"] if n["source"] == "山梨日日新聞")

    def test_google_link_is_replaced_by_article_url(self):
        self.assertEqual(self.sannichi_item()["url"], "https://www.sannichi.co.jp/article/1?g=co")

    def test_google_item_gets_article_image(self):
        self.assertEqual(self.sannichi_item()["image"], "https://cdn.sannichi.co.jp/img/a.jpg")

    def test_google_link_is_kept_when_it_cannot_be_resolved(self):
        self.broken = {"batchexecute"}
        self.assertEqual(self.sannichi_item()["url"], "https://news.google.com/rss/articles/S1?oc=5")

    def test_resolved_url_is_kept_when_article_cannot_be_read(self):
        self.broken = {"sannichi.co.jp/article"}
        self.assertEqual(self.sannichi_item()["url"], "https://www.sannichi.co.jp/article/1?g=co")

    def test_unresolved_link_is_not_a_source_failure(self):
        self.broken = {"batchexecute"}
        self.assertEqual(self.run_collect()["failures"], [])

    def test_same_article_from_two_sources_appears_once(self):
        items = [{"url": "https://a", "image": None, "n": 1}, {"url": "https://a", "image": "https://i", "n": 2}]
        self.assertEqual([i["n"] for i in collect.unique(items)], [2])

    def test_news_is_newest_first(self):
        published = [n["published"] for n in self.run_collect()["news"]]
        self.assertEqual(published, sorted(published, reverse=True))

    def test_board_posts_inside_window(self):
        self.assertEqual([p["no"] for p in self.run_collect()["boards"]["kofu5ch"]], [2])

    def test_cho_posts(self):
        self.assertEqual([p["no"] for p in self.run_collect()["boards"]["cho"]], [906571])

    def board(self, since, name="kofu5ch"):
        return [p["no"] for p in self.run_collect(since=since)["boards"][name]]

    def test_board_posts_before_previous_issue_are_dropped(self):
        self.assertEqual(self.board("2026-11-11T12:00:00+09:00"), [])

    def test_board_posts_since_previous_issue_reach_past_the_window(self):
        self.assertEqual(self.board("2026-11-10T06:00:00+09:00"), [2, 1])

    def test_previous_issue_older_than_three_days_is_ignored(self):
        self.assertEqual(self.board("2026-11-08T06:00:00+09:00"), [2])

    def test_post_in_the_minute_of_previous_issue_is_kept(self):
        self.assertEqual(self.board("2026-11-11T22:24:30+09:00", "cho"), [906571])

    def test_reads_include_note(self):
        self.assertIn("仙台戦の感想", self.reads())

    def test_reads_include_blog_post(self):
        self.assertIn("J2下位はなぜ勝てないのか", self.reads())

    def test_read_older_than_news_window_is_kept(self):
        self.assertIn("仙台戦の感想", self.reads(now=NOW + timedelta(days=3)))

    def test_read_older_than_a_week_is_dropped(self):
        self.assertEqual(self.reads(now=NOW + timedelta(days=8)), {})

    def test_blog_post_gets_article_image(self):
        self.assertEqual(self.reads()["J2下位はなぜ勝てないのか"]["image"], "https://blog.example/img/kofu.jpg")

    def test_broken_blog_feed_is_reported_by_host(self):
        self.broken = {"blog.example/feed"}
        self.assertEqual(self.run_collect()["failures"], ["blog.example"])

    def test_club(self):
        self.assertEqual(self.run_collect()["club"]["rank"], 20)

    def test_broken_source_is_reported(self):
        self.broken = {"ventforet.jp"}
        self.assertEqual(self.run_collect()["failures"], ["クラブ公式"])

    def test_broken_source_does_not_stop_others(self):
        self.broken = {"ventforet.jp"}
        self.assertTrue(self.run_collect()["boards"]["cho"])

    def test_list_page_without_items_is_reported(self):
        global OFFICIAL
        original, OFFICIAL = OFFICIAL, "<html>blocked</html>"
        self.addCleanup(lambda: globals().update(OFFICIAL=original))
        self.assertEqual(self.run_collect()["failures"], ["クラブ公式"])

    def test_broken_subject_reports_5ch(self):
        self.broken = {"subject.txt"}
        self.assertEqual(self.run_collect()["failures"], ["5ch"])


if __name__ == "__main__":
    unittest.main()
