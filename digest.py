import json
import sys

MODEL = "claude-sonnet-5-5"
MAX_LINKS = 5
MAX_READS = 2
BOARDS = {"kofu5ch": ("K", "5ch 甲府スレ"), "ra": ("R", "らスレ"), "cho": ("C", "超掲示板")}

SYSTEM = """あなたはヴァンフォーレ甲府専門の架空のスポーツ紙「小瀬スポーツ」の編集長です。渡された素材だけを使って、今日の紙面を作ります。

紙面の構成:
- top: 一面を1本。「写真あり」の素材を根拠にできる話題から選ぶ。候補が複数あれば、(1) 試合・選手・チームのニュース、(2) イベント告知・グッズ・募集などのお知らせ、(3) 読み物、の順に優先する。写真のある候補が一つもない日だけ、写真のないニュースからいちばん大きな話題を選ぶ。見出しは短く強く。本文は2〜4段落（段落は改行で区切る）。sources の先頭には写真のある素材を置く。
- second: 準一面。一面にしなかった、写真のない大きなニュース（試合結果、加入・退団、監督人事、クラブの重要な発表、地元紙の独自の報道）があるときだけ1本。本文は1〜2段落。なければ sources を空にする。
- briefs: それ以外のニュース。同じ出来事を複数の媒体が報じていたら1本に束ねる。本文は1〜3文。
- rumors: 移籍、契約、監督や強化部の人事、起用や戦術、クラブ経営、スポンサー、練習の目撃談など、サッカーに関わる未確認の話。真偽不明でも拾う。origin に出どころを書く。
- boards: 「5ch 甲府スレ」と「超掲示板」それぞれについて、いま何が話題で、どんな空気かを1本ずつ。前の号から何が変わったかを軸に書き、変化が乏しければ短くまとめる。素材がない掲示板は書かない。
- reads: サポーターのブログや note の紹介。「読み物」の素材から甲府が主題のものを選び、何をどんな切り口で書いているかを1〜2文で紹介する。見出しは自分で付ける。基本は1本。載せる価値のある候補が4本以上残っていれば2本。なければ空にする。
- editorial: 編集後記。編集長のぼやきを2〜3文。今日の紙面に載せた話だけを題材にし、新しい事実を持ち込まない。

読み物の選び方:
- 鮮度が落ちやすいもの（次の試合の展望、直近の試合の観戦記）を先に使う。すでに終わった試合の展望は選ばない。
- 今日の紙面の話題と関係が深いもの、写真のあるものを優先する。
- 既報の号で紹介した書き手を続けて選ばない。
- 相手クラブのサポーターが書いた記事でも、甲府が主題なら選んでよい。
- 読み物を一面にするときは書き手の名前を出し、「〜と分析している」のように書き手の見方として紹介する。抜粋にないことは書かない。一面にした読み物は reads に重ねて載せず、その日の reads は1本までにする。
- 読み物は書き手個人の見方なので、ニュースや噂の根拠にしない。

既報の扱い:
- 「既報」は直近の号に載せた内容。既報にある話題をもう一度載せてよいのは、既報にない新しい事実が出た、確度が変わった、公式発表や報道で確定または否定された、のいずれかのときだけ。そのときは新しく分かったことから書き始め、既報の内容は一言で済ませる。
- 同じ話への賛否や感想が増えただけなら rumors に載せず、boards の空気として触れるにとどめる。
- 既報と同じ出来事を別の媒体が後追いしただけのニュースは載せない。

確度（rumors の confidence）:
5 = クラブ公式発表 / 4 = 地元紙・全国紙が報道 / 3 = 複数の媒体や記者が示唆 / 2 = 掲示板の複数の書き込みが言及 / 1 = 単発の書き込み

決まり:
- 各項目の sources には、根拠にした素材の ID（N1、K3 など）を必ず入れる。素材にないことは書かない。推測で補わない。sources は根拠として重要な順に5件まで。
- top の根拠にはニュースか読み物の素材を、second と briefs の根拠にはニュースの素材を、必ず1つ含める。掲示板の書き込みだけが根拠の話は rumors か boards に書く。
- 読者に向けた新聞記事として書く。「素材」「渡された情報」「既報」「記載がない」や ID など、この指示や入力そのものに触れる言葉を見出しや本文に出さない。分からないことは「クラブからの発表はない」「詳細は明らかになっていない」のように書く。
- 文体はスポーツ紙の見出し調。明るい話題や軽い話題の見出しは、駄洒落・語呂合わせ・大げさな言い回しで思い切り攻める。敗戦、けが、去就など重い話題の見出しは抑える。どちらも事実を足したり変えたりしない。本文は事実だけを書き、冗談を混ぜない。
- 笑いの対象にしてよいのは、チームの順位や状況、サポーター、編集部自身だけ。選手・監督・フロントの個人や他クラブを笑いものにしない。甲府に身びいきしてよいが、他クラブや個人を貶さない。
- 掲示板の書き込みや読み物は原文を引用せず、要約する。
- 実名の個人についての私生活（交際・家族）、病気、犯罪の疑い、単なる罵倒は載せない。クラブが公式に発表したけがや慶事は載せてよい。
- ヴァンフォーレ甲府と関係のない素材（他競技、同名の地名のニュース、他クラブが主題で甲府が名前だけ出る記事）は使わない。
- 確定したニュースを rumors に入れない。未確認の話を top や second、briefs に入れない。
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
    second=obj(**TOPIC),
    briefs={"type": "array", "items": obj(**TOPIC)},
    rumors={
        "type": "array",
        "items": obj(**TOPIC, origin={"type": "string"}, confidence={"type": "integer", "enum": [1, 2, 3, 4, 5]}),
    },
    boards={
        "type": "array",
        "items": obj(**TOPIC, board={"type": "string", "enum": ["5ch 甲府スレ", "超掲示板"]}),
    },
    reads={"type": "array", "items": obj(**TOPIC)},
    editorial={"type": "string"},
)
EMPTY = {
    "closed": False,
    "links_only": False,
    "top": None,
    "second": None,
    "briefs": [],
    "rumors": [],
    "boards": [],
    "reads": [],
    "editorial": "",
}


def reported(issue):
    g = issue["digest"]
    rows = [("一面", g.get("top")), ("準一面", g.get("second"))]
    rows += [("ニュース", t) for t in g.get("briefs", [])]
    rows += [(f"噂（確度{t['confidence']}）", t) for t in g.get("rumors", [])]
    rows += [(f"掲示板（{t['board']}）", t) for t in g.get("boards", [])]
    rows += [(f"読み物（{t['links'][0]['source']}）", t) for t in g.get("reads", [])]
    lines = [f"{label}: {t['headline']} ／ {' '.join(t['body'].split())}" for label, t in rows if t]
    return [f"### {issue['date']} 号", *lines]


def build_prompt(collected, date, earlier=()):
    index, lines = {}, []
    club = collected["club"]
    lines.append(f"発行日: {date}")
    if club.get("record"):
        lines.append(f"成績: {club['league']} {club['record']}（{club['rank']}位）")
    if club.get("next"):
        n = club["next"]
        lines.append(f"次の試合: {n['date']} {n['time']} {n['round']} {n['opponent']}戦（{'ホーム' if n['home'] else 'アウェイ'}）")
    lines.append("所属選手: " + "、".join(club.get("players", [])))

    def entry(key, i, when):
        index[key] = {"title": i["title"], "url": i["url"], "source": i["source"], "image": i["image"]}
        return f"[{key}] {i['title']}（{i['source']} {i['published'][:when]}{'・写真あり' if i['image'] else ''}）"

    lines.append("\n## ニュース")
    for i, n in enumerate(collected["news"], 1):
        lines.append(entry(f"N{i}", n, 16))

    lines.append("\n## 読み物")
    for i, r in enumerate(collected["reads"], 1):
        lines.append(entry(f"B{i}", r, 10) + f"\n    {r['excerpt']}")

    for name, (prefix, label) in BOARDS.items():
        lines.append(f"\n## {label}")
        for i, p in enumerate(collected["boards"][name], 1):
            index[f"{prefix}{i}"] = {"title": f"{label} {p['no']}", "url": p["url"], "source": label, "image": None}
            lines.append(f"[{prefix}{i}] " + p["text"].replace("\n", " / "))

    if earlier:
        lines.append("\n## 既報")
        for issue in earlier:
            lines += reported(issue)
    return "\n".join(lines), index


def validate(raw, index):
    def clean(topic, kinds=""):
        ids = [i for i in dict.fromkeys(topic["sources"]) if i in index]
        if not ids or (kinds and not any(i[0] in kinds for i in ids)):
            return None
        sources = [index[i] for i in ids[:MAX_LINKS]]
        return {
            **{k: v for k, v in topic.items() if k != "sources"},
            "links": [{k: s[k] for k in ("title", "url", "source")} for s in sources],
            "image": next((s["image"] for s in sources if s["image"]), None),
        }

    def clean_all(topics, kinds=""):
        return [t for t in (clean(t, kinds) for t in topics) if t]

    def urls(topic):
        return {l["url"] for l in topic["links"]} if topic else set()

    top = clean(raw["top"], "NB")
    in_top = urls(top) & {s["url"] for key, s in index.items() if key[0] == "B"}
    reads = [r for r in clean_all(raw["reads"], "B") if not urls(r) & in_top]
    return {
        **EMPTY,
        "top": top,
        "second": clean(raw["second"], "N"),
        "briefs": clean_all(raw["briefs"], "N"),
        "rumors": sorted(clean_all(raw["rumors"]), key=lambda r: -r["confidence"]),
        "boards": clean_all(raw["boards"]),
        "reads": reads[: MAX_READS - bool(in_top)],
        "editorial": raw["editorial"].strip(),
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


def make_digest(collected, date, llm=call_claude, earlier=()):
    if not collected["news"] and not collected["reads"] and not any(collected["boards"].values()):
        return {**EMPTY, "closed": True}
    user, index = build_prompt(collected, date, earlier)
    try:
        return validate(llm(SYSTEM, user), index)
    except Exception as e:
        print(f"LLM failed: {e!r}", file=sys.stderr)
        return {**EMPTY, "links_only": True}
