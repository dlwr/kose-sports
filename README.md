# 小瀬スポーツ

ヴァンフォーレ甲府のニュースと噂を毎朝6時にまとめる、非公式の架空スポーツ紙。<https://kose-sports.yuta25.com>

GitHub Actions が毎朝 `build.py` を動かし、収集 → Claude で紙面化 → `data/YYYY-MM-DD.json` をコミット → GitHub Pages に出す。

```
python -m unittest
python build.py                # 収集して今日の号を作る（ANTHROPIC_API_KEY が必要。無ければ見出しのみの号になる）
python build.py --render-only  # data/ から dist/ を作り直すだけ
```
