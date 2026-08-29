# AI案件トレンド / AI Jobs Trend

毎週届くAI・データ領域のフリーランス案件メールを解析し、
**市場でいま求められている技術**を時系列で可視化するダッシュボード。

**公開URL**: https://banquetkuma.github.io/AI-Jobs-Trend/

- **今週の特集** (`/`) — 直近配信分の案件ハイライト、今週よく求められた技術、案件一覧
- **トレンド分析** (`/trends.html`) — 全期間の技術推移、業界・ポジション・稼働形態・単価分布、増減ランキング

## 仕組み

```
Gmail (毎週金曜 18:00 JST 配信)
  ↓  ローカルの Claude Code が Gmail コネクタで取得   ← /loop で自動化
data/raw/*.txt            （生メール本文・git管理外）
  ↓  scripts/build.py     （正規表現パース + 辞書ベースの技術抽出。LLM不使用）
data/projects.jsonl       （匿名化済み正規化データ・git管理）
docs/data/*.json          （集計結果）
  ↓  git push
GitHub Pages              （main ブランチの /docs を配信。GitHub Actions は不使用）
```

設計上のポイント:

- **GitHub Actions を使わない。** Pages のソースを `main` の `/docs` にしてあるので、
  push がそのままデプロイになる。CI 側に Gmail の認証情報を置く必要がない。
- **技術抽出は辞書ベース**（`scripts/tech_dict.py`）。決定論的で再現性100%、API課金ゼロ。
  LLM を使うのは「今週の所感」の生成だけ。
- **フロントエンドはビルド不要**。素の HTML + ES modules + 自作SVGチャート。npm 依存も CDN 依存も無い。

## 取り扱い

出典はエッジテクノロジー株式会社 AIソリューション事業部から受信者本人に配信される案件情報メール。
本リポジトリは受信者が個人利用の範囲で統計的に集計したもので、
**案件本文・案件番号・企業名・担当者名は保持も公開もしていない**。

`data/projects.jsonl` が持つのは、案件番号のSHA1先頭12桁（復元不可の識別子）と、
掲載週・ポジション・業界・稼働形態・稼働率・単価・技術タグのみ。
生メール本文を置く `data/raw/` は `.gitignore` で除外している。

## 使い方

### 週次更新（通常運用）

Claude Code のセッションで:

```
/loop /ai-jobs-update
```

インターバルを指定しない動的モードで回す。未処理メールが無い tick は何もせず終了するので、
金曜の配信を1時間以内に検知して取り込み、ページを更新する。
処理済みメールは `data/state.json` で管理しており、
取りこぼしがあっても次回の tick で自動的に追いつく。

### 手動で1回だけ更新

```
/ai-jobs-update
```

### 集計だけ再生成

```bash
python3 scripts/build.py            # docs/data/*.json を書き出す
python3 scripts/build.py --dry-run  # 件数サマリだけ表示
```

### ローカルで表示確認

```bash
python3 -m http.server 8000 --directory docs
# → http://localhost:8000
```

`file://` で直接開くと `fetch` が失敗するので、必ず http サーバー経由で開くこと。

## 技術辞書を育てる

新しい技術名が案件に出てきたら `scripts/tech_dict.py` の `TECHS` に
`(正規化名, カテゴリ, 検出用正規表現)` を1行足して `python3 scripts/build.py` を流し直す。
過去分にも遡って再集計されるため、時系列は常に最新の辞書で一貫する。

短いASCIIトークン（`R`, `Go`, `SQL` など）は誤検出しやすいので、
前後の文字クラスを縛った正規表現にすること（既存エントリが参考になる）。
