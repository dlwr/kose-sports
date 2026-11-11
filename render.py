from datetime import date
from html import escape
from pathlib import Path

TEMPLATE = (Path(__file__).parent / "template.html").read_text()
WEEKDAYS = "月火水木金土日"
BOARD_LINKS = [
    ("5ch 国内サッカー板", "https://kizuna.5ch.io/soccer/"),
    ("超ヴァンフォーレ甲府掲示板", "https://bm.best-hit.tv/ventforet/"),
]


def safe(url):
    return url if url and url.startswith(("https://", "http://")) else None


def anchor(url, label):
    return f'<a href="{escape(url)}">{escape(label)}</a>' if safe(url) else ""


def img(url):
    if not safe(url):
        return ""
    return f'<img src="{escape(url)}" alt="" referrerpolicy="no-referrer" loading="lazy" onerror="this.remove()">'


def paragraphs(body):
    return "".join(f"<p>{escape(p.strip())}</p>" for p in body.split("\n") if p.strip())


def sources(links):
    rows = [
        f"<li>{a}{'' if l['title'].startswith(l['source']) else f' <small>{escape(l["source"])}</small>'}</li>"
        for l in links
        if (a := anchor(l["url"], l["title"]))
    ]
    return f'<ul class="src">{"".join(rows)}</ul>' if rows else ""


def section(title, body, kind=""):
    if not body:
        return ""
    return f'<h2 class="sec {kind}"><span>{title}</span></h2>{body}'


def masthead(issue):
    d = date.fromisoformat(issue["date"])
    club, parts = issue["club"], []
    if n := club.get("next"):
        days = (date.fromisoformat(n["date"]) - d).days
        left = "本日キックオフ" if days == 0 else f"あと{days}日"
        when = f"{int(n['date'][5:7])}/{int(n['date'][8:])} {n['time']}".strip()
        parts.append(
            f"<span>次戦 {escape(n['round'])} {escape(n['opponent'])}戦（{'H' if n['home'] else 'A'}）{when} <b>{left}</b></span>"
        )
    if club.get("rank"):
        parts.append(f"<span>{escape(club['league'])} <b>{club['rank']}位</b> {escape(club['record'])}</span>")
    score = f'<div class="score"><div class="score-in">{"".join(parts)}</div></div>' if parts else ""
    return (
        '<header><div class="mast"><div class="mast-in"><div><p class="mast-sub">ヴァンフォーレ甲府専門</p>'
        '<h1><a href="./">小瀬スポーツ</a></h1></div>'
        f'<p class="mast-date">{d.year}年{d.month}月{d.day}日（{WEEKDAYS[d.weekday()]}）</p></div></div>{score}</header>'
    )


def top(t):
    if not t:
        return ""
    paras = [p for p in t["body"].split("\n") if p.strip()]
    picture = img(t["image"])
    side = picture or (f"<p>{escape(paras[0].strip())}</p>" if paras else "")
    rest = paras if picture else paras[1:]
    return (
        f'<article class="top"><div class="top-head"><h2>{escape(t["headline"])}</h2>'
        f'<div class="top-side">{side}</div></div>'
        f'<div class="body">{paragraphs(chr(10).join(rest))}</div>{sources(t["links"])}</article>'
    )


def brief(t):
    thumb = f'<div class="thumb">{picture}</div>' if (picture := img(t["image"])) else ""
    return (
        f'<article class="item"><h3>{escape(t["headline"])}</h3>{thumb}'
        f'<div class="body">{paragraphs(t["body"])}</div>{sources(t["links"])}</article>'
    )


def rumor(t):
    c = t["confidence"]
    cells = "".join(f'<i class="{"on" if i < c else ""}"></i>' for i in range(5))
    flag = "" if c >= 5 else '<span class="flag">未確認</span>'
    return (
        f'<article class="item"><p class="gauge"><span class="meter" aria-hidden="true">{cells}</span>'
        f"<span>確度 {c}/5</span>{flag}</p><h3>{escape(t['headline'])}</h3>"
        f'<p class="origin">出どころ: {escape(t["origin"])}</p>'
        f'<div class="body">{paragraphs(t["body"])}</div>{sources(t["links"])}</article>'
    )


def board(t):
    return (
        f'<article class="item"><p class="kicker">{escape(t["board"])}</p><h3>{escape(t["headline"])}</h3>'
        f'<div class="body">{paragraphs(t["body"])}</div>{sources(t["links"])}</article>'
    )


def media(i):
    link = anchor(i["url"], i["title"])
    if not link:
        return ""
    return f'<div class="media">{img(i["image"])}<div>{link}<small>{escape(i["source"])}</small></div></div>'


def many(fn, items):
    return "".join(map(fn, items))


def footer(issue, prev, next):
    notes = []
    if issue["digest"]["links_only"]:
        notes.append("本日は要約を作れなかったため、見出しの一覧だけでお届けします。")
    if issue["failures"]:
        notes.append(f"本日は {'、'.join(map(escape, issue['failures']))} を取得できませんでした。")
    older = f'<a href="{prev}.html">← 前日の号</a>' if prev else "<span></span>"
    newer = f'<a href="{next}.html">翌日の号 →</a>' if next else "<span></span>"
    boards = " ／ ".join(anchor(url, label) for label, url in BOARD_LINKS)
    return (
        f'<footer class="foot"><nav class="pager">{older}{newer}</nav>'
        + "".join(f"<p>{n}</p>" for n in notes)
        + f"<p>掲示板: {boards}</p>"
        "<p>小瀬スポーツは個人が作る非公式の読み物です。記事と写真の権利は各配信元にあります。"
        "「噂」「掲示板」には裏の取れていない話が含まれます。</p></footer>"
    )


def render_issue(issue, prev=None, next=None):
    g = issue["digest"]
    if g["closed"]:
        main = '<div class="closed"><h2>本日休刊</h2><p>甲府に関する新しいニュースはありませんでした。</p></div>'
    else:
        news = section("ニュース", many(brief, g["briefs"]) or (many(media, issue["news"]) if g["links_only"] else ""))
        rumors = section("噂", many(rumor, g["rumors"]), "is-rumor")
        ordered = [news, rumors] if issue["club"].get("next") else [rumors, news]
        main = top(g["top"]) + "".join(ordered) + section("掲示板", many(board, g["boards"]), "is-board")
    main += section("動画", many(media, issue["videos"])) + section("サポーターの note", many(media, issue["notes"]))
    body = f'{masthead(issue)}<main class="sheet">{main}{footer(issue, prev, next)}</main>'
    title = f"小瀬スポーツ {issue['date']}"
    return TEMPLATE.replace("<!--title-->", title).replace("<!--body-->", body)
