import json
import sys
from datetime import datetime
from pathlib import Path

import collect
import digest
import render

DOMAIN = "kose-sports.yuta25.com"
SEEN_ISSUES = 3


def load_issues(data):
    return [json.loads(p.read_text()) for p in sorted(data.glob("*.json"))]


def publish(now, data, collector=collect.collect, llm=digest.call_claude):
    now = now.astimezone(collect.JST)
    day = now.strftime("%Y-%m-%d")
    earlier = [i for i in load_issues(data) if i["date"] < day]
    recent = earlier[-SEEN_ISSUES:]
    seen = {x["url"] for i in recent for x in i["news"] + i["videos"]}
    featured = {
        l["url"] for i in earlier for t in [i["digest"]["top"], *i["digest"].get("reads", [])] if t for l in t["links"]
    }
    got = collector(now, since=earlier[-1].get("collected_at") if earlier else None)
    got["news"] = [n for n in got["news"] if n["url"] not in seen]
    got["videos"] = [v for v in got["videos"] if v["url"] not in seen]
    got["reads"] = [r for r in got["reads"] if r["url"] not in featured]
    summary = digest.make_digest(got, day, llm, recent)
    issue = {
        "date": day,
        "collected_at": now.isoformat(),
        "club": {k: v for k, v in got["club"].items() if k != "players"},
        "digest": summary,
        "news": got["news"],
        "videos": got["videos"],
        "failures": got["failures"] + (["要約"] if summary["links_only"] else []),
    }
    data.mkdir(exist_ok=True)
    (data / f"{day}.json").write_text(json.dumps(issue, ensure_ascii=False, indent=1) + "\n")
    return issue


def build_site(data, dist):
    issues = load_issues(data)
    dist.mkdir(exist_ok=True)
    for i, issue in enumerate(issues):
        prev = issues[i - 1]["date"] if i else None
        next = issues[i + 1]["date"] if i + 1 < len(issues) else None
        page = render.render_issue(issue, prev, next)
        (dist / f"{issue['date']}.html").write_text(page)
        if next is None:
            (dist / "index.html").write_text(page)
    (dist / "CNAME").write_text(DOMAIN + "\n")
    (dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    return len(issues)


def main():
    data, dist = Path("data"), Path("dist")
    if "--render-only" not in sys.argv:
        issue = publish(datetime.now(collect.JST), data)
        print(f"{issue['date']}: {len(issue['news'])} news, failures={issue['failures']}")
    print(f"{build_site(data, dist)} issues rendered")


if __name__ == "__main__":
    main()
