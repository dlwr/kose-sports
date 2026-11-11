import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote

JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
WINDOW = timedelta(hours=26)
ATTEMPTS = 3
CHO_MAX_PAGES = 60
KOFU = re.compile("甲府|ヴァンフォーレ|ＶＦ")
CLUB = "ヴァンフォーレ甲府"

GNEWS_URL = "https://news.google.com/rss/search?q=" + quote(CLUB) + "+when:2d&hl=ja&gl=JP&ceid=JP:ja"
OFFICIAL_URL = "https://www.ventforet.jp/news/all"
SANNICHI_URL = "https://www.sannichi.co.jp/news/vfk"
HOCHI_URL = "https://hochi.news/search?q=" + quote("甲府")
YOUTUBE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCtdA3-T8-1wLltOxVGuXyDg"
NOTE_URL = "https://note.com/hashtag/" + quote(CLUB) + "/rss"
BBS = "https://kizuna.5ch.io"
SUBJECT_URL = BBS + "/soccer/subject.txt"
THREAD_URL = BBS + "/test/read.cgi/soccer/{}/"
CHO_URL = "https://bm.best-hit.tv/ventforet/"
SCHEDULE_URL = "https://www.jleague.jp/club/kofu/day/"
PLAYERS_URL = "https://www.jleague.jp/club/kofu/player/"

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "note": "https://note.com",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch(url, encoding="utf-8", urlopen=urllib.request.urlopen, sleep=time.sleep):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for left in reversed(range(ATTEMPTS)):
        try:
            with urlopen(req, timeout=30) as res:
                return res.read().decode(encoding, "replace")
        except OSError:
            if not left:
                raise
            sleep(2)


def text_of(html, sep=" "):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", sep, html))).strip()


def iso(*parts):
    return datetime(*map(int, parts), tzinfo=JST).isoformat()


def item(source, title, url, published, image=None):
    return {"source": source, "title": title, "url": url, "published": published, "image": image}


def parse_gnews(xml):
    items = []
    for e in ET.fromstring(xml).iter("item"):
        source = e.findtext("source") or "Google ニュース"
        title = e.findtext("title").removesuffix(f" - {source}")
        published = parsedate_to_datetime(e.findtext("pubDate")).astimezone(JST).isoformat()
        items.append(item(source, title, e.findtext("link"), published))
    return items


def parse_official(html):
    items = []
    for href, body in re.findall(r'<a class="newsList__item" href="([^"]+)">(.*?)</a>', html, re.S):
        day = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", body)
        title = re.search(r'top-news__information__detail">(.*?)</p>', body, re.S)
        img = re.search(r'<img[^>]*src="([^"]+)"', body)
        image = img.group(1) if img and "notfound" not in img.group(1) else None
        items.append(
            item("クラブ公式", text_of(title.group(1)), "https://www.ventforet.jp" + href, iso(*day.groups(), 23, 59), image)
        )
    return items


def parse_sannichi(html):
    pattern = (
        r'<dt>\s*<a href="(/article/(\d{4})/[^"]+)">(.*?)</a>\s*'
        r'<span class="date">\((\d+)/(\d+) (\d+):(\d+)\)</span>.*?</dt>\s*<dd>(.*?)</dd>'
    )
    items = []
    for href, year, title, mo, d, h, mi, dd in re.findall(pattern, html, re.S):
        img = re.search(r"<img src=[\"']?([^\s\"'>]+)", dd)
        items.append(
            item(
                "山梨日日新聞",
                text_of(title),
                "https://www.sannichi.co.jp" + href,
                iso(year, mo, d, h, mi),
                img and img.group(1),
            )
        )
    return items


def parse_hochi(html):
    items = []
    for body in html.split('<li class="article-list__item">')[1:]:
        title = text_of(re.search(r'article-list__title">(.*?)</h3>', body, re.S).group(1))
        if not KOFU.search(title):
            continue
        href = re.search(r'href="([^"]+)"', body).group(1)
        when = re.search(r"(\d{4})年(\d{2})月(\d{2})日 (\d{2}):(\d{2})", body)
        img = re.search(r'data-src="([^"]+)"', body)
        items.append(item("スポーツ報知", title, "https://hochi.news" + href, iso(*when.groups()), img and img.group(1)))
    return items


def parse_youtube(xml):
    items = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        published = datetime.fromisoformat(e.findtext("a:published", namespaces=NS)).astimezone(JST).isoformat()
        items.append(
            item(
                "公式 YouTube",
                e.findtext("a:title", namespaces=NS),
                f"https://www.youtube.com/watch?v={vid}",
                published,
                f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            )
        )
    return items


def parse_note(xml):
    return [
        item(
            e.findtext("note:creatorName", namespaces=NS) or "note",
            e.findtext("title"),
            e.findtext("link"),
            parsedate_to_datetime(e.findtext("pubDate")).astimezone(JST).isoformat(),
            e.findtext("media:thumbnail", namespaces=NS),
        )
        for e in ET.fromstring(xml).iter("item")
    ]


def parse_subject(txt):
    kofu, ra = [], []
    for line in txt.splitlines():
        key, _, title = line.partition(".dat<>")
        if title.startswith(CLUB):
            kofu.append(key)
        part = re.match(r"移籍・レンタル・戦力外「ら」スレ Part(\d+)", title)
        if part:
            ra.append((int(part.group(1)), key))
    return {"kofu5ch": sorted(kofu, reverse=True)[:1], "ra": [k for _, k in sorted(ra, reverse=True)[:2]]}


def parse_5ch(html, key):
    pattern = (
        r'<div id="(\d+)"[^>]*class="clear post">.*?<span class="date">'
        r"(\d+)/(\d+)/(\d+)\(.\) (\d+):(\d+):(\d+)[^<]*</span>.*?"
        r'<div class="post-content">(.*?)</div></div>'
    )
    posts = []
    for no, y, mo, d, h, mi, s, body in re.findall(pattern, html, re.S):
        lines = [text_of(line, "") for line in re.split(r"<br\s*/?>", body)]
        posts.append(
            {
                "no": int(no),
                "published": iso(y, mo, d, h, mi, s),
                "text": "\n".join(line for line in lines if line),
                "url": THREAD_URL.format(key) + no,
            }
        )
    return posts


def parse_cho(html):
    posts = []
    for body in re.findall(r'<article class="post">(.*?)</article>', html, re.S):
        when = re.search(r'post__date">(\d+)/(\d+)/(\d+) (\d+):(\d+)', body)
        no = re.search(r"No\.(\d+)", body).group(1)
        content = re.search(r'<div class="post__body">(.*?)<footer', body, re.S).group(1)
        posts.append(
            {"no": int(no), "published": iso(*when.groups()), "text": text_of(content), "url": f"{CHO_URL}?anc={no}#anc"}
        )
    return posts


def select_ra(posts, keywords):
    hits = [p for p in posts if any(k in p["text"] for k in keywords)]
    wanted = {p["no"] for p in hits} | {int(n) for p in hits for n in re.findall(r">>(\d+)", p["text"])}
    return [p for p in posts if p["no"] in wanted]


def parse_schedule(html, now):
    html = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", html, flags=re.S)
    tokens = [t for t in (unescape(s).strip() for s in re.split(r"<[^>]+>", html)) if t]
    joined = "|".join(tokens)
    record = re.search(r"(\d+勝\d+分\d+敗)（(\d+)位）", joined)
    league = re.search(r"\|([^|]+)の成績\|", "|" + joined)
    is_time = re.compile(r"\d{1,2}:\d{2}$").match
    fixtures = []
    for i, tok in enumerate(tokens):
        day = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2}) \(.\)$", tok)
        rest = tokens[i + 1 : i + 9]
        # 試合前は「節|ホーム|略称|時刻|アウェイ|略称|会場略称|会場」、試合後は節の直後が時刻になる
        if not day or len(rest) < 8 or is_time(rest[1]):
            continue
        home = rest[1] == CLUB
        fixtures.append(
            {
                "date": "{:04d}-{:02d}-{:02d}".format(*map(int, day.groups())),
                "round": rest[0],
                "time": rest[3] if is_time(rest[3]) else "",
                "opponent": rest[4] if home else rest[1],
                "home": home,
                "venue": rest[7],
            }
        )
    today = now.astimezone(JST).strftime("%Y-%m-%d")
    return {
        "record": record and record.group(1),
        "rank": record and int(record.group(2)),
        "league": league and league.group(1),
        "next": next((f for f in fixtures if f["date"] >= today), None),
    }


def parse_players(html):
    return [n.replace(" ", "") for n in re.findall(r'o-table__player-name-link"[^>]*>([^<]+)<', html)]


def collect(now, fetch=fetch, sleep=time.sleep):
    cutoff = (now - WINDOW).isoformat()
    failures = []

    def recent(items):
        return sorted((i for i in items if i["published"] >= cutoff), key=lambda i: i["published"], reverse=True)

    def attempt(label, fn, default):
        try:
            return fn()
        except Exception as e:
            failures.append(label)
            print(f"skip {label}: {e!r}", file=sys.stderr)
            return default

    def listing(url, parser):
        html = fetch(url)
        items = parser(html)
        if not items:
            raise ValueError(f"no items in {len(html)} chars: {html[:200]!r}")
        return items

    news = attempt("Google ニュース", lambda: parse_gnews(fetch(GNEWS_URL)), [])
    news += attempt("クラブ公式", lambda: listing(OFFICIAL_URL, parse_official), [])
    news += attempt("山梨日日新聞", lambda: listing(SANNICHI_URL, parse_sannichi), [])
    news += attempt("スポーツ報知", lambda: parse_hochi(fetch(HOCHI_URL)), [])
    videos = attempt("YouTube", lambda: parse_youtube(fetch(YOUTUBE_URL)), [])
    notes = attempt("note", lambda: parse_note(fetch(NOTE_URL)), [])

    def club():
        return {**parse_schedule(fetch(SCHEDULE_URL), now), "players": parse_players(fetch(PLAYERS_URL))}

    club = attempt("Jリーグ公式", club, {"record": None, "rank": None, "league": None, "next": None, "players": []})

    def five_ch():
        keys = parse_subject(fetch(SUBJECT_URL, "cp932"))
        thread = lambda key: parse_5ch(fetch(THREAD_URL.format(key), "cp932"), key)
        keywords = ["甲府", "ヴァンフォーレ", *club["players"]]
        return {
            "kofu5ch": [p for key in keys["kofu5ch"] for p in thread(key)],
            "ra": [p for key in keys["ra"] for p in select_ra(thread(key), keywords)],
        }

    def cho():
        posts = {}
        for page in range(1, CHO_MAX_PAGES + 1):
            found = parse_cho(fetch(f"{CHO_URL}?page={page}", "cp932"))
            fresh = [p for p in found if p["no"] not in posts]
            posts.update((p["no"], p) for p in fresh)
            if not fresh or any(p["published"] < cutoff for p in found):
                break
            sleep(1)
        return list(posts.values())

    boards = attempt("5ch", five_ch, {"kofu5ch": [], "ra": []})
    boards["cho"] = attempt("超掲示板", cho, [])

    return {
        "news": recent(news),
        "videos": recent(videos),
        "notes": recent(notes),
        "boards": {name: recent(posts) for name, posts in boards.items()},
        "club": club,
        "failures": failures,
    }
