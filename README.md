# 日刊小瀬スポーツ

ヴァンフォーレ甲府のニュースと噂を毎朝6時にまとめる、非公式の架空スポーツ紙。<https://kose-sports.yuta25.com>

Cloudflare Worker（`trigger.js`）が毎朝6時に GitHub Actions を起動し、`build.py` が収集 → Claude で紙面化 → `data/YYYY-MM-DD.json` をコミット → GitHub Pages に出す。

```
python -m unittest
python build.py                # 収集して今日の号を作る（ANTHROPIC_API_KEY が必要。無ければ見出しのみの号になる。YOUTUBE_API_KEY が無ければ動画は載らない）
python build.py --render-only  # data/ から dist/ を作り直すだけ
wrangler deploy                # 起動用 Worker を出す（GITHUB_TOKEN は wrangler secret put で入れる。Actions の書き込み権限だけを持つトークン）
```
