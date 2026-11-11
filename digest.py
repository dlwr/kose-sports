import json
import sys

MODEL = "claude-sonnet-5-5"
BOARDS = {"kofu5ch": ("K", "5ch 甲府スレ"), "ra": ("R", "らスレ"), "cho": ("C", "超掲示板")}

SYSTEM = """あなたはヴァンフォーレ甲府専門の架空のスポーツ紙「小瀬スポーツ」の編集長です。渡された素材だけを使って、今日の紙面を作ります。

紙面の構成:
- top: 今日いちばん大きな話題を1本。見出しは短く強く。本文は2〜4段落（段落は改行で区切る）。
- briefs: それ以外のニュース。同じ出来事を複数の媒体が報じていたら1本に束ねる。本文は1〜3文。
- rumors: 移籍、契約、監督や強化部の人事、起用や戦術、クラブ経営、スポンサー、練習の目撃談など、サッカーに関わる未確認の話。真偽不明でも拾う。origin に出どころを書く。
- boards: 「5ch 甲府スレ」と「超掲示板」それぞれについて、いま何が話題で、どんな空気かを1本ずつ。素材がない掲示板は書かない。

確度（rumors の confidence）:
5 = クラブ公式発表 / 4 = 地元紙・全国紙が報道 / 3 = 複数の媒体や記者が示唆 / 2 = 掲示板の複数の書き込みが言及 / 1 = 単発の書き込み

決まり:
- 各項目の sources には、根拠にした素材の ID（N1、K3 など）を必ず入れる。素材にないことは書かない。推測で補わない。
- 文体はスポーツ紙の見出し調。甲府に身びいきしてよいが、他クラブや個人を貶さない。
- 掲示板の書き込みは原文を引用せず、要約する。
- 実名の個人についての私生活（交際・家族）、病気、犯罪の疑い、単なる罵倒は載せない。クラブが公式に発表したけがや慶事は載せてよい。
- ヴァンフォーレ甲府と関係のない素材（他競技、同名の地名のニュース、他クラブが主題で甲府が名前だけ出る記事）は使わない。
- 確定したニュースを rumors に入れない。未確認の話を top や briefs に入れない。
- 載せる話題がなければ、その欄は空にする。top に値する話題がなければ top の sources を空にする。"""

TOPIC = {
    "headline": {"type": "string"},
    "body": {"type": "string"},
    "sources": {"type": "array", "items": {"type": "string"}},
}


def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


SCHEMA = obj(
    top=obj(**TOPIC),
    briefs={"type": "array", "items": obj(**TOPIC)},
    rumors={
        "type": "array",
        "items": obj(**TOPIC, origin={"type": "string"}, confidence={"type": "integer", "enum": [1, 2, 3, 4, 5]}),
    },
    boards={
        "type": "array",
        "items": obj(**TOPIC, board={"type": "string", "enum": ["5ch 甲府スレ", "超掲示板"]}),
    },
)


def build_prompt(collected, date):
    index, lines = {}, []
    club = collected["club"]
    lines.append(f"発行日: {date}")
    if club.get("record"):
        lines.append(f"成績: {club['league']} {club['record']}（{club['rank']}位）")
    if club.get("next"):
        n = club["next"]
        lines.append(f"次の試合: {n['date']} {n['time']} {n['round']} {n['opponent']}戦（{'ホーム' if n['home'] else 'アウェイ'}）")
    lines.append("所属選手: " + "、".join(club.get("players", [])))

    lines.append("\n## ニュース")
    for i, n in enumerate(collected["news"], 1):
        index[f"N{i}"] = {"title": n["title"], "url": n["url"], "source": n["source"], "image": n["image"]}
        lines.append(f"[N{i}] {n['title']}（{n['source']} {n['published'][:16]}）")

    for name, (prefix, label) in BOARDS.items():
        lines.append(f"\n## {label}")
        for i, p in enumerate(collected["boards"][name], 1):
            index[f"{prefix}{i}"] = {"title": f"{label} {p['no']}", "url": p["url"], "source": label, "image": None}
            lines.append(f"[{prefix}{i}] " + p["text"].replace("\n", " / "))
    return "\n".join(lines), index


def validate(raw, index):
    def clean(topic):
        ids = [i for i in dict.fromkeys(topic["sources"]) if i in index]
        if not ids:
            return None
        sources = [index[i] for i in ids]
        return {
            **{k: v for k, v in topic.items() if k != "sources"},
            "links": [{k: s[k] for k in ("title", "url", "source")} for s in sources],
            "image": next((s["image"] for s in sources if s["image"]), None),
        }

    def clean_all(topics):
        return [t for t in map(clean, topics) if t]

    return {
        "closed": False,
        "links_only": False,
        "top": clean(raw["top"]),
        "briefs": clean_all(raw["briefs"]),
        "rumors": sorted(clean_all(raw["rumors"]), key=lambda r: -r["confidence"]),
        "boards": clean_all(raw["boards"]),
    }


def call_claude(system, user):
    import anthropic

    response = anthropic.Anthropic().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"stop_reason={response.stop_reason}")
    print(f"usage: {response.usage.input_tokens} in / {response.usage.output_tokens} out", file=sys.stderr)
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def make_digest(collected, date, llm=call_claude):
    empty = {"closed": False, "links_only": False, "top": None, "briefs": [], "rumors": [], "boards": []}
    if not collected["news"] and not any(collected["boards"].values()):
        return {**empty, "closed": True}
    user, index = build_prompt(collected, date)
    try:
        return validate(llm(SYSTEM, user), index)
    except Exception as e:
        print(f"LLM failed: {e!r}", file=sys.stderr)
        return {**empty, "links_only": True}
